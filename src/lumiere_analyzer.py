#!/usr/bin/env python3
"""
Lumière — 精选 TikTok 视频结构拆解与 Task 1 八大维度深析引擎

核心功能：
1. 接收 1 条或多条精选 TikTok 视频链接（支持直接传入 FR 法国代表视频 & UK 英国代表视频，或任意视频 URL 列表）。
2. 自动通过 PyTok 持久化登录态获取：
   - 视频完整元数据（文案、BGM 音乐、时长、分辨率、画幅比例、发布时间、创作者详情、互动数据）
   - 视频高清 MP4 原片下载（存入桌面 Lumière_视频深析/<video_id>/）
   - 视频自带英/法字幕轨（若有 `claInfo` 字幕）
   - 视频前 25 条高赞评论（用于实证分析 Audience Targeting 与 Engagement Strategy）
3. 使用 OpenCV + FFmpeg 对下载的 MP4 原片进行计算机视觉与镜头分析：
   - 统计视频时长、帧率 (FPS)、分辨率、画面亮度/对比度/色彩饱和度特征
   - 自动检测镜头切换次数 (Scene Cuts)，计算平均镜头时长 (ASL - Average Shot Length) 与剪辑节奏评级
   - 抽取黄金前 3 秒 Hook、25% 展开帧、50% 核心展示帧、75% 高潮帧、95% 结尾 CTA 帧，合成高清《电影分镜故事板 (Storyboard_Contact_Sheet.png)》
4. 围绕 Task 1 的 8 大分析维度生成：
   - 莫兰迪配色的《Lumière_Task1_视频深度拆解报表.xlsx》（含视频指标对比表 + 8 大维度拆解矩阵 + 观众评论实证表）
   - 《Lumière_Task1_AI深析档案.md》（包含完整的结构化证据链，可直接发给 Antigravity AI 结合本地 MP4 原片生成最终 Task 1 英文/双语报告）
"""

import argparse
import asyncio
import json
import logging
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import httpx
import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.drawing.image import Image as OpenpyxlImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from pytok.accounts import AccountsPool, NoAccountError
from pytok.helpers import extract_user_id_from_url, extract_video_id_from_url
from pytok.tiktok import PyTok

