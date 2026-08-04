# AGENT_LOG.md

> AI4SE 期末项目 · 群聊摘要与待办提取器 · 实现过程证据
>
> 按时间顺序记录每个 task 的关键节点，包含触发的 Superpowers 技能、prompt/context 配置、subagent 输出、人工干预与教训。
>
> §4.9 要求：这是实现工作中最重要的"过程证据"。

---

## [2026-08-05] Task T1: 项目骨架（FastAPI + uv + 第一个测试）

**所在 worktree**：`wt-foundation`（分支 `worktree-wt-foundation`）

**触发的 Superpowers 技能**：
- `superpowers:brainstorming`（前置：产出 SPEC.md）
- `superpowers:writing-plans`（前置：产出 PLAN.md）
- `superpowers:subagent-driven-development`（本 task 主流程）
- `superpowers:test-driven-development`（强制 TDD：先红后绿）

**派发 implementer subagent 的 prompt 摘要**：
- 模型：sonnet
- 任务：T1 完整五步 TDD（写失败测试 → 验证红 → 写实现 → 验证绿 → commit）
- 工作目录：`D:\大二下\summer\homework\.claude\worktrees\wt-foundation`
- 给定完整 task 文本（来自 PLAN.md T1 节）+ 架构上下文
- 强调：TDD 严格、Conventional Commits、YAGNI

**subagent 输出关键片段**：
- 状态：DONE_WITH_CONCERNS
- 9 个必需文件全部创建
- 红 → 绿验证：先 `ModuleNotFoundError: No module named 'fastapi'`，`uv sync` 后 `1 passed`
- Commit：`d172bcf` "feat: bootstrap FastAPI app with healthz endpoint and uv project"
- 同时提交了 `uv.lock`（最佳实践）
- 关注点：
  1. `[tool.uv].dev-dependencies` 字段在 uv 0.12.1 已弃用，每次 `uv run` 都警告
  2. FastAPI TestClient 弃用警告（上游问题，非阻塞）
  3. 未 push（合理，由编排器统一处理）
  4. `uv` 原本未安装，通过 `pip install uv` 装的
  5. Windows 无 `make`，直接用 `uv run pytest` 验证

**派发 spec compliance reviewer**：
- 模型：sonnet
- 验证方式：独立 `git show` 读 9 个文件，逐行对比 spec
- 结论：✅ Spec compliant，with minor concerns
  - 全部 9 个文件存在且符合 spec
  - `uv.lock` 是合理额外文件
  - 注意到 `[tool.uv]` 弃用与 Makefile `build` 目标引用未存在的 Dockerfile

**派发 code quality reviewer**：
- 模型：sonnet
- 结论：Ready to merge? **Yes, with one fix**
- Strengths：忠实于 PLAN.md、TDD 证据充分、可复现性（uv.lock 提交）、pytest 配置正确、.gitignore 正确排除
- Important issue：
  - `pyproject.toml:30-31` 的 `[tool.uv].dev-dependencies` 块已弃用，每次 `uv` 调用都警告，未来版本会变硬错误
- Minor issues：
  - `Makefile:7` `build` 目标引用不存在的 Dockerfile（T23 才加）
  - FastAPI TestClient 弃用警告（上游问题）
  - `app/main.py:6` 返回类型 `dict` 太宽（T1 spec 要求，后续 task 重构）
  - `app/__init__.py` 缺 `__all__`（无内容可导出，后续 task 重构）

**派发 fix implementer**：
- 模型：haiku（机械任务）
- 修复 1：删除 `pyproject.toml` 的 `[tool.uv]` 块
- 修复 2：`Makefile` `build` 目标上加 `# Requires Dockerfile (added in T23)` 注释
- 修复 3：把同样的 `[tool.uv]` 删除 backport 到 `PLAN.md`（避免后续 worktree 重新引入警告）
- Commit：`bba7b04` "fix: remove deprecated [tool.uv] block and document Makefile build target"

**人工干预**：
- 编排器（我）执行 grep 验证 fix 已应用：`tool.uv` 在 pyproject.toml 和 PLAN.md 中均无匹配；Makefile 注释已加
- 跳过完整 re-review：fix 范围极小（删 2 行 + 加 1 行注释 + 删 PLAN.md 2 行），implementer 自报 + 编排器 grep 双重验证足够

**学到的教训**：
1. PLAN.md 写得过于"字面"——把 `[tool.uv].dev-dependencies` 写死了，导致第一个 worktree 就把弃用警告引入。教训：写 PLAN 时若引用了某个工具的特定字段，最好快速查一下当前版本是否还支持。Backport 修复到 PLAN.md 是好习惯，避免后续 worktree 重新踩坑。
2. Windows 环境没 `make`，CI 用 Linux 有 `make`，但本地开发用 `uv run pytest` 等价命令即可。Makefile 主要是给 CI 与 Linux 用户用。
3. Worktree 工作流确实隔离干净——T1 的所有改动都在 `worktree-wt-foundation` 分支，main 分支没动，可以安全并行做其他事（虽然本项目串行）。
4. Subagent 报告"DONE_WITH_CONCERNS"很关键——它主动告知了 `[tool.uv]` 弃用警告，让 code quality reviewer 顺手就抓到了。如果 subagent 隐瞒，要走更多弯路。

