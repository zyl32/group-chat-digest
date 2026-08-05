# SPEC_PROCESS.md — 冷启动验证记录

> **依据**: PLAN.md §T25。本文件记录一个全新 session、无任何先前对话 memory 的 AI 编码 agent，仅凭 `SPEC.md` + `PLAN.md` 实现一个小功能时暴露的规约缺陷与误读，以及据此对 SPEC / PLAN 的修订建议。

---

## 1. 验证元数据

| 项 | 值 |
|---|---|
| **agent 类型** | Claude Code `general-purpose` 子 agent（新 session、隔离上下文，未导入主开发 session 的任何对话历史或 memory） |
| **session 起始** | 2026-08-06 03:00 (UTC+8) |
| **session 时长** | 约 30 分钟（阅读 18 min / 写测试 3 min / 实现 5 min / 环境 3 min / 提交 1 min） |
| **指派 task** | 实现 `GET /api/digests` 列表端点（返回所有 digest，按时间倒序），严格 TDD，遇不确定即暂停 |
| **worktree** | `worktree-wt-coldstart` 分支（从 `main` @ `775705c` 切出） |
| **commit** | `f6d9ef6` — `feat(digests): add GET /api/digests list endpoint` |
| **产出测试** | 3 个新测试全过；全量 132 tests pass |

选 `general-purpose` 子 agent 是因为它在 Claude Code 架构里是一个**完全隔离的子进程**：主 session 的对话历史、memory、TODO 列表均不可见，只有我主动放进 prompt 的内容才被它"看见"。这满足 §T25 "新 session、不导入历史/memory" 的硬性要求。同主开发 agent（Claude Code 主 session）属同一模型但不同上下文，足以做规约可读性的客观验证。

---

## 2. agent 在哪里暂停并提问

**结论**: agent 未因不明确而阻塞——但**这不是 SPEC 清晰的证据，而是现有代码约定足够强**。agent 在报告中明确列出了 4 处不明确的决策点，全部通过"读现有代码"而非"读 SPEC"解决。这恰恰是 SPEC 的缺陷：规约没有覆盖这些决策，靠代码补上了。

agent 在以下位置曾短暂停顿（报告原文摘录）：

> "SPEC.md 第 191–196 行 (§3.8 前端) 列出了 `/digests` 摘要列表页：按日期倒序，但从未明确 `GET /api/digests` 的 API 契约——没有路径、没有字段、没有状态码。"

> "PLAN.md：没有任何任务定义 `GET /api/digests`。`app/frontend/digests.html` 第 22 行明确指出'v1 后端（T15）目前未提供 `GET /api/digests` 列表端点' —— 此前端缺口是有意为之的 v1 版本限制。"

agent 选择了"补这个缺口"而非"暂停问人"，理由是任务提示明确要求实现该端点。但若任务提示改为"实现 SPEC/PLAN 中定义的下一个端点"，agent 就会卡住——因为 SPEC/PLAN 里没有下一个端点可挑。

---

## 3. 暴露的 spec 缺陷（具体到行号 / 字段）

### 缺陷 A — `GET /api/digests` API 契约缺失

- **位置**: `SPEC.md` §3.8 第 191–196 行
- **现状**: 仅在前端节列了 `/digests 摘要列表页：按日期倒序`，从未定义后端 API 契约（路径、字段、状态码、分页、过滤）。
- **影响**: agent 必须从 `app/routers/uploads.py:get_digest`（第 184–191 行）反推响应结构；任何后端字段调整都不会同步到 SPEC。

### 缺陷 B — "按日期倒序"二义性

- **位置**: `SPEC.md` §3.8 第 193 行 + §6.1（`Digest` 模型同时有 `date: str` (YYYY-MM-DD) 和 `created_at: datetime`）
- **现状**: "日期倒序"未指明字段。`date` 是字符串（按字典序排），`created_at` 是 DateTime（按时间序排）——同一组数据在两者上可能给出不同顺序（同一天的多条 digest）。
- **影响**: agent 选了 `created_at`，理由是任务提示用了"最新优先"措辞，且 `date` 是字符串排序语义不严格。但 SPEC 应明确。

### 缺陷 C — PLAN 无对应任务

- **位置**: `PLAN.md` 全文任务表
- **现状**: T1–T24 中没有任何任务定义 `GET /api/digests`。`app/frontend/digests.html:22` 显式承认这是 v1 缺口。
- **影响**: agent 实际上是在 PLAN 明确推迟的空白处填补，而非"执行 PLAN 中的 task"。这与 §T25 提示词模板"请实现 PLAN.md 中的 [Task N] 和 [Task N+1]"的预设不符——证明 PLAN 不完整。

### 缺陷 D — 响应结构与空列表状态码未文档化

- **位置**: `SPEC.md` §3.7（API 端点表）整体
- **现状**: 所有列表端点的响应结构、空列表状态码（200 + `[]` vs 404）、字段集合均未在 SPEC 中给出，靠 `tests/integration/test_todo_router.py:35` 的 `test_get_todos_empty` 反推。
- **影响**: agent 必须读测试代码而非 SPEC 才能知道"空列表返 200+[]"。这违反"SPEC 应自洽"原则。

