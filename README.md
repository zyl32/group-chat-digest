# 群聊摘要与待办提取器（Group Chat Digest）

> AI4SE 期末项目（B 类·应用类项目）

一个把班级群聊从消息洪流里抽出每日摘要与可执行待办的小工具。后端基于 FastAPI，LLM 层支持 Mock / DeepSeek / OpenAI 兼容协议，前端为单页 HTML。生产部署使用 Docker + Hugging Face Spaces（备选 Render / Fly.io，均不绑卡）。

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
render.yaml         # 备选：Render 部署（Blueprint IaC，需绑卡）
fly.toml            # 备选：Fly.io 部署（需绑卡）
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

## Hugging Face Spaces 部署（首选）

Hugging Face Spaces 是本项目的默认生产部署目标——**真免费、不绑卡、支持 Docker、URL 固定**。

**生产 URL**：`https://<你的HF用户名>-group-chat-digest.hf.space`

### 首次部署（一次性，浏览器操作 + 一次 git push）

**步骤 1：注册 HF 账号**

1. 打开 <https://huggingface.co/join> → 用 GitHub 账号登录 → Authorize
2. 填用户名 + 邮箱 + 密码 → 完成注册

**步骤 2：创建 Space**

1. 右上角头像 → **New Space**
2. 填写：
   - **Name**: `group-chat-digest`
   - **License**: MIT
   - **SDK**: 选 **Docker**
   - **Space hardware**: **CPU basic (Free)**
   - **Visibility**: Public（Private 要付费）
3. **Create Space** → 跳到空 Space 页面

**步骤 3：生成 HF access token**

1. 头像 → **Settings** → 左侧 **Access Tokens**
2. **New token** → Name: `deploy` → Role: **Write** → Create token
3. 复制 token（`hf_xxxxxxxxxx`）——只显示一次，丢了要重新生成

**步骤 4：把项目代码 push 到 Space**

```bash
# 在你电脑上
cd "D:/大二下/summer/homework"

# 添加 HF 为远程仓库
git remote add hf https://huggingface.co/spaces/<你的HF用户名>/group-chat-digest

# push（提示输入用户名/密码）
git push hf main
# Username: <你的HF用户名>
# Password: <粘贴刚生成的 token，不是 HF 账号密码>
```

push 后 Space 页面立刻进入 "Building" 状态。

**步骤 5：等 build 完成 + 验证**

3–5 分钟后 Space 状态变 "Running"，URL `https://<你的HF用户名>-group-chat-digest.hf.space` 出现在页面顶部。

验证：
```bash
curl https://<你的HF用户名>-group-chat-digest.hf.space/healthz
# 期望: {"status":"ok"}
```

### 后续部署

`main` 分支一 push 到 HF Space 仓库（`git push hf main`），Space 自动重新 build + 部署。**不需要 CI job**——HF 自己监听 push。

### （可选）切换为真实 LLM

Space 页面 → **Settings** → **Variables and secrets**：

| Name | Value | Type |
|---|---|---|
| `LLM_PROVIDER` | `deepseek` | Variable |
| `DEEPSEEK_API_KEY` | `sk-xxxxxxxx` | **Secret**（不回显） |

Save → Space 自动 restart（不重新 build）。

### 已知限制

- **Ephemeral filesystem**：免费 CPU basic tier 无持久存储——SQLite DB + 上传文件在 Space restart/sleep 后重置。演示场景可接受；持久化需付费 persistent storage（$5/月 20GB）。
- **闲置 sleep**：48h 无访问 Space 自动 sleep，下次访问自动唤醒（约 30s 冷启动）。
- **凭据保险库不可用**：HF Spaces Linux 容器无桌面 keyring 后端，`OSKeyringVault` 不可用——`/api/credentials/llm_api_key/status` 返回 `{"configured": false}`，POST 失败。**用 Space Variables/Secrets 注入 LLM key 替代**（v1.1 stretch：env-var vault backend）。

### 配置要点

- `SDK: Docker` 复用本仓库 `Dockerfile`，无单独构建脚本
- `Space hardware: CPU basic (Free)`：2 vCPU, 16GB RAM（比 Render free 多）
- `Dockerfile CMD` 用 shell form 读 `$PORT` env var——HF Spaces 默认 7860，本地 8000，任平台均可
- `Visibility: Public` 免费；Private 需 Pro 账号
- `LLM_PROVIDER=mock` 默认值，首次部署即可演示
- HF Spaces 自带 GitHub Actions-style 自动部署（push 触发），无需 `.github/workflows` 改动

---

## 备选 1：Render 部署

Render 是备选部署目标（free tier 需绑卡但不会扣费），配置已写入 `render.yaml`。需要绑信用卡，门槛高于 HF Spaces。

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

- Hugging Face Spaces / Render / Fly.io Linux 容器均无桌面 keyring 后端，`OSKeyringVault` 不可用 → 生产 LLM key 需用平台环境变量注入（HF Spaces Variables and secrets / Render Environment / `fly secrets set`，v1.1 stretch：env-var vault backend）
- WebUI 无身份认证（单用户演示场景）；多用户部署需自行加反向代理鉴权

## 线上 URL

- **目标 URL**：`https://<你的HF用户名>-group-chat-digest.hf.space`（Hugging Face Spaces，首选）
- **备选 URL**：`https://group-chat-digest.onrender.com`（Render，需绑卡）/ `https://group-chat-digest.fly.dev`（Fly.io，需绑卡 + 装 flyctl）
- **当前状态**：**未实际部署**——`Dockerfile` 已适配 HF Spaces（CMD shell form 读 `$PORT`），待仓库所有者在 HF 创建 Space 并 push 代码。HF 接到 push 后自动 build。
- **本地访问**：`uv run uvicorn app.main:app --reload --port 8000` → <http://localhost:8000>
- **Docker 本地**：`docker compose up` → <http://localhost:8000>

## CI

GitHub Actions 工作流 `.github/workflows/ci.yml`：

| Job | 触发 | 作用 |
|-----|------|------|
| `unit-test` | push/PR to main | `uv run pytest -v --cov=app`（§五-6 必需） |
| `docker-build` | push/PR to main | 构建 Docker 镜像 + 容器冒烟测试 `/healthz` |
| `deploy` (备选) | push to main（仅） | `fly deploy --remote-only`，依赖 `FLY_API_TOKEN` Secret；未配置时 graceful skip |

> **HF Spaces / Render 部署不依赖 CI**：HF Spaces 监听 Space git repo push 自动部署，Render 监听 GitHub webhook 自动部署。两者均无需 CI deploy job。`deploy` job 仅服务于备选 Fly.io 路径，未配 `FLY_API_TOKEN` 时会失败但不影响 `unit-test` / `docker-build`。

`deploy` job 需要仓库 Settings → Secrets → Actions 中配置 `FLY_API_TOKEN`（在本地执行 `fly tokens create deploy -a group-chat-digest` 生成）。

## 状态

- [x] SPEC.md
- [x] PLAN.md
- [x] 实现完成
- [x] AGENT_LOG.md
- [x] SPEC_PROCESS.md（冷启动验证）
- [x] REFLECTION.md
- [x] CI 配置（unit-test + docker-build + 备选 deploy）
- [x] 线上部署配置（`Dockerfile` 适配 HF Spaces，`render.yaml` + `fly.toml` 备选）
- [ ] 实际部署上线（需用户在 HF Spaces 创建 Space + `git push hf main`）

## 工作流

按 Superpowers 七步工作流推进：brainstorming → writing-plans → using-git-worktrees → subagent-driven-development → test-driven-development → requesting-code-review → finishing-a-development-branch。
