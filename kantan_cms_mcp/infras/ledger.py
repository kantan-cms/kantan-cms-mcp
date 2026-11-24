"""A tiny JSON-file ledger so provisioning is idempotent and resumable: each
lead (keyed by its external_key, else its name) records what was created, so a
re-run skips finished leads and resumes partially-created ones. Local to the
operator's machine — the backend has no "list my tenants" surface to dedupe
against, and a local ledger is enough for a single-operator batch tool."""
from __future__ import annotations

import json
import os
import threading


class Ledger:
    def __init__(self, path: str):
        self._path = path
        self._lock = threading.Lock()

    def _load(self) -> dict:
        try:
            with open(self._path, encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def get(self, key: str) -> dict:
        return self._load().get(key) or {}

    def put(self, key: str, value: dict) -> None:
        with self._lock:
            data = self._load()
            data[key] = value
            tmp = f"{self._path}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, self._path)  # atomic swap
