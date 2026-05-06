from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.llm_config import LLMProviderConfig
from app.schemas.llm_config import (
    LLMConfigCreate,
    LLMConfigUpdate,
    LLMConfigResponse,
    LLMConfigBrief,
    mask_api_key,
)
from app.agents.provider_manager import provider_manager

router = APIRouter()


@router.get("", response_model=list[LLMConfigResponse])
async def list_llm_configs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LLMProviderConfig).order_by(LLMProviderConfig.created_at.desc()))
    configs = list(result.scalars().all())
    for config in configs:
        config.api_key = mask_api_key(config.api_key)
    return configs


@router.get("/brief", response_model=list[LLMConfigBrief])
async def list_llm_configs_brief(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(LLMProviderConfig)
        .where(LLMProviderConfig.is_active == True)
        .order_by(LLMProviderConfig.name)
    )
    return list(result.scalars().all())


@router.get("/{config_id}", response_model=LLMConfigResponse)
async def get_llm_config(config_id: UUID, db: AsyncSession = Depends(get_db)):
    config = await db.get(LLMProviderConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="LLM config not found")
    config.api_key = mask_api_key(config.api_key)
    return config


@router.post("", response_model=LLMConfigResponse, status_code=201)
async def create_llm_config(data: LLMConfigCreate, db: AsyncSession = Depends(get_db)):
    config = LLMProviderConfig(**data.model_dump())
    db.add(config)
    await db.commit()
    await db.refresh(config)
    config.api_key = mask_api_key(config.api_key)
    return config


@router.put("/{config_id}", response_model=LLMConfigResponse)
async def update_llm_config(config_id: UUID, data: LLMConfigUpdate, db: AsyncSession = Depends(get_db)):
    config = await db.get(LLMProviderConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="LLM config not found")
    update_data = data.model_dump(exclude_unset=True)
    if "api_key" in update_data and update_data["api_key"] and "***" in update_data["api_key"]:
        del update_data["api_key"]
    for key, value in update_data.items():
        setattr(config, key, value)
    await db.commit()
    await db.refresh(config)
    provider_manager.clear_cache()
    config.api_key = mask_api_key(config.api_key)
    return config


@router.delete("/{config_id}", status_code=204)
async def delete_llm_config(config_id: UUID, db: AsyncSession = Depends(get_db)):
    config = await db.get(LLMProviderConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="LLM config not found")
    await db.delete(config)
    await db.commit()
    provider_manager.clear_cache()


@router.post("/{config_id}/test")
async def test_llm_config(config_id: UUID, db: AsyncSession = Depends(get_db)):
    config = await db.get(LLMProviderConfig, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="LLM config not found")
    if not config.is_active:
        raise HTTPException(status_code=400, detail="Config is not active")
    try:
        model = config.available_models[0] if config.available_models else "gpt-4o-mini"
        result = await provider_manager.generate_from_config(
            provider_type=config.provider_type,
            model=model,
            api_key=config.api_key,
            base_url=config.base_url,
            prompt="Say 'Hello' in one word.",
            temperature=0.0,
            max_tokens=10,
        )
        return {"success": True, "model": result.model, "response_preview": result.content[:100]}
    except Exception as e:
        return {"success": False, "error": str(e)}
