# 当前状态

**更新时间**：2026-05-29

## 当前阶段

正式产品处于 **Phase 1 A/B 已实现、Phase 2 A/B 已完成实现、Phase 3 B（智能问数后端）已完成开发** 阶段。

Phase 0 工程底座已落地并调整为单仓前后端分离结构：`backend/` 承载 FastAPI + SQLAlchemy AsyncSession + Alembic + PostgreSQL 后端 API，`frontend/` 承载 Vite Vue TypeScript + Pinia + Vue Router + Element Plus 前端；Docker Compose 继续在根目录提供开发数据库。后端进程只提供 API、健康检查和 OpenAPI 文档，不托管前端页面或构建产物。

Phase 1 A 开发分支 `feat/phase-1-auth-rbac` 已完成认证/RBAC/导航/审计全部后端实现和集成测试。Phase 1 B 后端已实现模型配置、凭据加密脱敏、连接测试、流式测试和调用统计。Phase 1 C 管理端已迁移到 Vite 脚手架前端，继续调用正式 `/api/v1` 接口，并保留用户、角色、功能导航、权限、审计、模型配置入口和 SSE 测试客户端页面。

早期示例原型仅被用于提取需求，已经从正式开发上下文中废弃；它不作为功能完成状态，也不要求新实现保持兼容。后续开发应按 `docs/product/`、`docs/architecture/`、`docs/database/` 和 `docs/api/` 中的新契约建设。

## 文档建设状态

| 内容 | 状态 |
| --- | --- |
| 产品愿景与首版需求 | 已定义 |
| MVP 边界与验收脚本 | 已定义 |
| 模块化 MVC 架构与安全基线 | 已定义 |
| 首版数据库契约与数据规则 | 已定义 |
| 首版 API 契约 | 已定义 |
| AI 开发流程与可复用 SOP | 已定义 |
| `uv` 依赖与项目环境工作流 | 已定义 |
| `pnpm` 前端依赖、Vite 脚手架与组件库选择 | 已定义 |
| Git 分支、约定式提交与 Code Review 流程 | 已定义 |
| 三人并行开发 Phase 计划 | 已定义 |

## 首版实现状态

| 模块 | 目标 | 正式实现状态 |
| --- | --- | --- |
| 认证与基础 RBAC | 登录、用户、角色、权限、功能导航和访问控制 | `feat/phase-1-auth-rbac` 已实现；C 工作流已迁移到 Vue 管理端并对接登录、导航、用户、角色、权限、功能导航和审计接口，支持现有管理 API 的主要写操作 |
| 模型引擎 | 脱敏配置、默认模型、测试与调用统计 | `feat/phase-1-model-engine` 后端已实现，包含模型配置 CRUD、凭据加密脱敏、基于 OpenAI Python SDK 的连接测试、流式测试、调用统计；集成测试已覆盖模型引擎 |
| 智能瞭望 | 数据源、规则和采集任务 | Phase 2 B 已实现完整 CRUD、异步任务执行、SSRF 防护；`feat/phase-2-watch-data-v2` 已实现 |
| 数据仓库 | 标准化入库、去重和内容治理 | Phase 2 B 已实现内容入库、重复检测和治理状态管理 |
| 智能问数 | 检索依据、流式回答与引用 | Phase 3 B 后端已实现会话/消息/引用 CRUD、流式问答、内容检索；`feat/phase-3-qa-engine` 已实现 |
| 安全与审计 | 秘密保护、SSRF 防护与高风险动作审计 | Phase 1 A 已覆盖认证/RBAC/CSRF/审计基础；Phase 1 B 已实现凭据加密；Phase 2 A 已实现采集 SSRF 校验组件与 watch/data 脱敏审计 helper |

## 下一里程碑

Phase 1 A/B 已完成，Phase 2 A/B 已完成，Phase 3 B 后端已实现。待完成：
- Phase 3 C：智能问数前端页面开发（用户问数界面、流式回答呈现、引用详情）
- Phase 4：MVP 集成验收与交付

## Phase 2 B 实现摘要

**分支**：`feat/phase-2-watch-data-v2`

