from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

from lxml import etree
from PIL import Image

from user_profile import load_user_profile, validate_author


W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML = "http://www.w3.org/XML/1998/namespace"
NS = {"w": W}
QN = lambda tag: f"{{{W}}}{tag}"

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = SKILL_DIR / "assets" / "reference-template.docx"
DEFAULT_AVATAR = SKILL_DIR / "assets" / "高然.png"
DEFAULT_TEMPLATE_SHA256 = "23f34a00cbe49172a7034744f686e6ff0e6f8ddf0323b38c600946e9df4a0dd0"
ASSET_NAMES = ["封面.png", "图片1.png", "图片2.png", "图片3.png", "图片4.png", "表1.png", "图片5.png"]
SLOT_RATIOS = dict(zip(ASSET_NAMES, [4.301, 1.680, 2.098, 0.967, 1.729, 1.603, 2.119]))
FULLWIDTH_ASCII = re.compile(r"（([\x20-\x7e]*[A-Za-z][\x20-\x7e]*)）")
INVALID_FILENAME = re.compile(r'[<>:"/\\|?*]')
FORBIDDEN_PATTERNS = {
    "我们": re.compile(r"我们"),
    "本文": re.compile(r"本文"),
    "本研究": re.compile(r"本研究"),
    "笔者": re.compile(r"笔者"),
    "我方": re.compile(r"我方"),
    "我": re.compile(r"(?:^|[，。；：、\s])我(?:[，。；：、\s]|$)"),
}
FORMULA_MARKERS = (r"\frac", r"\sum", r"\begin{equation", "∑", "∫", "≃", "≈")
PUBLICATION_METADATA_RE = re.compile(
    r'该成果以"(?P<title>[^"\r\n]*[A-Za-z][^"\r\n]*)"为题，'
    r'发表在"(?P<venue>[^"\r\n]*[A-Za-z][^"\r\n]*)"上。'
)
PUBLICATION_METADATA_EXAMPLE = '该成果以"Paper Title"为题，发表在"Journal Name"上。'


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_parentheses(text: str) -> str:
    return FULLWIDTH_ASCII.sub(r"(\1)", text.strip())


def validate_publication_metadata(text: str) -> tuple[str, str]:
    """Require exact English title/venue names in the canonical ASCII-quote form."""
    match = PUBLICATION_METADATA_RE.search(text)
    if match is None:
        raise ValueError(
            "The opening must include the exact English paper title and exact English "
            "journal/venue name in this form: " + PUBLICATION_METADATA_EXAMPLE
        )
    title = match.group("title").strip()
    venue = match.group("venue").strip()
    if title != match.group("title") or venue != match.group("venue"):
        raise ValueError("Do not place whitespace inside the publication metadata quotes")
    return title, venue


def require_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return normalize_parentheses(value)


def resolve_manifest_path(raw: str, manifest_path: Path) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = manifest_path.parent / path
    return path.resolve()


