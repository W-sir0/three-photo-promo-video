# University Showcase Video Skill

**用三张照片制作高校展示动画。** 上传校徽、校园地标和代表人物照片，Agent 会提取校徽配色，让校徽开场、金色三角展开校园画面，再依次呈现中英文校名、人物、校训和三个学科图标。默认导出 **1332 × 720、40 fps、4.8 秒的无声 MP4**，可用于高校介绍、校园活动片头和院系展示。

Turn three photos of a university emblem, campus landmark, and representative figure into a short, emblem-first showcase animation. The skill includes local Swift and FFmpeg renderers.

## 成片示例 / Demo videos

| 学校 | 精修版成片 |
| --- | --- |
| 吉林农业大学 · Jilin Agricultural University | [下载 MP4](https://github.com/W-sir0/university-showcase-skill/releases/download/demo-videos/jilin-agricultural-university.mp4) |
| 吉林大学 · Jilin University | [下载 MP4](https://github.com/W-sir0/university-showcase-skill/releases/download/demo-videos/jilin-university.mp4) |

[查看示例 Release](https://github.com/W-sir0/university-showcase-skill/releases/tag/demo-videos)

## 安装与上手 / Quick start

在你准备用来制作视频的项目目录运行。

```bash
npx skills add W-sir0/university-showcase-skill
```

安装时选择你的 Agent，例如 Antigravity、Claude Code、Codex 或 Cursor。也可以手动复制 [`university-showcase-video` 技能目录](./skills/university-showcase-video)到所用 Agent 的项目技能目录，例如 `.agents/skills/`。

打开工作区，把校徽、校园地标、代表人物照片发给 Agent，并附上学校和人物姓名。可以直接复制这段提示词。

> 用 `university-showcase-video` 为【学校名称】制作高校展示动画。三张附件依次是校徽、校园地标和【人物姓名】。请核对中英文校名、校训、人物头衔和三个特色学科，先给我确认文案和配色。确认后再制作，交付 MP4 和关键帧预览。

Agent 会先提取校徽色系并整理文案。你可以在渲染前核对文案、人物抠图和图标，成片后再用关键帧检查校徽开场、校园画面展开和完整画面。

## Agent 和模型要求 / Agent requirements

**纯文本或代码模型也可以用。** Agent 需要能读写工作区文件并执行终端命令。模型负责整理资料和配置，MP4 由本地脚本合成，无需视频生成模型。

| 你有的能力或素材 | 可以怎么用 |
| --- | --- |
| Agent 可以看图、联网搜索和调用生图工具 | 提供三张照片，让 Agent 核对资料、制作三个统一风格的学科图标并检查预览。 |
| 使用纯文本或代码模型 | 标明三张照片的用途，提供学校资料和三个学科图标文件。让 Agent 写配置、处理素材和渲染，由你查看预览。 |
| 没有联网搜索或生图工具 | 分别提供已核对的学校资料或自备图标。macOS 可用 Vision 生成肖像遮罩，也可准备现成的遮罩。 |

## 本地依赖 / Requirements

| 平台 | 渲染方式 | 需要安装 |
| --- | --- | --- |
| macOS | Swift 原生渲染，也可选 FFmpeg | Xcode Command Line Tools、Python 3.9+、Pillow、NumPy。选择 FFmpeg 时，另需带 `libx264` 的 FFmpeg。 |
| Linux / Windows | Python + FFmpeg | Python 3.9+、Pillow、NumPy、带 `libx264` 的 FFmpeg。将 `ffmpeg` 加入 `PATH`。 |

```bash
python3 -m pip install pillow numpy
```

## 配置与手动渲染 / Configuration and CLI

从[通用配置模板](./skills/university-showcase-video/examples/config.example.json)开始，也可参考[吉林大学配置](./skills/university-showcase-video/examples/jlu.example.json)。在仓库根目录初始化配置，填写学校资料，并放入照片及学科图标。配置里的相对路径以 `config.json` 所在的目录为准。

<details>
<summary>查看 macOS / Linux 命令示例</summary>

```bash
SKILL_DIR="skills/university-showcase-video"
mkdir -p raw build assets
cp "$SKILL_DIR/examples/config.example.json" config.json

# 填写 config.json，再将照片和图标放到对应路径
python3 "$SKILL_DIR/scripts/extract_palette.py" raw/emblem.jpg --update-config config.json

# 可选，仅 macOS。为复杂背景的人像生成遮罩
swiftc -O "$SKILL_DIR/scripts/segment_portrait.swift" -o build/segment_portrait
./build/segment_portrait raw/portrait.jpg assets/portrait_mask.png

# 处理素材后，检查 previews/assets_check.png
python3 "$SKILL_DIR/scripts/prep_assets.py" --config config.json

# macOS 原生渲染
swiftc -O "$SKILL_DIR/scripts/render_video.swift" -o build/render_video
./build/render_video --config config.json

# 也可以使用跨平台 FFmpeg 渲染
python3 "$SKILL_DIR/scripts/render_video_ffmpeg.py" --config config.json
```

</details>

- [技能工作流](./skills/university-showcase-video/SKILL.md)
- [配置字段与版式调整](./skills/university-showcase-video/references/config_schema.md)
- [3D 学科图标提示词](./skills/university-showcase-video/references/icon_prompts.md)
- [素材和成片验收清单](./skills/university-showcase-video/references/design_checklist.md)

## 许可证 / License

源码和配套文档使用 [MIT 许可证](./LICENSE)。
