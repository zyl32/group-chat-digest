"""Generate 3 mock chat datasets for demo and E2E testing.

Scenarios:
- normal: 200 mixed-topic messages from 20 synthetic students
- with_todos: 5 actionable items + 50 ack messages (LLM should extract 5 todos)
- noise: 120 short emoji/+1/收到 messages (LLM should produce fallback todos)

No real PII: synthetic names (student_XX) for normal/noise; common
surnames (张三/李四/王五/赵六/钱七) for with_todos. No phone numbers,
emails, or addresses.

Deterministic via random.seed(42/43/44) — same seed → same output.
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

__all__ = ["generate_normal", "generate_with_todos", "generate_noise", "main"]

_NAMES: list[str] = [f"student_{i:02d}" for i in range(20)]


def _ts(start: datetime, i: int) -> str:
    """Return ISO timestamp `start + i minutes`."""
    return (start + timedelta(minutes=i)).isoformat()


def generate_normal() -> list[dict[str, str]]:
    """Return 200 mixed-topic messages from synthetic students."""
    random.seed(42)
    start = datetime(2026, 8, 5, 9, 0)
    topics = ["操作系统作业", "数据结构复习", "下周小测", "实验报告", "图书馆约自习"]
    suffixes = ["讨论一下", "求带", "我懂了", "哪天截止"]
    return [
        {
            "sender": random.choice(_NAMES),
            "content": random.choice(topics) + " " + random.choice(suffixes),
            "timestamp": _ts(start, i),
            "msg_id": f"m{i:x}",
        }
        for i in range(200)
    ]


def generate_with_todos() -> list[dict[str, str]]:
    """Return 5 actionable items + 50 acks. LLM should extract 5 todos."""
    random.seed(43)
    start = datetime(2026, 8, 5, 10, 0)
    todos: list[tuple[str, str]] = [
        ("张三", "明天 18:00 前交报告，操作系统实验"),
        ("李四", "周五前订会议室"),
        ("王五", "下周一前回复导师邮件"),
        ("赵六", "周五 23:59 前提交小测"),
        ("钱七", "今晚 8 点前发会议链接"),
    ]
    msgs: list[dict[str, str]] = [
        {"sender": who, "content": what, "timestamp": _ts(start, i), "msg_id": f"t{i}"}
        for i, (who, what) in enumerate(todos)
    ]
    acks = ["收到", "好的", "了解", "我去"]
    for i in range(50):
        msgs.append(
            {
                "sender": random.choice(_NAMES),
                "content": random.choice(acks),
                "timestamp": _ts(start, len(todos) + i),
                "msg_id": f"r{i}",
            }
        )
    return msgs


def generate_noise() -> list[dict[str, str]]:
    """Return 120 short emoji/+1 messages. LLM should produce fallback todos."""
    random.seed(44)
    start = datetime(2026, 8, 5, 14, 0)
    noise = ["[表情]", "[图片]", "哈哈哈哈", "+1", "ok", "...", "[动画表情]"]
    return [
        {
            "sender": random.choice(_NAMES),
            "content": random.choice(noise),
            "timestamp": _ts(start, i),
            "msg_id": f"n{i}",
        }
        for i in range(120)
    ]


def main(out_dir: Path) -> None:
    """Write the 3 datasets as JSON to `out_dir`."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, gen in [
        ("mock_chat_normal.json", generate_normal),
        ("mock_chat_with_todos.json", generate_with_todos),
        ("mock_chat_noise.json", generate_noise),
    ]:
        (out_dir / name).write_text(
            json.dumps({"messages": gen()}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main(Path("data/mock"))
