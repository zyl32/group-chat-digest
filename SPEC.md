# SPEC.md · 群聊摘要与待办提取器（Group Chat Digest）

> AI4SE 期末项目（B 类·应用类）。本文件由 Superpowers `brainstorming` 技能沉淀产出，须经冷启动 agent 验证后方可进入实现阶段（见 §10）。
>
> 版本：v1.0 · 日期：2026-08-05 · 作者：朱雨乐

---

## 1. 问题陈述

### 1.1 要解决什么问题

班级群、课题组群、学生会群每天产生数百条消息，重要信息（任务分配、DDL、会议通知）被刷屏淹没。学生要么反复翻聊天记录找"那个 DDL 到底是几号"，要么错过截止时间。现有工具（微信群置顶、飞书待办）只解决"主动标记"的部分，无法从消息洪流中**主动抽取**结构化待办。

### 1.2 目标用户

- **主用户**：在校大学生，参与多个班级群 / 课程群 / 课题组群
- **次用户**：班委、课题组组长，需要从群消息里抽取待办分发

### 1.3 为什么值得做

- 30 秒电梯陈述："把你导出的群聊丢进去，吐回今日摘要 + 谁要在什么时间前做什么的待办清单，可一键导出到滴答清单。"
- 真实痛点：每个人都有过"错过群里 DDL"的经历
- 现成方案缺陷：ChatGPT 直接问需要每次复制粘贴 + 无状态管理 + 无法导出待办
- 工程深度：异构数据源解析、LLM 输出 schema 校验、状态机、adapter 抽象、凭据安全、容器分发，每个都是独立工程问题

---

## 2. 用户故事（INVEST 原则）

### US-1 · 上传群聊导出（Independent / Valuable / Estimable）

> 作为班级群成员，我希望把从微信/飞书导出的群聊文件拖入网页，系统就能识别格式并解析，这样我不需要手动整理消息。

**验收**：拖入文件后 5 秒内返回 upload_id；格式不识别时给出"建议转 TXT"的明确提示。

### US-2 · 查看主题摘要（Independent / Valuable）

> 作为群成员，我希望按日期查看群聊摘要，按主题分块呈现，这样我能在 1 分钟内掌握当天讨论重点。

**验收**：摘要按主题分块，每块不超过 3 句话；点击主题可跳转到对应原始消息。

### US-3 · 待办抽取与状态管理（Negotiable / Testable / Estimable）

> 作为群成员，我希望系统自动抽出"谁要在什么时间前做什么"的待办，并能在网页上勾选完成 / 忽略 / 推迟，这样我不用手动维护待办列表。

**验收**：每个待办字段完整（who / what / due_at / source）；非法状态转换被拒绝并返回 409。

### US-4 · 导出待办到外部工具（Independent / Valuable）

> 作为待办工具用户，我希望把抽出的待办导出为 ICS 日历或推送到 Todoist，这样我能在已有工作流里管理。

**验收**：ICS 文件可被 Apple 日历 / Google 日历导入；Todoist 推送使用用户自带 token，不持久化外部凭据。

### US-5 · 安全配置 LLM Key（Independent / Valuable / Testable）

> 作为用户，我希望首次运行时引导我安全录入 LLM API key（隐藏输入），能查看是否已配置（不回显明文），能更新与清除，这样我的 key 不会泄露。

**验收**：key 不出现在 git / 日志 / 终端 history；首次运行引导流程；查看状态只显示"已配置 / 未配置"；清除后无法恢复。

### US-6 · 演示使用合成数据（Independent / Testable）

> 作为评审与潜在用户，我希望用预制的脱敏合成数据演示，这样我看到的不是真实隐私数据，但仍能验证系统能力。

**验收**：仓库内含 3 份合成数据集（正常学术讨论 / 含明确待办 / 含刷屏噪声）；WebUI 在演示模式贴"DEMO DATA"角标；数据生成器可一键产出新数据。

---

## 3. 功能规约（按模块）

### 3.1 上传模块（Upload Router + Parser）

**输入**：multipart/form-data 文件，content-type 不限，扩展名 .json / .txt

