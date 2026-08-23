---
name: compot-writer
description: Create, revise, audit, and package numbered Chinese 文献速递 from one academic PDF, including source-faithful writing, paper figures, precisely formatted Word output, companion files, and a ZIP archive. Use when a user supplies a research-paper PDF and asks to continue the established literature-digest series, assign or correct an issue number, reproduce the 高然 format, or review an existing 文献速递 package. Optimized for a fast cached draft-to-final workflow while retaining final Word render QA.
---

# Compot Writer Compatibility Entry

This root file keeps the GitHub repository installable as a standalone Codex skill without duplicating the large templates and assets.

Before doing any task work, read `plugins/compot-writer/skills/compot-writer/SKILL.md` completely and follow it as the canonical instructions.

Resolve every relative path used by the canonical instructions against `plugins/compot-writer/skills/compot-writer/`. In particular, load supporting material from its `references/`, execute helpers from its `scripts/`, and use bundled files from its `assets/`. Do not resolve those paths against this repository root.

If the canonical skill file or one of its required resources is missing, stop and report that the GitHub installation is incomplete.
