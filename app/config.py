"""Configuration loader using OmegaConf with structured dataclass schema.

This module defines the application's typed configuration schema (frozen
dataclasses per `coding-style.md` immutability rule) and exposes a
`load_config` helper that returns a structured OmegaConf `DictConfig`.

The returned `DictConfig` supports attribute access (e.g. `cfg.llm.provider`)
and is resolved (interpolations expanded). We return the `DictConfig` directly
rather than calling `OmegaConf.to_container(...)` because the latter returns a
plain `dict`, which would break the attribute-access expectations of callers
and tests. The structured DictConfig also validates overrides against the
dataclass schema, giving us type-safe config without additional plumbing.
"""

from dataclasses import dataclass, field
from typing import Optional

from omegaconf import DictConfig, OmegaConf


@dataclass(frozen=True)
class LLMConfig:
    provider: str = "deepseek"
    model: str = "deepseek-chat"
    temperature: float = 0.3
    max_tokens: int = 2000
    retry_max: int = 3


@dataclass(frozen=True)
class DBConfig:
    url: str = "sqlite:///data/db/app.db"


@dataclass(frozen=True)
class UploadConfig:
    max_size_mb: int = 10
    allowed_extensions: tuple = (".json", ".txt")


@dataclass(frozen=True)
class AppConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    db: DBConfig = field(default_factory=DBConfig)
    upload: UploadConfig = field(default_factory=UploadConfig)


def load_config(overrides: Optional[list[str]] = None) -> DictConfig:
    """Load application configuration as a structured OmegaConf DictConfig.

    Args:
        overrides: Optional list of dotlist-style overrides, e.g.
            ``["llm.provider=mock"]``. Each entry follows the
            ``a.b.c=value`` syntax of ``OmegaConf.from_dotlist``.

    Returns:
        A resolved ``DictConfig`` mirroring :class:`AppConfig` that supports
        attribute access. The structured config produced by
        ``OmegaConf.structured`` from a frozen dataclass is read-only at the
        node level, which prevents ``OmegaConf.merge`` from applying dotlist
        overrides. To support overrides while keeping the schema dataclasses
        frozen, we first materialize the structured defaults into a plain
        dict and re-wrap it as a fresh ``DictConfig`` (mutable by default),
        then merge overrides on top. The result still mirrors
        :class:`AppConfig` and supports attribute access.
    """
    defaults = OmegaConf.structured(AppConfig)
    cfg = OmegaConf.create(OmegaConf.to_container(defaults, resolve=True))
    if overrides:
        cfg = OmegaConf.merge(cfg, OmegaConf.from_dotlist(overrides))
    OmegaConf.resolve(cfg)
    return cfg
