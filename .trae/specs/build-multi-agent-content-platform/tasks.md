# Tasks

## 阶段1: 项目骨架与基础设施

- [x] Task 1: 初始化项目结构与依赖配置
  - [x] SubTask 1.1: 创建Python项目目录结构（backend/app、frontend、tests）
  - [x] SubTask 1.2: 创建backend/pyproject.toml，声明依赖（fastapi, uvicorn, sqlalchemy, asyncpg, pgvector, redis, httpx, pydantic, python-multipart, websockets）
  - [x] SubTask 1.3: 创建frontend/package.json，初始化Vue3+Vite项目
  - [x] SubTask 1.4: 创建docker-compose.yml（PostgreSQL+pgvector, Redis）
  - [x] SubTask 1.5: 创建.env.example环境变量模板

- [x] Task 2: 数据库模型与迁移
  - [x] SubTask 2.1: 配置SQLAlchemy异步引擎与连接池
  - [x] SubTask 2.2: 创建Project模型（id, name, genre, style, world_setting, characters, status, created_at, updated_at）
  - [x] SubTask 2.3: 创建AgentConfig模型（id, project_id, name, prompt_template, provider, model, temperature, role_description, is_builtin）
  - [x] SubTask 2.4: 创建Task模型（id, project_id, plot_summary, status, iteration_count, max_iterations, ai_rate_threshold, created_at, completed_at）
  - [x] SubTask 2.5: 创建GenerationResult模型（id, task_id, agent_config_id, content, status, error_message, generation_time_ms, iteration）
  - [x] SubTask 2.6: 创建ScoreResult模型（id, generation_result_id, ai_rate_score, creativity_score, coherence_score, style_match_score, overall_score, external_ai_rate, scorer_type）
  - [x] SubTask 2.7: 创建Memory模型（id, project_id, content, embedding, category, confidence, source_task_id, created_at, expired_at）+ pgvector向量索引
  - [x] SubTask 2.8: 创建Alembic迁移配置与初始迁移脚本

- [x] Task 3: FastAPI应用骨架与配置
  - [x] SubTask 3.1: 创建FastAPI应用入口（app/main.py），配置CORS、异常处理、生命周期
  - [x] SubTask 3.2: 创建配置模块（app/core/config.py），使用pydantic-settings管理环境变量
  - [x] SubTask 3.3: 创建数据库依赖注入（app/core/database.py），提供get_db session
  - [x] SubTask 3.4: 创建Redis连接管理（app/core/redis.py）

## 阶段2: 核心后端API

- [x] Task 4: 项目管理API
  - [x] SubTask 4.1: POST /api/projects - 创建项目
  - [x] SubTask 4.2: GET /api/projects - 项目列表（分页）
  - [x] SubTask 4.3: GET /api/projects/{id} - 项目详情
  - [x] SubTask 4.4: PUT /api/projects/{id} - 更新项目
  - [x] SubTask 4.5: DELETE /api/projects/{id} - 删除项目
  - [x] SubTask 4.6: 编写项目管理API的单元测试

- [x] Task 5: Agent配置API
  - [x] SubTask 5.1: POST /api/projects/{id}/agents - 创建Agent配置
  - [x] SubTask 5.2: GET /api/projects/{id}/agents - 获取项目下所有Agent配置
  - [x] SubTask 5.3: PUT /api/agents/{id} - 更新Agent配置
  - [x] SubTask 5.4: DELETE /api/agents/{id} - 删除Agent配置
  - [x] SubTask 5.5: 创建预设Agent模板（文学风格/口语风格/叙事风格等3-5个模板）
  - [x] SubTask 5.6: 编写Agent配置API的单元测试

- [x] Task 6: 任务创建与查询API
  - [x] SubTask 6.1: POST /api/projects/{id}/tasks - 创建生成任务（入队Redis Stream）
  - [x] SubTask 6.2: GET /api/tasks/{id} - 任务详情（含生成结果与评分）
  - [x] SubTask 6.3: GET /api/projects/{id}/tasks - 项目任务列表（分页）
  - [x] SubTask 6.4: GET /api/tasks/{id}/status - 任务状态查询
  - [x] SubTask 6.5: 编写任务API的单元测试

## 阶段3: Agent调度引擎

