# Changelog / 更新记录

## 1.2 — 2026-09-09

### 中文

- 修复隐藏桌面图标后右键失效：隐藏时保留简化菜单，可显示图标、打开终端或桌面文件夹。
- 普通菜单新增打开终端；退出项红色悬停，并增加确认弹窗与可复制的恢复命令。
- 桌面和任务栏统一支持 `--start/-s`、`--stop/-S`、`--kill/-k`、`--restart/-r`。
- 新增 `--debug/-d` 前台日志及 `-1` 到 `-6` 六级过滤，默认 `-4`；记录菜单、打开请求、弹窗响应及窗口操作。
- `mnws --status` 同时显示两个组件的状态；组件级 `--status` 可单独查询。
- 启动成功保持安静；帮助支持 `-h`、`--help`、`-?`，集中展示用法、命令、选项和示例。
- 保持 Niri 支持范围；MHWS 分支的 Hyprland 适配仍未开始。

### English

- Keep a minimal desktop context menu available while icons are hidden, with actions to show icons, open a terminal and open the desktop folder.
- Add a terminal action to the regular menu, a red exit hover state, and exit confirmation with a copyable recovery command.
- Unify desktop/taskbar controls: `--start/-s`, `--stop/-S`, `--kill/-k` and `--restart/-r`.
- Add foreground debugging with `--debug/-d` and six verbosity levels (`-1` through `-6`, default `-4`), covering menu actions, launch requests, dialog responses and window operations.
- Add global `mnws --status` alongside per-component status queries.
- Make successful starts silent; provide compact help through `-h`, `--help` and `-?`.
- This release targets Niri. Hyprland adaptation on MHWS has not started.

### Validation / 验证

- 19 command and lyrics tests passed / 19 项命令与歌词测试通过。
- 6 isolated GTK desktop regression tests passed / 6 项隔离 GTK 桌面回归测试通过。
- Rust taskbar release build passed / Rust 任务栏发布编译通过。
- Live global status and silent-start checks passed / 实机总览状态与静默启动检查通过。

This is a source release. Rebuild the taskbar module when updating to enable its new operation logs.
本次为源码发布；升级时需重新编译任务栏模块，才能使用新增的任务栏操作日志。
