# mingdao-mcp-login

公开可安装的 **Agent Skill** 仓库：用**邮箱或手机号 + 密码**登录明道云，经官方 **OAuth 集成应用**授权后，生成 **Cursor / MCP 客户端**可用的个人 MCP JSON（`Bearer` 接入 `api2.mingdao.com/mcp`）。

实现要点：`POST /api/Login/MDAccountLogin`（与 Web 端相同的 RSA 加密）、`integration/oauth2/*` 拉授权与 token，与 [hap-oauth-mcp](https://github.com/garfield-bb/hap-oauth-mcp)（Playwright 抓 `md_pss_id` / Cookie）互补——本仓库走 **HTTP API**，无需浏览器自动化。

## 快速安装（作为 AI Skill）

### Claude Code

```bash
claude skill add --name mingdao-mcp-login https://github.com/garfield-bb/hap-oauth-mcp.git
```

安装后提到「配置 HAP MCP」「生成个人 MCP」等会触发根目录 **`SKILL.md`**。

### Cursor / Codex / 其他支持 `SKILL.md` 的工具

```bash
git clone https://github.com/garfield-bb/hap-oauth-mcp.git
```

把本仓库路径加入对应工具的 skill 目录，或直接在克隆目录里按 **`SKILL.md`** 操作。

### 仅安装 Python 包（pip）

```bash
pip install git+https://github.com/garfield-bb/hap-oauth-mcp.git
```

安装后可使用命令 `md-mingdao-login`、`md-generate-mcp-config`。

## 本地环境

```bash
bash scripts/install.sh
```

会在仓库根目录创建 `.venv` 并以可编辑方式安装 `mingdao-mcp-login`。需要 **Python 3.10+**。

若不想安装包本身，也可只装依赖后在仓库根目录用模块方式运行：

```bash
pip install -r requirements.txt
python3 -m mingdao_mcp_login.generate_mcp_config --help
```

## 一键生成 MCP 配置

SaaS 官方个人 MCP 的集成应用 id 见 **`docs/reference.md`**（勿在公开场合复述为「敏感信息」，但执行脚本时必须传入 `--oauth-app-id`）。

```bash
.venv/bin/md-generate-mcp-config \
  --account "your@mingdao.com" \
  --password "your_password" \
  --oauth-app-id "<见 docs/reference.md>" \
  --skip-wait
```

未使用 venv 时：

```bash
python3 -m mingdao_mcp_login.generate_mcp_config \
  --account "..." --password "..." --oauth-app-id "..." --skip-wait
```

- 若已有有效授权，stdout 直接输出 MCP JSON。
- 若需首次授权：按提示在浏览器完成 OAuth；可用 `--no-open-browser` 仅打印 URL；非交互环境用 `--skip-wait` 并在授权后**再执行一次**同一命令。

调试接口：

```bash
python3 -m mingdao_mcp_login.generate_mcp_config --account "..." --password "..." --oauth-app-id "..." --dump-api
```

环境变量：`MINGDAO_ACCOUNT`、`MINGDAO_PASSWORD`、`MINGDAO_OAUTH_APP_ID`、`MINGDAO_BASE_URL`、`MINGDAO_API_BASE_URL`、`MINGDAO_MCP_KEY`、`MINGDAO_MCP_URL_TEMPLATE` 等（与命令行混用时命令行优先）。

**退出码**：`0` 成功；`2` 参数不全；`3` 登录失败；`4` 拿不到 `oauth2Url`；`5` `getAllAccessTokenList` 失败；`6` 账号列表为空或无法解析账号 id；`7` `getRefreshTokenLogs` 失败；`8` 未解析到 `access_token`。

## 仅登录 / 只要授权链接

```bash
.venv/bin/md-mingdao-login --account "your@email.com" --password "your_password"
```

带集成应用 id 时在登录后再请求 authorize，JSON 中含 **`oauth2Url`**：

```bash
.venv/bin/md-mingdao-login --account "..." --password "..." --oauth-app-id "<见 docs/reference.md>"
```

**退出码**：`0` 成功；`1` 网络/HTTP 错误；`2` 缺参；`3` 未解析到 `md_pss_id`；`4` OAuth authorize 失败。

## 仓库结构

| 路径 | 说明 |
|------|------|
| `SKILL.md` | 供 Claude Code / Cursor 等加载的 Skill 入口 |
| `mingdao_mcp_login/` | Python 包：登录、OAuth 集成 API、生成 MCP JSON |
| `docs/reference.md` | HAP SaaS 固定域名与官方个人 MCP 集成 id |
| `scripts/install.sh` | 创建 venv 并 `pip install -e .` |

## 用新内容覆盖 GitHub 上旧仓库

若远程已有历史提交、希望**整库替换**为当前结构，在本地初始化并强制推送（**会改写远程历史**，协作者需重新克隆）：

```bash
cd /path/to/hap-oauth-mcp
git init
git add .
git commit -m "chore: publish mingdao-mcp-login skill layout"
git branch -M main
git remote add origin https://github.com/garfield-bb/hap-oauth-mcp.git
git push -u origin main --force
```

若更倾向保留历史，可用普通 `git push` 提交一次大变更，不必 `--force`。

## 安全提示

- 勿在仓库、命令历史或聊天中明文保存密码。
- `md_pss_id` 与 MCP 用的 `access_token` 均属高敏感凭据，泄露后请尽快在网页端退出或轮换。

## 许可

MIT，见 `LICENSE`。
