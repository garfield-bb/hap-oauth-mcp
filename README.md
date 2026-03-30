# 生成 HAP 个人授权 MCP

帮你获取和更新 HAP 个人授权 MCP 配置，无需手动操作 OAuth 流程。

> 在 HAP AI Connect 功能正式推出前（让用户能更便捷地将 HAP 的 Skill、MCP、CLI 与各 AI 工具相接），您可以通过本 Skill 来获取/更新个人 MCP，体验HAP API（个人授权） MCP 价值。

---

## 什么是 HAP 个人授权

HAP 提供了一套标准 OAuth 2.0 授权机制，允许用户授权第三方应用以**用户自身身份**安全访问或操作 HAP 中的数据。这不仅是一次授权方式的升级，更是 HAP 从「系统能力开放」走向「用户级能力开放」的关键基础设施。

1. 从"系统授权"升级为"用户授权" — 从「应用权限执行」转变为「用户身份执行」
2. 更细粒度的权限控制（Scope） — 权限最小化，指定资源与操作范围
3. 短生命周期凭证，降低安全风险 — Token 默认 1 天，可轮换，泄露影响有限
4. 用户可随时撤销授权 — 权限从「不可回收」变为可控、可撤销、可管理
5. 每一次调用都有明确身份归属 — 支持审计与合规追踪、用户行为分析

---

## 使用指南

详细使用步骤见：[个人权限 MCP 使用指南](https://www.kdocs.cn/l/ckhEnu77nbhl)

---

## 你需要准备什么

只需要你的 **HAP 账号和密码**（邮箱或手机号登录）。

---

## 安装 Skill

### Claude Code

```bash
claude skill add --name hap-oauth-mcp https://github.com/garfield-bb/hap-oauth-mcp.git
```

### Cursor / 其他 AI 工具

在对话中直接说：

> 帮我安装这个 skill：https://github.com/garfield-bb/hap-oauth-mcp.git

---

## 使用方式

安装后，直接告诉 AI：

> 帮我配置 HAP 个人 MCP，账号 `your@email.com`，密码 `xxx`

AI 会自动完成登录、OAuth 授权、获取 token，最终返回可直接粘贴到 MCP 客户端的配置 JSON：

```json
{
  "HAP Personal MCP": {
    "url": "https://api2.mingdao.com/mcp?Authorization=Bearer <your_token>"
  }
}
```

若是首次授权，AI 会引导你在浏览器完成一次 OAuth 确认，之后刷新 token 无需再次操作。

---

## 安全说明

所有代码**本地执行**，账号密码不会经过任何第三方服务。技术路径：本地调用 HAP 登录接口（与网页端相同的 RSA 加密），再通过官方 OAuth 集成接口获取和刷新 token。

---

## 许可

MIT