**行为**：
- 校验：文件 ≤ 10 MB；扩展名白名单；magic bytes 验证（JSON 必须以 `{` 或 `[` 开头）
- 落盘：原始文件写入 `data/uploads/{upload_id}.raw`，数据库写 Upload 记录 status='received'
- 异步触发：scheduler 入队 parse job，立即返回 202 + upload_id；parse job 启动时 Upload.status → 'parsing'；解析完成 → 'done'；解析失败 → 'failed' + error_msg
- 解析：Parser 按 fmt 归一化为 List[Message]，写 Message 表

**输出**：HTTP 202 + `{"upload_id": "uuid", "status": "received"}`

**边界**：
- 空文件 → 400
- 格式不识别 → 422 + `{"error": "unknown_format", "hint": "建议手动转 TXT"}`
- 文件过大 → 413

**错误处理**：所有错误返回 RFC 7807 Problem Details 格式

### 3.2 摘要服务（Digest Service）

**输入**：upload_id + 时间窗参数（默认 24h）

**行为**：
- 加载 Message 列表
- 按时间窗聚类（相邻 30 分钟内的消息视为同主题候选）
- 调 LLMProvider.complete()，prompt 强制 JSON schema：`{"blocks": [{"topic": str, "summary": str, "msg_range": [int, int]}]}`
- schema 校验失败 → 3 次重试 + 兜底为单块"摘要生成失败"
- 落库 Digest + DigestBlock

**输出**：Digest 对象（含 model_used 字段记录用的哪个 LLM）

**边界**：
- 消息 < 5 条 → 直接 LLM 单轮摘要，不聚类
- LLM 3 次失败 → Digest.summary_blocks = [{"topic":"错误","summary":"摘要生成失败，可重试"}]，状态标 failed

### 3.3 待办抽取器（Todo Extractor）

**输入**：upload_id + digest_id

**行为**：
- 加载 Message + Digest
- 调 LLMProvider.complete()，prompt 强制 JSON schema：`{"todos": [{"who": str, "what": str, "due_at": str|null, "source_msg_id": int}]}`
- schema 校验失败 → 兜底为"待确认"待办，标 source_msg_id 让用户手动判断
- 落库 Todo，初始 state='pending'

**输出**：List[Todo]

**边界**：
- LLM 输出 due_at 不可解析 → due_at = null
- 重复 source_msg_id → 视为更新而非新增

### 3.4 待办状态机（Todo State Machine）

**合法转换**：
- pending → done | ignored | snoozed
- snoozed → pending（仅手动 reactivate）

**非法转换**：done → 任意 / ignored → 任意 → 拒绝，返回 409 + `{"error": "illegal_transition", "from": "done", "to": "pending"}`

**接口**：`POST /api/todos/{id}/action` body=`{"action": "done"|"ignored"|"snoozed"|"reactivate"}`

### 3.5 导出服务（Export Service）

**输入**：todo_ids + format

**支持格式**：
- `ics`：生成 ICS 字节流，HTTP 200 + `Content-Type: text/calendar`
- `todoist_url`：返回 `https://todoist.com/import?...` 重定向 URL，不调外部 API
- `todoist_push`（可选）：用用户会话级 token 调 Todoist API，不持久化 token

**边界**：
- todo 不存在 → 404
- todoist_push 失败 → 502 + 详细错误，不破坏待办状态

### 3.6 凭据保险箱（Credential Vault）

**支持存储后端**：
- Windows Credential Manager（主）
- macOS Keychain（次）
- Linux Secret Service / libsecret（次）
- `.env` 文件（降级路径，SPEC §7.1 明示风险）

**接口**：
- `vault.store(key_name, value)` → 写入，明文不入日志
- `vault.load(key_name)` → 读取，返回 str | None；调用方负责不打印
- `vault.status(key_name)` → 返回 `{"configured": bool}`，不回显明文
- `vault.clear(key_name)` → 删除，不可恢复

**首次运行引导**：
- 检测到 key 未配置 → 跳转 /setup 页面
- 提示"请输入 DeepSeek API key"，input type=password
- 提交后调 vault.store()，不返回值给前端，只返回 `{"stored": true}`

