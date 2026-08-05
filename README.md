# 群聊摘要与待办提取器（Group Chat Digest）

> AI4SE 期末项目（B 类·应用类项目）

一个把班级群聊从消息洪流里抽出每日摘要与可执行待办的小工具。后端基于 FastAPI，LLM 层支持 Mock / DeepSeek / OpenAI 兼容协议，前端为单页 HTML。生产部署使用 Docker + Fly.io。

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
fly.toml            # Fly.io 部署
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

## Fly.io 部署

Fly.io 部署使用 T23 产出的 `Dockerfile`，由 Fly.io BuildKit 远程构建。生产 URL：**<https://group-chat-digest.fly.dev>**

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

- Fly.io Linux 机器无桌面 keyring 后端，`OSKeyringVault` 不可用 → 生产 LLM key 需用 `fly secrets set` 注入环境变量（v1.1 stretch：env-var vault backend）
- WebUI 无身份认证（单用户演示场景）；多用户部署需自行加反向代理鉴权

## 线上 URL

- **目标 URL**：<https://group-chat-digest.fly.dev>
- **当前状态**：**未实际部署**——CI deploy job 已配置（`fly deploy --remote-only`，gated on `main` push + `FLY_API_TOKEN` secret），但首次部署需仓库所有者本地执行 `fly deploy` 一次以创建应用。本仓库无 Fly.io 账号，故 URL 尚未激活。
- **本地访问**：`uv run uvicorn app.main:app --reload --port 8000` → <http://localhost:8000>
- **Docker 本地**：`docker compose up` → <http://localhost:8000>

## CI

GitHub Actions 工作流 `.github/workflows/ci.yml`：

| Job | 触发 | 作用 |
|-----|------|------|
| `unit-test` | push/PR to main | `uv run pytest -v --cov=app`（§五-6 必需） |
| `docker-build` | push/PR to main | 构建 Docker 镜像 + 容器冒烟测试 `/healthz` |
| `deploy` | push to main（仅） | `fly deploy --remote-only`，依赖 `FLY_API_TOKEN` Secret |

`deploy` job 需要仓库 Settings → Secrets → Actions 中配置 `FLY_API_TOKEN`（在本地执行 `fly tokens create deploy -a group-chat-digest` 生成）。未配置时该 job 会失败但不影响前两个 job。

## 状态

- [x] SPEC.md
- [x] PLAN.md
- [x] 实现完成
- [x] AGENT_LOG.md
- [x] SPEC_PROCESS.md（冷启动验证）
- [x] REFLECTION.md
- [x] CI 配置（unit-test + docker-build + deploy）
- [x] 线上部署配置（`fly.toml`）
- [ ] 实际部署上线（需用户执行 `fly deploy`）

## 工作流

按 Superpowers 七步工作流推进：brainstorming → writing-plans → using-git-worktrees → subagent-driven-development → test-driven-development → requesting-code-review → finishing-a-development-branch。
