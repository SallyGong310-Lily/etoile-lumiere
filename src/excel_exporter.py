"""
Étoile — 莫兰迪美学配色 Excel (.xlsx) 报表导出模块

设计布局：
1. 【核心视频信息区】置于最前面，其中「🔗 视频直达链接」位于第 2 列并使用醒目勃艮第暗红/玫瑰金高定底色高亮，支持一键点击跳转。
2. 【视频互动数据区】紧随视频信息之后（播放量、点赞、评论、分享、收藏、互动率），采用莫兰迪雾霾蓝配色。
3. 【博主身份三联列】将「账号ID (uniqueId)」「博主昵称 (nickname)」「用户UID (user_id)」紧挨排列，整列统一采用莫兰迪干枯玫瑰粉底色。
4. 【博主简介与影响力区】包含蓝V认证、个人简介(Bio)、主页直链、粉丝数、总获赞数、作品数、关注数，采用莫兰迪鼠尾草绿配色。
5. 【区域与语言核验区】包含命中特征原因、语言识别置信度与语言明细，采用莫兰迪燕麦暖灰配色。
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


# ---------------------------------------------------------------------------
# 莫兰迪 (Morandi) 色卡定义
# ---------------------------------------------------------------------------

# 边框：柔和浅暖灰细线
BORDER_SIDE = Side(border_style="thin", color="E2DDD7")
CELL_BORDER = Border(left=BORDER_SIDE, right=BORDER_SIDE, top=BORDER_SIDE, bottom=BORDER_SIDE)

HEADER_BORDER = Border(
    left=Side(border_style="thin", color="D0C9C0"),
    right=Side(border_style="thin", color="D0C9C0"),
    top=Side(border_style="medium", color="8C7A6B"),
    bottom=Side(border_style="medium", color="8C7A6B"),
)

# 1. 市场区域 (第1列) - 莫兰迪深炭褐
FILL_HEADER_MARKET = PatternFill(start_color="5C5552", end_color="5C5552", fill_type="solid")
FILL_BODY_MARKET = PatternFill(start_color="F5F3F2", end_color="F5F3F2", fill_type="solid")

# 2. 视频直达链接 (第2列，视觉焦点！) - 勃艮第红丝绒表头 + 柔和香槟金高亮底色
FILL_HEADER_VIDEO_URL = PatternFill(start_color="8C3B4A", end_color="8C3B4A", fill_type="solid")
FILL_BODY_VIDEO_URL = PatternFill(start_color="FDF6EC", end_color="FDF6EC", fill_type="solid")

# 3. 视频核心信息 (文案、发布日期、标签、视频ID) - 莫兰迪暖驼褐
FILL_HEADER_VIDEO_INFO = PatternFill(start_color="9A8B7A", end_color="9A8B7A", fill_type="solid")
FILL_BODY_VIDEO_INFO = PatternFill(start_color="FAF8F5", end_color="FAF8F5", fill_type="solid")

# 4. 视频互动数据 (播放、点赞、评论、分享、收藏、互动率) - 莫兰迪雾霾蓝
FILL_HEADER_METRICS = PatternFill(start_color="6E7F8D", end_color="6E7F8D", fill_type="solid")
FILL_BODY_METRICS = PatternFill(start_color="F3F6F8", end_color="F3F6F8", fill_type="solid")

# 5. 博主身份三联列 (uniqueId / nickname / user_id) - 莫兰迪干枯玫瑰粉 (三列同色)
FILL_HEADER_IDENTITY = PatternFill(start_color="A67B7B", end_color="A67B7B", fill_type="solid")
FILL_BODY_IDENTITY = PatternFill(start_color="F9F1F1", end_color="F9F1F1", fill_type="solid")

# 6. 博主简介与影响力 (认证、Bio、主页链接、粉丝、总赞、作品、关注) - 莫兰迪鼠尾草绿
FILL_HEADER_PROFILE = PatternFill(start_color="7A8B7B", end_color="7A8B7B", fill_type="solid")
FILL_BODY_PROFILE = PatternFill(start_color="F4F7F4", end_color="F4F7F4", fill_type="solid")

# 7. 属地与语言核验 (命中原因、置信度、语言分布) - 莫兰迪紫灰/燕麦灰
FILL_HEADER_AUDIT = PatternFill(start_color="847E89", end_color="847E89", fill_type="solid")
FILL_BODY_AUDIT = PatternFill(start_color="F6F5F7", end_color="F6F5F7", fill_type="solid")

# 字体定义
FONT_HEADER_LIGHT = Font(name="PingFang SC", size=11, bold=True, color="FFFFFF")
FONT_HEADER_GOLD = Font(name="PingFang SC", size=11, bold=True, color="FFEBC8")
FONT_BODY = Font(name="PingFang SC", size=10, color="2C2A29")
FONT_BODY_BOLD = Font(name="PingFang SC", size=10, bold=True, color="2C2A29")
FONT_LINK = Font(name="PingFang SC", size=10, bold=True, underline="single", color="8C3B4A")
FONT_PROFILE_LINK = Font(name="PingFang SC", size=10, underline="single", color="4A6B82")


def _format_timestamp(ts: Any) -> str:
    """将 Unix 时间戳格式化为直观的标准日期时间 YYYY-MM-DD HH:MM:SS。"""
    if not ts:
        return ""
    if isinstance(ts, str) and "-" in ts:
        return ts
    try:
        ts_int = int(float(ts))
        if ts_int <= 0:
            return ""
        return datetime.fromtimestamp(ts_int).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(ts)


def _format_market_label(market: str) -> str:
    m = (market or "FR").upper()
    if m == "FR":
        return "🇫🇷 法国 (FR)"
    elif m == "UK":
        return "🇬🇧 英国 (UK)"
    elif m == "ALL":
        return "🌍 全球 (ALL)"
    return m


def _format_reasons_cn(reasons_str: str) -> str:
    """将命中的特征原因转化为更直观的中文描述。"""
    if not reasons_str:
        return ""
    s = reasons_str
    replacements = [
        ("account_region:", "账号注册地:"),
        ("profile_emoji:", "主页国旗/符号:"),
        ("caption_emoji:", "文案国旗/符号:"),
        ("profile_symbol:", "主页符号:"),
        ("caption_symbol:", "文案符号:"),
        ("profile_location:", "主页法国地标:"),
        ("caption_location:", "文案法国地标:"),
        ("profile_uk_location:", "主页英国地标:"),
        ("caption_uk_location:", "文案英国地标:"),
        ("bio_french_keyword:", "简介法语特征词:"),
        ("bio_uk_keyword:", "简介英国特征词:"),
        ("bio_lang_fr:", "简介法语置信度:"),
        ("username_fr_pattern:", "账号名含FR:"),
        ("username_uk_pattern:", "账号名含UK:"),
        ("global_unfiltered", "全球不限"),
    ]
    for old, new in replacements:
        s = s.replace(old, new)
    return s


# 列配置定义：(中文表头, 宽度, 表头底色, 单元格底色, 对齐方式, 数字格式)
COLUMNS_SPEC = [
    # 1. 区域
    ("目标市场", 15, FILL_HEADER_MARKET, FILL_BODY_MARKET, "center", None),
    # 2. 视频核心区（置顶最前，视频直达链接醒目高亮，紧接视频时长方便一眼筛除超短视频）
    ("🔗 视频直达链接 (点击打开)", 38, FILL_HEADER_VIDEO_URL, FILL_BODY_VIDEO_URL, "left", None),
    ("视频时长 (秒)", 14, FILL_HEADER_VIDEO_INFO, FILL_BODY_VIDEO_INFO, "center", '0"s"'),
    ("时长叙事评级", 20, FILL_HEADER_VIDEO_INFO, FILL_BODY_VIDEO_INFO, "center", None),
    ("视频文案内容 (Caption)", 46, FILL_HEADER_VIDEO_INFO, FILL_BODY_VIDEO_INFO, "left", None),
    ("发布日期", 20, FILL_HEADER_VIDEO_INFO, FILL_BODY_VIDEO_INFO, "center", None),
    ("话题标签 (Hashtags)", 30, FILL_HEADER_VIDEO_INFO, FILL_BODY_VIDEO_INFO, "left", None),
    # 3. 视频互动数据区（相邻聚合）
    ("播放量", 13, FILL_HEADER_METRICS, FILL_BODY_METRICS, "right", "#,##0"),
    ("点赞量", 12, FILL_HEADER_METRICS, FILL_BODY_METRICS, "right", "#,##0"),
    ("评论量", 11, FILL_HEADER_METRICS, FILL_BODY_METRICS, "right", "#,##0"),
    ("分享量", 11, FILL_HEADER_METRICS, FILL_BODY_METRICS, "right", "#,##0"),
    ("收藏量", 11, FILL_HEADER_METRICS, FILL_BODY_METRICS, "right", "#,##0"),
    ("互动率", 11, FILL_HEADER_METRICS, FILL_BODY_METRICS, "right", "0.00%"),
    # 4. 博主身份三联列（uniqueId / nickname / user_id 同色莫兰迪玫瑰粉）
    ("账号ID (uniqueId)", 22, FILL_HEADER_IDENTITY, FILL_BODY_IDENTITY, "left", None),
    ("博主昵称 (nickname)", 22, FILL_HEADER_IDENTITY, FILL_BODY_IDENTITY, "left", None),
    ("用户UID (userid)", 21, FILL_HEADER_IDENTITY, FILL_BODY_IDENTITY, "center", "@"),
    # 5. 博主简介与粉丝影响力区
    ("蓝V认证", 11, FILL_HEADER_PROFILE, FILL_BODY_PROFILE, "center", None),
    ("个人简介 (Bio / Signature)", 42, FILL_HEADER_PROFILE, FILL_BODY_PROFILE, "left", None),
    ("粉丝数", 13, FILL_HEADER_PROFILE, FILL_BODY_PROFILE, "right", "#,##0"),
    ("博主总获赞", 14, FILL_HEADER_PROFILE, FILL_BODY_PROFILE, "right", "#,##0"),
    ("作品总数", 11, FILL_HEADER_PROFILE, FILL_BODY_PROFILE, "right", "#,##0"),
    ("关注数", 11, FILL_HEADER_PROFILE, FILL_BODY_PROFILE, "right", "#,##0"),
    ("博主主页链接", 34, FILL_HEADER_PROFILE, FILL_BODY_PROFILE, "left", None),
    # 6. 属地特征与语言核验区
    ("区域特征命中依据", 36, FILL_HEADER_AUDIT, FILL_BODY_AUDIT, "left", None),
    ("语言置信度", 12, FILL_HEADER_AUDIT, FILL_BODY_AUDIT, "right", "0.0%"),
    ("语言识别明细", 16, FILL_HEADER_AUDIT, FILL_BODY_AUDIT, "center", None),
    ("视频ID", 21, FILL_HEADER_VIDEO_INFO, FILL_BODY_VIDEO_INFO, "center", "@"),
]


def _format_duration_tier(dur_sec: int) -> str:
    """根据视频时长评估其是否适合 Lumière 多维度结构深析。"""
    if dur_sec <= 0:
        return "— 待核验 (图文/未知)"
    elif dur_sec < 12:
        return f"⚡ 碎片情绪 ({dur_sec}s · 较短)"
    elif dur_sec < 25:
        return f"✨ 标准节奏 ({dur_sec}s · 适中)"
    elif dur_sec <= 60:
        return f"🌟 黄金叙事 ({dur_sec}s · 极佳)"
    else:
        max_m, rem_s = divmod(dur_sec, 60)
        return f"🎬 深度长片 ({max_m}m{rem_s:02d}s · 极佳)"


def export_styled_excel(records: List[Dict[str, Any]], xlsx_path: Path) -> None:
    """将采集记录导出为带莫兰迪配色与中文表头的精致 .xlsx 文件。"""
    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Étoile 精选视频与博主"

    # 开启网格线但使用优雅的莫兰迪底色覆盖
    ws.views.sheetView[0].showGridLines = True

    # 冻结首行表头 + 前两列（目标市场 + 视频直达链接），方便左右滑动查看时始终锁定视频链接
    ws.freeze_panes = "C2"

    # 1. 写入表头
    ws.row_dimensions[1].height = 34
    for col_idx, (title, width, h_fill, _, _, _) in enumerate(COLUMNS_SPEC, start=1):
        cell = ws.cell(row=1, column=col_idx, value=title)
        cell.fill = h_fill
        cell.font = FONT_HEADER_GOLD if col_idx == 2 else FONT_HEADER_LIGHT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = HEADER_BORDER
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    # 2. 写入数据行
    for row_idx, rec in enumerate(records, start=2):
        ws.row_dimensions[row_idx].height = 42

        unique_id = str(rec.get("uniqueId") or "")
        video_id = str(rec.get("video_id") or "")
        video_url = str(rec.get("video_url") or f"https://www.tiktok.com/@{unique_id}/video/{video_id}")
        profile_url = f"https://www.tiktok.com/@{unique_id}" if unique_id else ""

        play_cnt = int(rec.get("play_count", 0) or 0)
        digg_cnt = int(rec.get("digg_count", 0) or 0)
        comm_cnt = int(rec.get("comment_count", 0) or 0)
        share_cnt = int(rec.get("share_count", 0) or 0)
        coll_cnt = int(rec.get("collect_count", 0) or 0)

        engagement_rate = (
            (digg_cnt + comm_cnt + share_cnt + coll_cnt) / play_cnt
            if play_cnt > 0
            else 0.0
        )

        reasons_raw = str(
            rec.get("creator_match_reasons")
            or rec.get("french_creator_reasons")
            or ""
        )

        dur_sec = int(float(rec.get("duration_sec", 0) or 0))
        dur_cell_val: Any = dur_sec if dur_sec > 0 else "—"

        row_values = [
            _format_market_label(str(rec.get("market") or "FR")),
            video_url,
            dur_cell_val,
            _format_duration_tier(dur_sec),
            str(rec.get("desc") or ""),
            _format_timestamp(rec.get("create_time")),
            str(rec.get("hashtags") or ""),
            play_cnt,
            digg_cnt,
            comm_cnt,
            share_cnt,
            coll_cnt,
            engagement_rate,
            f"@{unique_id}" if unique_id and not unique_id.startswith("@") else unique_id,
            str(rec.get("nickname") or ""),
            str(rec.get("user_id") or ""),
            "✅ 已认证" if rec.get("verified") else "—",
            str(rec.get("signature") or "").replace("\n", " | "),
            int(rec.get("follower_count", 0) or 0),
            int(rec.get("creator_heart_count", 0) or 0),
            int(rec.get("creator_video_count", 0) or 0),
            int(rec.get("following_count", 0) or 0),
            profile_url,
            _format_reasons_cn(reasons_raw),
            float(rec.get("lang_confidence", 0.0) or 0.0),
            str(rec.get("lang_summary") or ""),
            video_id,
        ]

        for col_idx, val in enumerate(row_values, start=1):
            _, _, _, b_fill, align_h, num_fmt = COLUMNS_SPEC[col_idx - 1]
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.fill = b_fill
            cell.border = CELL_BORDER

            # 文本换行策略：文案、简介、标签、命中依据开启自动换行
            wrap = col_idx in (5, 7, 18, 24)
            cell.alignment = Alignment(horizontal=align_h, vertical="center", wrap_text=wrap)

            if num_fmt and not (col_idx == 3 and not isinstance(val, (int, float))):
                cell.number_format = num_fmt

            # 特殊列样式处理
            if col_idx == 2 and video_url.startswith("http"):
                cell.hyperlink = video_url
                cell.font = FONT_LINK
            elif col_idx == 23 and profile_url.startswith("http"):
                cell.hyperlink = profile_url
                cell.font = FONT_PROFILE_LINK
            elif col_idx in (14, 15) or col_idx == 3:
                # 账号 ID、昵称与视频时长加粗突出
                cell.font = FONT_BODY_BOLD
            else:
                cell.font = FONT_BODY

    # 开启全表自动筛选漏斗
    last_col_letter = get_column_letter(len(COLUMNS_SPEC))
    last_row = max(2, len(records) + 1)
    ws.auto_filter.ref = f"A1:{last_col_letter}{last_row}"

    wb.save(xlsx_path)