### 3.7 LLM Provider Adapter

**接口**：
```python
class LLMProvider(Protocol):
    def complete(self, messages: list[LLMMessage], schema: dict | None) -> str: ...
    def name(self) -> str: ...
```

**v1 实现**：
- `DeepSeekAdapter`：兼容 OpenAI SDK，base_url=`https://api.deepseek.com`
- `OpenAIAdapter`：标准 OpenAI SDK
- `MockLLMAdapter`：测试专用，配置式响应 + 失败注入

**Registry 模式**：
```python
LLM_PROVIDERS: dict[str, type[LLMProvider]] = {}
def register_provider(name: str): ...
def get_provider(name: str) -> LLMProvider: ...
```

**配置切换**：Hydra YAML `llm.provider: deepseek|openai|mock`

### 3.8 前端静态站

**4 个页面**：
- `/` 上传页：拖拽区 + 上传历史列表 + 状态轮询
- `/digests` 摘要列表页：按日期倒序，点击进入详情
- `/digests/{id}` 摘要详情页：分块摘要 + 关联待办
- `/todos` 待办管理页：列表 + 状态操作 + 导出按钮
- `/setup` 凭据配置页：首次运行引导

**设计系统**：Open Design（https://github.com/nexu-io/open-design）

### 3.9 演示数据生成器

**脚本**：`scripts/gen_mock_chat.py`

**输出**：3 份合成数据集
- `mock_chat_normal.json`：正常学术讨论 200 条
- `mock_chat_with_todos.json`：含 5+ 明确待办（DDL/负责人/时间）
- `mock_chat_noise.json`：含刷屏/表情包/无关内容

**脱敏**：所有人名替换为 `student_01` / `student_02`...，所有电话替换为 `13800000000`，所有地址替换为 `placeholder_addr`

---

## 4. 非功能性需求

### 4.1 性能
- 上传响应 < 5s（10MB 文件）
- 摘要生成 < 60s（200 条消息）
- 前端首屏 < 2s（静态资源 CDN）

### 4.2 安全（凭据威胁模型）

| 威胁 | 对策 |
|---|---|
| Key 硬编码进源码 | pre-commit hook + grep 扫描；CI 检查 |
| Key 进入 git 历史 | .gitignore 拦 .env；首次 commit 前自查 |
| Key 进入日志 | logger 配置过滤器，匹配 sk-* / api_key 模式时脱敏 |
| Key 进入终端 history | 不使用命令行 export；用 vault store API |
| Key 在内存中被 dump | 不持久化 key 到磁盘明文；OS 钥匙串加密存储 |
| .env 被进程环境读取 | SPEC 明示风险；推荐生产环境用 OS 钥匙串 |
| 群消息含真实人名/电话 | 演示用合成数据；生产部署提示用户脱敏 |
| LLM provider 拿到原始消息 | SPEC 明示"消息内容经 LLM provider 处理，须用户授权"；adapter 接口预留 Ollama 本地模型 |

### 4.3 可用性
- 上传到摘要全流程 < 3 次点击
- 错误信息人话化（避免堆栈）
- 移动端响应式（≥ 375px 宽度可用）

### 4.4 可观测性
- 结构化日志（JSON 格式），含 request_id 贯穿
- 健康检查端点 `/healthz`
- LLM 调用计数 + token 消耗 + 失败率仪表盘（`/metrics`）

---

## 5. 系统架构

见浏览器架构图（已通过用户审查）。组件分层：

```
Browser (静态站)
  ↓ HTTP
FastAPI Router 层 (HTTP 边界)
  ↓
Service 层 (Digest / Todo / State / Export)
  ↓
Adapter 层 (LLMProvider / CredentialVault)
  ↓
Storage 层 (SQLAlchemy 抽象，SQLite 生产 / 内存测试)
```

外部依赖：
- DeepSeek API（默认 LLM）
- OpenAI API（可选 LLM）
- Todoist API（可选导出）
- OS 钥匙串（凭据存储）

---

## 6. 数据模型

### 6.1 ER 表

