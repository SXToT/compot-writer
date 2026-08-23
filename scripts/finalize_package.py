from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the final outer ZIP after DOCX visual QA has passed.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--author", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()

    folder = args.folder.expanduser().resolve()
    if not folder.is_dir():
        raise SystemExit(f"Package folder not found: {folder}")
    output = (
        args.output.expanduser().resolve()
        if args.output
        else folder.parent / f"{folder.name}-{args.author}.zip"
    )
    if output.exists() and not args.replace:
        raise SystemExit("Output ZIP exists; pass --replace only for the current task's generated ZIP")
    if output.parent != folder.parent:
        output.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(f"{folder.name}/", b"")
        for path in sorted(folder.iterdir()):
            if not path.is_file():
                continue
            compression = zipfile.ZIP_DEFLATED if path.suffix.lower() == ".txt" else zipfile.ZIP_STORED
            archive.write(path, f"{folder.name}/{path.name}", compress_type=compression)

    print(
        json.dumps(
            {
                "folder": str(folder),
                "zip": str(output),
                "entries": len([p for p in folder.iterdir() if p.is_file()]) + 1,
                "zip_sha256": sha256_file(output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
