---
name: compot-writer
description: Create, revise, audit, and package numbered Chinese 文献速递 from one academic PDF, including source-faithful writing, paper figures, precisely formatted Word output, companion files, and a ZIP archive. Use when a user supplies a research-paper PDF and asks to continue the established literature-digest series, assign or correct an issue number, reproduce the 高然 format, or review an existing 文献速递 package. Optimized for a fast cached draft-to-final workflow while retaining final Word render QA.
---

# Compot Writer

Create a complete numbered 文献速递 package. Treat the PDF as the content authority and a compatible DOCX/template as the layout authority.

## Companion skills

Load `pdf:pdf` and `documents:documents`. Read [references/layout-contract.md](references/layout-contract.md). Read [references/template-evidence.md](references/template-evidence.md) only when diagnosing template fidelity or using the bundled fallback.

Call the workspace dependency loader once and use its bundled Python path for every `python` command below; do not use system `python`/`py`. On the current Windows desktop runtime this is typically `C:\Users\<user>\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`, but always use the path returned for the active session.

## Resolve inputs once

- Check the per-user writer profile once before resolving task inputs:

  ```powershell
  python scripts/user_profile.py show
  ```

  If no profile exists, use the writer name and avatar supplied in the current request and save them with `python scripts/user_profile.py set --name "姓名" --avatar "头像图片路径"`. If either item is missing, ask the user for both before building. The saved profile is reused automatically in later tasks on the same Codex installation.
- Treat an explicitly supplied writer name and avatar as a per-task override unless the user asks to update the saved default. To update the default, run the same `set` command with the new values. Never overwrite the saved profile silently.
- Use the bundled 高然 avatar only when the user explicitly requests the legacy 高然 identity or an existing package already uses it; do not silently assign 高然 to a new user's package.
- Require one source PDF.
- Use an issue number explicitly supplied by the user or a supplied order sheet before inferring from filenames. Never replace an authoritative roster with “largest number + 1”.
- If no authoritative number exists, scan sibling numbered outputs and infer only when unambiguous; otherwise ask.
- Use the supplied publication slot; otherwise use `待定`.
- Preserve an existing publication filename such as `姓名 MMDD HH：MM发表.txt`; do not invent or normalize away supplied dates.

## Fast path

Use one task-local job directory and reuse it throughout. Do not repeat unchanged stages.

1. **Template:** Prefer a user-named/template DOCX. Otherwise run once:

   ```powershell
   python scripts/find_template.py --workspace "." --cache "job/template-cache.json"
   ```

   The search prioritizes numbered top-level folders, prunes generated directories, caches inspected files, and caps a broad scan at 250 candidates by default. Reuse the reported template for the task. Do not rescan after every edit. If no compatible local template exists, use `assets/reference-template.docx`; use `--scan-limit 0` only for a deliberate exhaustive search.

2. **PDF preview and text:** Run once at preview resolution:

   ```powershell
   python scripts/inspect_pdf.py "paper.pdf" --out-dir "job/source"
   ```

   The command caches by source size/mtime and defaults to 110 DPI. Read extracted text and inspect every preview page. Do not rerun when `cache_hit` is true.

3. **Evidence:** Identify title, authors, venue, DOI/link, method, experiments, exact numerical findings, useful figures, and a results table. Crop only selected regions at high resolution; never re-render the whole PDF at high DPI. Batch all regions in one process:

   ```powershell
   python scripts/render_pdf_regions.py "paper.pdf" "job/crops.json" --out-dir "job/assets" --dpi 240
   ```

   `crops.json` contains `{"crops":[{"page":1,"output":"封面.png","box":[l,t,r,b],"relative":true,"ratio":4.301}, ...]}`. The crop command caches each unchanged region. Use `--optimize` only for final assets if file size matters. `crop_page.py` remains a fallback for one-off corrections.

