# LLM 大模型前端配置化 & 流式输出 & Tool Calling 实施计划

## 概述

将 LLM Provider 从硬编码环境变量改为前端可配置的全局管理，支持多模型配置、OpenAI 兼容格式（覆盖 Gemini/DeepSeek 等）、SSE 流式输出、完整 Tool Calling 链路。

## 当前状态分析

| 维度 | 现状 | 目标 |
|------|------|------|
| Provider 配置 | 硬编码在 `provider_manager.py` 的 `PROVIDER_CONFIGS`，API Key 来自环境变量 | 数据库存储，前端 CRUD 管理 |
| Provider 类型 | 仅 openai / anthropic | 增加 openai_compatible（兼容 Gemini/DeepSeek 等） |
| 流式输出 | `stream_generate` 方法存在但从未调用，无 API 端点 | SSE 端点 + 前端实时预览 + Worker 流式处理 |
| Tool Calling | MCPSandbox 存在但未与 LLM 集成 | 完整链路：定义→LLM 调用→执行→结果回传 |
| Agent 配置 | provider/model 手动输入，API Key 全局共享 | 从已有 LLM 配置中选择，支持工具绑定 |

## 实施步骤

### Step 1: 数据库模型 — 新增 LLMProviderConfig 和 ToolDefinition

**文件: `backend/app/models/llm_config.py`** (新建)

```python
class LLMProviderConfig(Base):
    __tablename__ = "llm_provider_configs"

    id: UUID PK
    name: String(200)          # 配置名称，如 "OpenAI GPT-4o"
    provider_type: String(50)  # "openai" | "anthropic" | "openai_compatible"
    api_key: Text              # 加密存储，API Key
    base_url: String(500)      # 自定义 Base URL（OpenAI 兼容模式必填）
    available_models: JSON     # 可用模型列表，如 ["gpt-4o", "gpt-4o-mini"]
    is_active: Boolean         # 是否启用
    created_at: DateTime
    updated_at: DateTime
```

**文件: `backend/app/models/tool_definition.py`** (新建)

```python
class ToolDefinition(Base):
    __tablename__ = "tool_definitions"

    id: UUID PK
    name: String(100)              # 工具名称，如 "web_search"
    description: Text              # 工具描述（给 LLM 看）
    parameters_schema: JSON        # JSON Schema 格式的参数定义
    implementation_type: String(30) # "builtin" | "custom"
    implementation_config: JSON    # 实现配置（如 API endpoint 等）
    is_active: Boolean
    created_at: DateTime
```

**文件: `backend/app/models/agent_config.py`** (修改)

- 新增字段 `llm_config_id`: FK → `llm_provider_configs.id`，可为 NULL（兼容旧数据）
- 新增字段 `tools`: JSON，存储绑定的工具名称列表，如 `["web_search", "knowledge_query"]`
- 新增字段 `enable_streaming`: Boolean, default=False
- 保留 `provider` 和 `model` 字段，但当 `llm_config_id` 存在时从中获取

**文件: `backend/alembic/versions/002_llm_config_and_tools.py`** (新建)

- 创建 `llm_provider_configs` 表
- 创建 `tool_definitions` 表
- `agent_configs` 表新增 `llm_config_id`、`tools`、`enable_streaming` 列
- 插入内置工具定义（web_search, knowledge_query, time_query）

### Step 2: Provider 系统重构 — 支持 OpenAI 兼容模式 & Tool Calling

**文件: `backend/app/agents/providers/base.py`** (修改)

- `GenerateResult` 新增 `tool_calls` 字段（list[dict]）
- `LLMProvider` 新增方法:
  - `generate_with_tools(prompt, tools, temperature, max_tokens) -> GenerateResult`
  - `stream_generate(prompt, temperature, max_tokens) -> AsyncIterator[str]`（已有）
  - `stream_generate_with_tools(prompt, tools, temperature, max_tokens) -> AsyncIterator[dict]`（流式 chunk，包含 content 和 tool_call 事件）

**文件: `backend/app/agents/providers/openai_provider.py`** (修改)

- 实现 `generate_with_tools`: 传入 `tools` 参数调用 `chat.completions.create`
- 实现 `stream_generate_with_tools`: 流式版本，yield `{"type": "content", "data": "..."}` 或 `{"type": "tool_call", "data": {...}}`
- 处理 OpenAI tool_calls 响应格式

