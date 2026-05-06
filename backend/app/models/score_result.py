import uuid
from datetime import datetime

from sqlalchemy import String, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ScoreResult(Base):
    __tablename__ = "score_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    generation_result_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("generation_results.id", ondelete="CASCADE"), nullable=False)
    ai_rate_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    creativity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    coherence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    style_match_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    external_ai_rate: Mapped[float] = mapped_column(Float, nullable=True)
    scorer_type: Mapped[str] = mapped_column(String(30), nullable=False, default="llm")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    generation_result = relationship("GenerationResult", back_populates="score_results")
