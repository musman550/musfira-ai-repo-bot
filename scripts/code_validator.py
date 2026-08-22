"""
code_validator.py
Validates every generated file before it's allowed to be published, so a
broken/malformed file can never reach a repo — Python is syntax-checked
with ast.parse, JSON is parsed, and everything else just needs to be
non-empty.
"""

import ast
import json
import logging

logger = logging.getLogger("code_validator")


class ValidationError(Exception):
    pass


def validate_python(content: str, filename: str) -> None:
    try:
        ast.parse(content, filename=filename)
    except SyntaxError as exc:
        raise ValidationError(f"{filename}: syntax error - {exc}") from exc


def validate_json(content: str, filename: str) -> None:
    try:
        json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{filename}: invalid JSON - {exc}") from exc


def validate_non_empty(content: str, filename: str) -> None:
    if not content or not content.strip():
        raise ValidationError(f"{filename}: file is empty")


def validate_files(files: dict[str, str]) -> None:
    """
    Raises ValidationError on the first bad file. Caller should catch this
    and skip the whole repo rather than publish a partially-broken bundle.
    """
    for path, content in files.items():
        validate_non_empty(content, path)
        if path.endswith(".py"):
            validate_python(content, path)
        elif path.endswith(".json"):
            validate_json(content, path)
        # .md / .html / .txt: non-empty check above is sufficient
    logger.info("All %d files passed validation.", len(files))
