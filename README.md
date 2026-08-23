# Compot Writer

Compot Writer turns an academic PDF into a numbered Chinese 文献速递 package with source-faithful writing, paper figures, a formatted Word document, companion files, and a validated ZIP archive.

The repository supports both Codex plugin installation and direct Skill installation. The canonical Skill is stored at `plugins/compot-writer/skills/compot-writer/`; the root `SKILL.md` is a compatibility entry that delegates to it without duplicating templates or assets.

## Install as a Codex plugin (recommended)

Add the GitHub repository as a marketplace, then install the plugin:

```powershell
codex plugin marketplace add SXToT/compot-writer --ref main
codex plugin add compot-writer@sxtot-compot-writer
```

Restart the Codex/ChatGPT desktop app and use a new task after installation. The marketplace also appears as **SXToT Compot Writer** in the Plugins Directory.

See the [official plugin packaging and marketplace documentation](https://developers.openai.com/plugins/build/plugins) for the supported repository layout and marketplace commands.

## Install directly with `$skill-installer`

Paste this into Codex:

```text
$skill-installer Install https://github.com/SXToT/compot-writer/tree/main/plugins/compot-writer/skills/compot-writer
```

Legacy root-path installation also remains supported with `--repo SXToT/compot-writer --path . --name compot-writer`. The root compatibility Skill loads the canonical nested Skill and resolves its scripts, references, and assets from there.

## Compatibility and distribution

- The full final-render workflow currently targets Codex on Windows with Microsoft Word available.
- While this repository is private, another user needs GitHub repository access and configured Git credentials before installation.
- The bundled template and image are retained for faithful document generation. This repository does not assert a broad open-source license over those assets.
- Universal Plugins Directory publication is a separate OpenAI review process; this repository provides GitHub marketplace and direct Skill installation.

## Repository layout

```text
.agents/plugins/marketplace.json
SKILL.md
agents/openai.yaml
plugins/compot-writer/
  .codex-plugin/plugin.json
  skills/compot-writer/
    SKILL.md
    agents/
    assets/
    references/
    scripts/
```
