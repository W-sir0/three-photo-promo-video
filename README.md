# 三图宣传短片 / Three-Photo Promo Video

**用三张图制作一段宣传短片。** 准备标识图、场景图和一张主角图，Agent 会从标识提取配色，先展示标识，再用金色三角展开场景，依次呈现名称、主角、宣传语和三个亮点图标。可用于品牌、产品、活动、景区、团队和高校介绍。默认导出 **1332 × 720、40 fps、4.8 秒的无声 MP4**。

Turn a logo, a scene photo, and a featured image into a short promo video for a brand, product, event, place, or university. The Agent Skill includes local Swift and FFmpeg renderers.

## 高校成片示例 / University demos

| 学校 | 精修版成片 |
| --- | --- |
| 吉林农业大学 · Jilin Agricultural University | [下载 MP4](https://github.com/W-sir0/university-showcase-skill/releases/download/demo-videos/jilin-agricultural-university.mp4) |
| 吉林大学 · Jilin University | [下载 MP4](https://github.com/W-sir0/university-showcase-skill/releases/download/demo-videos/jilin-university.mp4) |
| 北京大学 · Peking University | [下载 MP4](https://github.com/W-sir0/university-showcase-skill/releases/download/demo-videos/peking-university.mp4) |
| 清华大学 · Tsinghua University | [下载 MP4](https://github.com/W-sir0/university-showcase-skill/releases/download/demo-videos/tsinghua-university.mp4) |

[查看示例 Release](https://github.com/W-sir0/university-showcase-skill/releases/tag/demo-videos)

## 安装与上手 / Quick start

在你准备用来制作视频的项目目录运行。

```bash
npx skills add W-sir0/university-showcase-skill
```

安装时选择你的 Agent，例如 Antigravity、Claude Code、Codex 或 Cursor。也可以手动复制 [`university-showcase-video` 技能目录](./skills/university-showcase-video)到所用 Agent 的项目技能目录，例如 `.agents/skills/`。

打开工作区，把标识图、场景图和主角图发给 Agent，并附上宣传对象的名称。可以直接复制这段提示词。

> 用 `university-showcase-video` 的版式为【品牌、产品、活动或学校的名称】制作宣传短片。三张附件依次是标识、场景和主角。请先给我确认名称、宣传语、三个亮点和配色，再制作 MP4 和关键帧预览。

### 换一个题材 / Adapt the template

| 准备的图片 | 高校示例 | 产品示例 | 活动示例 |
| --- | --- | --- | --- |
| 标识图 | 校徽 | 品牌 Logo | 活动标志 |
| 场景图 | 校园地标 | 产品使用场景 | 活动场地 |
| 主角图 | 代表人物 | 产品主体 | 主讲人或主展品 |

现成的 `config.json` 模板沿用高校版字段名。换题材时，把宣传对象的名称填入 `university`，主角的名称与副标题填入 `person`，宣传语填入 `motto.lines`，并用 `motto.label` 自定义字幕栏名称。用 `disciplines` 填写亮点和图标。产品或展品可以用抠好背景的透明 PNG，填到 `assets.portrait` 后交给渲染器。高校题材可按技能原流程核对校名、校训和特色学科。

## Agent 和模型要求 / Agent requirements

**纯文本或代码模型也可以用。** Agent 需要能读写工作区文件并执行终端命令。模型负责整理资料和配置，MP4 由本地脚本合成，无需视频生成模型。

| 你有的能力或素材 | 可以怎么用 |
| --- | --- |
| Agent 可以看图、联网搜索和调用生图工具 | 提供三张照片，让 Agent 核对资料、制作三个统一风格的学科图标并检查预览。 |
| 使用纯文本或代码模型 | 标明三张图的用途，提供名称、宣传语和三个亮点图标。让 Agent 写配置、处理素材和渲染，由你查看预览。 |
| 没有联网搜索或生图工具 | 分别提供已核对的文案或自备图标。macOS 可用 Vision 生成肖像遮罩，也可准备现成的遮罩。 |

## 本地依赖 / Requirements

| 平台 | 渲染方式 | 需要安装 |
| --- | --- | --- |
| macOS | Swift 原生渲染，也可选 FFmpeg | Xcode Command Line Tools、Python 3.9+、Pillow、NumPy。选择 FFmpeg 时，另需带 `libx264` 的 FFmpeg。 |
| Linux / Windows | Python + FFmpeg | Python 3.9+、Pillow、NumPy、带 `libx264` 的 FFmpeg。将 `ffmpeg` 加入 `PATH`。 |

```bash
python3 -m pip install pillow numpy
```

## 配置与手动渲染 / Configuration and CLI

从[通用配置模板](./skills/university-showcase-video/examples/config.example.json)开始，也可参考[吉林大学配置](./skills/university-showcase-video/examples/jlu.example.json)。在仓库根目录初始化配置，填写宣传对象资料，并放入图片和亮点图标。配置里的相对路径以 `config.json` 所在的目录为准。

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
