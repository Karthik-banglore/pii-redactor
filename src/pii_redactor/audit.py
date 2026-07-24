"""JSONL audit log of redaction decisions."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Optional, TextIO


@dataclass
class AuditRecord:
    location: str
    entity_type: str
    original: str
    replacement: str
    source: str
    score: float


class AuditLog:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else None
        self.records: List[AuditRecord] = []
        self._fh: Optional[TextIO] = None
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = open(self.path, "w", encoding="utf-8")

    def add(self, record: AuditRecord) -> None:
        self.records.append(record)
        if self._fh:
            self._fh.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
            self._fh.flush()

    def close(self) -> None:
        if self._fh:
            self._fh.close()
            self._fh = None

    def __enter__(self) -> "AuditLog":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    @staticmethod
    def load(path: Path) -> List[AuditRecord]:
        records: List[AuditRecord] = []
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                records.append(AuditRecord(**data))
        return records
