# 数智大屏与舆情分析 API

## 基础信息

- **Base URL**: `/api/v1/admin`
- **认证方式**: Cookie-based 会话认证（`cnagentos_session`）
- **CSRF**: 所有变更型请求（POST）需附带 `X-CSRF-Token` 请求头
- **权限守卫**: 声明所需权限代码

## Dashboard 统计

| 方法 | 路径 | 权限 | CSRF | 说明 |
| --- | --- | --- | --- | --- |
| `GET` | `/dashboard/stats` | `sentiment.view` | - | 聚合统计数据 |
| `GET` | `/dashboard/trends` | `sentiment.view` | - | 日趋势数据 |
| `GET` | `/dashboard/keywords` | `sentiment.view` | - | 关键词频率 |

### `GET /dashboard/stats`

返回系统核心模块的聚合统计数据。

**查询参数**：无

**响应示例**：

```json
{
  "data": {
    "knowledge_items": { "total": 100, "available": 80, "excluded": 10, "archived": 10 },
    "watch_sources": { "total": 20, "active": 15, "disabled": 5 },
    "collection_tasks": { "total": 50, "succeeded": 30, "failed": 5, "partial_failed": 5, "running": 1, "pending": 9 },
    "qa_sessions": { "total": 30, "active": 25, "archived": 5 },
    "users": { "total": 15, "active_today": 3 },
    "chat_messages": { "total_24h": 200, "total": 5000 },
    "model_calls": {
      "total": 1200,
      "total_today": 45,
      "by_purpose": {
        "qa_answer": { "count": 800, "failed": 5 },
        "sentiment_analysis": { "count": 300, "failed": 2 },
        "connection_test": { "count": 100, "failed": 10 }
      },
      "avg_latency_ms": 850.5,
      "avg_total_tokens": 1250.3
    },
    "collection_health": {
      "total_success": 9500,
      "total_failure": 120,
      "success_rate": 98.8,
      "recent_failures_7d": 3
    },
    "sentiment_summary": {
      "latest_task_name": "五月舆情分析",
      "latest_status": "completed",
      "risk_level": "低",
      "summary_snippet": "整体舆情态势平稳，主要话题集中在...",
      "completed_at": "2026-05-31T12:05:00Z"
    },
    "source_distribution": [
      { "source_name": "新闻API", "source_type": "web_api", "item_count": 450, "status": "active" },
      { "source_name": "论坛爬虫", "source_type": "web_page", "item_count": 230, "status": "active" }
    ],
    "updated_at": "2026-05-31T12:00:00Z"
  },
  "meta": { "request_id": "uuid" }
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `knowledge_items` | object | 知识项总数及按状态分布 |
| `watch_sources` | object | 数据源总数及按状态分布 |
| `collection_tasks` | object | 采集任务总数及按状态分布 |
| `qa_sessions` | object | 问数会话总数及按状态分布 |
| `users` | object | 用户总数及今日活跃数 |
| `chat_messages` | object | 聊天消息总数 |
| `model_calls` | object | 模型调用统计：总数、今日数、按用途分组、平均延迟、平均 token 消耗 |
| `collection_health` | object | 采集健康度：成功/失败总数、成功率、近7天失败数 |
| `sentiment_summary` | object\|null | 最新舆情分析摘要：任务名称、风险等级（低/中/高）、摘要片段 |
| `source_distribution` | array | 数据源知识项分布 Top 15：数据源名称、类型、数量、状态 |
| `updated_at` | string | 聚合时间戳 |

### `GET /dashboard/trends`

返回指定天数的日趋势数据。

**查询参数**：

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `days` | integer | 30 | 回溯天数，最大 90 |

**响应示例**：

```json
{
  "data": {
    "knowledge_items": [
      { "date": "2026-05-01", "count": 10 },
      { "date": "2026-05-02", "count": 5 }
    ],
    "qa_questions": [
      { "date": "2026-05-01", "count": 3 }
    ],
    "chat_messages": [
      { "date": "2026-05-01", "count": 45 }
    ],
    "model_calls": [
      { "date": "2026-05-01", "count": 30 },
      { "date": "2026-05-02", "count": 25 }
    ],
    "model_tokens": [
      { "date": "2026-05-01", "count": 45000 },
      { "date": "2026-05-02", "count": 38000 }
    ]
  },
  "meta": { "request_id": "uuid" }
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `knowledge_items` | array | 每日知识项入库数 |
| `qa_questions` | array | 每日用户问数问题数 |
| `chat_messages` | array | 每日聊天消息数 |
| `model_calls` | array | 每日模型调用次数（新增） |
| `model_tokens` | array | 每日 token 消耗总量（新增） |

### `GET /dashboard/keywords`

返回从知识内容中提取的高频关键词。

**查询参数**：

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `limit` | integer | 50 | 返回关键词数量 |

**响应示例**：

```json
{
  "data": [
    { "word": "人工智能", "count": 120 },
    { "word": "数据", "count": 85 }
  ],
  "meta": { "request_id": "uuid" }
}
```

## 舆情分析任务

| 方法 | 路径 | 权限 | CSRF | 说明 |
| --- | --- | --- | --- | --- |
| `POST` | `/sentiment/tasks` | `sentiment.manage` | ✓ | 创建并自动执行分析任务 |
| `GET` | `/sentiment/tasks` | `sentiment.view` | - | 任务列表 |
| `GET` | `/sentiment/tasks/{id}` | `sentiment.view` | - | 任务详情（含报告） |
| `GET` | `/sentiment/reports/{id}` | `sentiment.view` | - | 报告详情 |

### `POST /sentiment/tasks`

创建并自动执行舆情分析任务。创建即同步执行，响应返回任务结果和报告。

**请求体**：

```json
{
  "name": "五月舆情分析",
  "scope": "data_warehouse",
  "data_scope": {
    "start_date": "2026-05-01",
    "end_date": "2026-05-31",
    "source_ids": ["src1", "src2"]
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `name` | string | 是 | 任务名称，1-120 字符 |
| `scope` | string | 是 | 分析范围：`chat`(聊天分析)、`data_warehouse`(数据仓库分析) |
| `data_scope` | object | 否 | 数据范围：`start_date`/`end_date`/`source_ids` |

**响应** `200`：

```json
{
  "data": {
    "id": "task-uuid",
    "name": "五月舆情分析",
    "scope": "data_warehouse",
    "status": "completed",
    "progress": 100,
    "source_item_count": 80,
    "created_at": "2026-05-31T12:00:00Z",
    "completed_at": "2026-05-31T12:05:00Z",
    "reports": [
      {
        "id": "report-uuid",
        "report_type": "summary",
        "summary_text": "完整的分析报告文本（markdown 格式）",
        "report_data": {
          "raw": "完整的分析报告文本（与 summary_text 相同）"
        }
      }
    ]
  },
  "meta": { "request_id": "uuid" }
}
```

### `GET /sentiment/tasks`

分页列表。

**查询参数**：`page`、`page_size`、`status`（可选过滤）

**响应**：

```json
{
  "data": [
    {
      "id": "task-uuid",
      "name": "五月舆情分析",
      "scope": "data_warehouse",
      "status": "completed",
      "progress": 100,
      "source_item_count": 80,
      "created_at": "2026-05-31T12:00:00Z",
      "completed_at": "2026-05-31T12:05:00Z"
    }
  ],
  "meta": { "page": 1, "page_size": 20, "total": 1, "request_id": "uuid" }
}
```

### `GET /sentiment/tasks/{id}`

任务详情，含关联的报告列表。

**响应**：

```json
{
  "data": {
    "id": "task-uuid",
    "name": "五月舆情分析",
    "scope": "data_warehouse",
    "status": "completed",
    "progress": 100,
    "source_item_count": 80,
    "created_by": { "id": "user-uuid", "display_name": "管理员" },
    "created_at": "2026-05-31T12:00:00Z",
    "started_at": "2026-05-31T12:00:01Z",
    "completed_at": "2026-05-31T12:05:00Z",
    "reports": [
      {
        "id": "report-uuid",
        "report_type": "summary",
        "summary_text": "完整的分析报告文本...",
        "report_data": {"raw": "完整的分析报告文本..."},
        "source_item_count": 80,
        "created_at": "2026-05-31T12:05:00Z"
      }
    ]
  },
  "meta": { "request_id": "uuid" }
}
```

### `GET /sentiment/reports/{id}`

获取单份报告详情。结构与上方 `report_data` 一致。
```

### `GET /sentiment/tasks`

分页列表。

**查询参数**：`page`、`page_size`、`status`（可选过滤）

**响应**：

```json
{
  "data": [
    {
      "id": "task-uuid",
      "name": "五月舆情分析",
      "task_type": "full",
      "status": "completed",
      "progress": 100,
      "source_item_count": 80,
      "created_at": "2026-05-31T12:00:00Z",
      "completed_at": "2026-05-31T12:05:00Z"
    }
  ],
  "meta": { "page": 1, "page_size": 20, "total": 1, "request_id": "uuid" }
}
```

### `GET /sentiment/tasks/{id}`

任务详情，含关联报告摘要。

**响应**：

```json
{
  "data": {
    "id": "task-uuid",
    "name": "五月舆情分析",
    "task_type": "full",
    "data_scope": { "start_date": "2026-05-01", "end_date": "2026-05-31" },
    "include_chat_data": false,
    "status": "completed",
    "progress": 100,
    "error_message": null,
    "source_item_count": 80,
    "created_by": { "id": "user-uuid", "display_name": "管理员" },
    "created_at": "2026-05-31T12:00:00Z",
    "started_at": "2026-05-31T12:00:01Z",
    "completed_at": "2026-05-31T12:05:00Z",
    "reports": [
      { "id": "report-uuid", "report_type": "summary", "summary_text": "摘要内容...", "created_at": "..." }
    ]
  },
  "meta": { "request_id": "uuid" }
}
```

### `POST /sentiment/tasks/{id}/run`

手动运行或重跑指定任务。

**请求体**：无

**响应**：

```json
{
  "data": { "id": "task-uuid", "status": "running" },
  "meta": { "request_id": "uuid" }
}
```

### `GET /sentiment/tasks/{id}/reports`

获取指定任务的所有分析报告。

**响应**：

```json
{
  "data": [
    {
      "id": "report-uuid",
      "report_type": "sentiment",
      "report_data": {
        "positive": 45,
        "neutral": 30,
        "negative": 25,
        "details": [
          { "content_title": "标题", "sentiment": "positive", "confidence": 0.92 }
        ]
      },
      "summary_text": "整体情感倾向偏正面",
      "source_item_count": 80,
      "period_start": "2026-05-01",
      "period_end": "2026-05-31",
      "created_at": "2026-05-31T12:05:00Z"
    }
  ],
  "meta": { "request_id": "uuid" }
}
```

### `GET /sentiment/reports/{id}`

获取单份报告详情。结构与上方 `report_data` 一致。

## 错误码

| HTTP | 错误代码 | 场景 |
| --- | --- | --- |
| 400 | `VALIDATION_ERROR` | 参数不合法 |
| 403 | `PERMISSION_DENIED` | 权限不足 |
| 404 | `NOT_FOUND` | 任务或报告不存在 |
| 422 | `MODEL_UNAVAILABLE` | 未配置默认模型 |

## 数据安全

- Dashboard 统计仅返回聚合数值，不暴露单个用户或会话内容。
- 聊天数据只有在 `include_chat_data=true` 时且当前用户仍有群成员身份时才纳入分析。
- 舆情分析报告不包含模型原始 prompt 或完整知识内容；`summary_text` 是 AI 生成的摘要。