**文件: `backend/app/agents/providers/anthropic_provider.py`** (修改)

- 实现 `generate_with_tools`: 传入 `tools` 参数调用 `messages.create`
- 实现 `stream_generate_with_tools`: 流式版本
- 处理 Anthropic tool_use 响应格式（转换为统一格式）

**文件: `backend/app/agents/providers/openai_compatible_provider.py`** (新建)

- 继承 `OpenAIProvider`，复用 OpenAI SDK
- 默认 `provider_type = "openai_compatible"`
- 用于 Gemini（OpenAI 兼容端点）、DeepSeek、Ollama 等
- `base_url` 为必填项

**文件: `backend/app/agents/providers/__init__.py`** (修改)

- `PROVIDER_REGISTRY` 新增 `"openai_compatible": OpenAICompatibleProvider`

### Step 3: ProviderManager 重构 — 从数据库读取配置

**文件: `backend/app/agents/provider_manager.py`** (重写)

- 移除硬编码 `PROVIDER_CONFIGS` 和 `FALLBACK_ORDER`
- `get_provider_from_config(config: LLMProviderConfig, model: str) -> LLMProvider`: 从数据库配置创建 Provider
- `generate_with_fallback` 改为接受 `llm_config_id`，从数据库读取配置
- 保留缓存机制，但缓存 key 改为 `config_id:model`
- 新增 `generate_stream_with_fallback` 和 `generate_with_tools_fallback`

### Step 4: Tool Calling 执行引擎

**文件: `backend/app/agents/tool_executor.py`** (新建)

```python
class ToolExecutor:
    def __init__(self, tool_definitions: list[ToolDefinition]):
        self.tools = {t.name: t for t in tool_definitions}
        self._builtin_implementations = {
            "web_search": self._web_search,
            "knowledge_query": self._knowledge_query,
            "time_query": self._time_query,
        }

    async def execute(self, tool_name: str, arguments: dict) -> str:
        # 查找工具定义 → 执行 → 返回结果字符串

    async def _web_search(self, query: str) -> str: ...
    async def _knowledge_query(self, query: str, project_id: str) -> str: ...
    async def _time_query(self) -> str: ...

    def get_tools_for_llm(self) -> list[dict]:
        # 转换为 LLM API 需要的 tools 格式
```

**文件: `backend/app/agents/tool_calling_loop.py`** (新建)

```python
async def run_with_tools(
    provider: LLMProvider,
    prompt: str,
    tools: list[dict],
    tool_executor: ToolExecutor,
    max_rounds: int = 5,
    temperature: float = 0.7,
) -> GenerateResult:
    """
    Tool Calling 循环：
    1. 发送 prompt + tools 给 LLM
    2. 如果 LLM 返回 tool_calls → 执行工具 → 将结果追加到消息 → 再次调用 LLM
    3. 重复直到 LLM 不再调用工具或达到 max_rounds
    4. 返回最终 GenerateResult
    """
```

### Step 5: 后端 API — LLM 配置管理 & 流式端点 & 工具管理

**文件: `backend/app/schemas/llm_config.py`** (新建)

- `LLMConfigCreate`: name, provider_type, api_key, base_url?, available_models, is_active
- `LLMConfigUpdate`: 同上但全部 Optional
- `LLMConfigResponse`: 脱敏展示（api_key 显示为 `sk-***abc`）
- `LLMConfigBrief`: id, name, provider_type, available_models（Agent 配置页下拉选择用）

**文件: `backend/app/schemas/tool.py`** (新建)

- `ToolDefinitionCreate/Update/Response`

**文件: `backend/app/api/llm_configs.py`** (新建)

- `GET /api/llm-configs` — 列表
- `POST /api/llm-configs` — 创建（含 API Key）
- `GET /api/llm-configs/{id}` — 详情
- `PUT /api/llm-configs/{id}` — 更新
- `DELETE /api/llm-configs/{id}` — 删除
- `POST /api/llm-configs/{id}/test` — 测试连接（发送简单 prompt 验证配置正确性）
- `GET /api/llm-configs/brief` — 精简列表（Agent 配置页用）

**文件: `backend/app/api/tools.py`** (新建)