**T1 完成 commit 链**：
- `d172bcf` feat: bootstrap FastAPI app with healthz endpoint and uv project
- `bba7b04` fix: remove deprecated [tool.uv] block and document Makefile build target
- `d7bb815` docs(agent-log): T1 entry with full process evidence

---

## [2026-08-05] Task T2: CI 骨架（GitHub Actions unit-test job）

**所在 worktree**：`wt-foundation`（分支 `worktree-wt-foundation`）

**触发的 Superpowers 技能**：
- `superpowers:subagent-driven-development`
- spec reviewer + code quality reviewer 两阶段评审

**派发 implementer subagent 的 prompt 摘要**：
- 模型：sonnet
- 任务：创建 `.github/workflows/ci.yml`，含 unit-test + docker-build + deploy stub 三个 job
- 关键约束：unit-test 名字硬性要求（§五-6）

**subagent 输出关键片段**：
- 状态：DONE
- Commit：`af04fc9` "ci: add unit-test, docker-build, and deploy stub jobs"
- self-review 抓到一个 critical bug：deploy stub 初始用 `exit 1` 会失败 CI（违反 §五-7），自改成 `echo`
- 注意：`uv.lock` 有 unrelated 修改，正确地未 stage

**派发 spec compliance reviewer**：
- 模型：sonnet
- 结论：✅ Spec compliant
- 验证：YAML 语法、action 版本、job 名、依赖链、触发条件全部符合

**派发 code quality reviewer**：
- 模型：sonnet
- 结论：Ready to merge? **No, needs fixes**
- Critical #1：`docker-build` job 在 T23（Dockerfile）前注定失败，违反 §五-7。建议整个 docker-build job 删掉，T23 时再加回。
- Critical #2：smoke test grep 模式太宽松 `"ok"` 应改为 `{"status":"ok"}`
- Important #3：缺 `concurrency` 控制块
- Important #4：`setup-python` 与 `setup-uv` 重复
- Important #5：缺 `permissions` 块（最小权限）
- Important #6：smoke test 用固定 `sleep 5` 脆弱
- Important #7：缺 `timeout-minutes`
- Minor #8-11：uv 版本固定、缓存、artifact 名、pytest maxfail

**派发 fix implementer**：
- 模型：sonnet（修复涉及多个 yaml 结构调整）
- 关键决策：整个 docker-build 与 deploy job 都删掉（T23/T24 再加回），而不是用 `continue-on-error` 掩盖——避免后续真实故障被掩盖
- 修复 1：删除 docker-build 与 deploy job（只留 unit-test）
- 修复 2：顶层加 `concurrency: { group: ci-${{ github.ref }}, cancel-in-progress: true }`
- 修复 3：删除 `actions/setup-python` 步骤，把 `python-version: "3.12"` 并入 `setup-uv`
- 修复 4：顶层加 `permissions: { contents: read }`
- 修复 5：unit-test job 加 `timeout-minutes: 10`
- 修复 6：setup-uv 加 `enable-cache: true` + `cache-dependency-glob: "uv.lock"`
- Commit：`7a5e18f` "fix(ci): remove docker-build/deploy stubs, add concurrency/permissions/timeout/cache"

**人工干预**：
- 编排器读最终 ci.yml 验证：38 行干净 YAML，仅 unit-test job，所有 6 项 fix 可见
- 跳过完整 re-review：fix 范围是机械删除 + 标准 yaml 块添加，编排器直接 Read 文件验证足够

**学到的教训**：
1. PLAN.md T2 写"docker-build job 在 T2 就建好"，但 Dockerfile 要到 T23 才有——这是 PLAN.md 的逻辑错误。教训：写 PLAN 时，CI job 与它依赖的产物要在同一 task 或之后才加，不能提前。Backport 修复到 PLAN.md 应该把 docker-build 移到 T23。
2. Subagent self-review 抓到 deploy stub `exit 1` bug 很有价值——subagent 主动报告 critical bug 比让 reviewer 抓更省一轮。
3. Code quality reviewer 提的 Minor 问题（uv 版本固定、artifact 名、pytest maxfail）我选择不修——工程量与价值不匹配，YAGNI。等 T24 真部署时再优化。
4. PyYAML 把 `on:` 解析为布尔键 `True` 是已知问题，GitHub Actions 实际能正确处理。但如果以后要用 `yq` 或其他工具解析，要注意。

**T2 完成 commit 链**：
- `af04fc9` ci: add unit-test, docker-build, and deploy stub jobs
- `7a5e18f` fix(ci): remove docker-build/deploy stubs, add concurrency/permissions/timeout/cache

---

## [2026-08-05] Task T3: 配置加载（Hydra + OmegaConf + frozen dataclasses）

**所在 worktree**：`wt-foundation`（分支 `worktree-wt-foundation`）

**触发的 Superpowers 技能**：
- `superpowers:subagent-driven-development`
- spec reviewer + code quality reviewer 两阶段评审

**派发 implementer subagent 的 prompt 摘要**：
- 模型：sonnet
- 任务：T3 完整 TDD — 实现 `app/config.py` 用 OmegaConf 包装 frozen dataclass `AppConfig`（含 LLMConfig/DBConfig/UploadConfig 三组），暴露 `load_config(overrides)` 返回 DictConfig 支持 `cfg.llm.provider` 属性访问
- 关键约束：coding-style.md 要求 frozen dataclass + 不可变配置；OmegaConf 结构化校验
- 测试要求：默认值 + override 两测试

