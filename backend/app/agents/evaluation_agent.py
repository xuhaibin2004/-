import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

import httpx

from app.agents.provider_manager import provider_manager
from app.core.config import settings

logger = logging.getLogger(__name__)


EVALUATION_PROMPT = """你是一位专业的内容质量评审专家，请对以下文本进行多维度评分。

请严格按照以下JSON格式输出评分结果，不要输出其他内容：
{{
  "ai_rate_score": <0-100的整数，越高越像AI生成，越低越自然>,
  "creativity_score": <0-100的整数，创意性评分>,
  "coherence_score": <0-100的整数，连贯性评分>,
  "style_match_score": <0-100的整数，风格匹配度评分>,
  "overall_score": <0-100的整数，综合评分>,
  "analysis": "<简要分析说明>"
}}

评分标准：
- ai_rate_score: 文本是否像AI生成的？常见AI特征包括：重复句式、过度使用连接词、空洞的总结性语句、缺乏具体细节、语气过于正式或机械。越像AI分数越高，越自然分数越低。
- creativity_score: 内容是否有独特的观点、新颖的表达、出人意料的比喻？
- coherence_score: 逻辑是否通顺、段落衔接是否自然、论证是否有力？
- style_match_score: 内容是否符合预期的风格和题材要求？
- overall_score: 综合考虑所有维度的总体评分。

待评估文本：
---
{content}
---

风格要求：{style}
题材：{genre}
世界观：{world_setting}

请输出JSON格式的评分结果："""


@dataclass
class EvaluationOutput:
    ai_rate_score: float
    creativity_score: float
    coherence_score: float
    style_match_score: float
    overall_score: float
    analysis: str
    external_ai_rate: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None


class EvaluationAgent:
    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
    ):
        self.provider = provider
        self.model = model
        self.temperature = temperature

    def build_prompt(
        self,
        content: str,
        style: str = "",
        genre: str = "",
        world_setting: str = "",
    ) -> str:
        return EVALUATION_PROMPT.format(
            content=content,
            style=style or "无特定风格要求",
            genre=genre or "无特定题材要求",
            world_setting=world_setting or "无特定世界观设定",
        )

    async def evaluate(
        self,
        content: str,
        style: str = "",
        genre: str = "",
        world_setting: str = "",
    ) -> EvaluationOutput:
        prompt = self.build_prompt(content, style, genre, world_setting)
        try:
            result = await provider_manager.generate_with_fallback(
                provider_name=self.provider,
                model=self.model,
                prompt=prompt,
                temperature=self.temperature,
            )
            scores = self._parse_scores(result.content)
            external_ai_rate = await self._get_external_ai_rate(content)
            if external_ai_rate is not None:
                scores["ai_rate_score"] = (
                    scores["ai_rate_score"] * 0.4 + external_ai_rate * 0.6
                )
            return EvaluationOutput(
                ai_rate_score=scores["ai_rate_score"],
                creativity_score=scores["creativity_score"],
                coherence_score=scores["coherence_score"],
                style_match_score=scores["style_match_score"],
                overall_score=scores["overall_score"],
                analysis=scores.get("analysis", ""),
                external_ai_rate=external_ai_rate,
            )
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return EvaluationOutput(
                ai_rate_score=50.0,
                creativity_score=50.0,
                coherence_score=50.0,
                style_match_score=50.0,
                overall_score=50.0,
                analysis="",
                error_message=str(e),
                success=False,
            )

    def _parse_scores(self, content: str) -> dict:
        try:
            json_match = re.search(r'\{[^{}]+\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    "ai_rate_score": float(data.get("ai_rate_score", 50)),
                    "creativity_score": float(data.get("creativity_score", 50)),
                    "coherence_score": float(data.get("coherence_score", 50)),
                    "style_match_score": float(data.get("style_match_score", 50)),
                    "overall_score": float(data.get("overall_score", 50)),
                    "analysis": data.get("analysis", ""),
                }
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse evaluation scores: {e}")
        return {
            "ai_rate_score": 50.0,
            "creativity_score": 50.0,
            "coherence_score": 50.0,
            "style_match_score": 50.0,
            "overall_score": 50.0,
            "analysis": "",
        }

    async def _get_external_ai_rate(self, content: str) -> Optional[float]:
        if not settings.GPTZERO_API_KEY:
            return None
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.gptzero.me/v2/predict/text",
                    headers={"x-api-key": settings.GPTZERO_API_KEY, "Content-Type": "application/json"},
                    json={"document": content},
                )
                if response.status_code == 200:
                    data = response.json()
                    documents = data.get("documents", [])
                    if documents:
                        avg_prob = documents[0].get("average_generated_prob", 0.0)
                        return avg_prob * 100
            return None
        except Exception as e:
            logger.warning(f"GPTZero API call failed: {e}")
            return None
