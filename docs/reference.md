# HAP SaaS：个人 MCP 固定参数

以下适用于 **明道云 HAP SaaS**（公网）。私有化部署另以实际域名为准。

## 域名与端点

| 用途 | 值 |
|------|-----|
| Web 站点根（登录页同源） | `https://www.mingdao.com` |
| API 根（integration 接口） | `https://api.mingdao.com` |
| MCP 服务 URL 模板（脚本默认） | `https://api2.mingdao.com/mcp?Authorization=Bearer {access_token}` |

## 官方个人 MCP 集成应用

生成个人 MCP 时，`--oauth-app-id` 及 OAuth authorize 请求体 `{"id":"…"}` 使用 **官方固定集成应用 id**（与 README、`generate_mcp_config` 示例一致）：

`69bcae07257900ec41aa2733`

## 相关接口路径（均相对 `API 根`）

| 说明 | 路径 |
|------|------|
| OAuth2 授权（取 `oauth2Url`） | `POST /integration/oauth2/authorize`，body `{"id":"<集成应用id>"}` |
| 已授权账号列表 | `POST /integration/oauth2/getAllAccessTokenList`，body `{"id":"<集成应用id>"}` |
| 换票 / token 日志 | `POST /integration/oauth2/getRefreshTokenLogs`，body 中账号 id 为列表条目 id |

## 环境变量（与脚本默认值一致时可省略）

- `MINGDAO_BASE_URL` → Web 站点根  
- `MINGDAO_API_BASE_URL` → API 根  
- `MINGDAO_MCP_URL_TEMPLATE` → MCP URL 模板  
