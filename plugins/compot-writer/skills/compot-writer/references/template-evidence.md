# Bundled fallback template evidence

## Reference identity

- Asset: `assets/reference-template.docx`
- SHA-256: `23f34a00cbe49172a7034744f686e6ff0e6f8ddf0323b38c600946e9df4a0dd0`
- Reference render: six pages, one section.
- Package: 22 parts; eight PNG media parts.

Verify the hash before using the fallback. If it differs, redistill the template and update this evidence file rather than bypassing the check.

## Page system

- A4 portrait: approximately 8.268 × 11.693 inches.
- Margins: top/bottom 1.00 inch; left/right 1.25 inches.
- Header distance 0.591 inch; footer distance 0.689 inch.
- No extra sections, columns, odd/even variants, or first-page variant.

## Typography

- Title: 15 pt, bold, dark blue `#0A2F41`; Chinese font `黑体`, Latin font Times New Roman.
- Opening writer line: Normal style, directly below the title.
- Body: 10.5 pt reference scale, about 0.292-inch first-line indent, original paragraph rhythm retained.
- Captions: 9 pt, left aligned, directly beneath their images.
- Disclaimer: 9 pt on the final writer-card page.

## Components and stable slots

- Direct body paragraphs: 36.
- Inline images: eight; relationship-backed media `word/media/image1.png` through `image8.png`.
- Image display sizes in inches: `5.768×1.341`, `5.768×3.433`, `5.355×2.552`, `5.188×5.365`, `5.768×3.337`, `5.260×3.281`, `5.768×2.722`, `1.407×1.733`.
- Paragraph slots follow `layout-contract.md`. The final writer card is paragraph 33 and the fixed disclaimer is paragraph 34; the builder adds `pageBreakBefore` to paragraph 33 so shorter articles cannot split the card across pages.

## Package-preservation gate

Only these package parts may change during a normal build:

- `word/document.xml`
- `docProps/core.xml`
- `word/media/image1.png` through `word/media/image7.png`
- `word/media/image8.png` only when the avatar is intentionally replaced

Preserve styles, themes, settings, relationships, numbering, headers, footers, drawing extents, content types, and every other package part byte-for-byte. Keep the retained template unchanged.

## Fidelity gate

- Compare the output package inventory with the reference.
- Re-run section and image audits.
- Render the final DOCX and inspect all pages at 100% zoom.
- Reject clipping, overlap, broken captions, stretched figures, unexpected pagination, or movement of the final writer card.
