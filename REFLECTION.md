# REFLECTION.md

> **学术规范声明**：作者本人撰写与思考，AI 仅辅助润色语法与错别字，所有观点为作者本人。

## 1. 哪些 Superpowers 技能发挥了最大作用、哪些"形式大于实质"

最大作用：`subagent-driven-development`（保护编排器上下文，24 task 不污染主 session）、`test-driven-development`（"红"对 AI 是诊断非冗余，T18 的 `format: str→Literal` 重构就是测试失败逼重读 Pydantic v2 spec）、`using-git-worktrees`（回滚成本零，T23 `ghcr.io` 不可达时直接删 worktree 重派）。形式大于实质：`requesting-code-review`（4 次中 3 次提 minor 不阻断，主观不如客观测试）、`finishing-a-development-branch`（内容已被 subagent-driven 吸收，未提供新约束）。

## 2. TDD 在 AI 协作下是阻碍还是放大器

放大器，且比人-only 更强。AI 不疲惫，"红"步骤对 subagent 是诊断而非冗余。早期 T1–T5 有 subagent 试图"实现+测试一起写"，结果测试假阳（实现错测试也错二者一致通过）。唯一摩擦：探索性任务（UI/架构）会过早锁死决策。本项目规约化任务契合，TDD 完美。

## 3. subagent-driven 让智能体能自主运行多久而不偏离

30–90 分钟单次 task。≤60 分钟 + 边界明确（单端点/单服务）→ 自主率高。>90 分钟跨多文件 + 边界模糊 → 必偏离。T22（E2E）90 分钟偏离一次（`get_provider("mock")` vs fixture 注入），人工纠正后回归。编排器不应"派完就走"：每 subagent 完成后立即 review + 决定下一步，是连续闭环非 fire-and-forget。

## 4. task 颗粒度最优

1 task = 1 可独立测试产物（单端点/单服务方法/单模型）+ 1–3 文件 + 30–90 分钟。判据：能否一句话描述完成态可观察产物。T1（骨架）和 T22（E2E）都偏大——应拆。过小（"加一个字段"）则上下文切换成本超实现成本。

## 5. SPEC/PLAN 质量如何影响实现质量——具体案例

T22 `mock_llm` 注入偏离：SPEC §3.7 写"upload 端点支持 process 调用 LLM"，PLAN T22 写"测试用 `mock_llm` fixture 程序化响应"——**都没说 `process` 如何拿到 LLM 实例**（参数注入 vs 工厂取）。subagent 选 `get_provider("mock")`，与 `mock_llm` fixture 不匹配，测试失败。修复用 `monkeypatch.setattr` 补。根因：SPEC 未指定依赖注入方式。约 30% task 出过类似"SPEC 未指定 → subagent 选一种 → 测试适配"的隐性偏离。

## 6. 最有效的 prompt/context 策略

派 subagent 时 prompt 含 4 固定节：(1) Scene-setting（你是谁/在哪/做什么）；(2) Spec verbatim（直接贴原文而非让 subagent 读文件，锁范围）；(3) Conventions list（Pydantic v2 extra='forbid'/Literal/Depends(get_db)/services flush 不 commit 等显式列出，切断靠代码反推）；(4) Status reporting format（DONE/BLOCKED/NEEDS_CONTEXT + 7 字段）。反例：T1 prompt 简短让 subagent 读 SPEC 全文，跑偏到 Hydra 章节。**prompt 越具体越好，"让 subagent 自己读"是偷懒**。

## 7. 凭据与分发这两条工程要求迫使想清楚了哪些原本会忽略的问题

凭据（§3.1）：从"API key 是字符串"细化为威胁模型——存储介质（keyring/env/加密文件）/ 传输路径（不进 git/log/history）/ 状态可见性（不回显明文）/ 生命周期（引导+查看+更新+清除）。T19 setup.html 首次运行引导 + 隐藏输入 + form 重置全是凭据要求具体化。`security-guard.js` T19 真拦过一次 `body.value` 进 console.log。分发（§五-9）：WebUI 必须可访问 → Fly.io + volume 持久化 + auto_stop + CI deploy 全链路。CI 必须有 `unit-test` job 名 → 字面保留。数据卷 per-region 不可见是部署 Fly 才会想的问题。**工程要求是逼迫把没想清的想清，6 条 v1.1 修订建议一半来自凭据/分发要求具体化过程中暴露的 spec 漏洞。**

## 8. 如果重做会改变什么

改 5 件：(1) SPEC 写完立即让 fresh subagent 跑"可读性 audit"前置冷启动，省 24 task 隐性继承错误；(2) PLAN 拆更碎（T22→T22a/T22b）；(3) 每 task 后回写 SPEC 增量，让 SPEC 成为 living doc；(4) T1 后立即加 ruff/mypy CI job；(5) REFLECTION 在 T7/T14/T21 各写一段中程反思。保留 3 件：subagent-driven + 两阶段 review；7-worktree 策略；TDD 不可走捷径。

## 9. 对 Superpowers 方法论的批判——它假设了什么，这些假设成立吗

4 个假设：(1) subagent 是黑箱靠 prompt+review 控制——成立；(2) TDD 普适最优——部分成立，规约化任务成立，探索性任务过早锁死；(3) git worktree 是隔离单元——成立（Windows .venv 文件锁偶发但可恢复）；(4) **SPEC/PLAN self-sufficient——不成立**。T25 冷启动验证暴露 6 处缺陷（响应字段/排序字段/空列表状态码/路由文件位置/created_at 暴露/PLAN 缺 task），subagent 靠读代码补了洞。最强约束：流程对齐（worktree+TDD+subagent+review 四件套），价值 8/10。最弱假设：SPEC 自足——实际 SPEC 永远有缺口，subagent 用代码补。Superpowers 应增加"前置冷启动 audit"约束修补。**subagent-driven 非"无人值守"**：24 task 平均每 task 介入 1.5 次（提供 context/纠正偏离/决定下一步），自主的是"实现+自 review"，非"全流程"。最终评判：方法论价值 7/10——流程对齐 8/10，SPEC 自足假设 4/10，本项目 132 测试 + 24 task + 部署链路质量可接受，但若重做会前置冷启动 audit 修补最弱假设。

---

*作者：朱雨乐 / 完成日期：2026-08-06 / 项目：group-chat-digest (AI4SE B 类应用)*
