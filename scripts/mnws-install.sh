#!/usr/bin/env bash
# 把 MNWS 配置安装到当前运行环境（幂等，可重复执行）。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/waybar"
LOCAL_BIN="$HOME/.local/bin"

# Fail before changing any existing user files.
python3 "$ROOT/tools/mnws_health.py" --preinstall
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

python3 "$ROOT/tools/mnws_health.py" --init-desktop

for script in taskbar-toggle.sh taskbar-state.sh; do
    ln -sfn "$ROOT/scripts/$script" "$LOCAL_BIN/$script"
    chmod +x "$ROOT/scripts/$script"
    echo "已链接 ~/.local/bin/$script"
done

ln -sfn "$ROOT/tools/mnws-config.py" "$LOCAL_BIN/mnws-config"
ln -sfn "$ROOT/mnws" "$LOCAL_BIN/mnws"
chmod +x "$ROOT/mnws" "$ROOT/tools/mnws-config.py"
echo
python3 "$ROOT/tools/mnws_uninstall.py" --record
echo "安装完成。运行 mnws-config 打开统一设置；运行 mnws desktop --start（或 -s）启动桌面。"
