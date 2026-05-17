"""add llm_provider_configs, tool_definitions, and agent_config extensions

Revision ID: 002
Revises: 001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_provider_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("provider_type", sa.String(50), nullable=False),
        sa.Column("api_key", sa.Text, nullable=False, server_default=""),
        sa.Column("base_url", sa.String(500), nullable=False, server_default=""),
        sa.Column("available_models", JSON, nullable=False, server_default="[]"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "tool_definitions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("parameters_schema", JSON, nullable=False, server_default="{}"),
        sa.Column("implementation_type", sa.String(30), nullable=False, server_default="builtin"),
        sa.Column("implementation_config", JSON, nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.add_column("agent_configs", sa.Column("llm_config_id", UUID(as_uuid=True), sa.ForeignKey("llm_provider_configs.id", ondelete="SET NULL"), nullable=True))
    op.add_column("agent_configs", sa.Column("tools", JSON, nullable=False, server_default="[]"))
    op.add_column("agent_configs", sa.Column("enable_streaming", sa.Boolean, nullable=False, server_default="false"))

    op.execute("""
        INSERT INTO tool_definitions (id, name, description, parameters_schema, implementation_type, implementation_config, is_active)
        VALUES
            (gen_random_uuid(), 'web_search', '搜索互联网获取信息',
             '{"type": "object", "properties": {"query": {"type": "string", "description": "搜索关键词"}}, "required": ["query"]}',
             'builtin', '{}', true),
            (gen_random_uuid(), 'knowledge_query', '从项目知识库中检索相关信息',
             '{"type": "object", "properties": {"query": {"type": "string", "description": "查询内容"}, "project_id": {"type": "string", "description": "项目ID"}}, "required": ["query"]}',
             'builtin', '{}', true),
            (gen_random_uuid(), 'time_query', '获取当前日期时间',
             '{"type": "object", "properties": {"timezone_name": {"type": "string", "description": "时区名称，如 Asia/Shanghai"}}}',
             'builtin', '{}', true)
    """)


def downgrade() -> None:
    op.drop_column("agent_configs", "enable_streaming")
    op.drop_column("agent_configs", "tools")
    op.drop_column("agent_configs", "llm_config_id")
    op.drop_table("tool_definitions")
    op.drop_table("llm_provider_configs")
