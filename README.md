# 群聊摘要与待办提取器（Group Chat Digest）

> AI4SE 期末项目（B 类·应用类项目）

一个把班级群聊从消息洪流里抽出每日摘要与可执行待办的小工具。后端基于 FastAPI，LLM 层支持 Mock / DeepSeek / OpenAI 兼容协议，前端为单页 HTML。生产部署使用 Docker + Render（备选 Fly.io）。

## 功能

- 上传群聊导出（JSON / 纯文本），生成结构化每日摘要
- 抽取待办事项（负责人 / 截止日 / 优先级）
- LLM 提供者可热切换：Mock（演示）、DeepSeek、OpenAI 兼容
- WebUI 在线查看，REST API 对外开放

## 项目结构

```
app/                # FastAPI 后端
  adapters/         # LLM 适配器（mock/deepseek/openai）
  routers/          # API 路由
  parsers/          # 群聊解析器
  services/         # 业务编排
  frontend/         # 单页前端
data/               # Mock 数据 + SQLite DB（运行时生成）
scripts/            # 工具脚本（导入/批处理）
run/                # 运行配置
tests/              # 单测 + e2e
Dockerfile          # 生产镜像
docker-compose.yml  # 本地全栈
render.yaml         # Render 部署（Blueprint IaC）
fly.toml            # 备选：Fly.io 部署
```

## 本地开发

```bash
# 安装依赖（含 dev）
uv sync --extra dev

# 跑测试
uv run pytest

# 启动开发服务器（热重载）
uv run uvicorn app.main:app --reload --port 8000
```

打开 http://localhost:8000 即可访问 WebUI。

## Docker

```bash
# 构建镜像
docker build -t group-chat-digest:dev .

# 启动（Mock LLM）
docker run -p 8000:8000 -e LLM_PROVIDER=mock group-chat-digest:dev

# 或用 docker compose 一键起全栈
docker compose up
```

健康检查：`curl http://localhost:8000/healthz` → `{"status":"ok"}`。

## Render 部署（首选）

Render 是本项目的默认生产部署目标。配置已写入 `render.yaml`（Blueprint IaC），无需安装任何 CLI——所有操作在浏览器 dashboard 完成。

**生产 URL**：**<https://group-chat-digest.onrender.com>**

### 首次部署（一次性，浏览器操作）

1. <https://render.com> → Sign up → 用 GitHub 账号登录
2. New → **Blueprint** → 选择已连接的 GitHub 仓库 `zyl32/group-chat-digest`
3. Render 自动识别 `render.yaml` → 显示配置预览 → Apply
4. 等待 build 完成（5–10 min，首次会拉基础镜像较慢）→ 拿到 URL `https://group-chat-digest.onrender.com`
5. 验证：`curl https://group-chat-digest.onrender.com/healthz` → `{"status":"ok"}`

### 后续部署

`main` 分支一 push，Render 通过 GitHub webhook 自动触发部署。**不需要 CI deploy job**——这与 Fly.io 不同（Fly 需要 `fly deploy --remote-only` CI job）。

### （可选）切换为真实 LLM

Render dashboard → Environment → Add Environment Variable：

- `LLM_PROVIDER` = `deepseek`
- `DEEPSEEK_API_KEY` = `sk-xxxxxxxx`（勾选 "Secret" 不在界面回显）

保存后 Render 自动重启服务，无需重新部署。

### 已知限制：凭据保险库

T13/T19 的凭据存储使用 `OSKeyringVault`（操作系统 keyring）。Render Linux 容器无桌面 keyring 后端，因此：

- `/api/credentials/llm_api_key/status` 在 Render 上返回 `{"configured": false}`
- `/api/credentials/llm_api_key` POST 会失败（KeyringError）

**演示用**：使用 `LLM_PROVIDER=mock`（无需 API key）。
**生产用**：通过 Render 环境变量注入 `DEEPSEEK_API_KEY`，并扩展 LLM 适配器工厂使其优先从 env 读取（v1.1 stretch goal）。

### 配置要点

- `runtime: docker` 复用本仓库 `Dockerfile`，无单独构建脚本
- `plan: free` 单用户演示足够（512MB RAM / 0.1 CPU）
- `region: singapore` 对中国大陆延迟友好（备选 `frankfurt` / `oregon`）
- `healthCheckPath: /healthz` Render 用它判断服务健康状态
- `disk: 1GB /app/data` 挂载持久卷——SQLite 数据库 + 上传文件跨部署持久化
- `autoDeploy: true` main push 自动重新部署
- `LLM_PROVIDER=mock` 默认值，首次部署即可演示

> **服务名冲突**：若 `group-chat-digest` 在 Render 上已被占用，请修改 `render.yaml` 的 `name` 字段为唯一名称（如 `group-chat-digest-<your-handle>`），并相应更新本文档中的 URL。

## 备选：Fly.io 部署

Fly.io 是备选部署目标，配置已写入 `fly.toml`。需要安装 `flyctl` CLI。

### 首次部署（一次性，需人工执行）

```bash
# 1. 安装 flyctl（macOS/Linux）
curl -L https://fly.io/install.sh | sh
# Windows PowerShell:
# iex "& {$(irm https://fly.io/install.ps1)}"

# 2. 登录
fly auth login

# 3. 部署（首次会自动创建应用并分配 IP/域名）
fly deploy

# 4. （可选）切换为真实 LLM
fly secrets set LLM_PROVIDER=deepseek
fly secrets set DEEPSEEK_API_KEY=sk-xxxxxxxx
```

