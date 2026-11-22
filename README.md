# University Showcase Video Skill (`university-showcase-video`)

> **只需要提供 3 张照片（校徽 + 校园标志建筑 + 代表人物），即可在 AI 辅助下完成「先出校徽、再拉出金色三角主视觉、自动提取校徽色系、统一 3D 学科雕塑图标、人像智能抠图与高清 MP4 导出」的高校卡点图鉴展示动画。**
>
> An Agent Skill following the open `SKILL.md` standard. Provide just **3 photos** (university emblem, campus landmark, representative scholar/founder) and let your AI coding agent research official university metadata, extract a hue-locked palette from the emblem, prepare unified 3D clay discipline icons and clean portrait cutouts, and render a studio-grade silent MP4 animation.

---

## 成片示例 / Demo Videos

两段精修版 MP4 展示了从校徽开场到校园主视觉展开的效果。

- 吉林农业大学 · [下载 MP4](https://github.com/W-sir0/university-showcase-skill/releases/download/demo-videos/jilin-agricultural-university.mp4)
- 吉林大学 · [下载 MP4](https://github.com/W-sir0/university-showcase-skill/releases/download/demo-videos/jilin-university.mp4)

[查看 Release 和全部附件](https://github.com/W-sir0/university-showcase-skill/releases/tag/demo-videos)

---

## 核心特性 / Features

- **极简 3 图输入**：仅需提供校徽、校园实景照、代表人物照片各 1 张。
- **AI 自动补全 + 人工审核**：AI 自动联网检索官网校训、英文校名、人物规范头衔、3 个王牌特色学科，展示结构化信息卡片供你确认后再动手。
- **严格锁定校徽原色系**：`extract_palette.py` 从校徽像素中精准提取主色相 `H`（误差 `±1°`），自动推导出中心柔光、中景底色、四角暗角、底部遮罩与人物名牌底色。
- **标准"先校徽、再展开"卡点节奏**：
  1. `0.00s – 0.48s`：纯校徽主题纹理底上，大尺寸校徽居中放大显现并完成外圈金环扫掠。
  2. `0.48s – 0.96s`：校徽稳步上移至顶点，同时拉出香槟金斜边三角形主视觉，呈现校园地标建筑与柔和压暗遮罩。
  3. `0.62s – 1.16s`：中英校名、人物高清抠图与渐隐名牌条、右侧 3 个统一暖象牙白 3D 雕塑图标、校训错拍顺次入场。
  4. `1.16s – 4.80s`：微推进（Ken Burns）、图标轻悬浮、背景微粒光斑与金边扫光持续呼吸。
- **双引擎渲染支持**：
  - **macOS 原生引擎**（零外部软件依赖）：Swift `CoreGraphics` + `CoreText` + `Vision` + `AVFoundation` 硬件 H.264 编码。
  - **跨平台引擎**（Linux / Windows / macOS）：Python (`Pillow` + `NumPy`) + `FFmpeg`。

---

## 目录结构 / Repository Structure

```text
university-showcase-skill/
├── README.md
├── LICENSE
├── .gitignore
└── skills/
    └── university-showcase-video/
        ├── SKILL.md                      # AI Agent 执行规范与工作流
        ├── scripts/
        │   ├── extract_palette.py        # 从校徽提取色相并生成 4 阶暗角配色 JSON
        │   ├── segment_portrait.swift    # macOS Vision 神经网络人像分割抠图
        │   ├── prep_assets.py            # 校徽/校园图调色与全景补天/人像融合/3D 图标去黑底
        │   ├── render_video.swift        # macOS 原生 Swift 高清 MP4 渲染器
        │   └── render_video_ffmpeg.py    # 跨平台 Pillow + FFmpeg 渲染器
        ├── references/
        │   ├── icon_prompts.md           # 统一暖象牙白 3D 图标提示词模板与本地 SDF 备选方案
        │   ├── config_schema.md          # config.json 完整字段说明与版式微调指南
        │   └── design_checklist.md       # 视觉自检与成片验收标准
        └── examples/
            ├── config.example.json       # 通用高校空白模板
            └── jlu.example.json          # 吉林大学配置示例
```

---

## 安装方式 / Installation

### 方式一：使用 `npx skills`（支持 Antigravity / Claude Code / Codex / Cursor）

```bash
npx skills add W-sir0/university-showcase-skill
```

### 方式二：手动克隆到 Agent Skill 目录

**Google Antigravity（当前项目或全局）**
```bash
# 仅当前项目生效：
git clone https://github.com/W-sir0/university-showcase-skill.git /tmp/uss
cp -R /tmp/uss/skills/university-showcase-video .agents/skills/

# 或全局安装（所有工作区可用）：
mkdir -p ~/.gemini/config/skills
cp -R /tmp/uss/skills/university-showcase-video ~/.gemini/config/skills/
```

**Claude Code / Cursor / Codex**
```bash
# Claude Code 项目级：
cp -R /tmp/uss/skills/university-showcase-video .claude/skills/

# Codex / 通用 .agents 目录：
cp -R /tmp/uss/skills/university-showcase-video .agents/skills/
```

---

## 快速开始 / Quick Usage

安装好 Skill 后，只需在对话框中把 **3 张图片**发给 AI，并说出类似指令：

> "用 `university-showcase-video` 帮我做【某大学】的展示动画，校训和特色学科你帮我查，查完先发我审核再渲染。"

AI 会自动执行以下流程：
1. 识别学校与人物并联网核对校训、英文校名、人物头衔、3 个优势特色学科。
2. 运行 `extract_palette.py` 从你的校徽提取精确色相并生成配色方案。
3. **先向你展示完整的文案 + 配色 + 学科图标方案，经你确认后才继续**。
4. 生成 3 个统一暖象牙白 3D 图标、处理校徽/校园建筑/人物 3/4 侧身抠图，先输出 `assets_check.png` 核验无误。
5. 编译/渲染导出 `1332×720`、`40fps`、`4.8s` 无声高清 MP4（含开场/展开/定格关键帧预览）。

---

## 环境依赖 / Requirements

### macOS（推荐，零额外视频软件安装）
- Xcode Command Line Tools（`swiftc`，系统内置 CoreGraphics / Vision / AVFoundation）
- Python 3.9+，安装 `pillow` 与 `numpy`：
  ```bash
  python3 -m pip install pillow numpy
  ```

### Linux / Windows
- Python 3.9+：`python3 -m pip install pillow numpy`
- `ffmpeg`（需包含 `libx264` 编码器并加入系统 `PATH`）
- （可选）若人物照片背景复杂，建议安装 `rembg` 生成人像遮罩后传给 `prep_assets.py`，或先使用纯色背景照片。

---

## 手动脚本调用参考 / CLI Quick Reference

```bash
SKILL_DIR="skills/university-showcase-video"

# 1. 从校徽提取配色并写入 config.json
python3 "$SKILL_DIR/scripts/extract_palette.py" raw/emblem.jpg --update-config config.json

# 2. (macOS 可选) 生成神经网络人像分割遮罩
swiftc -O "$SKILL_DIR/scripts/segment_portrait.swift" -o build/segment_portrait
./build/segment_portrait raw/portrait.jpg assets/portrait_mask.png

# 3. 批量预处理素材并生成自检拼图 previews/assets_check.png
python3 "$SKILL_DIR/scripts/prep_assets.py" --config config.json

# 4a. macOS 原生渲染 MP4
swiftc -O "$SKILL_DIR/scripts/render_video.swift" -o build/render_video
./build/render_video --config config.json

# 4b. 或跨平台 Python + FFmpeg 渲染
python3 "$SKILL_DIR/scripts/render_video_ffmpeg.py" --config config.json
```

---

## License

[MIT](./LICENSE)
