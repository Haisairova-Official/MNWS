#!/usr/bin/env bash
# 切换底部任务栏显示/隐藏，并刷新 waybar 开关图标
marker="$HOME/.local/state/taskbar-hidden"
mkdir -p "$(dirname "$marker")"

if [ -f "$marker" ]; then
    rm -f "$marker"
else
    touch "$marker"
fi

pkill -USR1 -f '[c]onfig-bottom.jsonc'
sleep 0.3
pkill -RTMIN+10 waybar