| 实体 | 字段 | 关系 |
|---|---|---|
| Upload | id (PK, uuid), filename, fmt, size, received_at, status, error_msg | 1 → N Message, 1 → 1 Digest, 1 → N Todo |
| Message | id (PK, int), upload_id (FK), sender, content, timestamp, msg_id (来源平台去重) | N → 1 Upload |
| Digest | id (PK, int), upload_id (FK), date, window, summary_blocks (JSON), created_at, model_used | 1 → 1 Upload |
| Todo | id (PK, int), upload_id (FK), who, what, due_at, source_msg_id (FK), state, created_at, updated_at | N → 1 Upload, N → 1 Message |
| Setting | key (PK), value | 单用户配置 KV |

### 6.2 约束
- Todo.state ∈ {pending, done, ignored, snoozed}
- Upload.status ∈ {received, parsing, done, failed}
- Message.msg_id 在同一 upload_id 内唯一

---

## 7. 凭据与分发设计

### 7.1 凭据流程

**首次运行引导**：
1. 检测 `LLM_API_KEY` 未配置 → 重定向 /setup
2. 用户输入 key（input type=password）
3. 后端调 `vault.store("llm_api_key", value)`，写入 OS 钥匙串
4. 返回 `{"stored": true}`，不回显值
5. 重定向 /

**查看状态**：`vault.status("llm_api_key")` → `{"configured": true}`，不回显明文

**更新**：再次走 /setup 流程，覆盖写入

**清除**：`vault.clear("llm_api_key")`，不可恢复；前端显示"已清除"

**降级路径**：`.env` 文件加载，SPEC 明示风险：
- `.env` 是明文，任何能读该文件的进程都能读 key
- 进程环境对子进程可见，可能被 dump
- 不建议生产部署使用

### 7.2 分发形态

**主形态：Docker 镜像**
- `docker build -t group-chat-digest .` 单条命令
- `docker run -p 8000:8000 -v $(pwd)/data:/data group-chat-digest` 单条命令启动
- 推送到 GitHub Container Registry（ghcr.io）

**次形态：本地开发**
- `uv sync && uv run uvicorn app.main:app --reload`
- 用于开发与测试

**目标平台**：
- Linux x86_64（生产容器）
- Windows / macOS（本地开发）
- 不签名（学生项目），README 注明首次运行系统拦截的处理方式

**Key 在目标机的配置**：
- 容器：通过环境变量注入（`-e LLM_API_KEY=...`），README 注明"此路径仅用于容器演示，生产部署应使用 Docker Secret 或外部 vault"
- 本地：通过 /setup 页面写入 OS 钥匙串

---

## 8. 技术选型与理由

| 维度 | 选型 | 理由 |
|---|---|---|
| 后端语言 | Python 3.12 | 类型提示成熟 / LLM 生态完善 / 笔者熟悉 |
| Web 框架 | FastAPI | 异步、自带 OpenAPI、与 LLM async 契合 |
| 包管理 | uv | 速度快、锁文件稳定、符合 CLAUDE.md 默认 |
| 配置 | Hydra + OmegaConf | composition 友好，便于切换 LLM provider |
| 数据库 | SQLite | 单用户部署无需 Postgres，单文件便于容器分发 |
| ORM | SQLAlchemy 2.0 | 异步支持好，测试可换内存实现 |
| 前端 | 静态 HTML + Open Design | §3.6 强制 Open Design；不上 React 降低复杂度 |
| LLM SDK | 自实现 adapter + openai SDK 复用 | DeepSeek 兼容 OpenAI SDK，复用生态 |
| 鉴权 | 单一管理员 token | 单用户部署无需注册系统 |
| 测试 | pytest + httpx + MockLLMAdapter | TDD 强制；MockLLM 让 CI 不依赖真实 key |
| CI | GitHub Actions | 含 unit-test job（§五-6 硬性要求）+ docker-build job |
| 部署 | Fly.io 免费层 | 学生额度、全球 CDN、Dockerfile 直推 |
| 凭据存储 | OS 钥匙串（keyring 库） | §3.1 至少一种安全存储 |
| 前端设计系统 | Open Design | §3.6 强制 |

