#!/usr/bin/env bash
# 读取底部任务栏开关状态，输出给 waybar
if [ -f "$HOME/.local/state/taskbar-hidden" ]; then
    printf '{"text":"\uf108","class":"disabled","tooltip":"底部任务栏：已隐藏"}'
else
    printf '{"text":"\uf109","class":"enabled","tooltip":"底部任务栏：显示中"}'
fi
