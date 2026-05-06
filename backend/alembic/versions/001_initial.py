"""initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('genre', sa.String(100), nullable=False),
        sa.Column('style', sa.String(100), nullable=False),
        sa.Column('world_setting', sa.Text(), nullable=False, server_default=''),
        sa.Column('characters', sa.Text(), nullable=False, server_default=''),
        sa.Column('status', sa.String(20), nullable=False, server_default='initialized'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )

    op.create_table(
        'agent_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('prompt_template', sa.Text(), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False, server_default='openai'),
        sa.Column('model', sa.String(100), nullable=False, server_default='gpt-4o-mini'),
        sa.Column('temperature', sa.Float(), nullable=False, server_default='0.7'),
        sa.Column('role_description', sa.Text(), nullable=False, server_default=''),
        sa.Column('is_builtin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )

    op.create_table(
        'tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plot_summary', sa.Text(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='queued'),
        sa.Column('iteration_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_iterations', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('ai_rate_threshold', sa.Float(), nullable=False, server_default='70.0'),
        sa.Column('agent_count', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'generation_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_config_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_configs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('content', sa.Text(), nullable=False, server_default=''),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('generation_time_ms', sa.Integer(), nullable=True),
        sa.Column('iteration', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_edited', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_recommended', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_selected', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )

    op.create_table(
        'score_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('generation_result_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('generation_results.id', ondelete='CASCADE'), nullable=False),
        sa.Column('ai_rate_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('creativity_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('coherence_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('style_match_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('overall_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('external_ai_rate', sa.Float(), nullable=True),
        sa.Column('scorer_type', sa.String(30), nullable=False, server_default='llm'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )

    op.create_table(
        'memories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('category', sa.String(50), nullable=False, server_default='general'),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('source_task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tasks.id', ondelete='SET NULL'), nullable=True),
        sa.Column('is_expired', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('expired_at', sa.DateTime(), nullable=False),
    )

    op.create_index('ix_memories_project_id', 'memories', ['project_id'])
    op.create_index('ix_memories_category', 'memories', ['category'])
    op.execute("CREATE INDEX ix_memories_embedding ON memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)")


def downgrade() -> None:
    op.drop_table('memories')
    op.drop_table('score_results')
    op.drop_table('generation_results')
    op.drop_table('tasks')
    op.drop_table('agent_configs')
    op.drop_table('projects')
    op.execute('DROP EXTENSION IF EXISTS vector')
