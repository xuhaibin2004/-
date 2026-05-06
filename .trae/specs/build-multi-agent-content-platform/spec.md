# 多Agent协作内容生成与优化平台 Spec

## Why
当前AI生成内容存在"AI味重"的核心问题——读者能明显感知内容由AI生成。本平台通过多Agent并行生成多样化候选内容、多维度评分（以AI率为核心指标）、用户审核反馈、长期记忆闭环，系统性降低生成内容的AI率，产出更自然、更高质量的文字内容。

## What Changes
- 搭建 FastAPI 后端服务，提供项目管理和任务调度的完整API
- 实现多Agent并行生成与评分调度引擎（基于进程池隔离）
- 集成外部AI检测API（GPTZero）作为AI率客观基线，LLM评分作为辅助
- 实现基于 PostgreSQL + pgvector 的长期记忆系统（语义检索+经验写入）
- 基于 Redis Stream 的异步任务队列与Agent间通信
- 实现迭代生成机制：评分不达标时自动反馈重生成（最多N轮）
- 提供 Vue3 前端用户界面（项目创建、任务管理、内容审核、评分查看）
- 实现用户审核与反馈收集流程，将确认的低分原因写入记忆库

## Impact
- Affected specs: 全新项目，无已有规格受影响
- Affected code: 全新代码库，从零搭建

---

## ADDED Requirements

### Requirement: 项目管理
系统 SHALL 提供项目创建与管理功能，用户可创建内容生成项目并配置基础信息。

#### Scenario: 创建项目成功
- **WHEN** 用户提交项目创建请求，包含项目名称、题材/风格、世界观设定、角色设定
- **THEN** 系统创建项目记录，返回项目ID，项目状态为"已初始化"

#### Scenario: 配置Agent Prompt
- **WHEN** 用户为项目配置生成Agent的Prompt模板（可选择预设模板或自定义）
- **THEN** 系统保存Prompt配置，关联到该项目，后续生成任务使用该配置

#### Scenario: 项目列表查看
- **WHEN** 用户请求项目列表
- **THEN** 系统返回用户所有项目，包含名称、状态、创建时间、最近任务时间

---

### Requirement: 内容生成任务调度
系统 SHALL 支持用户提交剧情概要，调度多个生成Agent并行产出候选内容。

#### Scenario: 提交生成任务
- **WHEN** 用户输入剧情概要并提交生成任务
- **THEN** 系统创建任务记录，状态为"生成中"，检索长期记忆获取相关经验教训，调度N个生成Agent并行工作

#### Scenario: 生成Agent并行执行
- **WHEN** 系统调度生成任务
- **THEN** 每个生成Agent在独立进程中执行，使用不同的Prompt策略（差异化角色/风格/温度参数），可调用MCP工具获取辅助信息，生成结果互不干扰

#### Scenario: 生成Agent超时处理
- **WHEN** 某个生成Agent执行超过配置的超时时间（默认120秒）
- **THEN** 系统终止该Agent进程，标记该Agent结果为"超时"，其他Agent不受影响

#### Scenario: 生成Agent异常处理
- **WHEN** 某个生成Agent执行过程中抛出异常
- **THEN** 系统捕获异常，标记该Agent结果为"失败"并记录错误信息，其他Agent不受影响

---

### Requirement: 内容评分
系统 SHALL 对每个生成结果进行多维度评分，AI率为核心指标。

#### Scenario: 评分Agent并行执行
- **WHEN** 所有生成Agent完成（或超时/失败）后
- **THEN** 系统调度N个评分Agent并行评估每个有效生成结果，评分维度包含：AI率评分(0-100,越低越自然)、创意性、连贯性、风格匹配度、综合评分

#### Scenario: 外部AI检测集成
- **WHEN** 对生成内容进行AI率评估时
- **THEN** 系统调用GPTZero API获取客观AI率基线分数，该分数作为AI率评分的主要参考（权重60%），LLM评分Agent的AI率判断作为辅助参考（权重40%）

#### Scenario: 评分结果聚合
- **WHEN** 所有评分Agent完成评估
- **THEN** 系统聚合评分结果，按综合评分排序，生成评分报告供用户审核

---

### Requirement: 迭代生成机制
系统 SHALL 支持评分不达标时自动触发迭代重新生成。

#### Scenario: 自动迭代重生成
- **WHEN** 所有生成结果的AI率评分均高于阈值（默认70分），且当前迭代次数未达上限（默认3次）
- **THEN** 系统将最低评分结果及评分反馈作为上下文，重新调度生成Agent，Prompt中加入"避免以下问题"的指导信息

#### Scenario: 迭代次数耗尽
- **WHEN** 迭代次数达到上限，仍无结果低于AI率阈值
- **THEN** 系统标记任务为"需人工审核"，将当前最优结果呈现给用户

#### Scenario: 迭代中找到达标结果
- **WHEN** 迭代过程中某个结果的AI率评分低于阈值
- **THEN** 系统停止迭代，标记该结果为"推荐"，进入用户审核阶段