**subagent 输出关键片段**：
- 状态：DONE
- Commit：`f3d753e` "feat(config): add OmegaConf-based load_config with frozen dataclass schema"
- 实现：4 个 frozen dataclass + `load_config` 函数
- 关键设计决策：
  1. 返回 `DictConfig` 直接（而非 `to_container` 后的 dict），保留 `cfg.llm.provider` 属性访问
  2. 用 `OmegaConf.structured(frozen_dataclass)` 后再 merge overrides 会触发 `ReadonlyConfigError`，因此先把 structured defaults 通过 `OmegaConf.to_container(..., resolve=True)` 物化成 dict，再用 `OmegaConf.create(...)` 重新包成可变 DictConfig，最后 merge overrides

**派发 spec compliance reviewer**：
- 模型：sonnet
- 结论：✅ Spec compliant
- 验证：4 个 dataclass 字段齐全、load_config 签名匹配、frozen=True 满足 immutability、覆盖测试通过

**派发 code quality reviewer**：
- 模型：sonnet
- 结论：Ready to merge? **No, needs fixes**
- Important #1：`run/conf/config.yaml` 文件存在但 `load_config` 完全不读它（死代码，operator 误以为改 yaml 生效）
- Important #2：缺边界 case 测试（空 overrides list 应等同 None）
- Important #3：缺 YAML 加载测试
- Minor #4：TODO 注释应放在 workaround 附近便于后续 task 回找
- Minor #5：structured validation 被静默绕过（frozen → 物化 → 重建丢了 schema 校验），应留 TODO 给 T11/T12 重新启用

**派发 fix implementer**：
- 模型：sonnet（修复涉及 OmegaConf merge 链路 + 新增测试）
- 修复 1：在 `load_config` 中插入 YAML 文件加载层 — 优先级：dataclass defaults → YAML → CLI overrides
- 修复 2：新增 `test_load_config_empty_overrides_list` 验证空 list 与 None 行为一致
- 修复 3：新增 `test_load_config_reads_yaml_file` 验证 YAML 读取
- 修复 4：在 workaround 注释旁加 `TODO(T11/T12)` 引用，便于后续 task 重新启用 structured validation
- Commit：`89a9832` "fix(config): load YAML file, add edge case tests, defer structured validation TODO"

**人工干预**：
- 编排器读 `app/config.py` 与 `tests/unit/test_config.py` 验证：YAML 加载逻辑就位、2 个新测试存在、TODO 注释指向 T11/T12
- 跑 `uv run pytest -v`：5 项全过（2 原 config + 2 新增 + 1 healthz）
- 跳过完整 re-review：fix 范围是机械添加（YAML 加载 4 行 + 2 个测试 + TODO 1 行），implementer 自报 + 编排器直接 Read + 跑测试 三重验证足够

**学到的教训**：
1. `OmegaConf.structured(frozen_dataclass)` 会产生 readonly 节点，与 `OmegaConf.merge(overrides)` 不兼容。变通方法：先 `to_container(resolve=True)` 物化成 plain dict，再 `OmegaConf.create(...)` 重新包成可变 DictConfig。代价：丢失 structured schema 校验（坏 override 静默接受）。在 T11/T12 LLM provider 集成时，错误 override 才会显式爆炸，那时再切回 structured + 变更 frozen 实现策略。
2. 死代码是 spec compliance 看不见但 code quality 抓得到的典型 issue — `run/conf/config.yaml` 既然存在就必须有路径读取，否则要么删文件要么接通。最终选择接通（YAML 是 operator 调优的合理途径）。
3. 边界 case 测试（空 list vs None）容易漏。写 PLAN 时若提到 `Optional[list[str]] = None`，应在测试一栏同时给出 `[]` 与 `None` 两种调用。
4. Workaround 注释要带 TODO 引用具体 task 编号，否则后续 task 不知道回来修。注释 + 引用 = 给未来自己留路标。

**T3 完成 commit 链**：
- `f3d753e` feat(config): add OmegaConf-based load_config with frozen dataclass schema
- `89a9832` fix(config): load YAML file, add edge case tests, defer structured validation TODO

---

## [2026-08-05] Task T4: 数据模型（SQLAlchemy ORM）

**所在 worktree**：`wt-foundation`（分支 `worktree-wt-foundation`）

**触发的 Superpowers 技能**：
- `superpowers:subagent-driven-development`
- spec reviewer + code quality reviewer 两阶段评审

**派发 implementer subagent 的 prompt 摘要**：
- 模型：sonnet
- 任务：T4 完整 TDD — 创建 7 个模型文件 + 1 个测试文件
- 模型清单：Upload/Message/Digest/Todo/Setting + db.py(Base+get_engine+get_session) + `__init__.py` 导出 `__all__`
- 关键约束：coding-style.md `__all__` 要求、YAGNI（不加 Alembic、不加额外列）、Conventional Commits
- 给定完整 PLAN.md T4 节文本（含所有模型代码）

