---
name: mingdao-mcp-login
description: >-
  通过 HAP OAuth 应用授权，生成个人权限的 MCP JSON；必要时引导浏览器 OAuth。
  触发词：配置/更新 HAP MCP、明道 MCP、个人 MCP、Bearer、账号密码接入 HAP。
---

# HAP 个人 MCP

## 需要向用户确认

- **账号**：邮箱或手机号；大陆手机用 **`+8613…`**，勿只填 11 位。
- **密码**：不在对话里复述；优先用环境变量 `MINGDAO_ACCOUNT` / `MINGDAO_PASSWORD`（见 `README.md`）。
- **环境**：默认 **HAP SaaS**；固定域名、官方集成应用 id、接口路径见 **`docs/reference.md`**（勿把 id 写进本 skill 正文）。

执行脚本时 `--oauth-app-id` 仍必填：从 **`docs/reference.md`** 取 SaaS 官方个人 MCP 的固定 id。

## 流程（克隆本仓库后的根目录）

先安装依赖（任选其一）：

```bash
bash scripts/install.sh
```

或：`pip install -e .`（需 Python 3.10+）；或 `pip install -r requirements.txt` 后仅用 `python3 -m mingdao_mcp_login.*`（无需 editable 安装）。

**1. 生成（优先）**

```bash
.venv/bin/md-generate-mcp-config \
  --account "<账号>" --password "<密码>" --oauth-app-id "<集成应用id>" \
  --skip-wait
```

未用 venv 时：`python3 -m mingdao_mcp_login.generate_mcp_config`（参数相同）。

- stdout 出现 **MCP JSON** → 按下文「交付与回复技巧」交给用户。
- 需首次授权：stderr 会打印授权 URL → 用户浏览器完成 OAuth 后，**再执行同一条命令**。

**2. 只要授权链接时**

```bash
.venv/bin/md-mingdao-login --account "..." --password "..." --oauth-app-id "..."
```

或：`python3 -m mingdao_mcp_login.md_login`（参数相同）。

从输出取 **`oauth2Url`**；授权完成后再跑 **1**。

## 交付与回复技巧

**给用户的内容**

1. **stdout 的 JSON 原样**放在代码块里，便于一键复制；成功时顶层 key 默认为 **`HAP Personal MCP`**（脚本 `--mcp-key`，可用环境变量 `MINGDAO_MCP_KEY` 覆盖）。
2. **少说背景**：一两句即可，例如「已生成个人 MCP 配置，粘贴到 MCP 客户端」；不要展开流程说明、不要复述命令参数细节。交付后可补一句：**Token 会过期，下次要刷新时告诉我**——不要补充环境变量示例、`docs/reference.md`、改密等。
3. **不要写进回复**：集成应用 id、OAuth 应用 id、具体 Bearer / token 片段（JSON 里不可避免的 URL 除外，那是交付物本身）；id 只从 **`docs/reference.md`** 读取供执行脚本，对用户用「官方个人 MCP 集成」等泛指即可。
4. **结构**：优先「短说明 + JSON」；需要步骤时再列 1～3 条，避免长段落与重复句。
5. **排版**：非必要不用粗体；列表适度，便于扫读。

## 排错

参数与退出码见根目录 `README.md`。
