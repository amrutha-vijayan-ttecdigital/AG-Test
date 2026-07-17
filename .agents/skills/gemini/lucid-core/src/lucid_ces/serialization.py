"""Serialization and deserialization helpers preserving unknown fields."""

from __future__ import annotations

import json
from enum import Enum
from typing import Any, Type, TypeVar, Optional, get_origin, get_args, get_type_hints
from .errors import LucidCesParseError

T = TypeVar("T")

def from_dict(cls: Type[T], data: dict[str, Any]) -> T:
    """Instantiate a dataclass from a dict, capturing unknown fields."""
    if not isinstance(data, dict):
        return data

    try:
        hints = get_type_hints(cls)
    except Exception:
        hints = {}

    kwargs = {}
    unknown = {}

    for k, v in data.items():
        if k in hints:
            kwargs[k] = _deserialize_value(hints[k], v)
        else:
            if k != "unknown_fields":
                unknown[k] = v

    try:
        obj = cls(**kwargs)
    except TypeError as e:
        raise LucidCesParseError(f"Failed to instantiate {cls.__name__}: {e}")

    if hasattr(obj, "unknown_fields"):
        obj.unknown_fields = unknown

    return obj

def _deserialize_value(hint: Any, value: Any) -> Any:
    if value is None:
        return None

    origin = get_origin(hint)
    args = get_args(hint)

    # Handle Union / Optional
    if origin is not None and type(None) in args:
        non_none = [a for a in args if a != type(None)]
        if non_none:
            return _deserialize_value(non_none[0], value)

    # Handle List
    if origin is list or hint is list:
        item_type = args[0] if args else Any
        if isinstance(value, list):
            return [_deserialize_value(item_type, item) for item in value]

    # Handle Dict
    if origin is dict or hint is dict:
        val_type = args[1] if len(args) > 1 else Any
        if isinstance(value, dict):
            return {k: _deserialize_value(val_type, v) for k, v in value.items()}

    # Handle Enum
    if isinstance(hint, type) and issubclass(hint, Enum):
        try:
            return hint(value)
        except ValueError:
            return value

    # Handle Dataclass
    if isinstance(hint, type) and hasattr(hint, "__dataclass_fields__"):
        return from_dict(hint, value)

    return value

def to_dict(obj: Any) -> Any:
    """Serialize a dataclass to dict, flattening unknown fields."""
    if hasattr(obj, "__dataclass_fields__"):
        res = {}
        for field_name, f in obj.__dataclass_fields__.items():
            if field_name == "unknown_fields":
                continue
            val = getattr(obj, field_name)
            res[field_name] = to_dict(val)
        if hasattr(obj, "unknown_fields") and isinstance(obj.unknown_fields, dict):
            for k, v in obj.unknown_fields.items():
                res[k] = to_dict(v)
        return res
    elif isinstance(obj, list):
        return [to_dict(v) for v in obj]
    elif isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    elif isinstance(obj, Enum):
        return obj.value
    return obj

def load_json(path: str) -> dict[str, Any]:
    """Helper to read JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_json_atomic(path: str, data: Any) -> None:
    """Atomically write JSON data."""
    import tempfile
    import os
    serialized = json.dumps(data, indent=2, ensure_ascii=False)
    p = os.path.dirname(os.path.abspath(path))
    if p:
        os.makedirs(p, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=p, delete=False, encoding="utf-8") as f:
        f.write(serialized)
        temp_name = f.name
    os.replace(temp_name, path)
