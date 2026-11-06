# Étoile & Lumière

**两个用于研究法国与英国 Gen Z TikTok 趋势的 macOS 小工具。**

[English](README.md) · [安装](docs/setup.md) · [合规与伦理](docs/legal.md)

> **这是研究工具，不是数据供应商。** Étoile 和 Lumière 通过
> [PyTok](https://github.com/MEOMcGill/pytok) 驱动一个已登录的 TikTok 会话。
> TikTok 的服务条款禁止未经授权的抓取，PyTok 本身使用
> **PolyForm Noncommercial 1.0.0**（禁止商业使用）。使用前请阅读
> [docs/legal.md](docs/legal.md)，并且不要公开传播抓取到的视频、字幕或评论。

---

## 两个 App 分别做什么

| | **Étoile（星）** | **Lumière（光）** |
|---|---|---|
| 作用 | 按 hashtag 采样，筛出符合目标市场的创作者与视频 | 对选定的视频做结构与文化拆解 |
| 输入 | 市场（FR / UK / ALL）、一个或多个 hashtag、样本量 | 一条视频链接，或一对用于对比的链接 |
| 输出 | JSON + CSV + 莫兰迪配色 XLSX（一行一条视频） | MP4、自动字幕、高赞评论、镜头统计、5 格分镜图、八维 XLSX + Markdown |
| 适合 | 从零建立候选池 | 对精选片单做深读 |

推荐流程是 **Étoile → 精选 → Lumière**：先用 Étoile 广撒网，挑出有代表性的视频，再用 Lumière 抽取做内容/结构/受众分析所需的证据。

```
 hashtags ──► Étoile ──► JSON / CSV / XLSX ──► 精选片单 ──► Lumière ──► MP4 + 分镜图
                │                                              │            + 评论
                └─ 市场筛选（FR / UK / ALL）                    └─ 八维报告
```

## 功能

### Étoile — 创作者与视频采样

- 通过真实浏览器会话（Camoufox + PyTok）抓取 hashtag，能处理普通 HTTP 抓取器过不去的挑战。
- 用**两类信号**做市场筛选：文案语言（`langdetect`）+ 创作者特征（国旗、城市、货币、域名、简介语言）。
- 支持 `FR`、`UK`、`ALL`，一次运行多个 hashtag，可配置请求间隔。
- 输出 JSON、CSV 和带可点击链接、语言/区域命中依据的莫兰迪配色 XLSX。

### Lumière — 结构与文化拆解

- 抓取完整元数据、MP4 原片、自动字幕轨（若有）和前若干条高赞评论。
- 用 OpenCV/FFmpeg 做镜头分析：时长、帧率、分辨率、亮度、对比度、饱和度、镜头切换数、平均镜头长度，并生成 5 格分镜图（Hook / 25% / 50% / 75% / CTA）。
- 生成八维报告：
  1. 内容风格（Content Style）
  2. 视频结构（Video Structure）
  3. 受众定位（Audience Targeting）
  4. 语调与语言（Tone and Language）
  5. 视觉呈现（Visual Presentation）
  6. 互动策略（Engagement Strategy）
  7. 文化特征（Cultural Characteristics）
  8. 整体趋势与代表性（Overall Trend Representation）
- 通过 yt-dlp 兜底支持非 TikTok 链接（元数据会少一些：没有 TikTok 评论与字幕轨）。

## 环境要求

- macOS 12 或更新（启动器使用 `osascript` 对话框与 `open`）
- Python 3.10–3.12
- 一个愿意用于研究的 TikTok 账号，**请使用专用账号**
- 约 2 GB 磁盘（Python 环境 + Camoufox 浏览器）

## 快速开始

```bash
git clone https://github.com/SallyGong310-Lily/etoile-lumiere.git
cd etoile-lumiere

# 1) 创建 .venv、安装依赖、下载 Camoufox
./scripts/install.sh

# 2) 首次登录（会弹出浏览器；会话由 PyTok 保存在本地）
.venv/bin/python -m pytok.accounts.cli login --username "$USER" --manual-login

# 3) 启动
./scripts/etoile_launcher.sh
./scripts/lumiere_launcher.sh
```

账号标识只在本机使用，不会上传，也不会写进仓库。

## 命令行用法

Étoile：

```bash
.venv/bin/python src/scrape_french_creators.py \
  --market FR \
  --hashtag "blocus, rentree, octobrerose" \
  --count 80 \
  --delay 4 \
  --output-json out/Etoile_FR_blocus.json \
  --output-csv  out/Etoile_FR_blocus.csv
```

Lumière：

```bash
.venv/bin/python src/lumiere_analyzer.py \
  --urls "https://www.tiktok.com/@user/video/1234567890" \
  --out-dir "$HOME/TikTokResearch/Lumière_视频深析" \
  --comments 20
```

对比两条视频：

```bash
.venv/bin/python src/lumiere_analyzer.py \
  --urls "V1:https://www.tiktok.com/@a/video/111 V2:https://www.tiktok.com/@b/video/222"
```

## 构建 macOS App

```bash
./scripts/build_app.sh
open dist/Étoile.app
open dist/Lumière.app
```

生成的 `.app` 只是薄壳：它们定位到仓库后调用同一套启动器。如果把 `.app` 移出仓库，请把 `ETOILE_HOME` / `LUMIERE_HOME` 指向仓库路径。

## 输出位置

| App | 文件 |
|---|---|
| Étoile | `$ETOILE_OUTPUT_DIR`（默认 `~/TikTokResearch/Étoile`）下的 `Etoile_<市场>_<标签>.json / .csv / .xlsx` |
| Lumière | `$LUMIERE_OUTPUT_DIR`（默认 `~/TikTokResearch/Lumière_视频深析`）下的报表、`Storyboard_<id>.png` 与 `<creator>_<id>/<id>.mp4` |

## 已知局限

- **市场判定是启发式的。** 语言检测和简介关键词会误判侨民创作者、双语账号、没填地区的账号。每条记录都保留命中依据，方便复核。
- **Lumière 的文案模板是为一个时尚案例调的。** `build_dimension_insights` 里的“洞察”默认提到 Victoria's Secret、haul 文化、18–28 岁女性；换题材时请改 `src/lumiere_analyzer.py` 里的提示文案。量化的指标（切换数、平均镜头、亮度、互动率）是通用的。
- **八维文字是初稿，不是结论。** 请把它当成结构化证据来审阅，而不是自动正确的分析。
- **接口和选择器会变。** `requirements.txt` 把 PyTok 固定在 commit `b04636c`；如果上游变了，请固定到测试过的 commit。
- **限流和账号风险是真实存在的。** `--delay` 保持 4 秒以上，小批量运行，并预期偶尔出现验证挑战。

## 合规、伦理与隐私

本项目面向**非商业学术研究**。在基于它发布任何内容之前：

- 阅读并遵守 TikTok 服务条款与所在机构的伦理审查要求。
- 不要重新分发抓取到的视频、字幕、评论或创作者资料。
- 把“公开”数据当个人数据对待：GDPR 等法规仍然适用。
- 不要用于骚扰、大规模画像或绕过访问控制。
- PyTok 是 PolyForm Noncommercial 1.0.0——见 [NOTICE](NOTICE) 与 [docs/legal.md](docs/legal.md)。

## 许可

本仓库代码使用 MIT 许可（见 [LICENSE](LICENSE)）。第三方依赖保留各自许可；其中 **PyTok 为非商业许可**。如需商业使用，请替换 PyTok 客户端层或取得其作者授权。

## 致谢

- [PyTok](https://github.com/MEOMcGill/pytok)（Ben Steel 与贡献者）——本项目的浏览器端 TikTok 客户端基础。
- [Camoufox](https://github.com/daijro/camoufox) 与 [Playwright](https://playwright.dev/python/)——浏览器自动化层。
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)——非 TikTok 链接的兜底解析。
- 报告使用的莫兰迪色彩体系。