**已实现能力**：
- 数据源 CRUD、状态管理（active/disabled）
- 采集规则 CRUD、状态管理
- 采集任务 CRUD、取消、执行（后台异步）
- 知识库内容列表、详情、状态更新
- Phase 2 A 采集安全组件复用（`validate_source_policy`、`validate_fetch_target`、`validate_rule_security`）
- `watch_audit.write_watch_audit` 审计日志（含敏感信息脱敏）
- 采集内容 HTML/JSON 提取、重复检测（SHA-256）
- SSRF 校验：HTTPS 强制、私网 IP 拒绝、DNS rebinding 防护、精确 host 白名单

**已实现接口**：

| 模块 | 端点 | 状态 |
| --- | --- | --- |
| 数据源 | `GET/POST /api/v1/admin/watch-sources`、`GET/PATCH /watch-sources/{id}`、`PATCH /watch-sources/{id}/status` | 已实现 |
| 采集规则 | `GET/POST /api/v1/admin/watch-sources/{id}/rules`、`PATCH /watch-rules/{id}` | 已实现 |
| 采集任务 | `POST /api/v1/admin/collection-tasks`、`GET /collection-tasks`、`GET /collection-tasks/{id}`、`POST /collection-tasks/{id}/cancel`、`POST /collection-tasks/{id}/execute` | 已实现 |
| 知识库 | `GET /api/v1/admin/knowledge-items`、`GET /knowledge-items/{id}`、`PATCH /knowledge-items/{id}/status` | 已实现 |

**技术细节**：
- 后台任务执行（`/execute`）使用 `asyncio.create_task` + `sessionmaker` 确保独立 session
- 集成测试覆盖 22 条：SSRF 策略、HTTPS 强制、私网 IP 拒绝、DNS rebinding、端点存在性、CSRF 校验、审计日志

## Phase 3 B 实现摘要

**分支**：`feat/phase-3-qa-engine`

**已实现能力**：
- 会话 CRUD：创建、获取、列表、更新会话标题和状态（active/archived）
- 消息管理：保存用户问题和助手回答，包含状态追踪
- 引用管理：保存并获取回答与知识内容的关联关系
- 内容检索：基于关键词从 `status=available` 的知识内容中检索相关条目
- 流式问答：使用 SSE 流式返回模型回答，支持增量片段和完成事件
- 模型编排：调用默认模型（`qa_answer` 用途），错误状态记录到 `model_call_log`
- 权限隔离：用户只能访问自己的会话、消息和引用
- 审计日志：记录会话创建和问数动作

**已实现接口**：

| 模块 | 端点 | 状态 |
| --- | --- | --- |
| 会话 | `GET/POST /api/v1/qa/sessions`、`GET/PATCH /qa/sessions/{id}` | 已实现 |
| 消息 | `GET /api/v1/qa/sessions/{id}/messages` | 已实现 |
| 流式问答 | `POST /api/v1/qa/sessions/{id}/questions/stream` | 已实现 |
| 引用 | `GET /api/v1/qa/messages/{id}/citations` | 已实现 |

**技术细节**：
- 使用 `StreamingResponse` + `text/event-stream` 返回 SSE 流式响应
- 检索策略：提取问题关键词，从 `available` 状态知识内容中按相关度排序
- 提示词构建：外部采集内容按不可信处理，在提示词中声明参考资料限制
- 模型调用通过 `ModelProviderClient.stream_chat` 实现，调用日志含 `qa_answer` 用途
- 集成测试覆盖：权限隔离、会话隔离、CSRF 保护、模型可用性、流式响应、错误处理

**代码修复记录**：
- 修复 `qa_engine.py` 中 `selectinload` 链式加载重复问题
- 修复 `qa_engine.py` 中空值检查逻辑不清晰问题
- 修复 `qa_knowledge.py` 中查询条件逻辑错误（移除了错误的 or_ 条件）
- 修复 `entities.py` 中注释格式问题
- 修复 `qa_engine.py` 中缺少 `KnowledgeItem` 导入问题
- 修复 `model_engine.py` 中设置默认模型时的数据库约束冲突问题（添加 flush）
- 修复 `qa.py` 中 `require_permission` 依赖使用方式不正确导致权限检查失效问题
- 修复 `qa.py` 中 `require_csrf` 依赖使用方式不正确导致请求验证失败问题
- 集成测试全部通过（12/12）：权限检查、会话隔离、CSRF 保护、模型可用性、流式响应、错误处理