from scrape_french_creators import (
    detect_target_language,
    evaluate_french_creator,
    evaluate_uk_creator,
    extract_user_dict_from_info,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("LumiereAnalyzer")

# ---------------------------------------------------------------------------
# 莫兰迪 (Morandi) 视觉色卡
# ---------------------------------------------------------------------------
BORDER_SIDE = Side(border_style="thin", color="E2DDD7")
CELL_BORDER = Border(left=BORDER_SIDE, right=BORDER_SIDE, top=BORDER_SIDE, bottom=BORDER_SIDE)
HEADER_BORDER = Border(
    left=Side(border_style="thin", color="D0C9C0"),
    right=Side(border_style="thin", color="D0C9C0"),
    top=Side(border_style="medium", color="7A6A5E"),
    bottom=Side(border_style="medium", color="7A6A5E"),
)

FILL_HEADER_BURGUNDY = PatternFill(start_color="7D3C4A", end_color="7D3C4A", fill_type="solid")
FILL_HEADER_SLATE = PatternFill(start_color="5E6E78", end_color="5E6E78", fill_type="solid")
FILL_HEADER_SAGE = PatternFill(start_color="6E7E71", end_color="6E7E71", fill_type="solid")
FILL_HEADER_TAUPE = PatternFill(start_color="8C7D70", end_color="8C7D70", fill_type="solid")
FILL_HEADER_ROSE = PatternFill(start_color="9E7676", end_color="9E7676", fill_type="solid")

FILL_BODY_CREAM = PatternFill(start_color="FDFBF7", end_color="FDFBF7", fill_type="solid")
FILL_BODY_ROSE = PatternFill(start_color="F9F2F2", end_color="F9F2F2", fill_type="solid")
FILL_BODY_BLUE = PatternFill(start_color="F3F6F8", end_color="F3F6F8", fill_type="solid")
FILL_BODY_GREEN = PatternFill(start_color="F4F7F4", end_color="F4F7F4", fill_type="solid")
FILL_BODY_GOLD = PatternFill(start_color="FDF6EC", end_color="FDF6EC", fill_type="solid")

FONT_HEADER = Font(name="PingFang SC", size=11, bold=True, color="FFFFFF")
FONT_HEADER_GOLD = Font(name="PingFang SC", size=11, bold=True, color="FFEBC8")
FONT_BODY = Font(name="PingFang SC", size=10, color="2C2A29")
FONT_BOLD = Font(name="PingFang SC", size=10, bold=True, color="2C2A29")
FONT_LINK = Font(name="PingFang SC", size=10, bold=True, underline="single", color="7D3C4A")


# ---------------------------------------------------------------------------
# 1. OpenCV 计算机视觉：镜头节奏检测与分镜故事板生成
# ---------------------------------------------------------------------------

def analyze_video_visuals_and_storyboard(
    mp4_path: Path,
    out_dir: Path,
    video_id: str,
) -> Dict[str, Any]:
    """
    对下载的 MP4 视频进行视觉特征提取、镜头切换检测，并生成 5 格关键帧分镜图。
    """
    result: Dict[str, Any] = {
        "duration_sec": 0.0,
        "fps": 0.0,
        "width": 0,
        "height": 0,
        "aspect_ratio": "9:16",
        "scene_cuts_count": 0,
        "avg_shot_length_sec": 0.0,
        "pacing_style": "未知",
        "avg_brightness": 0.0,
        "avg_saturation": 0.0,
        "visual_tone_desc": "",
        "keyframe_paths": [],
        "storyboard_path": None,
    }

    if not mp4_path or not mp4_path.exists():
        return result

    cap = cv2.VideoCapture(str(mp4_path))
    if not cap.isOpened():
        return result

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration = total_frames / fps if fps > 0 else 0.0

    result["fps"] = round(fps, 2)
    result["width"] = width
    result["height"] = height
    result["duration_sec"] = round(duration, 2)
    if width > 0 and height > 0:
        result["aspect_ratio"] = "9:16 (竖屏沉浸)" if height > width else "16:9 (横屏)"

    # 抽样遍历计算镜头切换 (直方图差异) 与色彩/亮度均值
    prev_hist = None
    scene_cuts = 0
    brightness_vals = []
    saturation_vals = []

    sample_step = max(1, int(fps / 5))  # 每秒采样约 5 帧检测转场
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % sample_step == 0:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            brightness_vals.append(float(np.mean(hsv[:, :, 2])))
            saturation_vals.append(float(np.mean(hsv[:, :, 1])))

            hist = cv2.calcHist([hsv], [0, 1], None, [32, 32], [0, 180, 0, 256])
            cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
            if prev_hist is not None:
                corr = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
                if corr < 0.55:  # 显著画面切换阈值
                    scene_cuts += 1
            prev_hist = hist
        frame_idx += 1

    total_shots = scene_cuts + 1
    asl = duration / total_shots if total_shots > 0 and duration > 0 else duration
    result["scene_cuts_count"] = scene_cuts
    result["avg_shot_length_sec"] = round(asl, 2)

    if asl < 1.8:
        result["pacing_style"] = f"快节奏高频卡点 (共 {scene_cuts} 次转场，平均每镜 {asl:.1f}s)"
    elif asl < 4.0:
        result["pacing_style"] = f"中速流畅叙事 (共 {scene_cuts} 次转场，平均每镜 {asl:.1f}s)"
    else:
        result["pacing_style"] = f"长镜头/沉浸式氛围感 (共 {scene_cuts} 次转场，平均每镜 {asl:.1f}s)"

    avg_b = float(np.mean(brightness_vals)) if brightness_vals else 128.0
    avg_s = float(np.mean(saturation_vals)) if saturation_vals else 100.0
    result["avg_brightness"] = round(avg_b, 1)
    result["avg_saturation"] = round(avg_s, 1)

    b_label = "明亮通透 (High-Key)" if avg_b >= 145 else ("自然柔和 (Natural)" if avg_b >= 95 else "暗调电影感 (Low-Key Moody)")
    s_label = "高饱和鲜艳视觉" if avg_s >= 115 else ("克制低饱和/法式胶片感" if avg_s <= 75 else "自然真实色彩")
    result["visual_tone_desc"] = f"{b_label} + {s_label} (亮度均值 {avg_b:.0f}/255, 饱和度 {avg_s:.0f}/255)"

    # 抽取 5 个关键结构时间点：
    # 1. Hook (前1.5秒或5%) 2. Rising (25%) 3. Core (50%) 4. Climax (75%) 5. CTA (92%)
    stages = [
        ("01_Hook_黄金前3秒钩子", min(int(fps * 1.2), max(0, int(total_frames * 0.08)))),
        ("02_Setup_铺垫展开(25%)", int(total_frames * 0.25)),
        ("03_Core_核心内容展示(50%)", int(total_frames * 0.50)),
        ("04_Climax_情绪或视觉高潮(75%)", int(total_frames * 0.75)),
        ("05_CTA_结尾留存与号召(92%)", int(total_frames * 0.92)),
    ]

    keyframes_dir = out_dir / f"keyframes_{video_id}"
    keyframes_dir.mkdir(parents=True, exist_ok=True)
    thumbs = []
    target_thumb_h = 360

    for label, f_no in stages:
        cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, min(f_no, max(0, total_frames - 1))))
        ok, frame = cap.read()
        if not ok or frame is None:
            continue
        kf_path = keyframes_dir / f"{label}.jpg"
        cv2.imwrite(str(kf_path), frame)
        result["keyframe_paths"].append(str(kf_path))

        h, w, _ = frame.shape
        scale = target_thumb_h / h if h > 0 else 1.0
        thumb_w = max(120, int(w * scale))
        resized = cv2.resize(frame, (thumb_w, target_thumb_h), interpolation=cv2.INTER_AREA)

        # 为分镜添加顶部深色信息条 (时间戳)
        sec_mark = f_no / fps if fps > 0 else 0.0
        banner = np.full((36, thumb_w, 3), (38, 34, 35), dtype=np.uint8)
        stage_short = label.split("_")[0] + " " + label.split("_")[1]
        cv2.putText(
            banner,
            f"{stage_short} ({sec_mark:.1f}s)",
            (8, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            (235, 225, 215),
            1,
            cv2.LINE_AA,
        )
        card = np.vstack([banner, resized])
        thumbs.append(card)

    cap.release()

    if thumbs:
        # 拼接成一张横向的故事板长图
        sep = np.full((thumbs[0].shape[0], 10, 3), (245, 242, 238), dtype=np.uint8)
        spaced = []
        for i, t in enumerate(thumbs):
            spaced.append(t)
            if i < len(thumbs) - 1:
                spaced.append(sep)
        storyboard_img = np.hstack(spaced)
        sb_path = out_dir / f"Storyboard_{video_id}.png"
        cv2.imwrite(str(sb_path), storyboard_img)
        result["storyboard_path"] = str(sb_path)

    return result


# ---------------------------------------------------------------------------
# 2. 提取 TikTok 原生字幕轨 (WebVTT / ASR 文本)
# ---------------------------------------------------------------------------

async def fetch_tiktok_subtitles(v_dict: Dict[str, Any]) -> str:
    """如果视频自带 TikTok 自动识别字幕 (claInfo / subtitleInfos)，直接下载并提取纯文本台词。"""
    video_obj = v_dict.get("video") or {}
    cla_info = video_obj.get("claInfo") or {}
    sub_infos = cla_info.get("captionInfos") or video_obj.get("subtitleInfos") or []

    if not sub_infos:
        return ""

    # 优先选原声字幕 (original) 或法语/英语字幕
    chosen_url = None
    for sub in sub_infos:
        if not isinstance(sub, dict):
            continue
        url = sub.get("url") or sub.get("Url")
        if url:
            chosen_url = url
            break

    if not chosen_url:
        return ""

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(chosen_url)
            if resp.status_code != 200:
                return ""
            raw_vtt = resp.text
            # 清理 WEBVTT 时间轴，保留台词
            lines = []
            for line in raw_vtt.splitlines():
                line_s = line.strip()
                if (
                    not line_s
                    or line_s.startswith("WEBVTT")
                    or "-->" in line_s
                    or line_s.isdigit()
                ):
                    continue
                if line_s not in lines:
                    lines.append(line_s)
            return " ".join(lines)
    except Exception as ex:
        logger.debug(f"字幕拉取失败: {ex}")
        return ""


# ---------------------------------------------------------------------------
# 3. 围绕 Task 1 八大维度自动生成启发式特征诊断
# ---------------------------------------------------------------------------

def build_8_perspectives_analysis(item: Dict[str, Any]) -> Dict[str, str]:
    """
    结合视频元数据、视觉分镜指标、文案、标签与评论区，自动生成 Task 1 要求的 8 大维度结构化洞察。
    """
    market = item.get("market_tag", "FR/UK")
    desc = item.get("desc", "")
    hashtags = item.get("hashtags", "")
    duration = item.get("duration_sec", 0.0)
    pacing = item.get("pacing_style", "")
    visual_tone = item.get("visual_tone_desc", "")
    music_title = item.get("music_title", "原声")
    music_author = item.get("music_author", "")
    subtitles = item.get("transcript", "")
    eng_rate = item.get("engagement_rate", 0.0) * 100
    play_cnt = item.get("play_count", 0)
    digg_cnt = item.get("digg_count", 0)
    comm_cnt = item.get("comment_count", 0)
    coll_cnt = item.get("collect_count", 0)
    share_cnt = item.get("share_count", 0)
    sig = item.get("signature", "")
    comments_preview = item.get("top_comments", [])

    # 1. Content Style (内容风格)
    style_tags = []
    lower_all = f"{desc} {hashtags}".lower()
    if any(k in lower_all for k in ["haul", "tryon", "commande", "shopping", "achats"]):
        style_tags.append("沉浸式开箱/试穿测评 (Haul & Try-On)")
    if any(k in lower_all for k in ["grwm", "prepare", "look", "ootd", "tenue", "outfit"]):
        style_tags.append("日常穿搭灵感/GRWM (Get Ready With Me)")
    if any(k in lower_all for k in ["promo", "offre", "code", "bonplan", "sale", "deal"]):
        style_tags.append("门店探店/高性价比种草 (Retail Discovery & Promo)")
    if any(k in lower_all for k in ["vlog", "journee", "dayinmylife", "paris", "london"]):
        style_tags.append("都市生活美学 Vlog (Lifestyle Aesthetic Vlog)")
    if not style_tags:
        style_tags.append("原生真实感种草/视觉美学展示 (Native Aesthetic Showcase)")

    content_style = (
        f"【定性】{' + '.join(style_tags)}。\n"
        f"【配乐协同】使用音频《{music_title}》({music_author})，总时长 {duration}s。"
    )

    # 2. Video Structure (视频结构)
    video_structure = (
        f"【三段式黄金结构】总时长 {duration}s，{pacing}。\n"
        f"• 黄金前3秒 (Hook)：通过视觉高光单品/门店场景或悬念文案直接切入主题（参见分镜图 01_Hook）；\n"
        f"• 中段展开 (Body, 25%~75%)：多角度展示细节/上身效果与质感切换（平均每镜头 {item.get('avg_shot_length_sec', 0)}s）；\n"
        f"• 结尾留存 (CTA, 90%+)：利用优惠信息、互动提问或高颜值定格画面激发收藏 ({coll_cnt:,}) 与转发 ({share_cnt:,})。"
    )

    # 3. Audience Targeting (受众定位)
    audience_targeting = (
        f"【核心受众】{market} 市场 18-28 岁 Z 世代与千禧一代年轻女性（关注时尚穿搭、内衣美学、都市生活方式与悦己消费）。\n"
        f"【标签矩阵】通过 #{hashtags.replace(', ', ' #')} 精准触达本土算法推荐池（如法国 #pourtoi 或英国 #fyp / #ukfashion）。\n"
        f"【博主画像契合度】博主简介“{sig or '未设置'}”，粉丝基数 {item.get('follower_count', 0):,}。"
    )

    # 4. Tone and Language (语调与语言)
    lang_info = item.get("lang_summary", "")
    tone_and_lang = (
        f"【语言特征】文案识别结果 `{lang_info}`；文案原文：“{desc}”。\n"
        + (f"【语音/字幕台词】“{subtitles[:180]}...”\n" if subtitles else "【语音/字幕】以视觉画面配乐卡点为主（或纯口播无内嵌字幕轨）。\n")
        + (
            "【法式语调】注重亲切感与审美共鸣（常见 'incroyable', 'pépite', 'votre offre préférée' 等法式生活化感叹）。"
            if "FR" in market
            else "【英式语调】直接、高能量且带有闺蜜分享式的亲近感（常见 'obsessed', 'run don't walk', 'bargain/haul' 等表达）。"
        )
    )

    # 5. Visual Presentation (视觉呈现)
    visual_presentation = (
        f"【画幅与影调】{item.get('aspect_ratio', '9:16')} ({item.get('width')}x{item.get('height')})；{visual_tone}。\n"
        f"【镜头语言】第一人称主观视角/对镜自拍与近景特写交替，弱化硬广感，强化原生 TikTok 真实质感（已抽帧生成 5 阶段分镜图）。"
    )

    # 6. Engagement Strategy (互动策略)
    save_to_like_ratio = (coll_cnt / digg_cnt * 100) if digg_cnt > 0 else 0.0
    share_to_like_ratio = (share_cnt / digg_cnt * 100) if digg_cnt > 0 else 0.0
    comm_sample = " | ".join(comments_preview[:3]) if comments_preview else "暂无评论样本"
    engagement_strategy = (
        f"【核心指标】播放量 {play_cnt:,} | 点赞 {digg_cnt:,} | 评论 {comm_cnt:,} | 收藏 {coll_cnt:,} | 分享 {share_cnt:,}（综合互动率 {eng_rate:.2f}%）。\n"
        f"【深度转化信号】收藏/点赞比达 {save_to_like_ratio:.1f}%（代表强种草/保存复看欲），分享/点赞比达 {share_to_like_ratio:.1f}%（代表闺蜜社交裂变）。\n"
        f"【评论区高频反馈】{comm_sample}"
    )

    # 7. Cultural Characteristics (文化特征)
    if "FR" in market:
        cultural_char = (
            "【法国本土文化映射】体现了法国年轻一代对“Effortless Chic（毫不费力的精致感）”与悦己主义（Self-care）的推崇："
            "不盲目追求浮夸戏剧冲突，而强调天然氛围感、实体门店体验以及法式生活美学；同时对高性价比促消费（Bon plan）同样敏锐。"
        )
    elif "UK" in market:
        cultural_char = (
            "【英国本土文化映射】体现了英国 TikTok 典型的“Haul Culture（开箱试穿文化）”与真实身材包容度（Body Positivity / 明确标注 UK 尺码）："
            "叙事节奏明快直接，兼具实用主义（价格/尺码参考）与社群共鸣感。"
        )
    else:
        cultural_char = (
            f"【区域文化特征】融合全球流行品牌符号（Victoria's Secret）与本土语言社媒语境（命中依据：{item.get('creator_match_reasons', '')}）。"
        )

    # 8. Overall Trend Representation (整体趋势代表性 —— Why Representative)
    overall_trend = (
        f"【为什么该视频具有 {market} 市场代表性？】\n"
        f"1. 从“品牌仰视”转向“真实生活场景融入”：通过原生竖屏镜头将国际品牌转化为本土日常穿搭/探店体验；\n"
        f"2. 算法与社交双驱动：高收藏比 ({save_to_like_ratio:.1f}%) 与高转发比 ({share_to_like_ratio:.1f}%) 完美契合当下 TikTok 重视“完播+收藏+私信分享”的推荐权重；\n"
        f"3. 极具代表性的 {market} 创作者范式：兼顾审美调性与商业种草转化力。"
    )

    return {
        "1_Content_Style (内容风格)": content_style,
        "2_Video_Structure (视频结构)": video_structure,
        "3_Audience_Targeting (受众定位)": audience_targeting,
        "4_Tone_and_Language (语调与语言)": tone_and_lang,
        "5_Visual_Presentation (视觉呈现)": visual_presentation,
        "6_Engagement_Strategy (互动策略)": engagement_strategy,
        "7_Cultural_Characteristics (文化特征)": cultural_char,
        "8_Overall_Trend_Representation (整体趋势代表性)": overall_trend,
    }


# ---------------------------------------------------------------------------
# 4. 导出莫兰迪配色《Lumière Task 1 深度拆解报表 (.xlsx)》与 Markdown 简报
# ---------------------------------------------------------------------------

def export_lumiere_excel_and_md(
    analyzed_items: List[Dict[str, Any]],
    out_dir: Path,
) -> Tuple[Path, Path]:
    """生成莫兰迪配色的多工作表 Excel 报告与 Markdown 报告。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    ts_str = datetime.now().strftime("%Y%m%d_%H%M")
    xlsx_path = out_dir / f"Lumière_Task1_视频深度分析报表_{ts_str}.xlsx"
    md_path = out_dir / f"Lumière_Task1_AI深析档案_{ts_str}.md"

    wb = Workbook()

    # =========================================================================
    # Sheet 1: 8大维度深度对比矩阵 (Task 1 Question 1 核心)
    # =========================================================================
    ws1 = wb.active
    ws1.title = "1_Task1八大维度深度拆解"
    ws1.views.sheetView[0].showGridLines = True
    ws1.freeze_panes = "B2"

    headers_s1 = ["Task 1 核心分析维度 (Perspectives)"]
    for idx, item in enumerate(analyzed_items, start=1):
        m_tag = item.get("market_tag", f"视频{idx}")
        u_id = item.get("uniqueId", "")
        headers_s1.append(f"【{m_tag}】@{u_id} (视频 {item.get('video_id', '')})")

    ws1.row_dimensions[1].height = 36
    ws1.column_dimensions["A"].width = 34
    for col_i, h_text in enumerate(headers_s1, start=1):
        cell = ws1.cell(row=1, column=col_i, value=h_text)
        cell.fill = FILL_HEADER_BURGUNDY if col_i == 1 else (FILL_HEADER_SLATE if col_i == 2 else FILL_HEADER_SAGE)
        cell.font = FONT_HEADER_GOLD if col_i == 1 else FONT_HEADER
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = HEADER_BORDER
        if col_i > 1:
            ws1.column_dimensions[get_column_letter(col_i)].width = 58

    # 先写入基础概览行（直达链接、本地原片路径、文案、核心数据）
    meta_rows = [
        ("🔗 视频直达链接", lambda x: x.get("video_url", "")),
        ("🎬 本地已下载 MP4 原片路径", lambda x: x.get("local_mp4_path", "未下载")),
        ("🖼️ 5阶段分镜故事板路径", lambda x: x.get("storyboard_path", "未生成")),
        ("👤 创作者账号 (uniqueId / 昵称 / 粉丝数)", lambda x: f"@{x.get('uniqueId')} ({x.get('nickname')}) | 粉丝: {x.get('follower_count', 0):,}"),
        ("📝 视频原始文案 (Caption)", lambda x: x.get("desc", "")),
        ("🗣️ 提取字幕/语音台词 (Transcript)", lambda x: x.get("transcript", "") or "（无内嵌字幕轨，可直接由 AI 观看本地 MP4 提取）"),
        ("🎵 背景音乐 (BGM) & 视频时长", lambda x: f"《{x.get('music_title')}》- {x.get('music_author')} | 时长: {x.get('duration_sec')}s"),
        ("📊 核心互动表现", lambda x: f"播放: {x.get('play_count', 0):,} | 点赞: {x.get('digg_count', 0):,} | 评论: {x.get('comment_count', 0):,} | 收藏: {x.get('collect_count', 0):,} | 分享: {x.get('share_count', 0):,} | 互动率: {x.get('engagement_rate', 0)*100:.2f}%"),
    ]

    current_row = 2
    for row_title, getter in meta_rows:
        ws1.row_dimensions[current_row].height = 42
        c_title = ws1.cell(row=current_row, column=1, value=row_title)
        c_title.fill = FILL_BODY_ROSE
        c_title.font = FONT_BOLD
        c_title.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        c_title.border = CELL_BORDER

        for idx, item in enumerate(analyzed_items, start=2):
            val = getter(item)
            c_val = ws1.cell(row=current_row, column=idx, value=val)
            c_val.fill = FILL_BODY_GOLD if current_row == 2 else FILL_BODY_CREAM
            c_val.border = CELL_BORDER
            c_val.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
            if current_row == 2 and str(val).startswith("http"):
                c_val.hyperlink = str(val)
                c_val.font = FONT_LINK
            else:
                c_val.font = FONT_BODY
        current_row += 1

    # 写入 8 大分析维度行
    perspective_keys = [
        "1_Content_Style (内容风格)",
        "2_Video_Structure (视频结构)",
        "3_Audience_Targeting (受众定位)",
        "4_Tone_and_Language (语调与语言)",
        "5_Visual_Presentation (视觉呈现)",
        "6_Engagement_Strategy (互动策略)",
        "7_Cultural_Characteristics (文化特征)",
        "8_Overall_Trend_Representation (整体趋势代表性)",
    ]

    for p_key in perspective_keys:
        ws1.row_dimensions[current_row].height = 95
        c_p = ws1.cell(row=current_row, column=1, value=p_key)
        c_p.fill = FILL_HEADER_TAUPE
        c_p.font = FONT_HEADER
        c_p.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        c_p.border = CELL_BORDER

        for idx, item in enumerate(analyzed_items, start=2):
            p_map = item.get("perspectives", {})
            c_val = ws1.cell(row=current_row, column=idx, value=p_map.get(p_key, ""))
            c_val.fill = FILL_BODY_BLUE if idx % 2 == 0 else FILL_BODY_GREEN
            c_val.font = FONT_BODY
            c_val.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
            c_val.border = CELL_BORDER
        current_row += 1

    # =========================================================================
    # Sheet 2: 观众高赞评论实证样本 (用于支撑 Audience & Engagement 分析)
    # =========================================================================
    ws2 = wb.create_sheet(title="2_观众高赞评论实证")
    ws2.views.sheetView[0].showGridLines = True
    ws2.freeze_panes = "A2"

    s2_cols = [
        ("所属视频市场", 16, FILL_HEADER_TAUPE),
        ("视频ID", 22, FILL_HEADER_TAUPE),
        ("评论作者 (@uniqueId)", 24, FILL_HEADER_ROSE),
        ("评论内容 (Comment Text)", 55, FILL_HEADER_SLATE),
        ("评论点赞数", 14, FILL_HEADER_SLATE),
        ("评论语种", 12, FILL_HEADER_SAGE),
    ]
    ws2.row_dimensions[1].height = 32
    for c_i, (c_title, c_w, c_fill) in enumerate(s2_cols, start=1):
        cell = ws2.cell(row=1, column=c_i, value=c_title)
        cell.fill = c_fill
        cell.font = FONT_HEADER
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = HEADER_BORDER
        ws2.column_dimensions[get_column_letter(c_i)].width = c_w

    r_idx = 2
    for item in analyzed_items:
        for comm in item.get("raw_comments", []):
            ws2.row_dimensions[r_idx].height = 28
            vals = [
                item.get("market_tag", ""),
                item.get("video_id", ""),
                comm.get("user", ""),
                comm.get("text", ""),
                comm.get("digg_count", 0),
                comm.get("lang", ""),
            ]
            for c_i, v in enumerate(vals, start=1):
                cell = ws2.cell(row=r_idx, column=c_i, value=v)
                cell.fill = FILL_BODY_CREAM
                cell.font = FONT_BODY
                cell.border = CELL_BORDER
                cell.alignment = Alignment(
                    horizontal="left" if c_i in (3, 4) else "center",
                    vertical="center",
                    wrap_text=(c_i == 4),
                )
            r_idx += 1

    wb.save(xlsx_path)

    # =========================================================================
    # 生成结构化 Markdown 深度档案（方便用户直接阅读或发给 AI 生成最终英文报告）
    # =========================================================================
    md_lines = [
        "# ✨ Lumière — TikTok 代表性视频深度拆解档案 (Task 1 专用)",
        "",
        f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"> 配套莫兰迪 Excel 报表：`{xlsx_path.name}`",
        "",
    ]

    for idx, item in enumerate(analyzed_items, start=1):
        m_tag = item.get("market_tag", f"Video {idx}")
        md_lines.extend([
            f"## {idx}. 【{m_tag}】@{item.get('uniqueId')} — 视频 `{item.get('video_id')}`",
            "",
            f"- **视频直达链接**：{item.get('video_url')}",
            f"- **本地原片 MP4**：`{item.get('local_mp4_path')}`",
            f"- **5阶段分镜故事板**：`{item.get('storyboard_path')}`",
            f"- **创作者信息**：`@{item.get('uniqueId')}` ({item.get('nickname')}) | 粉丝数：`{item.get('follower_count', 0):,}` | 获赞：`{item.get('creator_heart_count', 0):,}` | 认证：`{item.get('verified')}`",
            f"- **创作者简介 (Bio)**：{item.get('signature') or '无'}",
            f"- **发布时间**：{item.get('create_time_str')}",
            f"- **背景音乐 (BGM)**：《{item.get('music_title')}》 — {item.get('music_author')}",
            f"- **视频技术与视觉指标**：时长 `{item.get('duration_sec')}s` | 分辨率 `{item.get('width')}x{item.get('height')}` | {item.get('pacing_style')} | {item.get('visual_tone_desc')}",
            f"- **互动表现**：播放 `{item.get('play_count', 0):,}` | 点赞 `{item.get('digg_count', 0):,}` | 评论 `{item.get('comment_count', 0):,}` | 收藏 `{item.get('collect_count', 0):,}` | 分享 `{item.get('share_count', 0):,}` | **综合互动率 `{item.get('engagement_rate', 0)*100:.2f}%`**",
            f"- **原始文案 (Caption)**：\n  > {item.get('desc')}",
            f"- **语音/字幕台词 (Transcript)**：\n  > {item.get('transcript') or '（无内嵌字幕轨，可由 AI 直接观看本地 MP4 分析画面与原声）'}",
            "",
            "### 📐 Task 1 八大维度拆解 (8 Perspectives)",
            "",
        ])
        for p_k, p_v in item.get("perspectives", {}).items():
            md_lines.append(f"#### {p_k}")
            md_lines.append(p_v)
            md_lines.append("")

        if item.get("top_comments"):
            md_lines.append("### 💬 高赞观众评论样本 (Top Audience Comments)")
            for c_str in item["top_comments"][:8]:
                md_lines.append(f"- {c_str}")
            md_lines.append("")

        md_lines.append("---")
        md_lines.append("")

    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    return xlsx_path, md_path


# ---------------------------------------------------------------------------
# 5. 核心异步单条/多条视频采集与深度分析流水线
# ---------------------------------------------------------------------------

def parse_url_inputs(raw_input: str) -> List[Tuple[str, str]]:
    """
    解析用户输入的视频链接。
    支持：
    - 任意平台的单个或多个视频 URL（TikTok, YouTube, Instagram, 小红书, Bilibili 等，以空格、逗号或换行分隔）
    - 可选前缀标记，如 `V1:https://...`、`FR:https://...` 或 `UK:https://...`
    """
    tokens = re.split(r"[\s,，;；\n]+", raw_input.strip())
    results: List[Tuple[str, str]] = []
    for tok in tokens:
        tok = tok.strip()
        if not tok:
            continue
        m_prefix = re.match(r"^([A-Za-z0-9_-]{1,10})[:=](https?://\S+)$", tok)
        if m_prefix:
            results.append((m_prefix.group(1).upper(), m_prefix.group(2)))
        elif tok.startswith("http"):
            results.append(("AUTO", tok))
    return results


def analyze_generic_url_via_ytdlp(
    url: str,
    out_dir: Path,
    idx: int,
    label_hint: str = "AUTO",
    download_mp4: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    使用 yt-dlp 通用引擎解析并下载非 TikTok 视频（如 YouTube, Instagram, X, 小红书, Bilibili 等）或作为 TikTok 的备用通道。
    """
    import yt_dlp

    ydl_opts_info: Dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "skip_download": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as ex:
        logger.error(f"yt-dlp 无法解析链接 {url}: {ex}")
        return None

    if not info:
        return None

    vid_id = str(info.get("id") or f"vid_{idx}")
    uploader_id = str(info.get("uploader_id") or info.get("channel_id") or info.get("uploader") or "creator").lstrip("@")
    nickname = str(info.get("uploader") or info.get("channel") or uploader_id)
    title = str(info.get("title") or "")
    desc_raw = str(info.get("description") or title)
    desc = desc_raw if desc_raw else title
    extractor = str(info.get("extractor_key") or info.get("extractor") or "Web")

    video_dir = out_dir / f"{re.sub(r'[^a-zA-Z0-9_-]', '_', uploader_id)[:25]}_{vid_id}"
    video_dir.mkdir(parents=True, exist_ok=True)

    local_mp4_path: Optional[Path] = None
    if download_mp4:
        target_mp4 = video_dir / f"{vid_id}.mp4"
        ydl_opts_dl: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "merge_output_format": "mp4",
            "outtmpl": str(target_mp4),
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts_dl) as ydl:
                ydl.download([url])
            if target_mp4.exists():
                local_mp4_path = target_mp4
            else:
                mp4s = list(video_dir.glob("*.mp4"))
                if mp4s:
                    local_mp4_path = mp4s[0]
        except Exception as dl_ex:
            logger.warning(f"yt-dlp 下载视频原片未完成: {dl_ex}")

    visual_metrics = (
        analyze_video_visuals_and_storyboard(local_mp4_path, video_dir, vid_id)
        if local_mp4_path
        else {}
    )

    is_fr_lang, _, fr_sum = detect_target_language(desc, "fr", 0.5)
    is_en_lang, _, en_sum = detect_target_language(desc, "en", 0.5)
    author_mock = {"uniqueId": uploader_id, "nickname": nickname, "signature": ""}
    is_fr_c, fr_reasons = evaluate_french_creator(author_mock, desc)
    is_uk_c, uk_reasons = evaluate_uk_creator(author_mock, desc)

    if label_hint and label_hint != "AUTO":
        market_tag = f"{label_hint} ({extractor})"
    elif is_fr_c or is_fr_lang:
        market_tag = f"FR / 法语 ({extractor})"
    elif is_uk_c:
        market_tag = f"UK / 英语 ({extractor})"
    elif is_en_lang:
        market_tag = f"EN / 英语 ({extractor})"
    else:
        market_tag = f"{extractor} 视频"

    play_cnt = int(info.get("view_count", 0) or 0)
    digg_cnt = int(info.get("like_count", 0) or 0)
    comm_cnt = int(info.get("comment_count", 0) or 0)
    share_cnt = int(info.get("repost_count", 0) or 0)
    coll_cnt = int(info.get("save_count", 0) or 0)
    eng_rate = (digg_cnt + comm_cnt + share_cnt + coll_cnt) / play_cnt if play_cnt > 0 else 0.0

    tags_list = info.get("tags") or []
    hashtags_from_desc = re.findall(r"#([\w\u00C0-\u017F]+)", desc)
    all_tags = list(dict.fromkeys([str(t) for t in tags_list] + hashtags_from_desc))

    ts = info.get("timestamp") or 0
    create_str = (
        datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")
        if ts
        else str(info.get("upload_date") or "")
    )

    item_record: Dict[str, Any] = {
        "market_tag": market_tag,
        "video_id": vid_id,
        "video_url": info.get("webpage_url") or url,
        "uniqueId": uploader_id,
        "nickname": nickname,
        "user_id": str(info.get("channel_id") or uploader_id),
        "verified": bool(info.get("channel_is_verified", False)),
        "signature": str(info.get("uploader_url") or ""),
        "follower_count": int(info.get("channel_follower_count", 0) or 0),
        "creator_heart_count": 0,
        "create_time_str": create_str,
        "desc": desc,
        "hashtags": ", ".join(all_tags[:20]),
        "music_title": str(info.get("track") or "原声 / BGM"),
        "music_author": str(info.get("artist") or nickname),
        "duration_sec": visual_metrics.get("duration_sec") or float(info.get("duration", 0) or 0),
        "width": visual_metrics.get("width") or int(info.get("width", 0) or 0),
        "height": visual_metrics.get("height") or int(info.get("height", 0) or 0),
        "aspect_ratio": visual_metrics.get("aspect_ratio", "自适应画幅"),
        "scene_cuts_count": visual_metrics.get("scene_cuts_count", 0),
        "avg_shot_length_sec": visual_metrics.get("avg_shot_length_sec", 0.0),
        "pacing_style": visual_metrics.get("pacing_style", "标准视频叙事节奏"),
        "visual_tone_desc": visual_metrics.get("visual_tone_desc", "自然光效"),
        "local_mp4_path": str(local_mp4_path) if local_mp4_path else "未下载",
        "storyboard_path": visual_metrics.get("storyboard_path") or "未生成",
        "keyframe_paths": visual_metrics.get("keyframe_paths", []),
        "transcript": "",
        "play_count": play_cnt,
        "digg_count": digg_cnt,
        "comment_count": comm_cnt,
        "share_count": share_cnt,
        "collect_count": coll_cnt,
        "engagement_rate": eng_rate,
        "lang_summary": fr_sum if fr_sum != "empty" else en_sum,
        "creator_match_reasons": "; ".join(fr_reasons + uk_reasons),
        "top_comments": [],
        "raw_comments": [],
    }
    item_record["perspectives"] = build_8_perspectives_analysis(item_record)
    (video_dir / f"video_{vid_id}_full_analysis.json").write_text(
        json.dumps(item_record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return item_record


async def analyze_selected_videos(
    url_pairs: List[Tuple[str, str]],
    out_dir: Path,
    download_mp4: bool = True,
    fetch_comments_count: int = 20,
    headless: Any = False,
) -> Tuple[Optional[Path], Optional[Path], List[Dict[str, Any]]]:
    """
    智能路由：
    - 若链接为 TikTok 视频，优先使用 PyTok 获取深度元数据、原片、字幕与高赞评论（若失败自动回退至 yt-dlp）；
    - 若链接为其他任意平台视频（YouTube, Instagram, X, 小红书, Bilibili 等），自动调用 yt-dlp 下载原片并执行 OpenCV 分镜拆解与 8 大维度分析。
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    analyzed_items: List[Dict[str, Any]] = []

    has_tiktok_urls = any("tiktok.com" in u.lower() for _, u in url_pairs)
    pytok_instance = None
    if has_tiktok_urls:
        pool = AccountsPool()
        try:
            pytok_instance = await PyTok.from_pool(
                pool,
                request_delay=3,
                headless=headless,
                page_load_timeout=90,
            )
        except NoAccountError as err:
            logger.warning(f"PyTok 账号池无可用账号 ({err})，将使用通用 yt-dlp 引擎解析。")
            pytok_instance = None

    import contextlib
    ctx = pytok_instance if pytok_instance is not None else contextlib.nullcontext(None)

    async with ctx as api:
        for idx, (market_hint, url) in enumerate(url_pairs, start=1):
            logger.info(f"[{idx}/{len(url_pairs)}] 正在深度解析视频: {url} ...")

            # 非 TikTok 链接或无 PyTok 实例时，直接走 yt-dlp 通用引擎
            if "tiktok.com" not in url.lower() or api is None:
                generic_item = analyze_generic_url_via_ytdlp(
                    url=url,
                    out_dir=out_dir,
                    idx=idx,
                    label_hint=market_hint,
                    download_mp4=download_mp4,
                )
                if generic_item:
                    analyzed_items.append(generic_item)
                continue

            try:
                vid_id = extract_video_id_from_url(url)
                u_name = extract_user_id_from_url(url)
            except Exception:
                m_vid = re.search(r"/video/(\d+)", url)
                m_usr = re.search(r"/@([^/?]+)", url)
                vid_id = m_vid.group(1) if m_vid else f"video_{idx}"
                u_name = m_usr.group(1) if m_usr else "user"

            video_dir = out_dir / f"{u_name}_{vid_id}"
            video_dir.mkdir(parents=True, exist_ok=True)

            video_obj = api.video(id=vid_id, username=u_name, url=url)
            try:
                v_dict = await video_obj.info()
            except Exception as ex:
                logger.warning(f"通过默认方式获取视频 {vid_id} 详情失败 ({ex})，尝试页面抓取...")
                try:
                    v_dict = await video_obj._info_scraping()
                    video_obj.as_dict = v_dict
                except Exception as ex2:
                    logger.warning(f"PyTok 无法获取视频 {url} ({ex2})，回退至 yt-dlp 通用解析...")
                    generic_item = analyze_generic_url_via_ytdlp(
                        url=url,
                        out_dir=out_dir,
                        idx=idx,
                        label_hint=market_hint,
                        download_mp4=download_mp4,
                    )
                    if generic_item:
                        analyzed_items.append(generic_item)
                    continue

            desc = str(v_dict.get("desc") or "")
            author_data = dict(v_dict.get("author") or {})
            author_stats = dict(v_dict.get("authorStats") or v_dict.get("stats") or {})
            author_merged = {**author_data, **author_stats}
            unique_id = str(author_merged.get("uniqueId") or u_name or "")

            # 补充查询博主主页信息（如果缺少 followerCount 或 signature）
            if unique_id and not author_merged.get("followerCount"):
                try:
                    u_obj = api.user(
                        username=unique_id,
                        user_id=author_merged.get("id"),
                        sec_uid=author_merged.get("secUid"),
                    )
                    u_info = extract_user_dict_from_info(await u_obj._info_full_api())
                    if u_info:
                        author_merged.update(u_info)
                except Exception:
                    pass

            # 自动推断或使用指定的市场标签 (FR / UK)
            is_fr_lang, fr_prob, fr_sum = detect_target_language(desc, "fr", 0.5)
            is_en_lang, en_prob, en_sum = detect_target_language(desc, "en", 0.5)
            is_fr_c, fr_reasons = evaluate_french_creator(author_merged, desc)
            is_uk_c, uk_reasons = evaluate_uk_creator(author_merged, desc)

            if market_hint and market_hint != "AUTO":
                if is_fr_c or is_fr_lang:
                    market_tag = f"{market_hint} · 🇫🇷 FR"
                elif is_uk_c or is_en_lang:
                    market_tag = f"{market_hint} · 🇬🇧 UK/EN"
                else:
                    market_tag = market_hint
            else:
                if is_fr_c or is_fr_lang:
                    market_tag = "🇫🇷 FR (法语)"
                elif is_uk_c or is_en_lang:
                    market_tag = "🇬🇧 UK/EN (英语)"
                else:
                    market_tag = f"Video {idx}"

            reasons_combined = fr_reasons if "FR" in market_tag else (uk_reasons if "UK" in market_tag else (fr_reasons + uk_reasons))

            # 1. 下载高清 MP4 原片
            local_mp4_path: Optional[Path] = None
            if download_mp4:
                try:
                    logger.info(f"正在下载视频 {vid_id} 的高清 MP4 原片...")
                    post_media = await video_obj.media(timeout=60)
                    saved_paths = post_media.save(video_dir)
                    for sp in saved_paths:
                        if sp.suffix.lower() == ".mp4":
                            local_mp4_path = sp
                            break
                    if local_mp4_path:
                        logger.info(f"✅ MP4 原片已保存至: {local_mp4_path}")
                except Exception as m_ex:
                    logger.warning(f"MP4 原片下载未完成: {m_ex}")

            # 2. 提取 TikTok 原生字幕轨 (若有)
            transcript = await fetch_tiktok_subtitles(v_dict)

            # 3. 抓取高赞评论样本
            raw_comments: List[Dict[str, Any]] = []
            top_comments_str: List[str] = []
            if fetch_comments_count > 0:
                try:
                    logger.info(f"正在拉取视频 {vid_id} 的前 {fetch_comments_count} 条观众评论...")
                    async for comm in video_obj.comments(count=fetch_comments_count, fetch_replies=False):
                        if not isinstance(comm, dict):
                            continue
                        c_text = str(comm.get("text") or "").strip()
                        c_digg = int(comm.get("digg_count", 0) or 0)
                        c_lang = str(comm.get("comment_language") or "")
                        c_user_obj = comm.get("user") or {}
                        c_user = (
                            c_user_obj.get("unique_id")
                            or c_user_obj.get("uniqueId")
                            or "user"
                            if isinstance(c_user_obj, dict)
                            else "user"
                        )
                        if c_text:
                            raw_comments.append({
                                "user": f"@{c_user}",
                                "text": c_text,
                                "digg_count": c_digg,
                                "lang": c_lang,
                            })
                    # 按点赞排序
                    raw_comments.sort(key=lambda x: x["digg_count"], reverse=True)
                    top_comments_str = [
                        f"[{c['digg_count']}赞] {c['user']}: {c['text']}"
                        for c in raw_comments[:10]
                    ]
                except Exception as c_ex:
                    logger.warning(f"评论拉取跳过: {c_ex}")

            # 4. 执行 OpenCV 镜头切换检测与 5 阶段分镜故事板生成
            visual_metrics = analyze_video_visuals_and_storyboard(
                local_mp4_path, video_dir, vid_id
            ) if local_mp4_path else {}

            stats = v_dict.get("stats") or {}
            play_cnt = int(stats.get("playCount", 0) or 0)
            digg_cnt = int(stats.get("diggCount", 0) or 0)
            comm_cnt = int(stats.get("commentCount", 0) or 0)
            share_cnt = int(stats.get("shareCount", 0) or 0)
            coll_cnt = int(stats.get("collectCount", 0) or 0)
            eng_rate = (digg_cnt + comm_cnt + share_cnt + coll_cnt) / play_cnt if play_cnt > 0 else 0.0

            music_info = v_dict.get("music") or {}
            video_meta = v_dict.get("video") or {}
            hashtags_list = [
                extra.get("hashtagName")
                for extra in (v_dict.get("textExtra") or [])
                if extra.get("hashtagName")
            ]

            create_ts = int(v_dict.get("createTime", 0) or 0)
            create_str = (
                datetime.fromtimestamp(create_ts).strftime("%Y-%m-%d %H:%M:%S")
                if create_ts > 0
                else ""
            )

            item_record: Dict[str, Any] = {
                "market_tag": market_tag,
                "video_id": vid_id,
                "video_url": f"https://www.tiktok.com/@{unique_id}/video/{vid_id}",
                "uniqueId": unique_id,
                "nickname": author_merged.get("nickname", ""),
                "user_id": str(author_merged.get("id", "")),
                "verified": bool(author_merged.get("verified", False)),
                "signature": author_merged.get("signature", ""),
                "follower_count": int(author_merged.get("followerCount", 0) or 0),
                "creator_heart_count": int(
                    author_merged.get("heartCount", author_merged.get("heart", 0)) or 0
                ),
                "create_time_str": create_str,
                "desc": desc,
                "hashtags": ", ".join(hashtags_list),
                "music_title": music_info.get("title", "Original Sound"),
                "music_author": music_info.get("authorName", unique_id),
                "duration_sec": visual_metrics.get("duration_sec") or float(video_meta.get("duration", 0) or 0),
                "width": visual_metrics.get("width") or int(video_meta.get("width", 0) or 0),
                "height": visual_metrics.get("height") or int(video_meta.get("height", 0) or 0),
                "aspect_ratio": visual_metrics.get("aspect_ratio", "9:16 (竖屏)"),
                "scene_cuts_count": visual_metrics.get("scene_cuts_count", 0),
                "avg_shot_length_sec": visual_metrics.get("avg_shot_length_sec", 0.0),
                "pacing_style": visual_metrics.get("pacing_style", "标准短视频叙事节奏"),
                "visual_tone_desc": visual_metrics.get("visual_tone_desc", "自然光效"),
                "local_mp4_path": str(local_mp4_path) if local_mp4_path else "未下载",
                "storyboard_path": visual_metrics.get("storyboard_path") or "未生成",
                "keyframe_paths": visual_metrics.get("keyframe_paths", []),
                "transcript": transcript,
                "play_count": play_cnt,
                "digg_count": digg_cnt,
                "comment_count": comm_cnt,
                "share_count": share_cnt,
                "collect_count": coll_cnt,
                "engagement_rate": eng_rate,
                "lang_summary": fr_sum if fr_sum != "empty" else en_sum,
                "creator_match_reasons": "; ".join(reasons_combined),
                "top_comments": top_comments_str,
                "raw_comments": raw_comments,
            }

            item_record["perspectives"] = build_8_perspectives_analysis(item_record)
            analyzed_items.append(item_record)

            # 保存单条视频的完整 JSON 档案
            (video_dir / f"video_{vid_id}_full_analysis.json").write_text(
                json.dumps(item_record, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    if not analyzed_items:
        return None, None, []

    xlsx_path, md_path = export_lumiere_excel_and_md(analyzed_items, out_dir)
    logger.info(
        f"✨ Lumière 视频深度拆解完成！\n"
        f"  - Excel 报表: {xlsx_path}\n"
        f"  - AI 深析档案: {md_path}"
    )
    return xlsx_path, md_path, analyzed_items


def parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lumière — TikTok 精选视频结构拆解与 Task 1 八大维度分析引擎"
    )
    parser.add_argument(
        "--urls",
        type=str,
        required=True,
        help="一个或多个 TikTok 视频链接（用空格或逗号分隔，支持 FR:url UK:url 前缀）",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default=str(Path.home() / "TikTokResearch" / "Lumière_视频深析"),
        help="输出目录路径（默认: ~/TikTokResearch/Lumière_视频深析）",
    )
    parser.add_argument(
        "--comments",
        type=int,
        default=20,
        help="每条视频抓取的高赞评论数量（默认: 20）",
    )
    parser.add_argument(
        "--no-mp4",
        action="store_true",
        help="仅分析元数据与评论，不下载 MP4 原片",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_cli_args()
    pairs = parse_url_inputs(args.urls)
    if not pairs:
        logger.error("未检测到有效的 TikTok 视频链接！请传入完整的 https://www.tiktok.com/@.../video/... 链接。")
    else:
        asyncio.run(
            analyze_selected_videos(
                url_pairs=pairs,
                out_dir=Path(args.out_dir),
                download_mp4=not args.no_mp4,
                fetch_comments_count=args.comments,
            )
        )
