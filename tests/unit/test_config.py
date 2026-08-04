from app.config import load_config


def test_load_config_default():
    cfg = load_config()
    assert cfg.llm.provider == "deepseek"
    assert cfg.db.url == "sqlite:///data/db/app.db"
    assert cfg.upload.max_size_mb == 10


def test_load_config_override():
    cfg = load_config(overrides=["llm.provider=mock"])
    assert cfg.llm.provider == "mock"