4. **Draft:** Write `manifest.json` to the contract, then build without a ZIP:

   ```powershell
   python scripts/build_package.py manifest.json --assets-dir "job/assets" --output-parent "job/output" --template "template.docx" --draft
   python scripts/validate_package.py manifest.json --output-parent "job/output" --fast
   ```

   Iterate on manifest/assets using `--replace-generated --draft`. Fast validation is the inner loop; do not create, CRC-test, hash, or copy the outer ZIP yet.

   Draft mode stages the DOCX outside the watched output tree before copying it into place. This avoids incomplete packages and reduces file-lock races from sync/indexing software.

5. **One final Word render:** Only after content, assets, naming, and fast validation are stable, copy the DOCX to a short fixed QA path and render with `scripts/render_word_cached.ps1`. It skips Word when the DOCX hash is unchanged. Convert the QA PDF with:

   ```powershell
   python scripts/render_pdf_pages.py "qa/output.pdf" --out-dir "job/word-pages"
   ```

   The renderer safely replaces only prior `page-*.png` files in that QA directory. Visually inspect every page. Re-render only after a real DOCX change.

6. **Finalize once:** After visual QA passes, create the outer ZIP from the accepted folder:

   ```powershell
   python scripts/finalize_package.py "job/output/N 标题"
   python scripts/validate_package.py manifest.json --output-parent "job/output"
   ```

   The finalizer uses the saved writer profile by default. For a per-task writer override, pass `--author "姓名"`. If replacing a ZIP generated earlier in the same task, add `--replace`. Copy final deliverables to their destination only after final validation. Compare delivery hashes once; do not repeatedly hash during drafting.

## Non-negotiable writing rules

- Attribute the source work to `作者`、`该研究`、`该论文`、`原文` or named authors. Never use `我`、`我们`、`本文`、`本研究` in authored digest content, especially page 1. The fixed disclaimer may use `本文` because it refers to the digest.
- Omit formulas by default. Explain mechanisms in concise prose; keep a formula only when the core idea cannot be understood without it.
- Use ASCII parentheses `()` when the entire parenthetical content is English/ASCII, such as `(AEU)` or `(MFEL-YOLO)`. Use `（）` when Chinese is present.
- Do not fabricate metadata, numerical results, dataset details, or conclusions. Keep every technical claim traceable to the PDF.
- Write compact, natural Chinese rather than sentence-by-sentence translation.

## Output contract

- Folder: `N 标题`
- Word: `[文献速递No.N]标题.docx`
- ZIP: `N 标题-撰稿人.zip`, containing exactly one root folder named `N 标题`
- Keep the original PDF filename, cover, scientific figures/table, avatar, and publication TXT in the root folder.
- Title: 15 pt, dark blue, bold; Chinese explicitly 黑体 and Latin Times New Roman.
- Put `撰稿人：姓名` below the title and before a cover image that visibly includes journal/venue, full English title, and authors.
- Keep the final writer card and disclaimer together on a new page.
- Do not overwrite unrelated existing outputs. When correcting a deliverable created in the current task, write and validate the replacement first, then remove the wrong generated copy.
- Deliver no DOCX before its latest Word render has been inspected page by page.

## When to leave the fast path

- Scanned/poor-text PDF: use OCR after preview inspection.
- Long-path Word failure: use `prepare_render_copy.py` before retrying; do not repeatedly call Word with the same failing path.
- Missing results table: use an authentic quantitative figure or a clearly labeled screenshot of exact numerical results from the paper in the required `表1.png` evidence slot. Do not invent a table or values.
- Incompatible asset ratio: recrop or add white margins; never stretch scientific evidence.
- Existing nonstandard package: preserve its content density and image count when the user requested review rather than template recreation; enforce naming, attribution, cover, title formatting, pagination, and ZIP integrity.

## Existing ZIP review shortcut

When the input is already a 文献速递 ZIP, do not parse the paper or rebuild from the standard manifest unless content verification is requested. Extract once, audit the folder/Word/ZIP, make minimal local corrections, run fast structural checks, render the changed Word once, then create and validate one replacement ZIP. Preserve the original ZIP and any supplied avatar/publication TXT. Build the corrected replacement under a distinct task-local staging folder, validate it, then copy it over the generated delivery; do not delete the accepted output before its replacement exists.

