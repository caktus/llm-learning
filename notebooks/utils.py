from dataclasses import fields, is_dataclass
from io import StringIO
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel


def load_envrc(path="../.envrc"):
    """VS Code's Jupyter extension doesn't support loading .envrc, so if you're
    using VS Code, we load it here."""

    envrc = Path(path)
    stream = StringIO()
    [
        stream.write(f"{line}\n")
        for line in envrc.read_text().splitlines()
        if line.startswith("export")
    ]
    stream.seek(0)

    load_dotenv(stream=stream)


def strip_fields(obj: Any, omit: list[str], with_class_name: bool = True) -> dict | list | Any:
    """
    Recursively converts dataclasses and dictionaries to simplified dictionaries,
    omitting specified keys. Returns a structure perfectly suited for rich.print().
    """

    # 1. Handle Lists/Iterables (recurse on every item)
    if isinstance(obj, (list, tuple)):
        return [strip_fields(item, omit, with_class_name) for item in obj]

    # 2. Handle Pydantic Models
    if isinstance(obj, BaseModel):
        data = {
            k: strip_fields(v, omit, with_class_name)
            for k, v in obj.model_dump().items()
            if k not in omit
        }
        if with_class_name:
            return {obj.__class__.__name__: data}
        return data

    # 3. Handle Dataclasses
    if is_dataclass(obj):
        # Build a dictionary of fields, excluding the 'omit' list
        data = {}
        for f in fields(obj):
            if f.name in omit:
                continue

            # Get value and recurse (in case it's a nested dataclass/dict)
            val = getattr(obj, f.name)
            data[f.name] = strip_fields(val, omit, with_class_name)

        # Option: Wrap in class name for context (e.g. {"User": {...}})
        if with_class_name:
            return {obj.__class__.__name__: data}
        return data

    # 4. Handle Dictionaries
    if isinstance(obj, dict):
        return {k: strip_fields(v, omit, with_class_name) for k, v in obj.items() if k not in omit}

    # 5. Handle Primitives (str, int, float, etc.) - return as is
    return obj
