import json
from pathlib import Path
from typing import Any

import yaml

from core.logger import logger


class ConfigLoader:
    def __init__(self):
        self._data: dict = {}
        self._loaded_files: list[str] = []

    def load(self, path: str | Path) -> dict:
        path = Path(path)
        if not path.exists():
            logger.warning(f"Config file not found: {path}")
            return {}

        raw = path.read_text(encoding="utf-8")
        suffix = path.suffix.lower()

        if suffix in (".yaml", ".yml"):
            data = yaml.safe_load(raw) or {}
        elif suffix == ".json":
            data = json.loads(raw)
        else:
            logger.warning(f"Unsupported config format: {suffix}")
            return {}

        self._data.update(data)
        self._loaded_files.append(str(path))
        logger.info(f"Loaded config: {path}")
        return data

    def load_dir(self, directory: str | Path) -> dict:
        directory = Path(directory)
        if not directory.is_dir():
            logger.warning(f"Config directory not found: {directory}")
            return {}

        for f in sorted(directory.iterdir()):
            if f.suffix.lower() in (".yaml", ".yml", ".json"):
                self.load(f)

        return self._data

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        val = self._data
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
                if val is None:
                    return default
            else:
                return default
        return val

    def set(self, key: str, value: Any):
        keys = key.split(".")
        d = self._data
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value

    @property
    def data(self) -> dict:
        return self._data

    @property
    def loaded_files(self) -> list[str]:
        return self._loaded_files

    def __repr__(self):
        return f"ConfigLoader(files={len(self._loaded_files)}, keys={len(self._data)})"


config = ConfigLoader()
