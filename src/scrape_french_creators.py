#!/usr/bin/env python3
"""
TikTok 多区域（法国 FR / 英国 UK / 全球 ALL）创作者与视频采集脚本 (基于 MEOMcGill/pytok)

功能：
1. 从 ~/.pytok 账号池获取已登录账号并启动 Camoufox 反指纹浏览器
2. 遍历指定 Hashtag（如 #victoriasecret）下的视频流
3. 根据目标市场（--market FR / UK / ALL）：
   - FR (法国区): 使用 langdetect 判定视频文案是否为法语 (fr)，并核验博主法国特征（🇫🇷、法国城市、.fr、法语简介等）
   - UK (英国区): 使用 langdetect 判定视频文案是否为英语 (en)，并核验博主英国特征（🇬🇧/🏴󠁧󠁢󠁥󠁮󠁧󠁿/🏴󠁧󠁢󠁳󠁣󠁴󠁿、£ 英镑、London/Manchester 等英国城市、.co.uk、UK 尺码标识等）
   - ALL (全球不限): 不限语言与地区，全量导出该 Hashtag 下的创作者与视频数据
4. 实时保存匹配的创作者及视频数据至 JSON 和 CSV 文件
"""

import argparse
import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd
from langdetect import DetectorFactory, LangDetectException, detect_langs

from pytok.accounts import AccountsPool, NoAccountError
from pytok.exceptions import (
    AccountPrivateException,
    ApiFailedException,
    ConnectionDroppedException,
    EmptyResponseException,
    LoginException,
    NoContentException,
    NotAvailableException,
    NotFoundException,
    TimeoutException,
)
from pytok.tiktok import PyTok

# 固定随机种子以保证 langdetect 语言检测结果的一致性
DetectorFactory.seed = 0

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("EtoileCurator")

# ---------------------------------------------------------------------------
# 1. 法国 (FR) 创作者特征词库与正则规则
# ---------------------------------------------------------------------------

FRENCH_FLAGS = ("🇫🇷", "🥖", "🥐", "🗼")

FRENCH_LOCATIONS_KEYWORDS = [
    r"france",
    r"fran[çc]ais(?:e)?",
    r"french(?:\s+girl|\s+boy|\s+creator|\s+style)?",
    r"paris",
    r"parisien(?:ne)?",
    r"lyon",
    r"lyonnais(?:e)?",
    r"marseille",
    r"toulouse",
    r"nice",
    r"nantes",
    r"montpellier",
    r"strasbourg",
    r"bordeaux",
    r"lille",
    r"rennes",
    r"reims",
    r"toulon",
    r"grenoble",
    r"dijon",
    r"angers",
    r"n[îi]mes",
    r"aix[\s-]en[\s-]provence",
    r"cannes",
    r"[îi]le[\s-]de[\s-]france",
    r"c[ôo]te\s+d['’]azur",
    r"provence",
    r"bretagne",
    r"normandie",
    r"alsace",
    r"corse",
    r"\+33\b",
    r"\b750\d{2}\b",
    r"\b6900\d\b",
    r"\b130\d{2}\b",
    r"\.[fF][rR]\b",
]

FRENCH_BIO_INDICATORS = [
    r"bienvenue",
    r"abonne[\s-]toi",
    r"abonnez[\s-]vous",
    r"partenariat",
    r"contact\s*pro",
    r"mes\s+r[ée]seaux",
    r"mon\s+insta",
    r"code\s+promo",
]

FR_LOCATION_PATTERN = re.compile(
    r"\b(?:" + "|".join(FRENCH_LOCATIONS_KEYWORDS) + r")\b",
    re.IGNORECASE,
)