### 缺陷 E — 路由文件位置未约定

- **位置**: `SPEC.md` §4（项目结构）+ §6.2（路由清单）
- **现状**: 未说明新资源应放新 router 文件还是合并进现有文件。`uploads.py` 前缀 `/api/uploads`，无法注册 `/api/digests`——必须新建 `digests.py`，但 SPEC 没说。
- **影响**: agent 凭 `todos.py` 的存在推断"每资源一文件"是约定。这是约定，但未文档化。

### 缺陷 F — `created_at` 是否暴露给前端未决

- **位置**: `SPEC.md` §6.1（`Digest` 模型字段表）+ §3.8（前端只说"按日期倒序"）
- **现状**: 列表按 `created_at` 排序但响应中不返回该字段（与 `get_digest` 一致）。前端要显示"生成时间"时无字段可用。
- **影响**: agent 选了"不暴露 `created_at`"以严格对齐 `get_digest`——但这可能不是设计意图，而是 `get_digest` 写时的疏漏被列表继承。

---

## 4. agent 做出的与原意不一致的解读

| 解读点 | agent 的选择 | 主开发 agent 的原意 | 评判 |
|---|---|---|---|
| 排序字段 | `Digest.created_at.desc()` | 未明确记录，但 `Digest.date` 字符串排序在 SQL 层面会按字典序（同一天内顺序未定），`created_at` 是更正确的选择 | agent 读对了，SPEC 写漏了 |
| 响应是否含 `created_at` | 不含（严格对齐 `get_digest`） | 未明确 | agent 选了"保守对齐"，但若设计意图是列表页要显示生成时间，则应暴露。**spec 写漏** |
| 路由文件位置 | 新建 `app/routers/digests.py` | 未明确，但项目结构隐含"每资源一文件" | agent 读对了 |
| 空列表状态码 | 200 + `[]` | 未明确，靠 `test_get_todos_empty` 隐式定义 | agent 从测试反推，**spec 应显式声明** |
| 是否分页 | 不分页 | 任务提示明确禁止 | 一致 |
| `summary_blocks` 字段是否原样返回 | 是 | `get_digest` 原样返回 | 一致 |

**核心发现**: agent 的所有决策都**合理**——问题不在 agent 读错，而在 SPEC/PLAN 没写。这印证了 §4.5"规约工作中最关键的客观证据"的价值：冷启动 agent 不是在"误解 spec"，而是在"补 spec 的洞"。

---

## 5. 产出与预期差距

| 维度 | 预期 | 实际 | 差距 |
|---|---|---|---|
| 实现的端点 | 1 个（`GET /api/digests`） | 1 个 | 0 |
| 测试数 | ≥ 2（基本 + 边界） | 3（空 / 排序 / 结构） | +1 |
| 全量测试 | 通过 | 132/132 通过 | 0 |
| 提交 | 1 次，Conventional Commits | `f6d9ef6 feat(digests): ...` | 0 |
| 范围蔓延 | 应避免 | 无（未加分页/过滤/排序参数） | 0 |
| 暂停提问数 | 期望 ≥ 1（暴露 spec 缺陷） | 0 次阻塞，但报告列了 6 处 | **−1**（agent 应更频繁暂停） |
| 代码风格违规 | 0 | 0（type hints / `Depends(get_db)` / `extra="forbid"` / `logger` 全对） | 0 |

**关键差距**: agent 没有暂停提问。这与 §T25 提示词"遇不清楚立即暂停并询问"略有出入。agent 的解释是"现有代码约定完全决定了实现方式"——这是合理的，但**理想的冷启动 agent 应在"排序字段"和"`created_at` 是否暴露"两点上暂停**，因为这两处 SPEC 确实缺失，agent 是靠"读代码"而非"读 spec"决定的。这提示我：在主开发 session 里，许多决策也是这样靠代码补的，但主 session 没有把它们回写到 SPEC。

---

## 6. 据此对 SPEC / PLAN 的修订

由于 SPEC.md / PLAN.md 是项目交付物（已 frozen 在 v1），对它们的修订以"修订建议"形式记录于此，不回改原文件——以保留规约演化的诚实轨迹。后续 v1.1 启动时应将这些修订合并入新 SPEC。

### 修订建议 1 — SPEC §3.7 增补 `GET /api/digests` 契约

**应增补内容**（diff 形式）:

```diff
+ ### GET /api/digests
+ 
+ 返回所有 digest，按 `created_at` 降序。
+ 
+ **响应**: `200 OK`
+ 
+ ```json
+ [
+   {
+     "id": 1,
+     "upload_id": "abc123",
+     "date": "2026-08-05",
+     "window": "24h",
+     "summary_blocks": [{"topic": "...", "summary": "...", "msg_range": [0, 10]}],
+     "model_used": "deepseek-chat"
+   }
+ ]
+ ```
+ 
+ 空存储返回 `200 OK` + `[]`。无分页、无过滤（v1）。
```

**字段选择理由**: `created_at` 而非 `date`——后者是字符串，同一天内顺序未定；前者是 DateTime，时间序严格。响应不暴露 `created_at`（与 `GET /api/uploads/{id}/digest` 一致）。