- [x] Task 7: LLM Provider抽象层
  - [x] SubTask 7.1: 创建LLMProvider基类（generate, stream_generate方法）
  - [x] SubTask 7.2: 实现OpenAI Provider（支持GPT-4o/GPT-4o-mini）
  - [x] SubTask 7.3: 实现Anthropic Provider（支持Claude系列）
  - [x] SubTask 7.4: 创建Provider工厂函数，根据配置创建对应Provider实例
  - [x] SubTask 7.5: 实现Provider故障转移逻辑（主Provider失败→备用Provider）
  - [x] SubTask 7.6: 编写Provider层单元测试（mock API调用）

- [x] Task 8: 生成Agent执行器
  - [x] SubTask 8.1: 创建GenerationAgent类，封装Prompt构建+LLM调用+结果解析
  - [x] SubTask 8.2: 实现Prompt差异化策略（角色/风格/温度参数自动差异化）
  - [x] SubTask 8.3: 实现长期记忆注入（检索相关记忆→拼接到Prompt上下文）
  - [x] SubTask 8.4: 实现进程级隔离执行（multiprocessing.Process + 超时控制 + 资源限制）
  - [x] SubTask 8.5: 实现MCP工具白名单机制（Agent可调用的工具集配置）
  - [x] SubTask 8.6: 编写GenerationAgent单元测试

- [x] Task 9: 评分Agent执行器
  - [x] SubTask 9.1: 创建EvaluationAgent类，封装评分Prompt构建+LLM调用+结构化评分解析
  - [x] SubTask 9.2: 实现多维度评分逻辑（AI率/创意性/连贯性/风格匹配度/综合）
  - [x] SubTask 9.3: 集成GPTZero API，获取外部AI率检测分数
  - [x] SubTask 9.4: 实现加权评分聚合（外部AI率60% + LLM评分40%）
  - [x] SubTask 9.5: 编写EvaluationAgent单元测试

- [x] Task 10: 任务调度引擎
  - [x] SubTask 10.1: 创建TaskScheduler类，编排完整任务流程（生成→评分→迭代判断→用户审核）
  - [x] SubTask 10.2: 实现Redis Stream Worker（消费任务消息、执行调度流程）
  - [x] SubTask 10.3: 实现并行调度逻辑（asyncio.gather并发执行多个Agent）
  - [x] SubTask 10.4: 实现迭代生成机制（评分不达标→反馈重生成，最多N轮）
  - [x] SubTask 10.5: 实现任务状态机与状态流转通知（Redis Pub/Sub → WebSocket）
  - [x] SubTask 10.6: 实现失败重试逻辑（可重试错误→重新入队，最多3次）
  - [x] SubTask 10.7: 编写TaskScheduler集成测试

## 阶段4: 长期记忆系统

- [x] Task 11: 记忆存储与检索
  - [x] SubTask 11.1: 创建MemoryService类，封装记忆的CRUD操作
  - [x] SubTask 11.2: 实现记忆写入（文本→embedding→存入pgvector，附带元数据）
  - [x] SubTask 11.3: 实现语义检索（查询文本→embedding→pgvector余弦相似度搜索，返回Top-K）
  - [x] SubTask 11.4: 实现记忆衰减逻辑（TTL过期+置信度衰减，定期清理任务）
  - [x] SubTask 11.5: 编写MemoryService单元测试

- [x] Task 12: 记忆集成到任务流程
  - [x] SubTask 12.1: 在任务生成前注入记忆检索结果到Agent Prompt
  - [x] SubTask 12.2: 在用户确认低分原因后写入记忆
  - [x] SubTask 12.3: 在任务完成时写入成功经验记忆
  - [x] SubTask 12.4: 编写记忆集成端到端测试

## 阶段5: 用户审核与反馈API

- [x] Task 13: 审核与反馈API
  - [x] SubTask 13.1: GET /api/tasks/{id}/review - 获取审核数据（内容+评分+迭代历史）
  - [x] SubTask 13.2: PUT /api/generation-results/{id} - 用户编辑内容
  - [x] SubTask 13.3: POST /api/generation-results/{id}/recheck - 编辑后重新AI检测
  - [x] SubTask 13.4: POST /api/generation-results/{id}/feedback - 提交低分原因反馈（写入记忆）
  - [x] SubTask 13.5: POST /api/tasks/{id}/finalize - 选择最终内容，完成任务
  - [x] SubTask 13.6: 编写审核与反馈API单元测试

- [x] Task 14: WebSocket实时通知
  - [x] SubTask 14.1: 创建WebSocket端点 /ws/tasks/{id} - 任务状态实时推送
  - [x] SubTask 14.2: 实现Redis Pub/Sub → WebSocket消息桥接
  - [x] SubTask 14.3: 编写WebSocket集成测试

