import json
import os
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

        # 优先从环境变量读取敏感信息（API key 和 base_url），避免推送到云端
        api_key = os.getenv("API_KEY") or data["api"]["key"]
        api_base_url = os.getenv("API_BASE_URL") or data["api"]["base_url"]
        api_model = os.getenv("API_MODEL") or data["api"]["model"]

        return cls(
            api=ApiConfig(key=api_key, base_url=api_base_url, model=api_model),
            files=FileConfig(**data["files"]),
            translation=TranslationConfig(**data["translation"]),
        )


# 默认配置实例
config = Config.load()