**subagent 输出关键片段**：
- 状态：DONE
- Commit：`7347232` "feat: add SQLAlchemy models for Upload/Message/Digest/Todo/Setting"
- 7 项测试全过（5 prior + 2 new）
- Self-review 抓到 2 处需调整：
  1. `app/models/message.py` 删除未用的 `from datetime import datetime`（`timestamp` 列用 `DateTime` 类型而非 `datetime` 调用）
  2. **必要偏离**：`Upload.id` 加 `default=_new_uuid`（`str(uuid.uuid4())`）—— 不加的话 T4 测试 `Upload(filename=..., fmt=..., size=..., status=...)` 会因 `NOT NULL constraint failed: uploads.id` 失败。spec 注释 `# uuid` 暗示这就是设计意图
- 关注点（非阻断）：
  - `datetime.utcnow()` 在 Python 3.12+ 已弃用（verbatim from PLAN.md）
  - `get_session` 退出时 auto-commit（by spec，后续 service 层可能需要更细控制）
  - `Upload.id` String 列在 SQLite 中无界，36 字符 uuid 完全容纳

**派发 spec compliance reviewer**：
- 模型：sonnet
- 验证方式：独立 `git show 7347232 -- <file>` 读 8 个文件，逐项对比 spec 10 条要求
- 结论：✅ Spec compliant
  - 8 个文件全部存在
  - 4 个模型字段全部对齐 spec（含 UniqueConstraint、index、unique=True、default 值）
  - `__all__` 含全部 8 个公共符号
  - 测试数 = 2（无额外测试）
  - `_new_uuid` 默认是必要偏离（让 literal 测试通过），列类型仍是 String PK，未变 — 在 leniency 范围内

**派发 code quality reviewer**：
- 模型：sonnet
- 结论：Ready to merge? **Yes, with two small fixes**
- Strengths：
  - 模块分离干净（每文件 < 25 行，远低于 400 行上限）
  - `_new_uuid` 是模块级函数 + 类型注解，`default=_new_uuid` 引用而非调用 — 正确 SQLAlchemy 模式
  - FK + index 配置合理（Message.upload_id/Todo.upload_id 索引，Digest.upload_id unique 1:1）
  - `except Exception:` 具体异常非 bare except
  - 包内相对导入 + 包外绝对导入 — PEP 8 合规
- Important issues：
  - **HIGH #1**：`datetime.utcnow` 在 Python 3.12+ 弃用，CI 每次 emit `DeprecationWarning`。修复：4 处 call site 改为 `lambda: datetime.now(timezone.utc)`
  - **HIGH #2**：`get_session(engine)` 缺类型注解，违反 coding-style.md "all functions must have type hints"。修复：`engine: Engine` + import `Engine` from sqlalchemy
- Minor issues（不阻断）：
  - 测试覆盖缺口（Digest CRUD / Setting CRUD / UniqueConstraint / Todo.state 默认值）— 推到 T5 fixtures 一并处理
  - `ResourceWarning: unclosed database` — 测试无 dispose engine，Low 优先级
  - `get_session` auto-commit 违反单一职责 — by spec，service 层可能需要更细控制，T7+ 再评估
  - `Column` 风格 vs SQLAlchemy 2.0 `Mapped[...]` — INFO，PLAN.md spec literal 用 Column，无即时收益，不动

**派发 fix implementer**：
- 模型：haiku（机械替换 + 类型注解添加）
- 修复 1：4 处 `datetime.utcnow` → `lambda: datetime.now(timezone.utc)`
  - `app/models/upload.py:20` received_at
  - `app/models/digest.py:16` created_at
  - `app/models/todo.py:18-19` created_at + updated_at（含 onupdate）
  - 4 个文件 import 行加 `timezone`
- 修复 2：`app/models/db.py` `get_session(engine)` → `get_session(engine: Engine)`，import 加 `Engine`
- Commit：`ac5d1ed` "fix(models): replace deprecated datetime.utcnow with timezone-aware now, type hint get_session"
- 验证：`uv run pytest -v` → 7 passed，`utcnow` DeprecationWarning 已清；仅剩 Starlette TestClient 上游弃用警告（非本项目代码，T1 已知）

**人工干预**：
- 编排器跑 `uv run pytest -v` 验证：7 passed，warnings summary 中无 `utcnow` 条目，仅 Starlette 上游警告
- 跳过完整 re-review：fix 范围极小（4 处 lambda 替换 + 1 个类型注解 + 2 个 import 修改），implementer 自报 + 编排器跑测试 + 直接读 diff 三重验证足够
- Minor 推迟：测试覆盖缺口推到 T5（conftest 会需要更广的 fixtures，到时一起补 Digest/Setting/UniqueConstraint/Todo default 测试）