def load_manifest(
    path: Path, *, default_author: str | None = None
) -> tuple[dict[str, object], dict[int, str]]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    number = manifest.get("number")
    if not isinstance(number, int) or number <= 0:
        raise ValueError("number must be a positive integer")
    title = require_text(manifest.get("title"), "title")
    if INVALID_FILENAME.search(title):
        raise ValueError("title contains a character that is invalid in Windows filenames")
    raw_author = manifest.get("author", default_author)
    if raw_author is None:
        raise ValueError(
            "author is missing and no compot-writer user profile is configured"
        )
    author = validate_author(require_text(raw_author, "author"))

    lead = manifest.get("lead")
    if not isinstance(lead, list) or len(lead) != 2:
        raise ValueError("lead must contain exactly two paragraphs")
    f1 = manifest.get("figure1")
    if not isinstance(f1, dict) or not isinstance(f1.get("text"), list) or len(f1["text"]) != 2:
        raise ValueError("figure1.text must contain exactly two paragraphs")

    slots: dict[int, str] = {
        0: f"[文献速递No.{number}]{title}",
        1: f"撰稿人：{author}",
        3: require_text(lead[0], "lead[0]"),
        4: require_text(lead[1], "lead[1]"),
        6: require_text(f1.get("caption"), "figure1.caption"),
        7: require_text(f1["text"][0], "figure1.text[0]"),
        8: require_text(f1["text"][1], "figure1.text[1]"),
    }
    validate_publication_metadata(f"{slots[3]}\n{slots[4]}")
    mapping = [
        ("figure2", 10, 11),
        ("figure3", 13, 14),
        ("figure4", 16, 17),
        ("table1", 19, 20),
        ("figure5", 22, 23),
    ]
    for key, caption_index, text_index in mapping:
        block = manifest.get(key)
        if not isinstance(block, dict):
            raise ValueError(f"{key} must be an object")
        slots[caption_index] = require_text(block.get("caption"), f"{key}.caption")
        slots[text_index] = require_text(block.get("text"), f"{key}.text")
    slots[24] = require_text(manifest.get("conclusion"), "conclusion")
    slots[27] = "原文链接："
    source_link = require_text(manifest.get("source_link"), "source_link")
    if source_link.lower().startswith("10."):
        source_link = f"https://doi.org/{source_link}"
    if not source_link.lower().startswith(("http://", "https://")):
        raise ValueError("source_link must be an HTTP(S) URL or a DOI beginning with 10.")
    slots[28] = source_link

    article = "\n".join(slots[index] for index in sorted(slots) if index not in (0, 1, 27, 28))
    forbidden = [label for label, pattern in FORBIDDEN_PATTERNS.items() if pattern.search(article)]
    if forbidden:
        raise ValueError(f"Authored content contains forbidden self-attribution: {forbidden}")
    formulas = [marker for marker in FORMULA_MARKERS if marker in article]
    if formulas:
        raise ValueError(f"Authored content contains formula markers that should be omitted: {formulas}")

    normalized = dict(manifest)
    normalized.update({"number": number, "title": title, "author": author, "source_link": source_link})
    return normalized, slots


def first_rpr(paragraph: etree._Element) -> etree._Element | None:
    rpr = paragraph.find(".//w:r/w:rPr", NS)
    return copy.deepcopy(rpr) if rpr is not None else None


def ensure_child(parent: etree._Element, tag: str) -> etree._Element:
    child = parent.find(QN(tag))
    if child is None:
        child = etree.SubElement(parent, QN(tag))
    return child


def replace_text(paragraph: etree._Element, text: str) -> None:
    rpr = first_rpr(paragraph)
    ppr = paragraph.find("w:pPr", NS)
    for child in list(paragraph):
        if child is not ppr:
            paragraph.remove(child)
    run = etree.SubElement(paragraph, QN("r"))
    if rpr is not None:
        run.append(rpr)
    node = etree.SubElement(run, QN("t"))
    if text.startswith(" ") or text.endswith(" ") or "\t" in text:
        node.set(f"{{{XML}}}space", "preserve")
    node.text = text


def enforce_title_font(paragraph: etree._Element) -> None:
    for run in paragraph.xpath("./w:r", namespaces=NS):
        rpr = run.find(QN("rPr"))
        if rpr is None:
            rpr = etree.Element(QN("rPr"))
            run.insert(0, rpr)
        fonts = ensure_child(rpr, "rFonts")
        fonts.set(QN("ascii"), "Times New Roman")
        fonts.set(QN("hAnsi"), "Times New Roman")
        fonts.set(QN("cs"), "Times New Roman")
        fonts.set(QN("eastAsia"), "黑体")
        ensure_child(rpr, "b")
        ensure_child(rpr, "bCs")


def enforce_page_break_before(paragraph: etree._Element) -> None:
    ppr = paragraph.find(QN("pPr"))
    if ppr is None:
        ppr = etree.Element(QN("pPr"))
        paragraph.insert(0, ppr)
    ensure_child(ppr, "pageBreakBefore")


def update_final_writer(paragraph: etree._Element, author: str) -> None:
    nodes = paragraph.xpath(".//w:t", namespaces=NS)
    if not nodes:
        raise RuntimeError("Final writer-card paragraph contains no text node")
    nodes[0].text = f" 撰稿人：{author}"
    for node in nodes[1:]:
        node.text = ""


def validate_assets(assets_dir: Path) -> None:
    for name, expected_ratio in SLOT_RATIOS.items():
        path = assets_dir / name
        if not path.is_file():
            raise FileNotFoundError(f"Missing required image asset: {path}")
        with Image.open(path) as image:
            ratio = image.width / image.height
        error = abs(ratio / expected_ratio - 1.0)
        if error > 0.03:
            raise ValueError(
                f"{name} ratio {ratio:.3f} does not match slot {expected_ratio:.3f}; recrop or add white padding"
            )


