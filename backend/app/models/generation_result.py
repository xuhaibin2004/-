import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class GenerationResult(Base):
    __tablename__ = "generation_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    agent_config_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_configs.id", ondelete="SET NULL"), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    generation_time_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    iteration: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_edited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_recommended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    task = relationship("Task", back_populates="generation_results")
    agent_config = relationship("AgentConfig", back_populates="generation_results")
    score_results = relationship("ScoreResult", back_populates="generation_result", cascade="all, delete-orphan")
