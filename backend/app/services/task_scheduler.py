import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.core.redis import redis_client, STREAM_KEY, STREAM_GROUP, STATUS_CHANNEL, publish_task_status
from app.models.task import Task
from app.models.project import Project
from app.models.agent_config import AgentConfig
from app.models.llm_config import LLMProviderConfig
from app.models.tool_definition import ToolDefinition
from app.models.generation_result import GenerationResult
from app.models.score_result import ScoreResult
from app.agents.generation_agent import GenerationAgent, create_diverse_agents
from app.agents.evaluation_agent import EvaluationAgent
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)


class TaskScheduler:
    def __init__(self):
        self.evaluation_agent = EvaluationAgent()

    async def run_task(self, task_id: uuid.UUID):
        async with AsyncSessionLocal() as db:
            try:
                task = await db.get(Task, task_id)
                if not task:
                    logger.error(f"Task {task_id} not found")
                    return

                project = await db.get(Project, task.project_id)
                if not project:
                    logger.error(f"Project {task.project_id} not found")
                    return

                await self._update_task_status(db, task, "generating")
                await publish_task_status(str(task_id), "generating")

                result = await db.execute(
                    select(AgentConfig).where(AgentConfig.project_id == task.project_id)
                )
                agent_configs = list(result.scalars().all())

                if not agent_configs:
                    await self._update_task_status(db, task, "failed")
                    await publish_task_status(str(task_id), "failed", {"error": "No agent configs found"})
                    return

                llm_configs_cache = {}
                for ac in agent_configs:
                    if ac.llm_config_id and ac.llm_config_id not in llm_configs_cache:
                        llm_config = await db.get(LLMProviderConfig, ac.llm_config_id)
                        llm_configs_cache[ac.llm_config_id] = llm_config

                tool_defs_cache = {}
                for ac in agent_configs:
                    if ac.tools:
                        for tool_name in ac.tools:
                            if tool_name not in tool_defs_cache:
                                tresult = await db.execute(
                                    select(ToolDefinition).where(
                                        ToolDefinition.name == tool_name,
                                        ToolDefinition.is_active == True,
                                    )
                                )
                                tdef = tresult.scalars().first()
                                if tdef:
                                    tool_defs_cache[tool_name] = tdef

                memory_service = MemoryService(db)
                memories = await memory_service.search_memories(task.project_id, task.plot_summary)
                memory_context = "\n".join([f"- {m.content}" for m in memories])

                for iteration in range(task.max_iterations + 1):
                    task.iteration_count = iteration
                    await db.commit()

                    feedback = ""
                    if iteration > 0:
                        prev_results = await db.execute(
                            select(GenerationResult).where(
                                GenerationResult.task_id == task_id,
                                GenerationResult.iteration == iteration - 1,
                            )
                        )
                        prev_gen_results = list(prev_results.scalars().all())
                        if prev_gen_results:
                            worst = min(prev_gen_results, key=lambda r: r.score_results[0].overall_score if r.score_results else 0) if prev_gen_results else None
                            if worst and worst.score_results:
                                score = worst.score_results[0]
                                feedback = f"上一轮评分最低的结果分析：AI率={score.ai_rate_score:.1f}, 创意性={score.creativity_score:.1f}, 连贯性={score.coherence_score:.1f}, 风格匹配={score.style_match_score:.1f}。请避免上述问题，努力降低AI率，提升自然度。"

                    gen_results = await self._run_generation(
                        db, task, agent_configs, llm_configs_cache, tool_defs_cache,
                        memory_context, project, iteration, feedback
                    )

                    await self._update_task_status(db, task, "evaluating")
                    await publish_task_status(str(task_id), "evaluating", {"iteration": str(iteration)})

                    await self._run_evaluation(db, gen_results, project)

                    best_result = await self._get_best_result(db, task_id, iteration)
                    if best_result and best_result.score_results:
                        best_score = best_result.score_results[0]
                        if best_score.ai_rate_score < task.ai_rate_threshold:
                            best_result.is_recommended = True
                            await db.commit()
                            await self._update_task_status(db, task, "pending_review")
                            await publish_task_status(str(task_id), "pending_review", {"iteration": str(iteration)})
                            return

                best_overall = await self._get_best_result_across_iterations(db, task_id)
                if best_overall:
                    best_overall.is_recommended = True
                    await db.commit()

                await self._update_task_status(db, task, "pending_review")
                await publish_task_status(str(task_id), "pending_review", {"iteration": str(task.iteration_count)})

            except Exception as e:
                logger.error(f"Task {task_id} failed: {e}", exc_info=True)
                async with AsyncSessionLocal() as error_db:
                    error_task = await error_db.get(Task, task_id)
                    if error_task:
                        error_task.status = "failed"
                        await error_db.commit()
                await publish_task_status(str(task_id), "failed", {"error": str(e)})

    async def _run_generation(
        self,
        db: AsyncSession,
        task: Task,
        agent_configs: list[AgentConfig],
        llm_configs_cache: dict,
        tool_defs_cache: dict,
        memory_context: str,
        project: Project,
        iteration: int,
        feedback: str,
    ) -> list[GenerationResult]:
        config_dicts = []
        for ac in agent_configs:
            llm_config = llm_configs_cache.get(ac.llm_config_id) if ac.llm_config_id else None
            agent_tool_defs = [tool_defs_cache[t] for t in (ac.tools or []) if t in tool_defs_cache]
            config_dicts.append({
                "name": ac.name,
                "prompt_template": ac.prompt_template,
                "provider": llm_config.provider_type if llm_config else ac.provider,
                "model": ac.model,
                "temperature": ac.temperature,
                "role_description": ac.role_description,
                "llm_config_id": str(ac.llm_config_id) if ac.llm_config_id else None,
                "api_key": llm_config.api_key if llm_config else "",
                "base_url": llm_config.base_url if llm_config else "",
                "tools": ac.tools or [],
                "tool_definitions": agent_tool_defs,
                "enable_streaming": ac.enable_streaming,
                "db": db,
                "project_id": str(task.project_id),
            })
        agents = create_diverse_agents(config_dicts)

        gen_coroutines = []
        for agent in agents:
            prompt = agent.build_prompt(
                plot_summary=task.plot_summary,
                memory_context=memory_context,
                world_setting=project.world_setting,
                characters=project.characters,
                style=project.style,
                genre=project.genre,
                feedback=feedback,
            )
            gen_coroutines.append(agent.generate(prompt))

        outputs = await asyncio.gather(*gen_coroutines, return_exceptions=True)

        results = []
        for i, output in enumerate(outputs):
            agent_config = agent_configs[i] if i < len(agent_configs) else None
            if isinstance(output, Exception):
                gen_result = GenerationResult(
                    task_id=task.id,
                    agent_config_id=agent_config.id if agent_config else None,
                    content="",
                    status="failed",
                    error_message=str(output),
                    iteration=iteration,
                )
            elif output.success:
                gen_result = GenerationResult(
                    task_id=task.id,
                    agent_config_id=agent_config.id if agent_config else None,
                    content=output.content,
                    status="completed",
                    generation_time_ms=output.generation_time_ms,
                    iteration=iteration,
                )
            else:
                gen_result = GenerationResult(
                    task_id=task.id,
                    agent_config_id=agent_config.id if agent_config else None,
                    content="",
                    status="timeout" if "timed out" in (output.error_message or "") else "failed",
                    error_message=output.error_message,
                    generation_time_ms=output.generation_time_ms,
                    iteration=iteration,
                )
            db.add(gen_result)
            results.append(gen_result)

        await db.commit()
        for r in results:
            await db.refresh(r)
        return results

    async def _run_evaluation(
        self,
        db: AsyncSession,
        gen_results: list[GenerationResult],
        project: Project,
    ):
        eval_coroutines = []
        valid_results = [gr for gr in gen_results if gr.status == "completed" and gr.content]

        for gr in valid_results:
            eval_coroutines.append(
                self.evaluation_agent.evaluate(
                    content=gr.content,
                    style=project.style,
                    genre=project.genre,
                    world_setting=project.world_setting,
                )
            )

        if not eval_coroutines:
            return

        eval_outputs = await asyncio.gather(*eval_coroutines, return_exceptions=True)

        for i, output in enumerate(eval_outputs):
            gr = valid_results[i]
            if isinstance(output, Exception):
                score = ScoreResult(
                    generation_result_id=gr.id,
                    ai_rate_score=50.0,
                    creativity_score=50.0,
                    coherence_score=50.0,
                    style_match_score=50.0,
                    overall_score=50.0,
                    scorer_type="llm",
                )
            else:
                score = ScoreResult(
                    generation_result_id=gr.id,
                    ai_rate_score=output.ai_rate_score,
                    creativity_score=output.creativity_score,
                    coherence_score=output.coherence_score,
                    style_match_score=output.style_match_score,
                    overall_score=output.overall_score,
                    external_ai_rate=output.external_ai_rate,
                    scorer_type="llm",
                )
            db.add(score)

        await db.commit()

    async def _get_best_result(self, db: AsyncSession, task_id: uuid.UUID, iteration: int) -> Optional[GenerationResult]:
        result = await db.execute(
            select(GenerationResult)
            .where(GenerationResult.task_id == task_id, GenerationResult.iteration == iteration, GenerationResult.status == "completed")
        )
        gen_results = list(result.scalars().all())
        if not gen_results:
            return None
        best = None
        best_ai_rate = float("inf")
        for gr in gen_results:
            scores = [s for s in gr.score_results if s.ai_rate_score < best_ai_rate]
            if scores:
                best_ai_rate = scores[0].ai_rate_score
                best = gr
        return best

    async def _get_best_result_across_iterations(self, db: AsyncSession, task_id: uuid.UUID) -> Optional[GenerationResult]:
        result = await db.execute(
            select(GenerationResult)
            .where(GenerationResult.task_id == task_id, GenerationResult.status == "completed")
        )
        gen_results = list(result.scalars().all())
        if not gen_results:
            return None
        best = None
        best_ai_rate = float("inf")
        for gr in gen_results:
            for s in gr.score_results:
                if s.ai_rate_score < best_ai_rate:
                    best_ai_rate = s.ai_rate_score
                    best = gr
        return best

    async def _update_task_status(self, db: AsyncSession, task: Task, status: str):
        task.status = status
        if status == "completed":
            task.completed_at = datetime.utcnow()
        await db.commit()


task_scheduler = TaskScheduler()
