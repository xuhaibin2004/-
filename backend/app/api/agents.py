from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.agent_config import AgentConfig
from app.models.project import Project
from app.schemas.agent import AgentCreate, AgentUpdate, AgentResponse

router = APIRouter()

BUILTIN_TEMPLATES = [
    {
        "name": "文学风格",
        "prompt_template": "你是一位资深文学创作者，擅长用细腻的笔触描绘场景和情感。请根据以下剧情概要，创作一段富有文学性的正文内容。要求：语言优美流畅，善用比喻和意象，避免AI常见的重复句式和空洞表达。\n\n剧情概要：{plot_summary}\n\n相关经验：{memory_context}",
        "provider": "openai",
        "model": "gpt-4o",
        "temperature": 0.8,
        "role_description": "资深文学创作者，追求语言的艺术性和感染力",
    },
    {
        "name": "口语风格",
        "prompt_template": "你是一位擅长口语化表达的创作者，文字自然亲切如同面对面讲述。请根据以下剧情概要，创作一段口语化的正文内容。要求：用词接地气，句式短促有力，避免书面语和AI腔调，像真人在讲故事。\n\n剧情概要：{plot_summary}\n\n相关经验：{memory_context}",
        "provider": "openai",
        "model": "gpt-4o",
        "temperature": 0.9,
        "role_description": "口语化叙事高手，文字自然不做作",
    },
    {
        "name": "叙事风格",
        "prompt_template": "你是一位精通叙事技巧的创作者，擅长构建紧凑的情节推进和悬念。请根据以下剧情概要，创作一段叙事性强的正文内容。要求：节奏明快，场景切换自然，对话生动，避免AI常见的平铺直叙和过度解释。\n\n剧情概要：{plot_summary}\n\n相关经验：{memory_context}",
        "provider": "openai",
        "model": "gpt-4o",
        "temperature": 0.7,
        "role_description": "叙事高手，擅长情节推进和悬念营造",
    },
    {
        "name": "深度风格",
        "prompt_template": "你是一位善于深度思考的创作者，文字富有哲理和内涵。请根据以下剧情概要，创作一段有深度的正文内容。要求：思考深入但不晦涩，观点独到但不偏激，语言精炼有力，避免AI常见的浅层归纳和泛泛而谈。\n\n剧情概要：{plot_summary}\n\n相关经验：{memory_context}",
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "temperature": 0.6,
        "role_description": "深度思考者，文字富有哲理和内涵",
    },
    {
        "name": "轻快风格",
        "prompt_template": "你是一位风格轻快的创作者，文字活泼有趣。请根据以下剧情概要，创作一段轻松愉快的正文内容。要求：语气轻松，善用幽默和反差，避免AI常见的严肃说教和刻板表达。\n\n剧情概要：{plot_summary}\n\n相关经验：{memory_context}",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "temperature": 1.0,
        "role_description": "轻松幽默的创作者，文字活泼有趣",
    },
]


@router.post("/projects/{project_id}/agents", response_model=AgentResponse, status_code=201)
async def create_agent(project_id: UUID, data: AgentCreate, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    agent = AgentConfig(project_id=project_id, **data.model_dump())
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.get("/projects/{project_id}/agents", response_model=list[AgentResponse])
async def list_agents(project_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentConfig).where(AgentConfig.project_id == project_id))
    return list(result.scalars().all())


@router.put("/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: UUID, data: AgentUpdate, db: AsyncSession = Depends(get_db)):
    agent = await db.get(AgentConfig, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent config not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(agent, key, value)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.delete("/agents/{agent_id}", status_code=204)
async def delete_agent(agent_id: UUID, db: AsyncSession = Depends(get_db)):
    agent = await db.get(AgentConfig, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent config not found")
    await db.delete(agent)
    await db.commit()


@router.post("/projects/{project_id}/agents/init-templates", response_model=list[AgentResponse], status_code=201)
async def init_builtin_templates(project_id: UUID, db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    agents = []
    for tpl in BUILTIN_TEMPLATES:
        agent = AgentConfig(project_id=project_id, is_builtin=True, **tpl)
        db.add(agent)
        agents.append(agent)
    await db.commit()
    for a in agents:
        await db.refresh(a)
    return agents