## 阶段6: 前端界面

- [x] Task 15: 前端项目搭建与路由
  - [x] SubTask 15.1: 初始化Vue3+Vite+TypeScript项目，安装依赖（vue-router, pinia, axios, element-plus, echarts）
  - [x] SubTask 15.2: 配置路由（项目列表/项目详情/任务创建/任务监控/内容审核）
  - [x] SubTask 15.3: 配置Pinia状态管理（project store, task store, auth store）
  - [x] SubTask 15.4: 创建API服务层（axios实例、拦截器、各模块API函数）

- [x] Task 16: 项目管理页面
  - [x] SubTask 16.1: 项目列表页（卡片式展示、搜索过滤、新建入口）
  - [x] SubTask 16.2: 项目创建/编辑表单（题材/风格/世界观/角色设定）
  - [x] SubTask 16.3: 项目详情页（基本信息+Agent配置+任务历史）

- [x] Task 17: Agent配置页面
  - [x] SubTask 17.1: Agent列表（展示当前配置+预设模板选择）
  - [x] SubTask 17.2: Agent编辑器（Prompt模板编辑、Provider/模型选择、温度参数调节）
  - [x] SubTask 17.3: Prompt预览功能（展示完整Prompt含记忆注入占位符）

- [x] Task 18: 任务创建与监控页面
  - [x] SubTask 18.1: 任务创建页（剧情概要输入、Agent数量选择、高级选项折叠面板）
  - [x] SubTask 18.2: 任务监控页（实时状态展示、Agent执行进度、WebSocket状态更新）

- [x] Task 19: 内容审核页面
  - [x] SubTask 19.1: 内容对比视图（左右分栏展示多个生成结果）
  - [x] SubTask 19.2: 评分雷达图（ECharts多维度可视化）
  - [x] SubTask 19.3: AI检测报告展示（外部检测分数+LLM评分对比）
  - [x] SubTask 19.4: 内容编辑器（在线编辑+重新检测按钮）
  - [x] SubTask 19.5: 反馈确认表单（问题类型多选+描述输入+提交写入记忆）
  - [x] SubTask 19.6: 最终选择与确认操作

## 阶段7: 集成测试与部署

- [x] Task 20: 端到端集成测试
  - [x] SubTask 20.1: 编写完整业务流程E2E测试（创建项目→配置Agent→提交任务→生成→评分→审核→记忆写入）
  - [x] SubTask 20.2: 编写迭代生成场景测试（AI率不达标→自动重生成→达标→审核）
  - [x] SubTask 20.3: 编写异常场景测试（Agent超时/失败/Provider故障转移）

- [x] Task 21: 部署配置
  - [x] SubTask 21.1: 创建后端Dockerfile（Python多阶段构建）
  - [x] SubTask 21.2: 创建前端Dockerfile（Node构建+Nginx服务）
  - [x] SubTask 21.3: 更新docker-compose.yml（添加backend/frontend服务）
  - [x] SubTask 21.4: 创建nginx.conf反向代理配置

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 1]
- [Task 4] depends on [Task 2, Task 3]
- [Task 5] depends on [Task 2, Task 3]
- [Task 6] depends on [Task 2, Task 3]
- [Task 7] depends on [Task 3]
- [Task 8] depends on [Task 7]
- [Task 9] depends on [Task 7]
- [Task 10] depends on [Task 8, Task 9]
- [Task 11] depends on [Task 2, Task 3]
- [Task 12] depends on [Task 11, Task 10]
- [Task 13] depends on [Task 6, Task 10]
- [Task 14] depends on [Task 3, Task 10]
- [Task 15] depends on [Task 1]
- [Task 16] depends on [Task 15, Task 4]
- [Task 17] depends on [Task 15, Task 5]
- [Task 18] depends on [Task 15, Task 6, Task 14]
- [Task 19] depends on [Task 15, Task 13]
- [Task 20] depends on [Task 12, Task 13, Task 14]
- [Task 21] depends on [Task 20]

# Parallelizable Work
- Task 4, Task 5, Task 6 可并行（均依赖Task 2+3）
- Task 7, Task 11 可并行（分别依赖Task 3, Task 2+3）
- Task 8, Task 9 可并行（均依赖Task 7）
- Task 16, Task 17 可并行（分别依赖Task 4, Task 5）
