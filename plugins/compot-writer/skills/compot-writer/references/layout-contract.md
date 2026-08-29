# 文献速递版式与内容契约

## 1. Final package names

For issue number `N`, Chinese title `T`, and writer `A`:

- Folder: `N T`
- Word: `[文献速递No.N]T.docx`
- Archive: `N T-A.zip`
- The archive must contain one root folder named `N T`.
- Root-folder files: source PDF with its original filename, Word file, `封面.png`, `图片1.png` to `图片5.png`, `表1.png`, `A.png`, and `A <publish_slot>发表.txt`.
- When no publication slot is supplied, use `A 待定发表.txt`.

## 2. Manifest schema

Use UTF-8 JSON. All text must come from the source PDF.

```json
{
  "number": 789,
  "title": "方法名用于某类任务",
  "author": "张三",
  "source_pdf": "C:/absolute/path/paper.pdf",
  "publish_slot": "0827 08：08",
  "lead": [
    "研究背景、任务难点与实际需求。",
    "作者、方法、核心贡献以及英文论文题名和期刊信息。"
  ],
  "figure1": {
    "caption": "图1 方法总体结构",
    "text": ["总体框架说明。", "第一关键模块及设计动机。"]
  },
  "figure2": {"caption": "图2 模块结构", "text": "模块工作方式与消融结果。"},
  "figure3": {"caption": "图3 模块结构", "text": "模块工作方式。"},
  "figure4": {"caption": "图4 两个模块（左）和（右）的结构", "text": "跨层或检测阶段说明。"},
  "table1": {"caption": "表1 主要数据集上的性能对比", "text": "实验设置与关键定量结果。"},
  "figure5": {"caption": "图5 定性结果对比", "text": "定性结果、消融证据或误差分析。"},
  "conclusion": "总结问题、方法、证据、效率和应用意义。",
  "source_link": "https://doi.org/..."
}
```

The builder requires every content field. `author` may be omitted when a saved writer profile exists; include it for a per-task override and pass the matching avatar to the builder. `figure1.text` has exactly two paragraphs; every other `text` field is one paragraph.

## 3. Paragraph plan

The normalized template contains 36 direct body paragraphs and eight inline images. A compatible legacy template may contain 35 paragraphs because it lacks the opening writer line; the builder inserts that line before filling content. Other structures require explicit adaptation and must not be used silently.

| Paragraph | Purpose |
|---:|---|
| 0 | `[文献速递No.N]T`, 15 pt, dark blue, bold; Chinese font `黑体` |
| 1 | `撰稿人：A` |
| 2 | Cover banner image |
| 3–4 | Two opening paragraphs |
| 5–8 | Figure 1, caption, and two explanatory paragraphs |
| 9–11 | Figure 2, caption, and explanation |
| 12–14 | Figure 3, caption, and explanation |
| 15–17 | Figure 4, caption, and explanation |
| 18–20 | Table 1, caption, and quantitative analysis |
| 21–24 | Figure 5, caption, analysis, and conclusion |
| 27–28 | `原文链接：` and DOI or stable link |
| 33–34 | Preserved final writer card and disclaimer; paragraph 33 must have `pageBreakBefore` |

Aim for about 2,500–3,200 Chinese characters excluding the fixed disclaimer. Prefer concrete evidence over exhaustive architectural detail.

## 4. Image slots

Prepare PNG files at the following approximate aspect ratios. A deviation within 3% is acceptable.

| File | Ratio W:H | Intended content |
|---|---:|---|
| `封面.png` | 4.301 | Journal line, English title, and authors from page 1 |
| `图片1.png` | 1.680 | Overall architecture |
| `图片2.png` | 2.098 | Key module |
| `图片3.png` | 0.967 | Key module or tall workflow |
| `图片4.png` | 1.729 | Fusion/head or paired modules |
| `表1.png` | 1.603 | Main quantitative comparison table |
| `图片5.png` | 2.119 | Qualitative or ablation comparison |

Crop from high-resolution page renders. Include figure labels and legends when they are needed to understand the scientific content. Add neutral white margins to match a slot; do not distort, redraw, or beautify the paper's evidence.

## 5. Language rules

- Use third-person attribution throughout the authored article. Forbidden forms in generated content: `我`, `我们`, `本文`, `本研究`. The fixed disclaimer may retain `本文` because it refers to the digest itself.
- Avoid formulas, variable derivations, and equation-by-equation exposition. Explain mechanisms in plain Chinese.
- Convert `（ASCII-only）` to `(ASCII-only)`. Keep Chinese parentheses for Chinese content.
- Retain exact method names, dataset names, metrics, author surnames, publication venue, and numerical results.
- Use `作者` rather than assigning the source paper's contribution to the digest writer.

## 6. Visual acceptance criteria

- A4 portrait; one section; margins: top/bottom 1 inch and left/right 1.25 inches.
- Six pages is the reference target.
- Eight images remain present and keep their intended slot sizes.
- No clipped title, caption, figure, table, DOI, writer card, or disclaimer.
- The final writer card starts on a new page and the disclaimer stays with it.
- No blank page other than intentional whitespace on the final writer card.
- The opening writer line appears below the title and above the cover banner.
- Inspect all rendered pages at readable resolution before delivery.