---

## 9. 验收标准

### 9.1 功能验收

| 验收项 | 客观判定 |
|---|---|
| 上传 JSON 被正确解析 | 上传 mock_chat_normal.json，5s 内 GET /api/uploads/{id}/status 返回 'done'，Message 表有 200 条 |
| 摘要按主题分块 | Digest.summary_blocks ≥ 2 块，每块 ≤ 3 句 |
| 待办抽取字段完整 | mock_chat_with_todos.json 抽出 ≥ 4 条 todo，所有字段非空 |
| 待办状态机拒绝非法转换 | done → pending 返回 409 |
| ICS 导出可被日历软件导入 | 生成的 .ics 文件可被 Apple 日历导入 |
| 凭据查看不回显明文 | /api/credentials/status 返回 `{"configured": bool}` |
| 凭据清除不可恢复 | clear 后 load 返回 None |

### 9.2 非功能验收

| 验收项 | 客观判定 |
|---|---|
| 全测试套件 < 60s | `uv run pytest` 输出时间 < 60s |
| CI 通过 | GitHub Actions unit-test job 末次 pass |
| 容器单条命令启动 | `docker run` 后 30s 内 /healthz 返回 200 |
| 线上 URL 可访问 | Fly.io 部署 URL 公网可达 |
| 凭据不入 git | `git log -p | grep -E "(sk-[a-zA-Z0-9]{20,}|deepseek-[a-zA-Z0-9]{20,})"` 无匹配 |

---

## 10. 风险与未决问题

### 10.1 已识别风险

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| 微信无官方导出 API | 必然 | 数据接入受限 | SPEC 明示"仅支持手动导出"，承认约束反而加分；adapter 接口预留 webhook 扩展位 |
| LLM 输出 JSON schema 不合 | 中 | 待办抽取失败 | 3 次重试 + 兜底为"待确认"待办，不阻断链路 |
| DeepSeek 服务不稳定 | 低 | 摘要生成失败 | 重试 + adapter 接口允许切换 OpenAI |
| Fly.io 免费层冷启动慢 | 中 | 演示现场首次访问慢 | 演示前 5 分钟 ping 一次预热 |
| MockLLMAdapter 与真实 adapter 行为不一致 | 中 | 测试通过但生产失败 | 契约测试 + 真实 adapter 的 smoke test（手动触发） |
| 凭据 vault 在 CI 环境不可用 | 必然 | CI 测试需 mock | 测试用 InMemoryVault 后端，生产用 OS 钥匙串 |

### 10.2 未决问题

1. **反馈闭环（v1.1 stretch）**：用户标记"这条不是待办"后，系统是否应该用 embedding 相似度匹配未来类似消息自动降权？工程量与效果难量化，留作 v1.1 探索。
2. **多群组管理**：v1 单一 Upload 单一 Digest，是否需要"群组"概念聚合多次上传？v1 不做，v1.1 评估。
3. **模型对比面板**：§3.6 鼓励"组合使用多种智能体并比较其表现"，是否要在 WebUI 加同消息多模型摘要 diff 页？v1 不做，留接口。
4. **本地 LLM 支持**：Ollama adapter 是否值得做？能满足"消息不出库"的隐私需求，但模型质量与速度待评估。v1.1 探索。

### 10.3 SPEC 与 PLAN 完成后的硬要求

- **冷启动验证**（§4.5）：用一个与主开发 agent 不同的 agent，新 session、不导入历史/memory，仅给 SPEC+PLAN，让它实现 1–2 个 task（1–2 小时）。记录其暂停提问、spec 缺陷到 `SPEC_PROCESS.md`。**这是规约工作中最关键的客观证据**，演示时一并发评审。

---

## 11. 学术规范声明

- 项目含 LLM 调用，所有 LLM 生成内容不冒充真实数据
- 演示用合成数据，仓库内不含真实人名/电话/地址
- 第三方代码遵守其许可证，README 列出
- `REFLECTION.md` 由学生本人撰写，禁止 AI 代写（可用 AI 辅助润色，需标注）
