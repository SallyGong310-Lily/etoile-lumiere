#!/bin/zsh
# ==============================================================================
# Étoile — Curated Creator Discovery (France / United Kingdom / Global)
# Portable launcher: resolves the project from this script's location.
# ==============================================================================
set -u

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="${ETOILE_HOME:-$(cd "$SCRIPT_DIR/.." && pwd)}"
PYTHON_BIN="${ETOILE_PYTHON:-$PROJECT_DIR/.venv/bin/python}"
OUTPUT_DIR="${ETOILE_OUTPUT_DIR:-$HOME/TikTokResearch/Étoile}"
ACCOUNT="${TIKTOK_ACCOUNT:-$USER}"

cd "$PROJECT_DIR" || exit 1

if [[ ! -x "$PYTHON_BIN" ]]; then
    osascript -e 'display alert "Étoile" message "Python environment not found.\n\nRun ./scripts/install.sh first, or set ETOILE_PYTHON." as critical'
    exit 1
fi

# 1) Choose target market
MARKET_CHOICE=$(osascript -e '
tell application "System Events"
    activate
    set marketList to {"🇫🇷 France · 法国区 (法语文案 + 法国创作者)", "🇬🇧 United Kingdom · 英国区 (英语文案 + 英国创作者)", "🌍 Global · 全球不限 (全量导出)"}
    set selectedItem to choose from list marketList with title "Étoile" with prompt "请选择本次要探索的目标区域市场：" default items {"🇫🇷 France · 法国区 (法语文案 + 法国创作者)"} OK button name "下一步" cancel button name "取消"
    if selectedItem is false then
        return "__CANCEL__"
    else
        return item 1 of selectedItem
    end if
end tell
')

if [[ "$MARKET_CHOICE" == "__CANCEL__" ]] || [[ -z "$MARKET_CHOICE" ]]; then
    exit 0
fi

if [[ "$MARKET_CHOICE" == *"France"* ]]; then
    MARKET="FR"
    MARKET_LABEL="🇫🇷 France"
    DEFAULT_TAG="blocus, rentree, octobrerose"
    TAG_HINT="支持 1 个或多个标签（逗号或空格分隔），如 blocus, rentree, octobrerose, pfw"
elif [[ "$MARKET_CHOICE" == *"United Kingdom"* ]]; then
    MARKET="UK"
    MARKET_LABEL="🇬🇧 United Kingdom"
    DEFAULT_TAG="backtoit, winterarc, autumnoutfit"
    TAG_HINT="支持 1 个或多个标签（逗号或空格分隔），如 backtoit, winterarc, autumnoutfit, vsfashionshow"
else
    MARKET="ALL"
    MARKET_LABEL="🌍 Global"
    DEFAULT_TAG="fyp"
    TAG_HINT="支持 1 个或多个 TikTok 话题标签（逗号或空格分隔，无需带 #）"
fi

# 2) Hashtags
HASHTAG=$(osascript -e '
tell application "System Events"
    activate
    try
        set userResponse to display dialog "请输入 1 个或多个 TikTok 话题标签 (Hashtag)：" & return & "当前目标市场：" & "'"$MARKET_LABEL"'" & return & "(" & "'"$TAG_HINT"'" & ")" default answer "'"$DEFAULT_TAG"'" with title "Étoile" buttons {"取消", "下一步"} default button "下一步"
        return text returned of userResponse
    on error
        return "__CANCEL__"
    end try
end tell
')

if [[ "$HASHTAG" == "__CANCEL__" ]] || [[ -z "$HASHTAG" ]]; then
    exit 0
fi

FILE_SLUG=$(echo "$HASHTAG" | sed -E 's/[#[:space:],，;]+/_/g; s/^_+//; s/_+$//' | cut -c1-45)
[[ -z "$FILE_SLUG" ]] && FILE_SLUG="multi_tags"

# 3) Sample size
COUNT=$(osascript -e '
tell application "System Events"
    activate
    try
        set userResponse to display dialog "设定每个标签扫描的视频样本数量：" default answer "80" with title "Étoile · " & "'"$MARKET"'" & " · " & "'"$HASHTAG"'" buttons {"取消", "开始探索"} default button "开始探索"
        return text returned of userResponse
    on error
        return "__CANCEL__"
    end try
end tell
')

if [[ "$COUNT" == "__CANCEL__" ]] || [[ -z "$COUNT" ]]; then
    exit 0
fi

mkdir -p "$OUTPUT_DIR"

OUTPUT_JSON="$OUTPUT_DIR/Etoile_${MARKET}_${FILE_SLUG}.json"
OUTPUT_CSV="$OUTPUT_DIR/Etoile_${MARKET}_${FILE_SLUG}.csv"
OUTPUT_XLSX="$OUTPUT_DIR/Etoile_${MARKET}_${FILE_SLUG}.xlsx"

# 4) Run in a Terminal window so progress is visible
RUNNER_SCRIPT="$PROJECT_DIR/.run_session.sh"
cat <<EOF > "$RUNNER_SCRIPT"
#!/bin/zsh
cd "$PROJECT_DIR" || exit 1
clear
echo ""
echo "  ✨  É T O I L E   —   C R E A T O R   C U R A T O R"
echo "  ──────────────────────────────────────────────────────────"
echo "  Target Market  : $MARKET_LABEL ($MARKET)"
echo "  Target Hashtag : #$HASHTAG"
echo "  Sample Depth   : $COUNT videos"
echo "  Account Pool   : $ACCOUNT"
echo "  Output Folder  : $OUTPUT_DIR"
echo "  ──────────────────────────────────────────────────────────"
echo ""

"$PYTHON_BIN" -m pytok.accounts.cli release >/dev/null 2>&1
ACTIVE_CHECK=\$("$PYTHON_BIN" -m pytok.accounts.cli list --active 2>/dev/null)

if [[ "\$ACTIVE_CHECK" == *"No accounts"* ]] || [[ -z "\$ACTIVE_CHECK" ]]; then
    echo "  [1/2] 首次运行：正在唤醒安全浏览器完成账号绑定..."
    echo "        请在弹出的窗口中登录 TikTok（仅首次需要，完成后自动继续）"
    echo ""
    "$PYTHON_BIN" -m pytok.accounts.cli login --username "$ACCOUNT" --manual-login
    ACTIVE_CHECK_AFTER=\$("$PYTHON_BIN" -m pytok.accounts.cli list --active 2>/dev/null)
    if [[ "\$ACTIVE_CHECK_AFTER" == *"No accounts"* ]] || [[ -z "\$ACTIVE_CHECK_AFTER" ]]; then
        osascript -e 'display notification "账号未完成登录，请重新打开 Étoile 重试。" with title "Étoile"'
        exit 1
    fi
fi

echo "  [2/2] 正在检索并筛选 [$MARKET_LABEL] 创作者与内容..."
echo ""

"$PYTHON_BIN" "$PROJECT_DIR/src/scrape_french_creators.py" \\
    --market "$MARKET" \\
    --hashtag "$HASHTAG" \\
    --count "$COUNT" \\
    --delay 4 \\
    --output-json "\$OUTPUT_JSON" \\
    --output-csv "\$OUTPUT_CSV"

osascript -e 'display notification "已完成 $HASHTAG ($MARKET) 的创作者筛选，正在为您打开数据表。" with title "Étoile · 采集完成" sound name "Glass"'

if [[ -f "\$OUTPUT_XLSX" ]]; then
    open -R "\$OUTPUT_XLSX"
    open "\$OUTPUT_XLSX"
elif [[ -f "\$OUTPUT_CSV" ]]; then
    open -R "\$OUTPUT_CSV"
    open "\$OUTPUT_CSV"
fi
echo ""
echo "  ✨ 采集完成，窗口将在 3 秒后自动收起..."
sleep 3
exit 0
EOF

chmod +x "$RUNNER_SCRIPT"
open -a Terminal "$RUNNER_SCRIPT"
