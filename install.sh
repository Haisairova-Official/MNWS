#!/usr/bin/env bash
# Convenience entry point; all installation logic lives in scripts/mnws-install.sh.
set -euo pipefail
ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"

if [ "$#" -eq 0 ]; then
    exec bash "$ROOT/scripts/mnws-install.sh"
fi
case "${1:-}" in
    -h|--help|'-?')
        echo "用法: ./install.sh"
        echo "检查依赖并安装 MNWS 配置及命令入口，保留已有配置。"
        echo "缺少依赖或组件时会询问是否安装、构建；支持 apt、pacman、dnf，Ctrl+C 取消。"
        ;;
    *)
        echo "未知参数: $1；使用 ./install.sh --help 查看帮助。" >&2
        exit 2
        ;;
esac