def patch_docx(
    template: Path,
    output: Path,
    slots: dict[int, str],
    assets_dir: Path,
    avatar: Path,
    author: str,
    deep_check: bool = True,
) -> None:
    replacements = {
        **{f"word/media/image{index}.png": assets_dir / name for index, name in enumerate(ASSET_NAMES, 1)},
        "word/media/image8.png": avatar,
    }
    with zipfile.ZipFile(template, "r") as source:
        infos = source.infolist()
        members = {info.filename: source.read(info.filename) for info in infos}
    root = etree.fromstring(members["word/document.xml"], etree.XMLParser(remove_blank_text=False))
    paragraphs = root.xpath("/w:document/w:body/w:p", namespaces=NS)
    if len(paragraphs) == 35:
        writer = etree.Element(QN("p"))
        run = etree.SubElement(writer, QN("r"))
        text = etree.SubElement(run, QN("t"))
        text.text = f"撰稿人：{author}"
        paragraphs[0].addnext(writer)
        paragraphs = root.xpath("/w:document/w:body/w:p", namespaces=NS)
    if len(paragraphs) != 36:
        raise RuntimeError(
            f"Reference template is not compatible: expected 35 or 36 body paragraphs, found {len(paragraphs)}"
        )
    for index, text in slots.items():
        replace_text(paragraphs[index], text)
    enforce_title_font(paragraphs[0])
    enforce_page_break_before(paragraphs[33])
    update_final_writer(paragraphs[33], author)
    members["word/document.xml"] = etree.tostring(
        root, xml_declaration=True, encoding="UTF-8", standalone="yes"
    )

    core = etree.fromstring(members["docProps/core.xml"], etree.XMLParser(remove_blank_text=False))
    dc = "http://purl.org/dc/elements/1.1/"
    title_node = core.find(f"{{{dc}}}title")
    if title_node is None:
        title_node = etree.SubElement(core, f"{{{dc}}}title")
    title_node.text = output.stem
    members["docProps/core.xml"] = etree.tostring(
        core, xml_declaration=True, encoding="UTF-8", standalone="yes"
    )
    for name, path in replacements.items():
        members[name] = path.read_bytes()

    output.parent.mkdir(parents=True, exist_ok=True)
    staged_output = output.with_name(f".{output.name}.tmp")
    if staged_output.exists():
        staged_output.unlink()
    with zipfile.ZipFile(staged_output, "w") as target:
        for info in infos:
            target.writestr(info, members[info.filename])

    try:
        with zipfile.ZipFile(staged_output) as after:
            if set(members) != set(after.namelist()):
                raise RuntimeError("DOCX package part set changed")
            if deep_check:
                editable = {"word/document.xml", "docProps/core.xml", *replacements.keys()}
                unexpected = [
                    name
                    for name, data in members.items()
                    if name not in editable and sha256_bytes(data) != sha256_bytes(after.read(name))
                ]
                if unexpected:
                    raise RuntimeError(f"Unexpected DOCX package changes: {unexpected}")
        os.replace(staged_output, output)
    finally:
        if staged_output.exists():
            staged_output.unlink()


def write_outer_zip(output_dir: Path, zip_path: Path, folder_name: str) -> None:
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(f"{folder_name}/", b"")
        for path in sorted(output_dir.iterdir()):
            if not path.is_file():
                continue
            # PDF, PNG and DOCX are already compressed; storing them avoids costly recompression.
            compression = zipfile.ZIP_DEFLATED if path.suffix.lower() == ".txt" else zipfile.ZIP_STORED
            archive.write(path, f"{folder_name}/{path.name}", compress_type=compression)