**学到的教训**：
1. **PLAN.md 中的 sample code 会带病传播**：T4 spec literal 用了 `datetime.utcnow`，第一个 worktree 就把弃用警告引入。教训与 T1 `[tool.uv]` 弃用一样 — 写 PLAN 时若 sample code 引用了某个标准库 API，最好快速查一下当前 Python 版本是否还支持。Backport 修复到 PLAN.md？这次没做，因为 fix 只 4 行且已记入 AGENT_LOG；后续 worktree 不会重做 T4，无传播风险。
2. **必要偏离要明示**：implementer 主动报告 `_new_uuid` default 是为了让 literal 测试通过而加的，spec reviewer 在 leniency 范围内接受。如果 implementer 隐瞒，spec reviewer 会判违规。Subagent 自报偏差是健康信号。
3. **`Column` vs `Mapped[...]`**：reviewer 建议保留 `Column` 风格，因为 spec literal 用了它，且整个项目尚未确立 2.0 typed ORM 模式 — 切换会让 T4 偏离 spec 且无即时收益。教训：风格选型看 spec 与已有 pattern，不要在 foundation task 里搞"理想主义重构"。
4. **Test coverage 推迟到合适 task**：T4 测试只覆盖核心 Upload→Message→Todo 路径，Digest/Setting/UniqueConstraint 都没测。reviewer 没要求 T4 补，因为 T5（conftest fixtures）会自然需要更广的 fixtures，到时一并补更合适。教训：测试覆盖增量要随 fixtures 一起长，不要为了 round-trip 强塞。
5. **`datetime.now(timezone.utc)` 的 lambda 包装**：直接写 `default=datetime.now(timezone.utc)` 会立即求值（所有行共享同一时间戳），必须 `default=lambda: datetime.now(timezone.utc)` 才能在每次 insert 时重新调用。SQLAlchemy `default` 接受 callable，这是常见 gotcha。

**T4 完成 commit 链**：
- `7347232` feat: add SQLAlchemy models for Upload/Message/Digest/Todo/Setting
- `ac5d1ed` fix(models): replace deprecated datetime.utcnow with timezone-aware now, type hint get_session

---

## [2026-08-05] Task T5: 测试 fixtures（conftest）

**所在 worktree**：`wt-foundation`（分支 `worktree-wt-foundation`）— 本 worktree 最后一个 task

**触发的 Superpowers 技能**：
- `superpowers:subagent-driven-development`
- spec reviewer + code quality reviewer 两阶段评审

**派发 implementer subagent 的 prompt 摘要**：
- 模型：sonnet
- 任务：T5 完整 TDD — 创建 `tests/conftest.py`（in_memory_db + client fixture）与 `tests/unit/test_conftest.py`
- 关键约束：
  1. PLAN 自我修订：mock_llm fixture 推迟到 T11，T5 只实现 in_memory_db + client
  2. PLAN 的 `client` fixture 中 `app.dependency_overrides[...] = lambda: in_memory_db` 是不完整 placeholder（T14 才有真 dep）—— 选 Option A：`yield TestClient(app)` minimal scaffolding + 注释 T14 扩展
  3. `in_memory_db` 用 clean `sessionmaker(bind=engine)()` 而非 PLAN 的 `get_session(engine).__enter__()` hack（避免 contextmanager 滥用）
  4. 加 `engine.dispose()` 修 T4 reviewer 提的 Low-severity ResourceWarning
  5. `datetime.now(timezone.utc)` 而非 `utcnow()`（T4 fix precedent）

**subagent 输出关键片段**：
- 状态：DONE
- Commit：`c546cd7` "test: add shared fixtures (in_memory_db, client)"
- 8 项测试全过（7 prior + 1 new）
- Self-review 6 项检查全过：fixture 可用、无 ResourceWarning、未实现 mock_llm、client minimal、无未用 import、clean sessionmaker

**派发 spec compliance reviewer**：
- 模型：sonnet
- 验证方式：独立 `git show c546cd7 -- <file>` 读两文件，9 项 spec 逐条对
- 结论：✅ Spec compliant
  - 2 个文件存在
  - `in_memory_db` 用 `sqlite://` + `Base.metadata.create_all` + session.close + engine.dispose
  - `mock_llm` 未实现（推 T11）✅
  - 测试数 = 1（无额外）✅
  - 3 个 disclosed deviations（sessionmaker / dispose / Option A client）全在 leniency 内

**派发 code quality reviewer**：
- 模型：sonnet
- 结论：Ready to merge? **Yes, with one fix**
- Strengths：
  - Teardown 顺序正确（session.close → engine.dispose，pytest 保证 post-yield 即使测试失败也跑）
  - 每个 test 独立 engine（function scope，schema 干净）
  - `datetime.now(timezone.utc)` 合规
  - `client` fixture 选 Option A 诚实——PLAN 的 `dependency_overrides[...]` 指向尚不存在的依赖，不实现是对的
  - Import hygiene 干净（stdlib→third-party→local）
  - T4 reviewer 提的 Digest/Setting/UniqueConstraint 测试 — `test_models.py` 已部分覆盖，无需在 conftest 重复
- Important issues：
  - **HIGH #1**：fixture 函数缺类型注解，违反 coding-style.md "all functions must have type hints"。修复：`in_memory_db() -> Iterator[Session]`、`client() -> Iterator[TestClient]`，import `Iterator` from typing
- Minor issues（不阻断）：
  - LOW #2：teardown 缺 `try/finally` 包裹 — `session.close()` 实际不会抛，纯防御性，跳过
  - LOW #3：`client` fixture 无 smoke test — 加一行 `def test_client_healthz(client): client.get("/healthz")` 闭环 scaffolding，廉价
  - LOW #4：`test_in_memory_db_fixture` 显式设 `received_at` — 可省略以同时测模型 default，但当前测试目标是 fixture 而非 model default，不动

