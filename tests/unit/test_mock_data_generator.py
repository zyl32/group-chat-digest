"""Tests for the mock chat data generator (T21)."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from scripts.gen_mock_chat import (
    generate_noise,
    generate_normal,
    generate_with_todos,
    main,
)


def test_normal_has_messages():
    msgs = generate_normal()
    assert len(msgs) == 200
    assert all("sender" in m and "content" in m for m in msgs)


def test_with_todos_contains_todos():
    msgs = generate_with_todos()
    joined = " ".join(m["content"] for m in msgs)
    assert "交报告" in joined or "deadline" in joined.lower()


def test_noise_has_many_short_messages():
    msgs = generate_noise()
    assert len(msgs) >= 100
    short_count = sum(1 for m in msgs if len(m["content"]) < 10)
    assert short_count > 50


def test_no_real_pii():
    msgs = generate_normal()
    text = json.dumps(msgs, ensure_ascii=False)
    assert "138" not in text  # 简化的电话检查
    assert "1" * 11 not in text


def test_all_generators_return_dicts_with_required_keys():
    for gen in (generate_normal, generate_with_todos, generate_noise):
        msgs = gen()
        assert len(msgs) > 0
        for m in msgs:
            assert isinstance(m, dict)
            assert "sender" in m
            assert "content" in m
            assert "timestamp" in m
            assert "msg_id" in m


def test_timestamps_are_isoformat_strings():
    for gen in (generate_normal, generate_with_todos, generate_noise):
        msgs = gen()
        for m in msgs:
            # Must parse without raising.
            datetime.fromisoformat(m["timestamp"])


def test_msg_ids_unique_within_dataset():
    for gen in (generate_normal, generate_with_todos, generate_noise):
        msgs = gen()
        ids = [m["msg_id"] for m in msgs]
        assert len(ids) == len(set(ids))


def test_with_todos_has_named_senders():
    msgs = generate_with_todos()
    # First 5 messages are the actionable todos.
    todo_senders = [m["sender"] for m in msgs[:5]]
    assert todo_senders == ["张三", "李四", "王五", "赵六", "钱七"]


def test_noise_messages_all_short():
    msgs = generate_noise()
    assert len(msgs) > 0
    for m in msgs:
        assert len(m["content"]) < 15


def test_deterministic_with_seed():
    a = generate_normal()
    b = generate_normal()
    assert a == b
    assert generate_with_todos() == generate_with_todos()
    assert generate_noise() == generate_noise()


def test_main_writes_files(tmp_path: Path):
    main(tmp_path)
    assert (tmp_path / "mock_chat_normal.json").exists()
    assert (tmp_path / "mock_chat_with_todos.json").exists()
    assert (tmp_path / "mock_chat_noise.json").exists()
    for name in (
        "mock_chat_normal.json",
        "mock_chat_with_todos.json",
        "mock_chat_noise.json",
    ):
        data = json.loads((tmp_path / name).read_text(encoding="utf-8"))
        assert "messages" in data
        assert len(data["messages"]) > 0
