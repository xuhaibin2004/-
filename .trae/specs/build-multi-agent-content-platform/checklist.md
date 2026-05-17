# Checklist

## 项目基础设施
- [ ] 项目目录结构完整，backend/frontend/tests目录已创建
- [ ] docker-compose.yml可正常启动PostgreSQL(pgvector)和Redis
- [ ] backend依赖安装无报错，pyproject.toml包含所有必要依赖
- [ ] frontend依赖安装无报错，Vue3+Vite项目可正常dev启动
- [ ] .env.example包含所有必要环境变量说明

## 数据库
- [ ] 所有模型已创建（Project, AgentConfig, Task, GenerationResult, ScoreResult, Memory）
- [ ] Alembic迁移脚本可正常执行，数据库表创建成功
- [ ] Memory模型的pgvector向量索引已创建
- [ ] 数据库连接池配置正确，异步引擎可正常工作

## FastAPI应用
- [ ] FastAPI应用可正常启动，访问/docs可见Swagger文档
- [ ] CORS配置正确，前端可跨域访问
- [ ] 全局异常处理中间件工作正常
- [ ] 配置模块可正确读取环境变量

## 项目管理API
- [ ] POST /api/projects 可创建项目并返回项目ID
- [ ] GET /api/projects 可分页返回项目列表
- [ ] GET /api/projects/{id} 可返回项目详情
- [ ] PUT /api/projects/{id} 可更新项目信息
- [ ] DELETE /api/projects/{id} 可删除项目
- [ ] 项目管理API单元测试全部通过

## Agent配置API
- [ ] POST /api/projects/{id}/agents 可创建Agent配置
- [ ] GET /api/projects/{id}/agents 可返回项目下所有Agent配置
- [ ] PUT /api/agents/{id} 可更新Agent配置
- [ ] DELETE /api/agents/{id} 可删除Agent配置
- [ ] 预设Agent模板数据可正常加载
- [ ] Agent配置API单元测试全部通过

## 任务API
- [ ] POST /api/projects/{id}/tasks 可创建任务并写入Redis Stream
- [ ] GET /api/tasks/{id} 可返回任务详情含生成结果与评分
- [ ] GET /api/projects/{id}/tasks 可分页返回项目任务列表
- [ ] GET /api/tasks/{id}/status 可返回任务当前状态
- [ ] 任务API单元测试全部通过

## LLM Provider抽象层
- [ ] LLMProvider基类定义完整，包含generate和stream_generate方法
- [ ] OpenAI Provider可正常调用GPT-4o/GPT-4o-mini
- [ ] Anthropic Provider可正常调用Claude系列模型
- [ ] Provider工厂函数可根据配置创建正确实例
- [ ] Provider故障转移逻辑工作正常（主Provider失败→备用Provider）
- [ ] Provider层单元测试全部通过

## 生成Agent
- [ ] GenerationAgent可构建差异化Prompt并调用LLM生成内容
- [ ] Prompt差异化策略生效（不同Agent使用不同角色/风格/温度）
- [ ] 长期记忆检索结果可正确注入Prompt上下文
- [ ] 进程级隔离执行正常，超时后进程被终止
- [ ] MCP工具白名单机制生效，未授权工具不可调用
- [ ] GenerationAgent单元测试全部通过

## 评分Agent
- [ ] EvaluationAgent可构建评分Prompt并返回结构化评分
- [ ] 多维度评分逻辑正确（AI率/创意性/连贯性/风格匹配度/综合）
- [ ] GPTZero API集成正常，可获取外部AI率检测分数
- [ ] 加权评分聚合正确（外部AI率60% + LLM评分40%）
- [ ] EvaluationAgent单元测试全部通过

## 任务调度引擎
- [ ] TaskScheduler可编排完整任务流程（生成→评分→迭代→审核）
- [ ] Redis Stream Worker可正常消费任务消息
- [ ] 并行调度逻辑正常，多个Agent可并发执行
- [ ] 迭代生成机制正常（AI率不达标→反馈重生成，最多N轮）
- [ ] 任务状态机流转正确，状态变更通过Redis Pub/Sub通知
- [ ] 失败重试逻辑正常（可重试错误→重新入队，最多3次）
- [ ] TaskScheduler集成测试全部通过

## 长期记忆系统
- [ ] MemoryService可正常写入记忆（文本→embedding→pgvector）
- [ ] 语义检索可返回相关度最高的Top-K记忆
- [ ] 记忆衰减逻辑正常（TTL过期+置信度衰减）
- [ ] 记忆检索结果可正确注入生成Agent的Prompt
- [ ] 用户反馈可正确写入记忆库
- [ ] 任务完成时成功经验可写入记忆
- [ ] MemoryService单元测试全部通过

## 用户审核与反馈API
- [ ] GET /api/tasks/{id}/review 可返回完整审核数据
- [ ] PUT /api/generation-results/{id} 可保存用户编辑内容
- [ ] POST /api/generation-results/{id}/recheck 可重新触发AI检测
- [ ] POST /api/generation-results/{id}/feedback 可提交反馈并写入记忆
- [ ] POST /api/tasks/{id}/finalize 可选择最终内容并完成任务
- [ ] 审核与反馈API单元测试全部通过

## WebSocket实时通知
- [ ] WebSocket端点 /ws/tasks/{id} 可正常连接
- [ ] 任务状态变更可通过Redis Pub/Sub → WebSocket推送到前端
- [ ] WebSocket集成测试通过

## 前端 - 项目管理
- [ ] 项目列表页可正常展示项目卡片
- [ ] 项目创建表单可提交并创建项目
- [ ] 项目详情页可展示基本信息、Agent配置、任务历史

## 前端 - Agent配置
- [ ] Agent列表可展示当前配置和预设模板
- [ ] Agent编辑器可编辑Prompt、选择Provider/模型、调节温度
- [ ] Prompt预览功能可展示完整Prompt

## 前端 - 任务创建与监控
- [ ] 任务创建页可输入剧情概要、选择Agent数量、配置高级选项
- [ ] 任务监控页可实时展示Agent执行状态（WebSocket更新）

## 前端 - 内容审核
- [ ] 内容对比视图可左右分栏展示多个生成结果
- [ ] 评分雷达图可正确展示多维度评分
- [ ] AI检测报告可展示外部检测分数与LLM评分对比
- [ ] 内容编辑器可在线编辑并重新检测
- [ ] 反馈确认表单可选择问题类型、输入描述、提交
- [ ] 最终选择操作可确认并完成任务

## 集成测试
- [ ] 完整业务流程E2E测试通过（创建项目→配置Agent→提交任务→生成→评分→审核→记忆写入）
- [ ] 迭代生成场景测试通过（AI率不达标→自动重生成→达标→审核）
- [ ] 异常场景测试通过（Agent超时/失败/Provider故障转移）

## 部署
- [ ] 后端Dockerfile可正常构建镜像
- [ ] 前端Dockerfile可正常构建镜像
- [ ] docker-compose可一键启动全部服务
- [ ] nginx反向代理配置正确