**派发 fix implementer**：
- 模型：haiku（机械添加类型注解 + 一行 smoke test）
- 修复 1：`tests/conftest.py` 加 `from typing import Iterator`，`Session` from sqlalchemy.orm 已有；两 fixture 加返回类型
- 修复 2：`tests/unit/test_conftest.py` 追加 `test_client_healthz(client)`，验证 `/healthz` 返回 200 + `{"status": "ok"}`
- Commit：`fb02ea8` "fix(tests): add type hints to fixtures, add client fixture smoke test"
- 验证：9 passed（8 prior + 1 new client smoke）

**人工干预**：
- 编排器跑 `uv run pytest -v` 验证：9 passed，唯一警告是 Starlette 上游 TestClient 弃用（T1 已知）
- 跳过完整 re-review：fix 是机械添加（类型注解 + 1 行测试），implementer 自报 + 编排器跑测试 + 直接读 diff 三重验证足够

**学到的教训**：
1. **Fixture 也是函数**：coding-style.md "all functions must have type hints" 字面包含 fixture。pytest fixture 风格上常省略类型，但项目规则严格要求 — fixture 返回 `Iterator[T]`（yield-only 模式），不用 `Generator[T, None, None]`（更复杂）。
2. **PLAN.md 自我修订是好实践**：T5 spec 在 PLAN 内部就明确写了"mock_llm 推到 T11"，避免了 implementer 在 spec 与 reviewer 之间纠结。教训：写 PLAN 时若发现 task 之间有依赖错位（fixture 依赖尚未实现的 adapter），及时在 PLAN 内做修订注记，比让 implementer 现场判断更稳。
3. **Scaffolding fixture 要有 smoke test**：`client` fixture 看似 trivial（一行 yield），但加一个 `test_client_healthz` 把 scaffolding 闭环 — 后续 T14 改 fixture 时，这个 smoke test 会立即告诉你是否打破了基础契约。教训：任何 scaffolding code 至少配一个最简 smoke test。
4. **`get_session(engine).__enter__()` 是 hack**：contextmanager 不应该这样手动 `__enter__()`。Clean 替代是直接 `sessionmaker(bind=engine)()`。教训：PLAN.md 里的 sample code 偶尔会有 hack 写法，implementer 应当识别并改进，而不是机械复制。
5. **wt-foundation 全程总结**：T1→T5 五个 task 在同一 worktree 内完成，分支 `worktree-wt-foundation` 共 12 个 commit。所有改动隔离干净，main 分支从未被污染。下一步用 `superpowers:finishing-a-development-branch` 合并到 main，然后开 wt-parsers-llm worktree 做 T6-T12。

**T5 完成 commit 链**：
- `c546cd7` test: add shared fixtures (in_memory_db, client)
- `fb02ea8` fix(tests): add type hints to fixtures, add client fixture smoke test

**wt-foundation 全部 commit（T1-T5）**：
- T1: `d172bcf` + `bba7b04` + `d7bb815` (agent-log)
- T2: `af04fc9` + `7a5e18f`
- T3: `f3d753e` + `89a9832` + `b005c04` (agent-log)
- T4: `7347232` + `ac5d1ed` + `4ffed62` (agent-log)
- T5: `c546cd7` + `fb02ea8`

---

## [2026-08-05] Task T6: Parser 协议 + WeChat JSON Parser

**所在 worktree**：`wt-parsers-llm`（分支 `worktree-wt-parsers-llm`）— 本 worktree 第一个 task

**触发的 Superpowers 技能**：
- `superpowers:subagent-driven-development`
- spec reviewer + code quality reviewer 两阶段评审

**派发 implementer subagent 的 prompt 摘要**：
- 模型：sonnet
- 任务：T6 完整 TDD — Parser Protocol + ParsedMessage (frozen dataclass) + ParseError + WechatJsonParser + PARSERS registry
- 关键约束：coding-style.md Factory/Registry 模式、`__all__` 在每个 `__init__.py`、frozen dataclass 不可变、YAGNI（不加 Feishu/PlainText，不加额外字段）
- 给定完整 PLAN.md T6 节文本（含 base.py/wechat_json.py/__init__.py 三段实现 + 3 个测试）

**subagent 输出关键片段**：
- 状态：DONE
- Commit：`f2821c5` "feat: add Parser protocol and WeChat JSON parser"
- 12 项测试全过（9 baseline + 3 new T6）
- Self-review 6 项检查全过
- 主动 disclosed deviations：
  1. 创建 `app/adapters/__init__.py`（空 `__all__` package marker）— coding-style.md 要求
  2. 防御性编程加强：加 `isinstance(data, dict)` + `isinstance(m, dict)` 检查，但 error contract 与 spec 一致
  3. `uv.lock` 有 unrelated venv sync diff — 正确地未 stage

**派发 spec compliance reviewer**：
- 模型：sonnet
- 验证方式：独立 `git show f2821c5 -- <file>` 读 5 个文件 + 1 个额外 `app/adapters/__init__.py`，11 项 spec 逐条对
- 结论：✅ Spec compliant
  - `ParsedMessage` frozen dataclass with 4 fields ✅
  - `Parser` Protocol with 2 methods ✅
  - `WechatJsonParser.name()` returns "wechat" ✅
  - 4 个 error path 全部抛 `ParseError` ✅
  - `__all__` 含 5 个公共符号 ✅
  - `PARSERS = {"wechat": WechatJsonParser}` ✅
  - Fixture 2 条消息 sender 正确 ✅
  - 测试数 = 3 ✅