### 修订建议 2 — SPEC §3.7 增补"列表端点通用约定"一节

**应增补内容**:

```diff
+ #### 列表端点通用约定
+ 
+ - 路径: `GET /api/<resource>`（复数）
+ - 响应: `list[dict[str, Any]]`，无 `response_model`（避免 Pydantic 二次校验开销）
+ - 空存储: `200 OK` + `[]`（不返 404）
+ - 无分页、无过滤、无排序参数（v1；v1.1 增 `?limit=&offset=`）
+ - 依赖: `Depends(get_db)`，复用 `app.routers.uploads.get_db`
```

### 修订建议 3 — SPEC §4 增补"新资源 → 新 router 文件"约定

**应增补内容**:

```diff
+ ### 路由文件组织
+ 
+ 每个资源（`uploads` / `digests` / `todos` / `exports` / `credentials`）一个 router 文件，
+ 位于 `app/routers/<resource>.py`，使用 `APIRouter(prefix="/api/<resource>")`。
+ 列表端点注册为 `@router.get("")`，详情端点为 `@router.get("/{id}")`。
```

### 修订建议 4 — PLAN 增补 T20.5 任务

**应增补内容**:

```diff
+ ## T20.5: Digest 列表端点
+ 
+ **Files**:
+ - Create: `app/routers/digests.py`
+ - Modify: `app/main.py`（include_router）
+ - Test: `tests/integration/test_digest_router.py`
+ 
+ 依赖: T15（Digest 模型）+ T22（get_digest 既有响应结构）
+ 
+ 实现 `GET /api/digests` 返回所有 digest 按 `created_at` 降序，
+ 响应结构对齐 `get_digest`。空存储返 200 + []。
```

### 修订建议 5 — SPEC §6.1 `Digest` 字段表标注暴露策略

**应增补内容**:

```diff
+ | 字段 | 类型 | 是否暴露给 API |
+ |---|---|---|
+ | id | int | 是 |
+ | upload_id | str | 是 |
+ | date | str (YYYY-MM-DD) | 是 |
+ | window | str | 是 |
+ | summary_blocks | JSON | 是 |
+ | model_used | str | 是 |
+ | created_at | datetime | **否**（仅用于排序） |
```

### 修订建议 6 — 提示词模板修订

§T25 提示词模板用"请实现 PLAN.md 中的 [Task N] 和 [Task N+1]"——这预设 PLAN 完整。冷启动验证暴露了 PLAN 不完整时该模板失效。**修订建议**:

```diff
- 请实现 PLAN.md 中的 [Task N] 和 [Task N+1]。
+ 请实现以下功能：<具体功能描述>。该功能在 SPEC.md 第 X 节有部分定义，
+ 但 PLAN.md 未拆解为独立 task。请按 TDD 实现，遇不确定即暂停。
```

---

## 7. 对 §4.5"客观证据"承诺的回应

§T25 称冷启动验证是"规约工作中最关键的客观证据"。本次验证产出的客观证据:

1. **SPEC 不自洽**: 6 处缺陷中，4 处（A/B/D/E）必须读代码而非 SPEC 才能解决。这违反"SPEC 应自洽"原则。
2. **PLAN 不完整**: 缺陷 C 证明 PLAN 缺一个 task。
3. **agent 决策合理**: 所有决策点 agent 都选了"对的"答案——但这是**幸存者偏差**：因为现有代码本身就实现了这些约定。若现有代码写错，agent 会继承错误。冷启动验证无法发现"代码错了但 SPEC 对"的缺陷，只能发现"SPEC 漏了但代码补了"的缺陷。
4. **暂停频率不足**: agent 未在 6 处缺陷上暂停提问，而是"读代码解决"。这降低了对"SPEC 可读性"的检验强度。下次冷启动验证应在提示词中**强制**："以下决策必须暂停询问，不得从代码推断：响应字段集合 / 排序字段 / 空列表状态码 / 路由文件位置"。

---

## 8. 后续行动项

| # | 行动 | 责任 | 状态 |
|---|---|---|---|
| 1 | 将本文件 6 条修订建议合并入 v1.1 SPEC | v1.1 启动时 | 待办 |
| 2 | 在 v1.1 SPEC 增"列表端点通用约定"一节 | v1.1 启动时 | 待办 |
| 3 | `app/frontend/digests.html:22` 注释 "v1 后端未提供 `GET /api/digests`" 现已过时，应删除 | 本 PR 内（`f6d9ef6` 已补端点） | 待办 |
| 4 | 下次冷启动验证提示词中显式列出"必须暂停"的决策类型 | 下次冷启动 | 待办 |

---

## 9. 引用

- agent 完整报告：本文件 §1–§5 整理自冷启动 agent 返回的结构化报告（agentId: `aee9230c4347c9580`）。
- agent 产出 commit: `f6d9ef6`（worktree `worktree-wt-coldstart`）。
- 验证基线 commit: `775705c`（main @ 2026-08-06 03:00）。
- 测试基线: 132/132 pass（`uv run pytest -q`）。
