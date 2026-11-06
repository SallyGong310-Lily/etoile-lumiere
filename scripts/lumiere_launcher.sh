#!/bin/zsh
# ==============================================================================
# Lumière — Deep Video Structure & Cultural Trend Studio
# Portable launcher: resolves the project from this script's location.
# ==============================================================================
set -u

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="${LUMIERE_HOME:-$(cd "$SCRIPT_DIR/.." && pwd)}"
PYTHON_BIN="${LUMIERE_PYTHON:-$PROJECT_DIR/.venv/bin/python}"
OUTPUT_DIR="${LUMIERE_OUTPUT_DIR:-$HOME/TikTokResearch/Lumière_视频深析}"

cd "$PROJECT_DIR" || exit 1

if [[ ! -x "$PYTHON_BIN" ]]; then
    osascript -e 'display alert "Lumière" message "Python environment not found.\n\nRun ./scripts/install.sh first, or set LUMIERE_PYTHON." as critical'
    exit 1
fi

# 1) Analysis mode
MODE_CHOICE=$(osascript -e '
tell application "System Events"
    activate
    set modeList to {"⚖️ 视频对比深析", "🎬 单条/多条精选视频自由深析（粘贴任意视频链接）"}
    set selectedItem to choose from list modeList with title "Lumière · 光影深析工坊" with prompt "请选择本次视频结构与文化趋势拆解模式：" default items {"⚖️ 视频对比深析"} OK button name "下一步" cancel button name "取消"
    if selectedItem is false then
        return "__CANCEL__"
    else
        return item 1 of selectedItem
    end if
end tell
')

if [[ "$MODE_CHOICE" == "__CANCEL__" ]] || [[ -z "$MODE_CHOICE" ]]; then
    exit 0
fi

DEFAULT_URL_1=""
DEFAULT_URL_2=""

if [[ "$MODE_CHOICE" == *"视频对比深析"* ]]; then
    URL_1=$(osascript -e '
    tell application "System Events"
        activate
        try
            set userResponse to display dialog "【视频 1】请粘贴第一条对比视频链接：" default answer "'"$DEFAULT_URL_1"'" with title "Lumière · 视频对比深析 (1/2)" buttons {"取消", "下一步"} default button "下一步"
            return text returned of userResponse
        on error
            return "__CANCEL__"
        end try
    end tell
    ')
    if [[ "$URL_1" == "__CANCEL__" ]] || [[ -z "$URL_1" ]]; then
        exit 0
    fi

    URL_2=$(osascript -e '
    tell application "System Events"
        activate
        try
            set userResponse to display dialog "【视频 2】请粘贴第二条对比视频链接：" default answer "'"$DEFAULT_URL_2"'" with title "Lumière · 视频对比深析 (2/2)" buttons {"取消", "开始深度拆解"} default button "开始深度拆解"
            return text returned of userResponse
        on error
            return "__CANCEL__"
        end try
    end tell
    ')
    if [[ "$URL_2" == "__CANCEL__" ]] || [[ -z "$URL_2" ]]; then
        exit 0
    fi

    URLS_ARG="V1:${URL_1} V2:${URL_2}"
else
    RAW_URLS=$(osascript -e '
    tell application "System Events"
        activate
        try
            set userResponse to display dialog "请粘贴视频链接（多条用空格或逗号分隔）：" default answer "'"$DEFAULT_URL_1"'" with title "Lumière · 单条/多条精选视频自由深析" buttons {"取消", "开始深度拆解"} default button "开始深度拆解"
            return text returned of userResponse
        on error
            return "__CANCEL__"
        end try
    end tell
    ')
    if [[ "$RAW_URLS" == "__CANCEL__" ]] || [[ -z "$RAW_URLS" ]]; then
        exit 0
    fi
    URLS_ARG="$RAW_URLS"
fi

# 2) Run in a Terminal window so progress is visible
RUNNER_SCRIPT="$PROJECT_DIR/.run_lumiere.sh"
cat <<EOF > "$RUNNER_SCRIPT"
#!/bin/zsh
cd "$PROJECT_DIR" || exit 1
clear
echo ""
echo "  🎞️  L U M I È R E   —   V I D E O   &   T R E N D   S T U D I O"
echo "  ──────────────────────────────────────────────────────────────────"
echo "  Analysis Scope : Content Style · Structure · Audience · Tone"
echo "                   Visuals · Engagement · Culture · Trend"
echo "  Output Folder  : $OUTPUT_DIR"
echo "  ──────────────────────────────────────────────────────────────────"
echo ""

"$PYTHON_BIN" -m pytok.accounts.cli release >/dev/null 2>&1
mkdir -p "$OUTPUT_DIR"

"$PYTHON_BIN" "$PROJECT_DIR/src/lumiere_analyzer.py" \\
    --urls "$URLS_ARG" \\
    --out-dir "$OUTPUT_DIR" \\
    --comments 20

LATEST_XLSX=\$(ls -t "$OUTPUT_DIR"/Lumière_Task1_视频深度分析报表_*.xlsx 2>/dev/null | head -n 1)
LATEST_STORYBOARD=\$(find "$OUTPUT_DIR" -name "Storyboard_*.png" -type f -print0 2>/dev/null | xargs -0 ls -t 2>/dev/null | head -n 1)

osascript -e 'display notification "已完成视频原片下载、5阶段分镜抽帧与八大维度拆解！" with title "Lumière · 深析完成" sound name "Glass"'

if [[ -n "\$LATEST_STORYBOARD" ]] && [[ -f "\$LATEST_STORYBOARD" ]]; then
    open "\$LATEST_STORYBOARD"
fi

if [[ -n "\$LATEST_XLSX" ]] && [[ -f "\$LATEST_XLSX" ]]; then
    open -R "\$LATEST_XLSX"
    open "\$LATEST_XLSX"
fi

echo ""
echo "  ✨ 拆解完成！原片 MP4、分镜故事板与分析报表已保存至："
echo "     $OUTPUT_DIR"
echo "  窗口将在 3 秒后自动收起..."
sleep 3
exit 0
EOF

chmod +x "$RUNNER_SCRIPT"
open -a Terminal "$RUNNER_SCRIPT"