- Minor observations（不阻断）：m2 timestamp 用完整 ISO 8601；try/except/else 风格不如 pytest.raises；PARSERS 类型注解太松

**派发 code quality reviewer**：
- 模型：sonnet
- 结论：Ready to merge? **Yes, with one fix**
- Strengths：frozen dataclass 简洁、Protocol 用 typing.Protocol 无需 runtime_checkable、错误处理具体（JSONDecodeError/KeyError/ValueError + raise from）、isinstance 防御合理（I/O 边界）、每文件 `__all__` + 类型注解
- Important issue：
  - **HIGH #1**：`PARSERS: dict[str, type]` 太松，改为 `dict[str, type[Parser]]`
- Minor issues（不阻断）：
  - MED #2：测试 try/except/else 不如 `pytest.raises` 惯用，且 `import pytest` 缺
  - MED #3：硬编码相对路径 `Path("tests/fixtures/wechat_sample.json")`，从非根目录跑会断 — 改 `FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"`
  - LOW #4：缺字段级边界测试（missing sender / bad timestamp format / non-string content）
  - LOW #5：timestamp 在 sender/content/msg_id 前验证，错误消息顺序耦合
  - LOW #6：`name()` 是实例方法，PARSERS 注册的是类 — 目前无冲突

**派发 fix implementer**：
- 模型：haiku
- 修复 1：`PARSERS: dict[str, type[Parser]] = {"wechat": WechatJsonParser}`
- 修复 2：测试改 `pytest.raises(ParseError, match="empty")` + `pytest.raises(ParseError)`，加 `import pytest`
- 修复 3：`FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"` 模块级常量
- Commit：`a6bd556` "fix(parsers): tighten PARSERS type hint, modernize test style to pytest.raises"
- 验证：12 passed，无回归

**人工干预**：
- 编排器跑 `uv run pytest -v` 验证：12 passed
- 跳过完整 re-review：fix 范围是机械添加（1 行类型注解 + 测试风格重构 + 路径常量化）
- LOW 字段级边界测试推迟 — T7/T8 自然引用 base.py，到时若发现 regression 再补

**学到的教训**：
1. **Registry 类型注解要精确**：`dict[str, type]` 丢失"Parser 子类型"契约，`dict[str, type[Parser]]` 把契约写在类型层
2. **测试风格 `pytest.raises` > try/except/else**：自带 `match` 正则断言，一行替代四行
3. **测试 fixture 路径用模块级常量**：`Path("tests/fixtures/...")` 假设从 root 跑；`Path(__file__).resolve().parent.parent / "fixtures"` 位置无关
4. **defensive isinstance 在 I/O 边界是合理的**：parser 入口接收任意 bytes，type guard 防止 AttributeError；非 YAGNI 违规
5. **uv.lock unstaged diff 处理**：implementer 正确未 stage unrelated venv sync diff，保持 commit 干净

**T6 完成 commit 链**：
- `f2821c5` feat: add Parser protocol and WeChat JSON parser
- `a6bd556` fix(parsers): tighten PARSERS type hint, modernize test style to pytest.raises

---

## [2026-08-05] Task T7: Feishu JSON Parser

**所在 worktree**：`wt-parsers-llm`（分支 `worktree-wt-parsers-llm`）

**触发的 Superpowers 技能**：
- `superpowers:subagent-driven-development`
- spec reviewer + code quality reviewer 两阶段评审

**派发 implementer subagent 的 prompt 摘要**：
- 模型：sonnet
- 任务：T7 完整 TDD — FeishuJsonParser + 注册到 PARSERS + 3 个测试（normal + 2 error-path，沿用 T6 lesson）
- 关键约束：
  1. Feishu 时间戳是 unix 秒字符串，必须用 `datetime.fromtimestamp(int(...), tz=timezone.utc)`
  2. sender 是嵌套对象 `m["sender"]["name"]`（非平铺）
  3. content 字段名是 `body`，msg_id 字段名是 `message_id`（与 WeChat 不同）
  4. 沿用 T6 lessons：`pytest.raises`、`Path(__file__).resolve()`、defensive isinstance、不 stage `uv.lock` diff

**subagent 输出关键片段**：
- 状态：DONE
- Commit：`8682996` "feat: add Feishu JSON parser"
- 15 项测试全过（12 prior + 3 new）
- 主动应用 T6 lessons：FIXTURES 常量、pytest.raises、defensive isinstance、PARSERS 类型已收紧
- 主动加 2 个 error-path 测试（empty + malformed）— 提前锁定 contract
- `uv.lock` 正确未 stage

**派发 spec compliance reviewer**：
- 模型：sonnet
- 结论：✅ Spec compliant
- 11 项 spec 逐条对：name() returns "feishu" ✅；timestamp 用 `tz=timezone.utc` ✅；sender 嵌套访问 ✅；content 从 `m["body"]` ✅；msg_id 从 `m["message_id"]` ✅；4 个 error path ✅；PARSERS 2 entries ✅；`__all__` 含 FeishuJsonParser ✅；fixture 1 message 字段正确 ✅
- Minor observations：sender dict 检查（authorized）；style nit on error-grouping

