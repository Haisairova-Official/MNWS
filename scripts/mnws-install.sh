#!/usr/bin/env bash
# 把 MNWS 配置安装到当前运行环境（幂等，可重复执行）。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR="$HOME/.config/waybar"
LOCAL_BIN="$HOME/.local/bin"

mkdir -p "$LOCAL_BIN" "$CONFIG_DIR"
for shared in modules.jsonc colors.css; do
    if [ ! -e "$CONFIG_DIR/$shared" ]; then
        cp "$ROOT/config/waybar/$shared" "$CONFIG_DIR/$shared"
    fi
done

# 底部任务栏专属配置：让 ~/.config/waybar 里的文件指向 MNWS 真源。
# colors.css / modules.jsonc 与顶部 waybar 共用，暂不接管，避免影响顶部。
for file in config-bottom.jsonc style-bottom.css; do
    target="$CONFIG_DIR/$file"
    if [ -L "$target" ] && [ "$(readlink -f "$target")" = "$ROOT/config/waybar/$file" ]; then
        echo "已是最新: $file"
    else
        if [ -e "$target" ] && [ ! -L "$target" ]; then
            cp -a "$target" "$ROOT/config/waybar/$file"
            echo "已备份当前 $file 内容到 MNWS/config/waybar/"
        fi
        ln -sfn "$ROOT/config/waybar/$file" "$target"
        echo "已链接 $file -> MNWS"
    fi
done

for script in taskbar-toggle.sh taskbar-state.sh; do
    ln -sfn "$ROOT/scripts/$script" "$LOCAL_BIN/$script"
    chmod +x "$ROOT/scripts/$script"
    echo "已链接 ~/.local/bin/$script"
done

ln -sfn "$ROOT/tools/mnws-config.py" "$LOCAL_BIN/mnws-config"
ln -sfn "$ROOT/mnws" "$LOCAL_BIN/mnws"
chmod +x "$ROOT/mnws" "$ROOT/tools/mnws-config.py"
echo
echo "安装完成。运行 mnws-config 打开统一设置；运行 mnws desktop --start（或 -s）启动桌面。"