---

### Requirement: 用户审核与反馈
系统 SHALL 提供用户审核界面，支持查看内容、评分详情、编辑内容、确认反馈。

#### Scenario: 查看任务结果
- **WHEN** 用户打开任务审核页面
- **THEN** 系统展示所有生成内容（按综合评分排序）、各维度评分详情、AI检测报告、迭代历史

#### Scenario: 用户编辑内容
- **WHEN** 用户对某条生成内容进行编辑修改
- **THEN** 系统保存编辑后的内容，标记为"用户修改"，可重新触发AI检测获取新的AI率分数

#### Scenario: 确认低分原因并写入记忆
- **WHEN** 用户确认某条内容的低分原因（选择问题类型+补充描述）
- **THEN** 系统将低分原因结构化后写入向量记忆库，关联当前项目、任务、内容片段，供未来生成任务检索参考

#### Scenario: 选择最终内容
- **WHEN** 用户选择某条内容作为最终结果
- **THEN** 系统标记任务为"已完成"，保存最终内容及完整任务记录（内容+评分+记忆）

---

### Requirement: 长期记忆系统
系统 SHALL 基于向量数据库实现长期记忆的存储与语义检索。

#### Scenario: 记忆写入
- **WHEN** 用户确认低分原因或任务完成时
- **THEN** 系统将经验教训（问题类型、描述、上下文）进行向量化后存入pgvector，附带元数据（项目ID、时间戳、置信度）

#### Scenario: 记忆检索
- **WHEN** 新任务开始生成前
- **THEN** 系统将剧情概要进行向量化，在pgvector中检索最相关的K条记忆（默认K=5），将检索结果注入生成Agent的Prompt上下文中

#### Scenario: 记忆衰减
- **WHEN** 记忆条目超过TTL（默认90天）或置信度低于阈值
- **THEN** 系统在定期清理任务中标记该记忆为"已过期"，不再参与检索

---

### Requirement: Agent隔离与资源控制
系统 SHALL 确保各Agent在隔离环境中执行，资源使用可控。

#### Scenario: 进程级隔离
- **WHEN** 调度Agent执行任务
- **THEN** 每个Agent在独立子进程中运行，通过multiprocessing.Process实现隔离，设置CPU和内存资源限制

#### Scenario: Agent权限沙箱
- **WHEN** Agent需要调用外部工具（MCP）
- **THEN** 系统通过白名单机制控制Agent可调用的工具集，禁止未授权的文件/网络访问

---

### Requirement: 异步任务队列
系统 SHALL 基于Redis Stream实现异步任务调度与状态追踪。

#### Scenario: 任务入队
- **WHEN** 用户提交生成任务
- **THEN** 系统将任务消息写入Redis Stream，返回任务ID，任务状态为"排队中"

#### Scenario: 任务消费与状态更新
- **WHEN** Worker进程从Stream中消费任务
- **THEN** 系统更新任务状态（排队中→生成中→评分中→待审核→已完成），状态变更通过Redis Pub/Sub通知前端

#### Scenario: 任务失败重试
- **WHEN** Worker处理任务时发生可重试错误
- **THEN** 系统将任务重新入队，最多重试3次，每次重试间隔递增

---

### Requirement: 前端用户界面
系统 SHALL 提供Vue3前端界面，支持完整业务流程操作。

#### Scenario: 项目管理页面
- **WHEN** 用户访问项目管理
- **THEN** 展示项目列表（卡片式）、创建项目表单（题材/风格/世界观/角色）、项目详情页（Agent配置/任务历史）

#### Scenario: 任务创建页面
- **WHEN** 用户在项目中创建新任务
- **THEN** 展示剧情概要输入框、生成Agent数量选择（1-5）、高级选项（温度/迭代次数/AI率阈值），提交后进入任务监控

#### Scenario: 任务监控页面
- **WHEN** 任务执行中
- **THEN** 实时展示各Agent状态（生成中/评分中/已完成）、进度条、WebSocket推送状态更新

#### Scenario: 内容审核页面
- **WHEN** 任务进入待审核状态
- **THEN** 展示内容对比视图（左右分栏）、评分雷达图、AI检测报告、编辑器、反馈确认表单、最终选择按钮

---

### Requirement: LLM Provider抽象层
系统 SHALL 提供统一的LLM调用抽象层，支持多Provider切换。

#### Scenario: 多Provider支持
- **WHEN** 系统配置了多个LLM Provider（OpenAI/Anthropic/本地模型）
- **THEN** 不同Agent可使用不同Provider，系统通过统一接口调用，配置中指定Provider和模型名称

#### Scenario: Provider故障转移
- **WHEN** 主Provider调用失败（超时/限流/服务不可用）
- **THEN** 系统自动切换到备用Provider重试，记录故障日志

---

## MODIFIED Requirements

无（全新项目）

## REMOVED Requirements

无（全新项目）