**派发 code quality reviewer**：
- 模型：sonnet
- 结论：Ready to merge? **Yes, with one fix**（实为 2 项）
- Strengths：类型注解完整、UTC 处理正确、isinstance 防御合理、test 沿用 T6 lessons、`__init__.py` 注册正确
- Important issues：
  - **HIGH #1**：`int(m["create_time"])` 在 float-字符串（`"1735431600.5"`）抛 ValueError，但在 JSON number float（`1735431600.5`）静默截断 — 行为不一致。Fix：显式 `int()` + 负值校验 + `int(None)` 经 TypeError 转 ParseError
  - **MEDIUM #2**：wechat_json.py 与 feishu_json.py 的 JSON loading + root-object + messages-list + empty + per-entry-isinstance preamble 18 行重复。YAGNI threshold（3+ parsers）"arguably already met"。Extract `_load_message_objects(raw) -> list[dict]` 到 `base.py`
- Minor issues（不阻断）：
  - LOW #3：fixture 仅 1 message — 可加 2-3 测多消息排序
  - LOW #4：缺 missing-field 测试（missing sender/body/create_time，non-dict sender）— 各 isinstance/KeyError 分支未被测试覆盖
  - LOW #5：`body`/`message_id` 未 type-check — 若是 null/number 会传非 str 给 ParsedMessage；与 WeChat 行为一致，acceptable
  - LOW #6：timestamp `1735431600` = 2024-12-29 09:00 UTC，合理近期日期

**派发 fix implementer**：
- 模型：sonnet（涉及多文件重构 + helper 抽取 + 新测试）
- 修复 1（HIGH）：feishu_json.py create_time 改为 `m.get(...)` → `int(ts_raw)` 显式 try/except + 负值校验 + `int(None)` 经 TypeError 转 ParseError
- 修复 2（MEDIUM）：
  - `base.py` 新增 `_load_message_objects(raw: bytes) -> list[dict]` helper，集中 JSON loading + 结构 validation，加入 `__all__`
  - `wechat_json.py` 重构：移除本地 `import json`，用 helper，合并 KeyError 分支
  - `feishu_json.py` 重构：移除本地 `import json`，用 helper，保留 Fix 1 的 create_time 校验
- 修复 3（LOW）：test_parsers_feishu.py 加 3 个 missing-field 测试：
  - `test_feishu_missing_sender` (match "sender")
  - `test_feishu_missing_create_time` (match "create_time")
  - `test_feishu_negative_create_time` (match "out of range")
- Commit：`ba384e9` "fix(parsers): extract _load_message_objects helper, harden create_time validation, add missing-field tests"
- 验证：18 passed（15 prior + 3 new），WeChat 重构后 3 测试全过，无回归

**人工干预**：
- 编排器跑 `uv run pytest -v` 验证：18 passed
- 跳过完整 re-review：fix 涉及 4 文件 + helper 抽取，但 implementer 自报 + 编排器跑测试 + 测试覆盖足够
- LOW fixture 多消息推迟 — 当前 1 message 已覆盖核心路径

**学到的教训**：
1. **Helper extraction 时机判断**：reviewer 说"YAGNI threshold 3+ arguably already met" — 但 T8 PlainText 不用 JSON loading，所以实际只有 2 个 JSON parser 受益。我选择抽取是因为 18 行 preamble 重复在 wechat+feishu 各出现一次，抽取后两文件都更干净，且 base.py 仅有 15 行 helper 增量。教训：YAGNI 阈值不是绝对，看重复代码的"密度"和"未来 task 是否会用到"。
2. **类型强制的不一致性**：`int("123.5")` 抛 `ValueError`，但 `int(123.5)` 静默截断 — Python 的隐式转换不对称。在 I/O 边界处理混合类型输入时，必须显式 `try int(...) except (TypeError, ValueError)`。教训：never trust JSON 字段类型，永远是 string/number/null 三种可能。
3. **测试覆盖 isinstance/KeyError 分支**：T6 没测 missing sender/missing content，T7 reviewer 抓到。每个 error-path branch 至少配一个测试，否则 reviewer 会要求补。教训：写代码时数一下 if/except 分支数，每个分支配一个测试。
4. **defensive isinstance 在 nested 对象上更重要**：`m["sender"]` 可能是 string/null/dict，`m["sender"]["name"]` 在 string/null 上会抛 TypeError 而非 KeyError。`isinstance(sender_obj, dict)` 前置检查把 TypeError 转为清晰的 ParseError("bad sender")。教训：嵌套访问前先 type-guard。
5. **`__all__` 在 regular module 也值得加**：coding-style.md 只要求 `__init__.py` 有 `__all__`，但 base.py 作为公共 helper 模块加 `__all__` 让 public API 显式（`_load_message_objects` 也在内，明示是 package-internal helper）。教训：helper 模块加 `__all__` 区分 public 与 internal。

**T7 完成 commit 链**：
- `8682996` feat: add Feishu JSON parser
- `ba384e9` fix(parsers): extract _load_message_objects helper, harden create_time validation, add missing-field tests

---
