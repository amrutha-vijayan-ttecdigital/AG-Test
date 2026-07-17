"""Visual export manifest utilities."""

from __future__ import annotations

import hashlib
import struct
from pathlib import Path
from typing import Any


def png_dimensions(data: bytes) -> tuple[int | None, int | None]:
    if len(data) >= 24 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    return None, None


def image_manifest_entry(path: str | Path, *, document_id: str, page_id: str | None, page_index: int | None, title: str | None) -> dict[str, Any]:
    data = Path(path).read_bytes()
    width, height = png_dimensions(data)
    return {
        "documentId": document_id,
        "pageId": page_id,
        "pageIndex": page_index,
        "title": title,
        "path": str(path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "width": width,
        "height": height,
    }