**Phase 2 A 实现摘要**

**分支**：`phase-2-collection-security`

**已实现能力**：
- 新增采集安全组件，支持数据源保存前和任务执行/重定向前的 HTTPS、精确 host 白名单、URL userinfo、本地域名、非公网 IP 与 DNS 解析结果校验。
- 新增采集规则安全校验，拒绝敏感请求头、换行注入、未知模板变量、脚本型解析配置和任意表达式。
- 新增 watch/data 审计 helper，约定数据源、规则、任务和内容治理动作代码，并对 URL 查询串、认证配置、请求头、Cookie、token、secret 等敏感信息脱敏。
- 不新增可见导航入口，也不交付数据源 CRUD、任务执行器、内容入库或前端页面；Phase 2 B 必须在真实业务路径中调用本安全组件。

## Phase 1 A 实现摘要

**分支**：`feat/phase-1-auth-rbac`

**已实现接口**（符合 `docs/api/auth-and-rbac.md`）：

| 模块 | 端点 | 状态 |
| --- | --- | --- |
| 认证 | `POST /api/v1/auth/login`、`POST /api/v1/auth/logout`、`GET /api/v1/auth/me`、`GET /api/v1/auth/boot`、`GET /api/v1/auth/navigation` | 已实现 |
| 用户管理 | `GET/POST /api/v1/admin/users`、`PATCH /users/{id}`、`PATCH /users/{id}/status`、`POST /users/{id}/password-reset` | 已实现 |
| 角色权限 | `GET /api/v1/admin/permissions`、`GET/POST/PATCH/DELETE /api/v1/admin/roles` | 已实现 |
| 导航管理 | `GET/POST/PATCH/DELETE /api/v1/admin/functions` | 已实现 |
| 审计 | `GET /api/v1/admin/audit-logs` | 已实现 |

**技术细节**：
- 密码 Argon2id 慢哈希、会话令牌 SHA-256 存储、CSRF 双令牌（HMAC 派生）
- 管理端初始化可通过 `/api/v1/auth/boot` 聚合读取用户与导航；接口鉴权仍实时依据当前角色和权限关联，撤权后续请求立即生效
- 权限字典 13 项覆盖 platform/models/watch/data/qa/audit 六个模块
- Bootstrap 数据：系统管理员角色、5 项系统导航（初始 disabled）
- `create-system-admin` CLI 支持 `--username` / `--display-name` 和交互式或环境变量密码输入
- 集成测试覆盖 15 条：CRUD、CSRF 校验、导航过滤、审计脱敏、权限拒绝、即时撤权、并发管理员保护、循环层级保护、系统角色保护

## Phase 1 B 实现摘要

**分支**：`feat/phase-1-model-engine`

**已实现接口**（符合 `docs/api/model-engine.md`）：

| 模块 | 端点 | 状态 |
| --- | --- | --- |
| 模型配置 | `GET/POST /api/v1/admin/models`、`GET/PATCH /models/{id}`、`PATCH /models/{id}/status`、`PUT /models/{id}/default` | 已实现 |
| 模型测试 | `POST /models/{id}/connection-tests`、`POST /models/{id}/connection-tests/stream` | 已实现 |
| 调用统计 | `GET /api/v1/admin/model-calls`、`GET /model-calls/summary` | 已实现 |

**技术细节**：
- API 密钥使用 Fernet (AES-128-CBC + HMAC-SHA256) 加密存储，凭据掩码只显示 `****xxxx` 格式
- 模型调用通过 OpenAI Python SDK 的 AsyncOpenAI 适配 OpenAI-compatible Chat Completions，连接测试支持普通响应和 SSE 流式响应
- 模型调用记录包含耗时、token 使用量和脱敏错误分类
- 集成测试覆盖 15 条：CRUD、列表过滤、脱敏验证、默认模型保护、权限控制、SDK 调用成功、上游错误映射、SSE 成功和流式错误处理

## 维护要求

- 完成一个正式模块或验收项后，更新本文件对应状态。
- 若实现改变正式数据库或 API 契约，先更新相应设计文档并记录决策。
- 不因旧原型曾存在同名页面或功能而将本表标记为完成。
