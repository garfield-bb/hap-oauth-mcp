# HAP 个人授权 MCP — AI Skill

帮你获取和更新 **HAP 个人授权 MCP 配置**，一句话搞定，无需手动操作 OAuth 流程。

## 什么是 HAP 个人授权

HAP 提供了一套标准 OAuth 2.0 授权机制，允许用户通过授权第三方应用，以用户身份权限安全访问或操作用户在 HAP 中的数据。

个人授权 MCP 配置形如：

```json
{
  "HAP Personal MCP": {
    "url": "https://api2.mingdao.com/mcp?Authorization=Bearer <your_token>"
  }
}
```

将其添加到你的 MCP 客户端（Cursor、Claude Code 等），即可以个人身份通过 AI 访问 HAP 数据。

## 你需要准备什么

只需要你的 **HAP 账号和密码**（邮箱或手机号登录）。

## 安装 Skill

### Claude Code

```bash
claude skill add --name hap-oauth-mcp https://github.com/garfield-bb/hap-oauth-mcp.git
```

### Cursor / 其他支持 SKILL.md 的工具

```bash
git clone https://github.com/garfield-bb/hap-oauth-mcp.git
```

将克隆路径添加到对应工具的 skill 目录即可。

## 使用方式

安装后，直接告诉 AI：

> 帮我配置 HAP 个人 MCP，账号 `your@email.com`，密码 `xxx`

AI 会自动完成登录、OAuth 授权、获取 token，最终返回可直接粘贴到 MCP 客户端的配置 JSON。

若是首次授权，AI 会引导你在浏览器完成一次 OAuth 确认，之后刷新 token 无需再次操作。

## 安全说明

- **所有代码本地执行**，账号密码不会上传或经过任何第三方服务
- 技术路径：本地调用 HAP 登录接口（与网页端相同的 RSA 加密），再通过官方 OAuth 集成接口获取和刷新 token
- 请勿将账号密码明文保存在聊天记录或仓库中；建议通过环境变量传入：`MINGDAO_ACCOUNT` / `MINGDAO_PASSWORD`

## 许可

MIT
