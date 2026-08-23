from __future__ import annotations

import argparse
import json
import os
import re
import zipfile
from pathlib import Path

from docx import Document


TITLE_RE = re.compile(r"^\[文献速递No\.(\d+)\]")
EXCLUDED_DIRS = {".git", ".codex", "node_modules", "tmp", "temp", "__pycache__"}
CACHE_VERSION = 1
NUMBERED_FOLDER_RE = re.compile(r"^\d+\s")


def inspect_candidate(path: Path) -> dict[str, object]:
    row: dict[str, object] = {"path": str(path), "compatible": False, "score": 0, "reasons": []}
    reasons: list[str] = row["reasons"]  # type: ignore[assignment]
    try:
        document = Document(path)
        paragraphs = document.paragraphs
        match = TITLE_RE.match(paragraphs[0].text if paragraphs else "")
        number = int(match.group(1)) if match else -1
        row["number"] = number
        if not match:
            reasons.append("title does not match [文献速递No.N]")
        if len(paragraphs) not in (35, 36):
            reasons.append(f"paragraph count is {len(paragraphs)}, expected 35 or 36")
        if len(document.inline_shapes) != 8:
            reasons.append(f"inline image count is {len(document.inline_shapes)}, expected 8")
        if len(document.sections) != 1:
            reasons.append(f"section count is {len(document.sections)}, expected 1")
        with zipfile.ZipFile(path) as package:
            media_count = sum(name.startswith("word/media/") for name in package.namelist())
        if media_count != 8:
            reasons.append(f"media count is {media_count}, expected 8")
        compatible = not reasons
        row["compatible"] = compatible
        if compatible:
            writer_at_start = len(paragraphs) > 1 and paragraphs[1].text.strip().startswith("撰稿人：")
            row["legacy_missing_opening_writer"] = not writer_at_start
            row["score"] = number * 10 + (5 if writer_at_start else 0)
    except Exception as exc:
        reasons.append(f"cannot inspect: {exc}")
    return row


def iter_docx(workspace: Path):
    """Walk without ever descending into known-heavy generated directories."""
    for root, dirs, files in os.walk(workspace, topdown=True):
        dirs[:] = [
            name
            for name in dirs
            if name.lower() not in EXCLUDED_DIRS and not name.startswith("~$")
        ]
        root_path = Path(root)
        for name in files:
            if name.startswith("~$") or not name.lower().endswith(".docx"):
                continue
            yield root_path / name


def iter_priority_docx(workspace: Path):
    """Check likely numbered packages before the rest of the workspace."""
    seen: set[Path] = set()
    try:
        children = sorted(workspace.iterdir(), key=lambda path: path.name, reverse=True)
    except OSError:
        children = []
    for child in children:
        if not child.is_dir() or not NUMBERED_FOLDER_RE.match(child.name):
            continue
        for path in child.glob("*.docx"):
            resolved = path.resolve()
            if not path.name.startswith("~$") and resolved not in seen:
                seen.add(resolved)
                yield path
    for path in iter_docx(workspace):
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            yield path


def fingerprint(path: Path) -> dict[str, int]:
    stat = path.stat()
    return {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def load_cache(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("version") == CACHE_VERSION and isinstance(payload.get("items"), dict):
            return payload
    except (OSError, ValueError, TypeError):
        pass
    return {"version": CACHE_VERSION, "items": {}}


def main() -> None:
    parser = argparse.ArgumentParser(description="Find compatible 文献速递 DOCX templates in a workspace.")
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--scan-limit", type=int, default=250, help="Maximum DOCX candidates to inspect; 0 means unlimited")
    parser.add_argument("--cache", type=Path, help="Optional JSON cache; defaults to a task-local cache beside the workspace")
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args()

    workspace = args.workspace.expanduser().resolve()
    if not workspace.is_dir():
        raise SystemExit(f"Workspace is not a directory: {workspace}")
    cache_path = args.cache.expanduser().resolve() if args.cache else None
    cache = (
        {"version": CACHE_VERSION, "items": {}}
        if args.no_cache or cache_path is None
        else load_cache(cache_path)
    )
    old_items: dict[str, object] = cache["items"]  # type: ignore[assignment]
    new_items: dict[str, object] = {}
    rows = []
    cache_hits = 0
    inspected = 0
    truncated = False
    for candidate_index, path in enumerate(iter_priority_docx(workspace), 1):
        if args.scan_limit > 0 and candidate_index > args.scan_limit:
            truncated = True
            break
        key = str(path.resolve())
        fp = fingerprint(path)
        cached = old_items.get(key)
        if isinstance(cached, dict) and cached.get("fingerprint") == fp and isinstance(cached.get("result"), dict):
            row = cached["result"]
            cache_hits += 1
        else:
            row = inspect_candidate(path)
            inspected += 1
        rows.append(row)
        new_items[key] = {"fingerprint": fp, "result": row}

    if not args.no_cache and cache_path is not None:
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(
                json.dumps({"version": CACHE_VERSION, "items": new_items}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            cache_path = None
    compatible = sorted(
        (row for row in rows if row["compatible"]),
        key=lambda row: (int(row["score"]), str(row["path"])),
        reverse=True,
    )
    report = {
        "workspace": str(workspace),
        "recommended": compatible[0]["path"] if compatible else None,
        "compatible_count": len(compatible),
        "candidates": compatible[: max(1, args.limit)],
        "rejected_count": len(rows) - len(compatible),
        "cache_hits": cache_hits,
        "inspected": inspected,
        "scan_limit": args.scan_limit,
        "scan_truncated": truncated,
        "cache": str(cache_path) if cache_path else None,
        "fallback": str(Path(__file__).resolve().parent.parent / "assets" / "reference-template.docx"),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