> **应用名冲突**：若 `group-chat-digest` 在 Fly.io 上已被占用，请修改 `fly.toml` 的 `app` 字段为唯一名称（如 `group-chat-digest-<your-handle>`），并相应更新本文档中的 URL。

> **注意**：本仓库**未**自动执行 `fly deploy`。CI 仅在 `main` 分支推送时触发 `fly deploy --remote-only`，前提是 GitHub Secret `FLY_API_TOKEN` 已配置。首次部署需由仓库所有者在本地手动执行 `fly deploy` 一次以创建应用。

### 配置要点

- `primary_region = "nrt"`（东京，对中国大陆延迟相对友好；备选 `hkg`）
- `internal_port = 8000` 与 Dockerfile `EXPOSE 8000` 一致
- `auto_stop_machines = true` + `min_machines_running = 0`：单用户场景的成本优化（闲置自动停机）
- `[[mounts]]` 挂载 `data_volume` 到 `/app/data`：SQLite 数据库跨部署持久化（不挂载则每次部署丢数据）
- `LLM_PROVIDER=mock` 为默认值，首次部署即可演示；真实 LLM 通过 `fly secrets set` 注入

### 已知限制：凭据保险库

T13/T19 的凭据存储使用 `OSKeyringVault`（操作系统 keyring）。Fly.io Linux 机器没有桌面 keyring 后端，因此：

- `/api/credentials/llm_api_key/status` 在 Fly.io 上将返回 `{"configured": false}`
- `/api/credentials/llm_api_key` POST 会失败

**演示用**：使用 `LLM_PROVIDER=mock`（无需 API key）。
**生产用**：通过 `fly secrets set DEEPSEEK_API_KEY=...` 注入环境变量，并扩展 LLM 适配器工厂使其优先从 env 读取。完整的 Fly.io 凭据管理为 v1.1 stretch goal，本期不实现。

## 安全边界说明

本项目凭据管理遵循 §3.1 硬约束：

- **绝不硬编码**：API key 不进源码、不进 git（含历史）、不进日志、不进终端 history、不进明文配置文件
- **存储介质**：`OSKeyringVault`（macOS Keychain / Windows Credential Manager / Linux SecretService）作为默认 vault；`InMemoryVault` 仅用于测试
- **传输路径**：`.env` 文件加载（不通过命令行 `export`）；首次运行通过 `/setup` 页面隐藏输入引导录入
- **状态可见性**：`GET /api/credentials/llm_api_key/status` 只返 `{"configured": bool}`，**不回显明文**
- **生命周期**：store / status / clear 三个端点，clear 用于轮换
- **威胁模型与对策**：详见 `SPEC.md` §3.1

**已知边界**（v1）：

- Fly.io / Render Linux 容器均无桌面 keyring 后端，`OSKeyringVault` 不可用 → 生产 LLM key 需用平台环境变量注入（Render dashboard Environment / `fly secrets set`，v1.1 stretch：env-var vault backend）
- WebUI 无身份认证（单用户演示场景）；多用户部署需自行加反向代理鉴权

## 线上 URL

- **目标 URL**：<https://group-chat-digest.onrender.com>（Render，首选）
- **备选 URL**：<https://group-chat-digest.fly.dev>（Fly.io，可选）
- **当前状态**：**未实际部署**——`render.yaml` Blueprint 配置已就绪，待仓库所有者在 Render dashboard 完成首次连接（浏览器操作，无需 CLI）。Render 连上 GitHub repo 后，后续 `main` push 自动部署。
- **本地访问**：`uv run uvicorn app.main:app --reload --port 8000` → <http://localhost:8000>
- **Docker 本地**：`docker compose up` → <http://localhost:8000>

## CI

GitHub Actions 工作流 `.github/workflows/ci.yml`：

| Job | 触发 | 作用 |
|-----|------|------|
| `unit-test` | push/PR to main | `uv run pytest -v --cov=app`（§五-6 必需） |
| `docker-build` | push/PR to main | 构建 Docker 镜像 + 容器冒烟测试 `/healthz` |
| `deploy` (备选) | push to main（仅） | `fly deploy --remote-only`，依赖 `FLY_API_TOKEN` Secret；未配置时 graceful skip |

> **Render 部署不依赖 CI**：Render 通过自己的 GitHub webhook 监听 `main` push 并自动部署，无需 CI job。`deploy` job 仅服务于备选 Fly.io 路径，未配 `FLY_API_TOKEN` 时会失败但不影响 `unit-test` / `docker-build`。

`deploy` job 需要仓库 Settings → Secrets → Actions 中配置 `FLY_API_TOKEN`（在本地执行 `fly tokens create deploy -a group-chat-digest` 生成）。

## 状态

- [x] SPEC.md
- [x] PLAN.md
- [x] 实现完成
- [x] AGENT_LOG.md
- [x] SPEC_PROCESS.md（冷启动验证）
- [x] REFLECTION.md
- [x] CI 配置（unit-test + docker-build + 备选 deploy）
- [x] 线上部署配置（`render.yaml` 首选 + `fly.toml` 备选）
- [ ] 实际部署上线（需用户在 Render dashboard 完成 Blueprint 连接）

## 工作流

按 Superpowers 七步工作流推进：brainstorming → writing-plans → using-git-worktrees → subagent-driven-development → test-driven-development → requesting-code-review → finishing-a-development-branch。
