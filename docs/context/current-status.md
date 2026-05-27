# 当前状态

**更新时间**：2026-05-27

## 当前阶段

正式产品处于 **Phase 1 A（平台与安全）已实现、Phase 1 C 管理端页面后续交互补齐中，Phase 1 B 待完成** 阶段。

Phase 0 工程底座已落地：FastAPI + SQLAlchemy AsyncSession + Alembic + PostgreSQL 骨架可运行，`uv` 依赖管理一致，Docker Compose 提供开发数据库。

Phase 1 A 开发分支 `feat/phase-1-auth-rbac` 已完成认证/RBAC/导航/审计全部后端实现和集成测试。Phase 1 C 已将登录页、后台框架和管理端页面接入 FastAPI 同源 View，前端默认调用正式 `/api/v1` 接口，并补齐用户、角色与功能导航管理的编辑、启停、删除和授权选择交互。

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
| Git 分支、约定式提交与 Code Review 流程 | 已定义 |
| 三人并行开发 Phase 计划 | 已定义 |

## 首版实现状态

| 模块 | 目标 | 正式实现状态 |
| --- | --- | --- |
| 认证与基础 RBAC | 登录、用户、角色、权限、功能导航和访问控制 | `feat/phase-1-auth-rbac` 已实现，集成测试通过（13 条）；C 工作流页面已对接登录、导航、用户、角色、权限、功能导航和审计接口 |
| 模型引擎 | 脱敏配置、默认模型、测试与调用统计 | `feat/phase-1-model-engine` 后端已实现，包含模型配置 CRUD、凭据加密脱敏、连接测试、流式测试、调用统计；集成测试待环境验证 |
| 智能瞭望 | 数据源、规则和采集任务 | 待开发 |
| 数据仓库 | 标准化入库、去重和内容治理 | 待开发 |
| 智能问数 | 检索依据、流式回答与引用 | 待开发 |
| 安全与审计 | 秘密保护、SSRF 防护与高风险动作审计 | Phase 1 A 已覆盖认证/RBAC/CSRF/审计基础；Phase 1 B 已实现凭据加密；采集安全待后续模块实现 |

## 下一里程碑

Phase 1 A（平台与安全）后端已实现，Phase 1 B 后端已实现，Phase 1 C 管理端页面已部分接入。待完成：
- A/B：联调模型引擎 API 与管理端页面，补齐模型启停/设默认等完整管理交互。
- C：与 A/B 真实接口继续联调，完成模型配置与测试页面的完整对接。
- B：进入智能瞭望实现（数据源、规则、采集任务）。

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
- 连接测试支持普通响应和 SSE 流式响应
- 模型调用记录包含耗时、token 使用量和脱敏错误分类
- 集成测试覆盖 9 条：CRUD、列表过滤、脱敏验证、默认模型保护、权限控制

## 维护要求

- 完成一个正式模块或验收项后，更新本文件对应状态。
- 若实现改变正式数据库或 API 契约，先更新相应设计文档并记录决策。
- 不因旧原型曾存在同名页面或功能而将本表标记为完成。
