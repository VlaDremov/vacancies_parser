from __future__ import annotations

from abc import ABC, abstractmethod

from app.types import RawJob, SourceConfig


class BaseParser(ABC):
    @abstractmethod
    def parse(self, content: str, source: SourceConfig) -> list[RawJob]:
        raise NotImplementedError