- `GET /api/tools` — 列表
- `POST /api/tools` — 创建
- `PUT /api/tools/{id}` — 更新
- `DELETE /api/tools/{id}` — 删除

**文件: `backend/app/api/stream.py`** (新建)

- `GET /api/stream/generate` — SSE 流式生成端点
  - 参数: agent_config_id, prompt, project_id
  - 返回: `text/event-stream`，每个事件包含 `{"type": "content"|"tool_call"|"done"|"error", "data": ...}`

**文件: `backend/app/schemas/agent.py`** (修改)

- `AgentCreate/Update` 新增 `llm_config_id?`, `tools?`, `enable_streaming?`
- `AgentResponse` 新增对应字段

**文件: `backend/app/main.py`** (修改)

- 注册新路由: `llm_configs`, `tools`, `stream`

### Step 6: GenerationAgent & TaskScheduler 适配

**文件: `backend/app/agents/generation_agent.py`** (修改)

- `generate` 方法支持 `llm_config_id`，从数据库获取 Provider 配置
- 新增 `generate_stream` 方法，yield 流式 chunk
- 新增 `generate_with_tools` 方法，调用 `tool_calling_loop.run_with_tools`
- `build_prompt` 保持不变

**文件: `backend/app/agents/evaluation_agent.py`** (修改)

- 支持从 `llm_config_id` 获取 Provider 配置

**文件: `backend/app/services/task_scheduler.py`** (修改)

- `_run_generation` 中根据 `agent_config.llm_config_id` 获取 Provider
- 如果 `agent_config.tools` 非空，走 tool calling 路径
- 如果 `agent_config.enable_streaming`，通过 Redis Pub/Sub 推送流式 chunk

### Step 7: 前端 — LLM 配置管理页

**文件: `frontend/src/api/llmConfigs.ts`** (新建)

- CRUD API 调用 + 测试连接接口

**文件: `frontend/src/views/LLMConfigList.vue`** (新建)

- LLM 配置列表页，展示所有 Provider 配置
- 每行显示: 名称、类型、模型列表、状态、操作
- 支持添加/编辑/删除/测试连接
- 编辑对话框: 名称、Provider 类型（下拉）、API Key（密码输入框，编辑时显示脱敏值）、Base URL、可用模型（动态增删）

**文件: `frontend/src/views/ToolManagement.vue`** (新建)

- 工具定义管理页
- 展示内置工具和自定义工具
- 支持创建自定义工具（名称、描述、参数 Schema）

**文件: `frontend/src/router/index.ts`** (修改)

- 新增 `/llm-configs` 路由 → `LLMConfigList.vue`
- 新增 `/tools` 路由 → `ToolManagement.vue`

**文件: `frontend/src/views/AgentConfig.vue`** (修改)

- Provider 选择改为从 LLM 配置下拉选择（`llm_config_id`）
- 选择 LLM 配置后，模型下拉自动填充该配置的 `available_models`
- 新增"工具绑定"多选框（从已定义的工具中选择）
- 新增"启用流式输出"开关

### Step 8: 前端 — 流式输出组件

**文件: `frontend/src/components/StreamPreview.vue`** (新建)

- SSE 连接组件，接收 `agent_config_id` 和 `prompt`
- 通过 `EventSource` 连接 `/api/stream/generate`
- 实时展示生成内容（逐字输出效果）
- 展示 tool calling 过程（如"正在搜索..."、"正在查询知识库..."）
- 支持停止生成

**文件: `frontend/src/views/TaskMonitor.vue`** (修改)

- 集成 `StreamPreview` 组件
- 当 Agent 启用流式输出时，实时展示生成过程

**文件: `frontend/src/views/TaskReview.vue`** (修改)

- 在审核页面增加"重新生成（流式）"按钮
- 点击后弹出流式预览对话框

### Step 9: 数据库迁移 & 种子数据

**文件: `backend/alembic/versions/002_llm_config_and_tools.py`** (新建)

- 创建 `llm_provider_configs` 表
- 创建 `tool_definitions` 表
- `agent_configs` 新增列
- 插入内置工具种子数据:
  - `web_search`: 参数 `{query: string}`, 描述"搜索互联网获取信息"
  - `knowledge_query`: 参数 `{query: string, project_id: string}`, 描述"从项目知识库中检索相关信息"
  - `time_query`: 参数 `{timezone?: string}`, 描述"获取当前日期时间"