FR_BIO_INDICATOR_PATTERN = re.compile(
    r"\b(?:" + "|".join(FRENCH_BIO_INDICATORS) + r")\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# 2. 英国 (UK) 创作者特征词库与正则规则
# ---------------------------------------------------------------------------

UK_FLAGS = ("🇬🇧", "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "🏴󠁧󠁢󠁷󠁬󠁳󠁿", "£")

UK_LOCATIONS_KEYWORDS = [
    # 国家与身份表达
    r"u\.?k\.?",
    r"united\s+kingdom",
    r"britain",
    r"british(?:\s+girl|\s+boy|\s+creator|\s+fashion)?",
    r"england",
    r"english(?:\s+girl|\s+boy)?",
    r"scotland",
    r"scottish",
    r"wales",
    r"welsh",
    r"northern\s+ireland",
    r"uktiktok",
    r"ukfashion",
    r"ukhaul",
    r"ukcreator",
    # 英国主要城市与地区
    r"london",
    r"londoner",
    r"manchester",
    r"mancunian",
    r"birmingham",
    r"liverpool",
    r"scouse(?:r)?",
    r"leeds",
    r"glasgow",
    r"edinburgh",
    r"bristol",
    r"sheffield",
    r"newcastle",
    r"geordie",
    r"nottingham",
    r"cardiff",
    r"belfast",
    r"brighton",
    r"leicester",
    r"coventry",
    r"southampton",
    r"portsmouth",
    r"oxford",
    r"cambridge",
    r"york",
    r"yorkshire",
    r"essex",
    r"surrey",
    r"kent",
    r"cornwall",
    r"cotswolds",
    r"cheshire",
    # 英国域名/区号/尺码标识 (穿搭美妆博主高频)
    r"\.co\.uk\b",
    r"\+44\b",
    r"\buk\s*(?:size\s*)?(?:4|6|8|10|12|14|16|18|20)\b",
]

UK_BIO_INDICATORS = [
    r"pr\s*(?:&|and)?\s*collabs?",
    r"enquiries",
    r"management\s*:",
    r"based\s+in\s+(?:the\s+)?uk",
    r"based\s+in\s+london",
    r"ldn\b",
    r"mcr\b",
    r"bham\b",
]

UK_LOCATION_PATTERN = re.compile(
    r"(?<!\w)(?:" + "|".join(UK_LOCATIONS_KEYWORDS) + r")(?!\w)",
    re.IGNORECASE,
)

UK_BIO_INDICATOR_PATTERN = re.compile(
    r"\b(?:" + "|".join(UK_BIO_INDICATORS) + r")\b",
    re.IGNORECASE,
)

# 清洗视频文案中的 #hashtag、@mention、URL，提取纯文本用于语言检测
HASHTAG_MENTION_URL_RE = re.compile(
    r"(https?://\S+|www\.\S+|#[\w\u00C0-\u017F]+|@[\w._]+)",
    re.UNICODE,
)


def clean_text_for_langdetect(text: str) -> str:
    """去除文案中的 URL、@提及 和 #标签，保留自然语言部分以提升语言识别准确率。"""
    if not text:
        return ""
    cleaned = HASHTAG_MENTION_URL_RE.sub(" ", text)
    return re.sub(r"\s+", " ", cleaned).strip()


def detect_target_language(
    desc: str,
    target_lang: str = "fr",
    min_prob: float = 0.65,
) -> Tuple[bool, float, str]:
    """
    判定视频文案（desc）是否为目标语言（如 'fr' 或 'en'）。

    返回:
        (is_matched_lang, confidence, detected_lang_summary)
    """
    if not desc or not desc.strip():
        return False, 0.0, "empty"

    cleaned = clean_text_for_langdetect(desc)
    target_text = cleaned if len(cleaned) >= 6 else desc.strip()

    if len(target_text) < 3:
        return False, 0.0, "too_short"

    try:
        langs = detect_langs(target_text)
        if not langs:
            return False, 0.0, "unknown"

        summary = ", ".join(f"{l.lang}:{l.prob:.2f}" for l in langs)
        for lang_item in langs:
            if lang_item.lang == target_lang and lang_item.prob >= min_prob:
                return True, round(lang_item.prob, 4), summary

        return False, round(langs[0].prob, 4), summary
    except LangDetectException:
        return False, 0.0, "detect_error"


def detect_french_caption(desc: str, min_prob: float = 0.65) -> Tuple[bool, float, str]:
    """向后兼容函数：判定视频文案是否为法语 (fr)。"""
    return detect_target_language(desc, target_lang="fr", min_prob=min_prob)


def evaluate_french_creator(
    author_dict: Dict[str, Any],
    video_desc: str,
) -> Tuple[bool, List[str]]:
    """判定是否为法国 (FR) 创作者。"""
    reasons: List[str] = []

    unique_id = str(author_dict.get("uniqueId") or author_dict.get("unique_id") or "")
    nickname = str(author_dict.get("nickname") or "")
    signature = str(author_dict.get("signature") or "")
    region = str(author_dict.get("region") or author_dict.get("country") or "")

    combined_profile_text = f"{unique_id} {nickname} {signature}"

    if region.upper() == "FR":
        reasons.append("account_region:FR")

    for flag in FRENCH_FLAGS:
        if flag in combined_profile_text:
            reasons.append(f"profile_emoji:{flag}")
        elif flag in video_desc:
            reasons.append(f"caption_emoji:{flag}")

    profile_loc_matches = FR_LOCATION_PATTERN.findall(combined_profile_text)
    if profile_loc_matches:
        unique_matches = sorted({m.lower() for m in profile_loc_matches})
        reasons.append(f"profile_location:{','.join(unique_matches)}")

    caption_loc_matches = FR_LOCATION_PATTERN.findall(video_desc)
    if caption_loc_matches:
        unique_matches = sorted({m.lower() for m in caption_loc_matches})
        reasons.append(f"caption_location:{','.join(unique_matches)}")

    if signature.strip():
        bio_kw_matches = FR_BIO_INDICATOR_PATTERN.findall(signature)
        if bio_kw_matches:
            unique_bio_kw = sorted({m.lower() for m in bio_kw_matches})
            reasons.append(f"bio_french_keyword:{','.join(unique_bio_kw)}")

        is_bio_fr, bio_prob, _ = detect_target_language(
            signature, target_lang="fr", min_prob=0.80
        )
        if is_bio_fr:
            reasons.append(f"bio_lang_fr:{bio_prob}")

    if re.search(r"(?:^|[._-])fr(?:$|[._-])", unique_id, re.IGNORECASE):
        reasons.append(f"username_fr_pattern:{unique_id}")

    return len(reasons) > 0, reasons


def evaluate_uk_creator(
    author_dict: Dict[str, Any],
    video_desc: str,
) -> Tuple[bool, List[str]]:
    """判定是否为英国 (UK) 创作者。"""
    reasons: List[str] = []

    unique_id = str(author_dict.get("uniqueId") or author_dict.get("unique_id") or "")
    nickname = str(author_dict.get("nickname") or "")
    signature = str(author_dict.get("signature") or "")
    region = str(author_dict.get("region") or author_dict.get("country") or "")

    combined_profile_text = f"{unique_id} {nickname} {signature}"

    # 1. 显式 Region 字段 (GB 或 UK)
    if region.upper() in ("GB", "UK"):
        reasons.append(f"account_region:{region.upper()}")

    # 2. 英国国旗 / 英格兰苏格兰威尔士旗帜 / £ 英镑符号
    for flag in UK_FLAGS:
        if flag in combined_profile_text:
            reasons.append(f"profile_symbol:{flag}")
        elif flag in video_desc:
            reasons.append(f"caption_symbol:{flag}")

    # 3. 简介或昵称中包含英国城市/地区/身份词/尺码
    profile_loc_matches = UK_LOCATION_PATTERN.findall(combined_profile_text)
    if profile_loc_matches:
        unique_matches = sorted({m.lower().strip() for m in profile_loc_matches})
        reasons.append(f"profile_uk_location:{','.join(unique_matches)}")

    # 4. 视频文案中包含英国地标/标签 (如 #london, #ukfashion, #british 等)
    caption_loc_matches = UK_LOCATION_PATTERN.findall(video_desc)
    if caption_loc_matches:
        unique_matches = sorted({m.lower().strip() for m in caption_loc_matches})
        reasons.append(f"caption_uk_location:{','.join(unique_matches)}")

    # 5. 个人简介中包含典型英式缩写或表达 (LDN, MCR, enquiries, .co.uk 等)
    if signature.strip():
        bio_kw_matches = UK_BIO_INDICATOR_PATTERN.findall(signature)
        if bio_kw_matches:
            unique_bio_kw = sorted({m.lower().strip() for m in bio_kw_matches})
            reasons.append(f"bio_uk_keyword:{','.join(unique_bio_kw)}")

    # 6. 账号 ID 以 uk 结尾/开头 (如 xxx.uk / xxx_uk)
    if re.search(r"(?:^|[._-])uk(?:$|[._-])", unique_id, re.IGNORECASE):
        reasons.append(f"username_uk_pattern:{unique_id}")

    return len(reasons) > 0, reasons


def evaluate_creator_by_market(
    market: str,
    author_dict: Dict[str, Any],
    video_desc: str,
) -> Tuple[bool, List[str]]:
    """根据市场代码 ('FR', 'UK', 'ALL') 路由创作者属地判定逻辑。"""
    market_upper = market.upper()
    if market_upper == "FR":
        return evaluate_french_creator(author_dict, video_desc)
    elif market_upper == "UK":
        return evaluate_uk_creator(author_dict, video_desc)
    else:
        return True, ["global_unfiltered"]


def extract_user_dict_from_info(user_info_resp: Dict[str, Any]) -> Dict[str, Any]:
    """兼容 PyTok User.info() API 路径与页面抓取路径返回的不同字典结构。"""
    if not isinstance(user_info_resp, dict):
        return {}
    if "userInfo" in user_info_resp:
        u_info = user_info_resp.get("userInfo", {})
        return {**u_info.get("user", {}), **u_info.get("stats", {})}
    return user_info_resp


from excel_exporter import export_styled_excel


def save_results(records: List[Dict[str, Any]], json_path: Path, csv_path: Path) -> None:
    """将筛选结果保存为莫兰迪配色的 Excel (.xlsx) 报表、CSV 及 JSON 文件。"""
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    # 1. 导出带莫兰迪配色与中文表头的精致 .xlsx 文件
    xlsx_path = csv_path.with_suffix(".xlsx")
    export_styled_excel(records, xlsx_path)

    # 2. 同步保留 UTF-8-SIG 编码的 CSV 备份
    if records:
        df = pd.DataFrame(records)
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")


async def scrape_creators(
    hashtag_name: str = "fyp",
    market: str = "FR",
    max_videos: int = 100,
    request_delay: int = 4,
    headless: Any = False,
    username: Optional[str] = None,
    min_lang_prob: float = 0.65,
    fetch_full_profile_on_miss: bool = True,
    output_json: Path = Path("french_creators.json"),
    output_csv: Path = Path("french_creators.csv"),
) -> List[Dict[str, Any]]:
    """
    核心异步采集与多区域筛选流程（支持传入单个或多个以逗号/空格/#分隔的 Hashtag）。
    """
    hashtags_to_scrape = [
        t.strip().lstrip("#")
        for t in re.split(r"[,，;\s#]+", hashtag_name)
        if t.strip().lstrip("#")
    ]
    if not hashtags_to_scrape:
        hashtags_to_scrape = ["victoriasecret"]

    market_upper = market.upper()
    target_lang_map = {"FR": "fr", "UK": "en", "ALL": None}
    target_lang = target_lang_map.get(market_upper)

    pool = AccountsPool()
    user_profile_cache: Dict[str, Dict[str, Any]] = {}
    seen_video_ids: Set[str] = set()
    matched_records: List[Dict[str, Any]] = []
    scanned_count = 0

    tags_display = ", ".join(f"#{t}" for t in hashtags_to_scrape)
    logger.info(
        f"准备从账号池获取账号 (目标市场: {market_upper}, 待探索标签 ({len(hashtags_to_scrape)}个): {tags_display}, 每个标签扫描上限: {max_videos}, 请求延迟: {request_delay}s)"
    )

    try:
        pytok_instance = await PyTok.from_pool(
            pool,
            username=username,
            request_delay=request_delay,
            headless=headless,
            page_load_timeout=90,
        )
    except NoAccountError as err:
        logger.error(
            f"账号池中没有可用账号: {err}\n"
            "请先双击打开 Étoile 完成首次账号登录。"
        )
        return []

    async with pytok_instance as api:
        for tag_idx, hashtag_clean in enumerate(hashtags_to_scrape, start=1):
            hashtag = api.hashtag(name=hashtag_clean)
            logger.info(
                f"[{tag_idx}/{len(hashtags_to_scrape)}] 开始拉取 #{hashtag_clean} 下的视频流 (每个标签最多扫描 {max_videos} 条，启用 prefer_scraping=True)..."
            )

            try:
                async for video in hashtag.videos(count=max_videos, prefer_scraping=True):
                    scanned_count += 1
                    try:
                        v_dict = video.as_dict or await video.info()
                    except Exception as ex:
                        logger.warning(f"[#{scanned_count}] 获取视频详情失败 (video_id={video.id}): {ex}")
                        continue

                    video_id = str(v_dict.get("id") or video.id or "")
                    if not video_id or video_id in seen_video_ids:
                        continue
                    seen_video_ids.add(video_id)

                    desc = str(v_dict.get("desc") or "")
                    author_data = dict(v_dict.get("author") or {})
                    author_stats = dict(v_dict.get("authorStats") or {})
                    author_merged = {**author_data, **author_stats}

                    unique_id = str(author_merged.get("uniqueId") or video.username or "")
                    if not unique_id:
                        continue

                    # -------------------------------------------------------
                    # 第一步：语言过滤
                    # -------------------------------------------------------
                    if target_lang:
                        is_lang_ok, lang_prob, lang_summary = detect_target_language(
                            desc, target_lang=target_lang, min_prob=min_lang_prob
                        )
                        if not is_lang_ok:
                            logger.debug(
                                f"[#{scanned_count}] 跳过 @{unique_id} (视频 {video_id}): 文案非 {target_lang} ({lang_summary})"
                            )
                            continue
                        logger.info(
                            f"[#{scanned_count}] 命中 {target_lang.upper()} 文案! 博主=@{unique_id}, 视频={video_id}, 置信度={lang_prob} ({lang_summary})"
                        )
                    else:
                        lang_prob = 1.0
                        lang_summary = "unfiltered"

                    # -------------------------------------------------------
                    # 第二步：国籍/地区判定
                    # -------------------------------------------------------
                    if unique_id in user_profile_cache:
                        author_merged.update(user_profile_cache[unique_id])

                    is_creator_match, match_reasons = evaluate_creator_by_market(
                        market_upper, author_merged, desc
                    )

                    # 注意：在 prefer_scraping 页面滚动模式下，不能调用会触发 self._page.goto() 的方法，
                    # 否则浏览器离开当前 Hashtag 页面会导致后续滚动中断！
                    # 因此若列表流内嵌的 author 缺少 signature，我们仅通过不改变当前页面 URL 的 API 方式尝试补全。
                    if (
                        market_upper != "ALL"
                        and fetch_full_profile_on_miss
                        and unique_id not in user_profile_cache
                        and (not author_merged.get("signature") or not is_creator_match)
                    ):
                        try:
                            logger.info(f"正在通过后台接口查询博主 @{unique_id} 的主页信息 (保持当前 Hashtag 页面不跳转)...")
                            user_obj = api.user(
                                username=unique_id,
                                user_id=author_merged.get("id"),
                                sec_uid=author_merged.get("secUid"),
                            )
                            full_info_raw = await user_obj._info_full_api()
                            full_user_dict = extract_user_dict_from_info(full_info_raw)
                            if full_user_dict:
                                user_profile_cache[unique_id] = full_user_dict
                                author_merged.update(full_user_dict)
                                is_creator_match, match_reasons = evaluate_creator_by_market(
                                    market_upper, author_merged, desc
                                )
                        except Exception as usr_ex:
                            logger.debug(f"后台查询 @{unique_id} 详情未返回额外数据: {usr_ex}")
                            user_profile_cache[unique_id] = {}

                    if not is_creator_match:
                        logger.info(
                            f"[#{scanned_count}] 博主 @{unique_id} 未命中 {market_upper} 属地特征，跳过。"
                            f" (简介: {author_merged.get('signature', '')!r})"
                        )
                        continue

                    # -------------------------------------------------------
                    # 第三步：结构化提取与实时落盘
                    # -------------------------------------------------------
                    stats = v_dict.get("stats") or {}
                    video_meta = v_dict.get("video") or {}
                    duration_sec = int(float(video_meta.get("duration") or v_dict.get("duration") or 0))
                    hashtags_list = [
                        extra.get("hashtagName")
                        for extra in (v_dict.get("textExtra") or [])
                        if extra.get("hashtagName")
                    ]
                    if hashtag_clean not in [h.lower() for h in hashtags_list if h]:
                        hashtags_list.insert(0, hashtag_clean)
                    video_url = f"https://www.tiktok.com/@{unique_id}/video/{video_id}"

                    record = {
                        "market": market_upper,
                        "source_hashtag": f"#{hashtag_clean}",
                        "uniqueId": unique_id,
                        "nickname": author_merged.get("nickname", ""),
                        "user_id": str(author_merged.get("id", "")),
                        "verified": bool(author_merged.get("verified", False)),
                        "signature": author_merged.get("signature", ""),
                        "follower_count": int(author_merged.get("followerCount", 0) or 0),
                        "following_count": int(author_merged.get("followingCount", 0) or 0),
                        "creator_heart_count": int(
                            author_merged.get("heartCount", author_merged.get("heart", 0)) or 0
                        ),
                        "creator_video_count": int(author_merged.get("videoCount", 0) or 0),
                        "video_id": video_id,
                        "video_url": video_url,
                        "duration_sec": duration_sec,
                        "create_time": int(v_dict.get("createTime", 0) or 0),
                        "desc": desc,
                        "lang_confidence": lang_prob,
                        "lang_summary": lang_summary,
                        "creator_match_reasons": "; ".join(match_reasons),
                        "play_count": int(stats.get("playCount", 0) or 0),
                        "digg_count": int(stats.get("diggCount", 0) or 0),
                        "comment_count": int(stats.get("commentCount", 0) or 0),
                        "share_count": int(stats.get("shareCount", 0) or 0),
                        "collect_count": int(stats.get("collectCount", 0) or 0),
                        "hashtags": ", ".join(hashtags_list),
                    }

                    matched_records.append(record)
                    logger.info(
                        f"✅ 成功匹配第 {len(matched_records)} 条 [{market_upper} · #{hashtag_clean}] 创作者视频: "
                        f"@{unique_id} ({record['nickname']}) | 时长: {duration_sec}s | 原因: {record['creator_match_reasons']} | "
                        f"播放量: {record['play_count']} | 链接: {video_url}"
                    )

                    save_results(matched_records, output_json, output_csv)

            except NoContentException as ex:
                logger.error(f"未找到 Hashtag #{hashtag_clean} 或无内容返回: {ex}")
            except LoginException as ex:
                logger.error(f"登录状态失效或 TikTok 强制要求重新登录: {ex}")
                break
            except ConnectionDroppedException as ex:
                logger.error(
                    f"TikTok 主动断开了连接（可能触发了 IP 频率限制）: {ex}，已保存当前已抓取的 {len(matched_records)} 条结果。"
                )
            except Exception as ex:
                logger.exception(f"遍历 #{hashtag_clean} 视频流时发生未预期异常: {ex}")

    save_results(matched_records, output_json, output_csv)
    logger.info(
        f"任务完成！共扫描 {scanned_count} 条视频，筛选出 {len(matched_records)} 条 [{market_upper}] 创作者视频。\n"
        f"  - JSON 输出: {output_json.resolve()}\n"
        f"  - CSV 输出:  {output_csv.resolve()}"
    )
    return matched_records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Étoile — 基于 PyTok 抓取指定 Hashtag 下的法国 (FR) / 英国 (UK) 创作者与视频"
    )
    parser.add_argument(
        "--market",
        type=str,
        default="FR",
        choices=["FR", "UK", "ALL", "fr", "uk", "all"],
        help="目标筛选区域: FR (法国区+法语), UK (英国区+英语), ALL (全球不限)，默认: FR",
    )
    parser.add_argument(
        "--hashtag",
        type=str,
        default="fyp",
        help="目标 Hashtag 名称（无需带 #，默认: fyp）",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="最多扫描的视频数量（默认: 100）",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=4,
        help="每次 API 请求之间的基础等待秒数，防止频率限制（默认: 4）",
    )
    parser.add_argument(
        "--username",
        type=str,
        default=None,
        help="指定使用账号池中的某个账号（默认自动选用最久未使用的活跃账号）",
    )
    parser.add_argument(
        "--headless",
        type=str,
        default="false",
        choices=["false", "true", "virtual"],
        help="浏览器显示模式: false (有头窗口，推荐), true (无头), virtual (Linux Xvfb 虚拟显示)",
    )
    parser.add_argument(
        "--min-lang-prob",
        type=float,
        default=0.65,
        help="langdetect 判定为目标语言的最低概率阈值（默认: 0.65）",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default="french_creators.json",
        help="输出的 JSON 文件路径",
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default="french_creators.csv",
        help="输出的 CSV 文件路径",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.headless == "false":
        headless_mode: Any = False
    elif args.headless == "true":
        headless_mode = True
    else:
        headless_mode = "virtual"

    asyncio.run(
        scrape_creators(
            hashtag_name=args.hashtag,
            market=args.market.upper(),
            max_videos=args.count,
            request_delay=args.delay,
            headless=headless_mode,
            username=args.username,
            min_lang_prob=args.min_lang_prob,
            output_json=Path(args.output_json),
            output_csv=Path(args.output_csv),
        )
    )
