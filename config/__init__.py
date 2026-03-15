import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class ApiConfig:
    key: str
    base_url: str
    model: str


@dataclass
class FileConfig:
    input: str
    output: str
    cache: str


@dataclass
class TranslationConfig:
    max_workers: int


@dataclass
class Config:
    api: ApiConfig
    files: FileConfig
    translation: TranslationConfig

    @classmethod
    def load(cls, path: str = None) -> "Config":
        if path is None:
            path = Path(__file__).parent / "config.json"
        else:
            path = Path(path)

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls(
            api=ApiConfig(**data["api"]),
            files=FileConfig(**data["files"]),
            translation=TranslationConfig(**data["translation"])
        )


# 默认配置实例
config = Config.load()
