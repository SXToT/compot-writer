# Compot Writer

Compot Writer turns an academic PDF into a numbered Chinese 文献速递 package with source-faithful writing, paper figures, a formatted Word document, companion files, and a validated ZIP archive.

The repository supports both Codex plugin installation and direct Skill installation. The canonical Skill is stored at `plugins/compot-writer/skills/compot-writer/`; the root `SKILL.md` is a compatibility entry that delegates to it without duplicating templates or assets.

## 使用方法

### 第一次使用：保存撰稿人姓名和头像

第一次调用时，请上传论文 PDF 和撰稿人头像，并在提示中给出姓名。例如：

```text
使用 compot-writer 制作这篇论文的文献速递。我的撰稿人姓名是张三，头像使用我上传的 avatar.jpg；请保存为默认撰稿人资料。
```

技能会把姓名和头像保存在当前 Codex 用户环境中，并将其用于开篇的 `撰稿人：张三`、文末撰稿人卡片、根目录的 `张三.png`、发表时间 TXT 文件名以及 ZIP 文件名。

### 后续使用：自动复用

保存成功后，同一 Codex 用户环境中的后续任务无需重复输入姓名和头像，只需提供论文、期号等本次任务所需信息。例如：

```text
使用 compot-writer，把这篇 PDF 制作为 No.801 文献速递。
```

### 临时更换或更新默认资料

- 只在当前稿件中临时换人：同时提供新的姓名和头像，并明确说明“本次使用，不要覆盖默认资料”。
- 永久更新默认资料：同时提供新的姓名和头像，并明确说明“更新默认撰稿人资料”。
- 更换电脑、Codex 用户环境或重新初始化配置后，需要重新设置一次。

### 执行效率与质量控制

- 原文预览、模板选择和论文裁图复用任务内缓存；模板未变化时复用已有格式证据，不重复扫描或渲染参考模板。
- 草稿阶段只检查文件夹和Word结构，不反复打包ZIP。稳定定稿后完成一次Word渲染和逐页检查，再生成并校验最终ZIP。
- QA页面图片按PDF路径、大小、修改时间、DPI和输出图片状态缓存。源文件、参数或图片发生变化时自动重新生成，也可使用`--force`主动刷新。
- Windows脚本采用UTF-8输出，避免中文路径或特殊元数据导致控制台编码错误。常规撰稿不额外审核其他稿件，也不执行无关的检索、下载或导出往返。

效率优化不会跳过论文数值与图表核对、英文题名和英文期刊名的双引号检查、正文总结段、纯文本DOI、最终Word逐页检查及ZIP完整性校验。

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
- This repository is public, so other users can install it directly from GitHub without private-repository credentials.
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
