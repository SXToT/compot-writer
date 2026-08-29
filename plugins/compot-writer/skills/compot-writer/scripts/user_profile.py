from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageOps


INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


def resolve_profile_dir(raw: str | Path | None = None) -> Path:
    if raw is not None:
        return Path(raw).expanduser().resolve()
    codex_home = os.environ.get("CODEX_HOME")
    base = Path(codex_home).expanduser() if codex_home else Path.home() / ".codex"
    return (base / "compot-writer").resolve()


def validate_author(name: str) -> str:
    normalized = name.strip()
    if not normalized:
        raise ValueError("Writer name must be a non-empty string")
    if INVALID_FILENAME.search(normalized) or normalized.rstrip(". ") != normalized:
        raise ValueError("Writer name contains a character that is invalid in filenames")
    if normalized.split(".", 1)[0].upper() in WINDOWS_RESERVED:
        raise ValueError("Writer name is reserved by Windows")
    return normalized


def verify_avatar(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Writer avatar not found: {path}")
    with Image.open(path) as image:
        image.verify()


def load_user_profile(
    profile_dir: str | Path | None = None, *, required: bool = False
) -> dict[str, str] | None:
    directory = resolve_profile_dir(profile_dir)
    config_path = directory / "profile.json"
    if not config_path.is_file():
        if required:
            raise FileNotFoundError(
                "No compot-writer profile is configured. Run user_profile.py set "
                "with a writer name and avatar first."
            )
        return None
    data = json.loads(config_path.read_text(encoding="utf-8"))
    name = validate_author(str(data.get("name", "")))
    raw_avatar = data.get("avatar", "avatar.png")
    avatar = Path(str(raw_avatar)).expanduser()
    if not avatar.is_absolute():
        avatar = directory / avatar
    avatar = avatar.resolve()
    verify_avatar(avatar)
    return {
        "name": name,
        "avatar": str(avatar),
        "profile": str(config_path),
        "profile_dir": str(directory),
    }


def save_user_profile(name: str, avatar_source: Path, profile_dir: Path) -> dict[str, str]:
    author = validate_author(name)
    source = avatar_source.expanduser().resolve()
    verify_avatar(source)
    profile_dir.mkdir(parents=True, exist_ok=True)

    avatar_path = profile_dir / "avatar.png"
    avatar_tmp = profile_dir / ".avatar.png.tmp"
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)
        image.load()
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGBA" if "transparency" in image.info else "RGB")
        image.save(avatar_tmp, format="PNG", optimize=True)
    os.replace(avatar_tmp, avatar_path)

    config_path = profile_dir / "profile.json"
    config_tmp = profile_dir / ".profile.json.tmp"
    payload = {
        "version": 1,
        "name": author,
        "avatar": "avatar.png",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    config_tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(config_tmp, config_path)
    return load_user_profile(profile_dir, required=True)  # type: ignore[return-value]


def reset_user_profile(profile_dir: Path) -> dict[str, object]:
    removed: list[str] = []
    for name in ("profile.json", "avatar.png"):
        path = profile_dir / name
        if path.is_file():
            path.unlink()
            removed.append(str(path))
    return {"configured": False, "profile_dir": str(profile_dir), "removed": removed}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create, inspect, or reset the per-user compot-writer identity profile."
    )
    parser.add_argument(
        "--profile-dir",
        type=Path,
        help="Override the per-user profile directory (primarily for testing or portable setups).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    set_parser = subparsers.add_parser("set", help="Save the default writer name and avatar.")
    set_parser.add_argument("--name", required=True)
    set_parser.add_argument("--avatar", required=True, type=Path)

    subparsers.add_parser("show", help="Show the configured writer profile.")
    subparsers.add_parser("path", help="Show the profile directory.")
    reset_parser = subparsers.add_parser("reset", help="Remove the saved writer profile.")
    reset_parser.add_argument("--yes", action="store_true", help="Confirm profile removal.")
    args = parser.parse_args()

    directory = resolve_profile_dir(args.profile_dir)
    if args.command == "set":
        result: dict[str, object] = {
            "configured": True,
            **save_user_profile(args.name, args.avatar, directory),
        }
    elif args.command == "show":
        profile = load_user_profile(directory)
        result = (
            {"configured": False, "profile_dir": str(directory)}
            if profile is None
            else {"configured": True, **profile}
        )
    elif args.command == "path":
        result = {"profile_dir": str(directory)}
    else:
        if not args.yes:
            raise SystemExit("Refusing to reset the profile without --yes")
        result = reset_user_profile(directory)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