def safe_remove_generated(path: Path, expected_parent: Path, is_dir: bool) -> None:
    resolved = path.resolve()
    if resolved.parent != expected_parent.resolve() or not resolved.name:
        raise RuntimeError(f"Refusing to remove unsafe generated path: {resolved}")
    if not resolved.exists():
        return
    if is_dir:
        shutil.rmtree(resolved)
    else:
        resolved.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a numbered 文献速递 Word folder and ZIP package.")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--assets-dir", required=True, type=Path)
    parser.add_argument("--output-parent", required=True, type=Path)
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument(
        "--avatar",
        type=Path,
        help="Per-task avatar override. Otherwise use the saved writer profile.",
    )
    parser.add_argument(
        "--profile-dir",
        type=Path,
        help="Override the per-user profile directory.",
    )
    parser.add_argument("--replace-generated", action="store_true")
    parser.add_argument("--draft", action="store_true", help="Build the folder/DOCX only; skip outer ZIP and deep package hashing")
    args = parser.parse_args()

    manifest_path = args.manifest.expanduser().resolve()
    profile = load_user_profile(args.profile_dir)
    default_author = profile["name"] if profile is not None else None
    manifest, slots = load_manifest(manifest_path, default_author=default_author)
    assets_dir = args.assets_dir.expanduser().resolve()
    output_parent = args.output_parent.expanduser().resolve()
    template = args.template.expanduser().resolve()
    author = str(manifest["author"])
    if args.avatar is not None:
        avatar = args.avatar.expanduser().resolve()
    elif profile is not None and author == profile["name"]:
        avatar = Path(profile["avatar"]).resolve()
    elif author == "高然":
        avatar = DEFAULT_AVATAR.resolve()
    else:
        raise ValueError(
            f"No avatar is configured for writer {author!r}; initialize the user "
            "profile or pass --avatar for this task"
        )
    source_pdf = resolve_manifest_path(str(manifest.get("source_pdf", "")), manifest_path)
    if not source_pdf.is_file() or source_pdf.suffix.lower() != ".pdf":
        raise FileNotFoundError(f"Source PDF not found: {source_pdf}")
    if not template.is_file() or not avatar.is_file():
        raise FileNotFoundError("Bundled template or avatar is missing")
    if template == DEFAULT_TEMPLATE.resolve() and sha256_file(template) != DEFAULT_TEMPLATE_SHA256:
        raise RuntimeError("Bundled reference-template.docx hash mismatch; redistill the template before use")
    validate_assets(assets_dir)

    number = int(manifest["number"])
    title = str(manifest["title"])
    folder_name = f"{number} {title}"
    output_dir = output_parent / folder_name
    zip_path = output_parent / f"{folder_name}-{author}.zip"
    relevant_zip_exists = zip_path.exists() and not args.draft
    if output_dir.exists() or relevant_zip_exists:
        if not args.replace_generated:
            raise FileExistsError("Final output already exists; use --replace-generated only for files from the current task")
        safe_remove_generated(output_dir, output_parent, True)
        if not args.draft:
            safe_remove_generated(zip_path, output_parent, False)
    output_parent.mkdir(parents=True, exist_ok=True)

    publish_slot = str(manifest.get("publish_slot") or "待定").strip().replace(":", "：")
    if INVALID_FILENAME.search(publish_slot):
        raise ValueError("publish_slot contains a character that is invalid in Windows filenames")

    # Stage outside the final output tree so cloud/sync/indexing hooks cannot
    # see or lock a half-built package. The final folder is copied only once.
    stage_parent = Path(tempfile.mkdtemp(prefix="compot-writer-"))
    temp_dir = stage_parent / folder_name
    temp_dir.mkdir()
    try:
        for name in ASSET_NAMES:
            shutil.copy2(assets_dir / name, temp_dir / name)
        shutil.copy2(avatar, temp_dir / f"{author}.png")
        shutil.copy2(source_pdf, temp_dir / source_pdf.name)
        (temp_dir / f"{author} {publish_slot}发表.txt").write_text("", encoding="utf-8")
        docx_name = f"[文献速递No.{number}]{title}.docx"
        docx_path = temp_dir / docx_name
        patch_docx(template, docx_path, slots, assets_dir, avatar, author, deep_check=not args.draft)
        shutil.copytree(temp_dir, output_dir)
    except Exception:
        raise
    finally:
        if stage_parent.exists():
            shutil.rmtree(stage_parent)

    if not args.draft:
        write_outer_zip(output_dir, zip_path, folder_name)

    result = {
        "folder": str(output_dir),
        "docx": str(output_dir / f"[文献速递No.{number}]{title}.docx"),
        "zip": None if args.draft else str(zip_path),
        "mode": "draft" if args.draft else "final",
    }
    if not args.draft:
        result["docx_sha256"] = sha256_file(output_dir / f"[文献速递No.{number}]{title}.docx")
        result["zip_sha256"] = sha256_file(zip_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
