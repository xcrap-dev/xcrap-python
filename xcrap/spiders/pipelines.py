import json
from typing import Any

from pydantic import BaseModel


def item_to_dict(item: Any) -> Any:
    return item.model_dump() if isinstance(item, BaseModel) else item


class ItemPipeline:
    """Post-processes items yielded by a spider. Raise `DropItem` in `process_item` to discard one."""

    async def open_spider(self, spider: Any) -> None:
        pass

    async def close_spider(self, spider: Any) -> None:
        pass

    async def process_item(self, item: Any, spider: Any) -> Any:
        return item


class MemoryPipeline(ItemPipeline):
    """Keeps every item in `items`."""

    def __init__(self) -> None:
        self.items: list[Any] = []

    async def process_item(self, item: Any, spider: Any) -> Any:
        self.items.append(item)

        return item


class JsonLinesPipeline(ItemPipeline):
    """Appends each item as one JSON line to `path`."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._file = None

    async def open_spider(self, spider: Any) -> None:
        self._file = open(self.path, "w", encoding="utf-8")

    async def close_spider(self, spider: Any) -> None:
        if self._file:
            self._file.close()
            self._file = None

    async def process_item(self, item: Any, spider: Any) -> Any:
        assert self._file is not None, "JsonLinesPipeline used before open_spider"
        self._file.write(json.dumps(item_to_dict(item), ensure_ascii=False, default=str) + "\n")

        return item


__all__ = ["ItemPipeline", "MemoryPipeline", "JsonLinesPipeline"]
