from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Copy a DOCX to a short temporary path for Word COM rendering.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()

    source = args.input.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not source.is_file() or source.suffix.lower() != ".docx":
        raise SystemExit(f"Not a readable DOCX: {source}")
    if output.suffix.lower() != ".docx":
        raise SystemExit("Output must use the .docx extension")
    if len(str(output)) > 90:
        raise SystemExit(f"Output path is still too long for Word COM ({len(str(output))} characters)")
    if output.exists() and not args.replace:
        raise SystemExit("Output already exists; pass --replace only for a QA copy from the current task")
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, output)
    print(output)


if __name__ == "__main__":
    main()
