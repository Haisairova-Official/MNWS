#!/usr/bin/env bash
# 把 MNWS 配置安装到当前运行环境（幂等，可重复执行）。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/waybar"
LOCAL_BIN="$HOME/.local/bin"

# Offer dependency repair before changing user configuration.
if ! command -v python3 >/dev/null 2>&1; then
    echo "缺少 Python 3，是否现在安装？（Y/n/Ctrl+C）"
    read -r answer || { echo "已取消。"; exit 1; }
    case "$answer" in
        ""|y|Y)
            if command -v apt-get >/dev/null; then packages=(apt-get install python3)
            elif command -v pacman >/dev/null; then packages=(pacman -S python)
            elif command -v dnf >/dev/null; then packages=(dnf install python3)
            else echo "请使用系统软件管理器安装 Python 3.11+ 后重试。"; exit 1; fi
            if [ "$EUID" -ne 0 ]; then packages=(sudo "${packages[@]}"); fi
            "${packages[@]}" || { echo "Python 安装失败，请检查软件源后重试。"; exit 1; }
            ;;
        *) echo "已取消。"; exit 1 ;;
    esac
fi
python3 "$ROOT/tools/mnws_setup.py"
LAUNCHER="$(python3 "$ROOT/tools/mnws_launcher.py" --select)"
mkdir -p "$LOCAL_BIN" "$CONFIG_DIR"
for file in config-bottom.jsonc style-bottom.css modules.jsonc colors.css; do
    target="$CONFIG_DIR/$file"
    if [ -e "$target" ] || [ -L "$target" ]; then
        echo "保留现有配置: $target"
    else
        cp "$ROOT/config/waybar/$file" "$target"
        python3 "$ROOT/tools/mnws_uninstall.py" --record-config "$target"
        echo "已安装默认配置: $target"
    fi
done

python3 "$ROOT/tools/mnws_launcher.py" --apply "$CONFIG_DIR/modules.jsonc" "$LAUNCHER"
python3 "$ROOT/tools/mnws_health.py" --init-desktop

python3 "$ROOT/tools/mnws_commands.py"
python3 "$ROOT/tools/mnws_uninstall.py" --record
"$ROOT/mnws" -v
echo "安装完成。运行 mnws-config 打开统一设置；运行 mnws desktop --start（或 -s）启动桌面。"
