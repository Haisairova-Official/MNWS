# Changelog / 更新记录

## 1.23 H — 2026-09-09

### 中文

- 帮助新增版本、构建日期、更新摘要。（B）
- 防止隐藏图标后的右键失效；顺便新增终端入口与退出确认。我觉得是个好功能。（C）
- 统一组件启停、状态查询及六级日志。（D）
- 移除了Koha D
- 提升了超级牛力。（E）
- 优化了安装逻辑，修复了一箩筐的bug（1.21）
- 简化了install，并直接在程序中添加了uninstall选项。（F）
- 优化了安装逻辑，启动器我之前忘记配置了。我的错。（1.22）
- 优化了任务栏菜单。（G）
- 优化了命令行参数处理逻辑。（H）

### English

- Add version, build date and update summaries to help. (B)
- Fix the context menu when desktop icons are hidden; add a terminal entry and exit confirmation. I think it is a nice feature. (C)
- Unify component start/stop controls, status queries and six logging levels. (D)
- Remove Koha D.
- Increase Super Cow Powers. (E)
- Improve installation logic and fix a basketful of bugs. (1.21)
- Simplify install and add an uninstall option directly to the program. (F)
- Improve installation logic: I forgot to configure the launcher earlier. My mistake. (1.22)
- Improve the taskbar menu. (G)
- Improve command-line argument handling. (H)

### 本次改动 / Changes in this version

- 组件与短、长操作参数支持前后互换；省略组件时，启动、停止、强制结束、重启及状态查询作用于桌面和任务栏。调试仍需指定单个组件。
- Accept component names before or after short and long operation options. Without a component, start, stop, kill, restart and status target both desktop and taskbar. Debugging still requires a single component.

### 验证 / Validation

- 56 项测试通过，包含参数顺序、一键启动、无效参数拒绝及命令入口转发。
- 56 tests passed, including argument ordering, starting both components, invalid-argument rejection and command dispatch.

## 1.22 G — 2026-09-09

### 中文

- 帮助新增版本、构建日期、更新摘要。（B）
- 防止隐藏图标后的右键失效；顺便新增终端入口与退出确认。我觉得是个好功能。（C）
- 统一组件启停、状态查询及六级日志。（D）
- 移除了Koha D
- 提升了超级牛力。（E）
- 优化了安装逻辑，修复了一箩筐的bug（1.21）
- 简化了install，并直接在程序中添加了uninstall选项。（F）
- 优化了安装逻辑，启动器我之前忘记配置了。我的错。（1.22）
- 优化了任务栏菜单。（G）

### English

- Add version, build date and update summaries to help. (B)
- Fix the context menu when desktop icons are hidden; add a terminal entry and exit confirmation. I think it is a nice feature. (C)
- Unify component start/stop controls, status queries and six logging levels. (D)
- Remove Koha D.
- Increase Super Cow Powers. (E)
- Improve installation logic and fix a basketful of bugs. (1.21)
- Simplify install and add an uninstall option directly to the program. (F)
- Improve installation logic: I forgot to configure the launcher earlier. My mistake. (1.22)
- Improve the taskbar menu. (G)

### 本次改动 / Changes in this version

- 开始按钮支持自定义文字与字符图标、读取当前内容、预览及自动选择发行版 Logo（需要 Nerd Fonts / Font Logos 字体支持）。
- 命令优先链接到 PATH 中的 ~/.local/bin，否则询问安装到 /usr/local/bin；保护同名程序，卸载核对链接归属，不修改终端配置。
- Customize the start button text or glyph, load its current content, preview it, and select a distribution logo (requires Nerd Fonts / Font Logos).
- Link commands into ~/.local/bin when on PATH, otherwise offer /usr/local/bin; preserve unrelated commands and verify link ownership during uninstall without editing shell configuration.

### 验证 / Validation

- 52 项测试通过；发行版识别、回退图标与启动命令保留检查通过。未完成 GUI 视觉验证。
- 52 tests passed; distribution detection, fallback glyph and launcher-command preservation checks passed. GUI visual verification remains outstanding.

## 1.22 F — 2026-09-09

### 中文

- 帮助新增版本、构建日期、更新摘要。（B）
- 防止隐藏图标后的右键失效；顺便新增终端入口与退出确认。我觉得是个好功能。（C）
- 统一组件启停、状态查询及六级日志。（D）
- 移除了Koha D
- 提升了超级牛力。（E）
- 优化了安装逻辑，修复了一箩筐的bug（1.21）
- 简化了install，并直接在程序中添加了uninstall选项。（F）
- 优化了安装逻辑，启动器我之前忘记配置了。我的错。（1.22）

### English

- Add version, build date and update summaries to help. (B)
- Fix the context menu when desktop icons are hidden; add a terminal entry and exit confirmation. I think it is a nice feature. (C)
- Unify component start/stop controls, status queries and six logging levels. (D)
- Remove Koha D.
- Increase Super Cow Powers. (E)
- Improve installation logic and fix a basketful of bugs. (1.21)
- Simplify install and add an uninstall option directly to the program. (F)
- Improve installation logic: I forgot to configure the launcher earlier. My mistake. (1.22)

### 安装流程 / Installation flow

- 缺少运行依赖或组件时询问是否补齐或构建，完成后重新检查；自动补齐支持 apt、pacman、dnf，拒绝或取消时停止。
- Offer to install missing runtime dependencies or build components, then check again. Automatic dependency installation supports apt, pacman and dnf; declining or cancelling stops installation.

### 验证 / Validation

- 48 项测试通过，包括启动器优先级、自定义命令、取消、安装成功与失败、配置备份。包管理器使用模拟测试，未实际安装系统软件。
- 48 tests passed, covering launcher priority, custom commands, cancellation, installation success/failure and configuration backups. Package manager calls were mocked; no system packages were installed.

## 1.21 F — 2026-09-09

### 中文

- 帮助新增版本、构建日期、更新摘要。（B）
- 防止隐藏图标后的右键失效；顺便新增终端入口与退出确认。我觉得是个好功能。（C）
- 统一组件启停、状态查询及六级日志。（D）
- 移除了Koha D
- 提升了超级牛力。（E）
- 优化了安装逻辑，修复了一箩筐的bug（1.21）
- 简化了install，并直接在程序中添加了uninstall选项。（F）

### English

- Add version, build date and update summaries to help. (B)
- Fix the context menu when desktop icons are hidden; add a terminal entry and exit confirmation. I think it is a nice feature. (C)
- Unify component start/stop controls, status queries and six logging levels. (D)
- Remove Koha D.
- Increase Super Cow Powers. (E)
- Improve installation logic and fix a basketful of bugs. (1.21)
- Simplify install and add an uninstall option directly to the program. (F)

### 验证 / Validation

- 35 项安装、命令、歌词、彩蛋与卸载测试通过；卸载在临时目录中验证。
- 72 项桌面回归测试通过；Rust 任务栏编译通过。
- 未完成全新发行版虚拟机验证；安装仍需要手动准备依赖和构建组件，命令入口仍依赖源码目录。
- 35 installation, CLI, lyrics, easter-egg and uninstall tests passed, with uninstall tests isolated in temporary directories.
- 72 desktop regression tests and the Rust taskbar build passed.
- No fresh-distribution VM validation yet. Dependencies and component builds remain manual; launchers still require the source checkout.

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
