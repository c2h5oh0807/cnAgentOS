# WebSocket 实时通信协议

> 本文档定义 cnAgentOS 聊天模块的 WebSocket 消息协议。实现阶段：Phase 6。

## 端点

```
ws://host/api/v1/ws              # 开发环境
wss://host/api/v1/ws             # 生产环境
```

## 鉴权

WebSocket 握手时复用 HTTP Cookie 中的会话令牌：

- Cookie 名：`cnagentos_session`（开发）或 `__Host-cnagentos_session`（生产）
- 服务端在 upgrade 阶段验证 Cookie，鉴权失败返回 4001 关闭码
- 非浏览器客户端支持 `?token=` 查询参数回退

## 消息帧格式

所有消息使用 JSON 文本帧，统一信封：

```json
{
  "type": "<event_type>",
  "payload": { ... },
  "id": "<optional_uuid>"
}
```

## 服务端推送事件

### `connected`
连接建立成功后的首帧：
```json
{ "type": "connected", "payload": { "user_id": "...", "username": "..." } }
```

### `new_message`
新消息推送（私聊或群聊）：
```json
{
  "type": "new_message",
  "payload": {
    "message_id": "...",
    "conversation_id": "...",
    "sender_id": "...",
    "sender_name": "...",
    "content_type": "text|image|file|system",
    "content": "消息文本或系统描述",
    "file_id": null,
    "reply_to_id": null,
    "created_at": "2026-06-01T00:00:00Z"
  }
}
```

### `message_read`
消息已读回执：
```json
{
  "type": "message_read",
  "payload": { "message_id": "...", "user_id": "...", "read_at": "..." }
}
```

### `friend_request`
好友请求通知：
```json
{
  "type": "friend_request",
  "payload": { "request_id": "...", "from_user_id": "...", "from_user_name": "...", "status": "pending" }
}
```

### `typing`
输入状态：
```json
{ "type": "typing", "payload": { "conversation_id": "...", "user_id": "...", "is_typing": true } }
```

### `presence`
在线状态变化：
```json
{ "type": "presence", "payload": { "user_id": "...", "status": "online|offline" } }
```

### `error`
异常信息：
```json
{ "type": "error", "payload": { "code": "ERROR_CODE", "message": "..." } }
```

## 客户端发送消息

### `send_message`
发送聊天消息：
```json
{
  "type": "send_message",
  "payload": {
    "conversation_id": "...",
    "content_type": "text|image|file",
    "content": "消息文本",
    "file_id": null,
    "reply_to_id": null
  },
  "id": "client-generated-uuid"
}
```

服务端响应 `new_message` 事件，包含服务端分配的 `message_id`。

### `mark_read`
标记消息已读：
```json
{
  "type": "mark_read",
  "payload": { "conversation_id": "...", "last_read_message_id": "..." }
}
```

### `typing`
发送输入状态：
```json
{
  "type": "typing",
  "payload": { "conversation_id": "...", "is_typing": true }
}
```

### `ping`
心跳保持：
```json
{ "type": "ping" }
```

服务端响应 `pong`。

## 心跳

- 服务端每 30 秒发送 `ping`
- 客户端须在 10 秒内回复 `pong`
- 超时关闭连接

## 断线重连

- 客户端使用指数退避重连（1s → 2s → 4s → ... → 30s cap）
- 重连后通过 `GET /api/v1/chat/messages?after=<last_message_id>` 补拉离线消息