### Step 10: 测试

**文件: `backend/tests/test_llm_config_api.py`** (新建)

- LLM 配置 CRUD 测试
- API Key 脱敏测试
- 连接测试

**文件: `backend/tests/test_tool_calling.py`** (新建)

- Tool Executor 单元测试
- Tool Calling Loop 测试（mock provider）
- 内置工具测试

**文件: `backend/tests/test_stream.py`** (新建)

- SSE 端点测试
- 流式输出格式验证

## 文件变更清单

| 操作 | 文件路径 |
|------|---------|
| 新建 | `backend/app/models/llm_config.py` |
| 新建 | `backend/app/models/tool_definition.py` |
| 修改 | `backend/app/models/agent_config.py` |
| 修改 | `backend/app/models/__init__.py` |
| 新建 | `backend/app/schemas/llm_config.py` |
| 新建 | `backend/app/schemas/tool.py` |
| 修改 | `backend/app/schemas/agent.py` |
| 新建 | `backend/app/api/llm_configs.py` |
| 新建 | `backend/app/api/tools.py` |
| 新建 | `backend/app/api/stream.py` |
| 修改 | `backend/app/api/agents.py` |
| 修改 | `backend/app/main.py` |
| 修改 | `backend/app/agents/providers/base.py` |
| 修改 | `backend/app/agents/providers/openai_provider.py` |
| 修改 | `backend/app/agents/providers/anthropic_provider.py` |
| 新建 | `backend/app/agents/providers/openai_compatible_provider.py` |
| 修改 | `backend/app/agents/providers/__init__.py` |
| 重写 | `backend/app/agents/provider_manager.py` |
| 新建 | `backend/app/agents/tool_executor.py` |
| 新建 | `backend/app/agents/tool_calling_loop.py` |
| 修改 | `backend/app/agents/generation_agent.py` |
| 修改 | `backend/app/agents/evaluation_agent.py` |
| 修改 | `backend/app/services/task_scheduler.py` |
| 新建 | `backend/alembic/versions/002_llm_config_and_tools.py` |
| 新建 | `backend/tests/test_llm_config_api.py` |
| 新建 | `backend/tests/test_tool_calling.py` |
| 新建 | `backend/tests/test_stream.py` |
| 新建 | `frontend/src/api/llmConfigs.ts` |
| 新建 | `frontend/src/api/tools.ts` |
| 新建 | `frontend/src/views/LLMConfigList.vue` |
| 新建 | `frontend/src/views/ToolManagement.vue` |
| 新建 | `frontend/src/components/StreamPreview.vue` |
| 修改 | `frontend/src/views/AgentConfig.vue` |
| 修改 | `frontend/src/views/TaskMonitor.vue` |
| 修改 | `frontend/src/views/TaskReview.vue` |
| 修改 | `frontend/src/router/index.ts` |

## 关键设计决策

1. **OpenAI 兼容模式**: 不引入 `google-generativeai` SDK，Gemini/DeepSeek/Ollama 等通过 OpenAI 兼容接口 + 自定义 `base_url` 接入，减少依赖
2. **API Key 存储**: 明文存数据库，前端展示脱敏，简单直接
3. **Tool Calling 统一格式**: 不同 Provider 的 tool_calls 响应统一转换为 `[{name, arguments, id}]` 格式
4. **流式协议**: SSE（Server-Sent Events），前端用 `EventSource` 接收，比 WebSocket 更简单
5. **向后兼容**: `agent_configs` 的 `provider`/`model` 字段保留，`llm_config_id` 为可选，旧数据无需迁移

## 验证步骤

1. 启动服务，在前端 LLM 配置页添加 OpenAI/Anthropic/OpenAI 兼容配置
2. 测试连接功能验证 API Key 正确性
3. 在 Agent 配置页选择 LLM 配置和模型，绑定工具
4. 创建任务，验证生成功能正常
5. 启用流式输出的 Agent，在监控页观察实时输出
6. 绑定工具的 Agent，观察 Tool Calling 过程（LLM 调用工具 → 执行 → 结果回传 → 继续生成）
7. 运行全部测试: `pytest backend/tests/`
