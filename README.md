> **声明：本 Repo 使用大量 vibe coding，可能不适合所有人。**
>
> **Notice: This repository makes extensive use of vibe coding and may not be suitable for everyone.**

> **MHWS 分支状态：尚未开始 Hyprland 适配。** 当前代码与创建分支时的 MNWS 基线相同，仍面向 Niri；本分支暂不提供 Hyprland 支持。下方功能与安装说明目前适用于 Niri。
>
> **MHWS branch status: Hyprland adaptation has not started.** The code is still the MNWS baseline from when this branch was created and targets Niri. This branch does not yet provide Hyprland support. The features and installation instructions below currently apply to Niri.

# MNWS — My Niri Workspace Solution

**A simpler desktop solution for Niri.**

[中文](#中文) · [English](#english)

## 中文

MNWS 为 Niri 整合桌面图标、底部任务栏、统一设置与插件，让日常桌面操作更简单。
它仍在持续开发，当前主要在 Niri/Shorin 26.04 环境验证；尚未完成不同发行版与上游 Niri 的兼容性验证。

### 功能

- **桌面图标层**：桌面文件展示、选择、拖动排序、文件操作及外观设置。
- **底部任务栏**：窗口图标随内容增长，空间不足时滚动；支持右键菜单，桌面与任务栏可独立显示或隐藏。
- **布局设置**：内置组件与用户插件可混合排序、放入左/中/右分区；中间分区对齐整条任务栏中心。设置窗口以浮动形式打开。
- **插件系统**：通过 `.mplg` 包分发插件，支持插件自带设置；长名称自动省略，操作按钮保持可见。
- **网易云歌词**：读取 Firefox 的 MPRIS 媒体会话，同步当前歌词。双语上下居中，原文与译文字号比为 3:2，中间以细线分隔，字号根据任务栏实时高度计算。支持字体、颜色、同步偏移和自定义歌词 API。

### 环境要求

- Linux、Niri，以及支持 CFFI v2 的 Waybar。
- Python 3.11+、PyGObject（GTK 3/Gio）、PyCairo、Pillow、gtk-layer-shell；文件管理集成使用 Thunar。
- Rust 1.87+ / Cargo、C 编译器、Make、pkg-config，以及 GTK 3、gtk-layer-shell、json-glib 开发文件。
- 桌面启动器使用 systemd 用户服务；默认应用菜单使用 Rofi，可在 `modules.jsonc` 修改。
- 歌词插件需要 Firefox 启用 MPRIS 并正在播放 `music.163.com` 的音乐。

任务栏使用随仓库提供的 `vendor/niri-ipc`，来自 Niri/Shorin 26.04 的本地源码快照，包含最小化等扩展接口。其他 Niri 版本可能需要适配。

### 构建与安装

这是源码集成项目，安装脚本不会自动安装系统依赖。先备份现有 Waybar 配置，再安装上述依赖。
以下命令均在仓库根目录执行。更新已有安装时，先停止底部 Waybar，再替换它加载的动态库。

```sh
git clone https://github.com/Haisairova-Official/MNWS.git
cd MNWS

cargo build --release --manifest-path src/niri-taskbar/Cargo.toml
make -C src/panel-rows
cc -shared -fPIC -O2 src/niri-desktop-layer/integration/waybar-space.c \
  -o src/niri-desktop-layer/integration/libwaybar-space.so \
  $(pkg-config --cflags --libs gtk+-3.0 gtk-layer-shell-0)

mkdir -p "$HOME/.local/lib/waybar"
install -m644 src/niri-taskbar/target/release/libniri_taskbar.so "$HOME/.local/lib/waybar/"
install -m644 src/panel-rows/libmnws_panel.so "$HOME/.local/lib/waybar/"
install -m644 src/niri-desktop-layer/integration/libwaybar-space.so "$HOME/.local/lib/waybar/"

./mnws install
./mnws layout apply --restart
./mnws config
```

`mnws install` 将启动器链接到 `~/.local/bin`，将底栏配置和样式链接到本仓库。
已有的普通底栏配置文件会先复制进仓库；共享的 `modules.jsonc` 和 `colors.css` 仅在缺失时安装。
如果使用已有共享配置，请确保它定义了 `custom/applauncher`、`niri/workspaces` 和 `clock`。
安装后应保留仓库目录，并把 `~/.local/bin` 加入 `PATH`。

将 [config/mnws-windows.kdl](config/mnws-windows.kdl) 中的窗口规则加入 Niri 配置，使设置窗口浮动。
用 `niri validate` 检查配置。启动桌面图标层：

```sh
./src/niri-desktop-layer/start-desktop-layer
./mnws autostart on
```

第二条命令开启桌面图标层登录自启；任务栏自启需加入你自己的会话启动配置。

### 使用与插件

```sh
./mnws check
./mnws config
./mnws layout show
./mnws layout render
./mnws layout apply --restart
./mnws mplg build plugins/netease-lyrics
./mnws mplg list
```

将打包命令生成的 `.mplg` 放到 `~/.local/share/mnws/plugins/`，在“组件与插件”中启用、调整位置并应用。
布局优先读取 `~/.config/mnws/taskbar-layout.json`，否则使用仓库默认配置。

网易云歌词默认不需要 API Key，也不读取浏览器登录信息。公开接口可能变化；匹配失败或没有同步歌词时，插件无法显示同步文本。
可在插件设置中指定自定义 GET API、LRC 文本或 JSON 字段路径。

详见 [歌词插件说明](plugins/netease-lyrics/README.md)、[插件规范](docs/mplg-spec.md) 与 [桌面图标层说明](src/niri-desktop-layer/README.md)。部分组件文档保留开发阶段说明，以本页的安装流程为准。

### 许可证

MNWS 原创代码采用 **GNU GPL v3.0 或更新版本（GPL-3.0-or-later）**。
第三方及独立许可组件保留原许可证与版权声明；请参阅 [LICENSE](LICENSE) 和 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## English

MNWS brings desktop icons, a bottom taskbar, unified settings and plugins to Niri, making everyday desktop interaction simpler.
It is under active development and has mainly been tested with Niri/Shorin 26.04. Compatibility across distributions and upstream Niri has not yet been verified.

### Features

- **Desktop icons:** display desktop files, select items, rearrange icons, perform file actions and customize appearance.
- **Bottom taskbar:** window icons grow with their content and scroll when space runs out. Context menus and independent desktop/taskbar visibility are supported.
- **Layout settings:** mix built-in components and user plugins in a persistent order across left, center and right sections. The center section aligns with the whole taskbar. Settings open as floating windows.
- **Plugins:** distribute plugins as `.mplg` packages with their own settings. Long names are ellipsized while action buttons remain visible.
- **NetEase lyrics:** follow Firefox's MPRIS session and display synchronized lyrics. Bilingual lines are centered with a 3:2 original/translation font-size ratio and a thin separator. Font sizes follow the actual taskbar height. Font, colors, timing offset and a custom lyrics API are configurable.

### Requirements

- Linux, Niri and Waybar with CFFI v2 support.
- Python 3.11+, PyGObject (GTK 3/Gio), PyCairo, Pillow and gtk-layer-shell. File-manager integration uses Thunar.
- Rust 1.87+ / Cargo, a C compiler, Make, pkg-config and development files for GTK 3, gtk-layer-shell and json-glib.
- The desktop launcher uses a systemd user service. The default application menu uses Rofi; change it in `modules.jsonc` if needed.
- Lyrics require Firefox with MPRIS enabled and music playing on `music.163.com`.

The taskbar uses the bundled `vendor/niri-ipc`, a local source snapshot from Niri/Shorin 26.04 with extensions such as window minimization. Other Niri versions may require changes.

### Build and install

This is a source integration project. The installer does not install system dependencies.
Back up your Waybar configuration, install the dependencies above, then run the build and installation commands in the [Chinese section](#构建与安装) from the repository root.
For an existing installation, stop the bottom Waybar before replacing its loaded shared libraries.

`mnws install` links launchers into `~/.local/bin` and links the bottom bar's configuration and stylesheet to this checkout.
Existing regular bottom-bar configuration files are copied into the checkout first. Shared `modules.jsonc` and `colors.css` files are installed only when missing.
If keeping existing shared configuration, make sure it defines `custom/applauncher`, `niri/workspaces` and `clock`.
Keep the checkout after installation and add `~/.local/bin` to your `PATH`.

Add the rules in [config/mnws-windows.kdl](config/mnws-windows.kdl) to your Niri configuration to make settings windows float, then check with `niri validate`.
Start the desktop icon layer with `./src/niri-desktop-layer/start-desktop-layer`.
Use `./mnws autostart on` to enable desktop-icon autostart; add taskbar startup to your own session configuration separately.

### Usage and plugins

Use `./mnws config` for settings, `./mnws check` for status and `./mnws layout apply --restart` to apply the layout.
Build the lyrics plugin with `./mnws mplg build plugins/netease-lyrics`.
Place the resulting `.mplg` file in `~/.local/share/mnws/plugins/`, then enable and position it in the components/plugins window and apply.
The layout is read from `~/.config/mnws/taskbar-layout.json` when present, otherwise from the repository default.

The default lyrics service needs no API key and does not read browser credentials.
Public endpoints can change, and synchronized text is unavailable when matching fails or timed lyrics are missing.
Plugin settings support a custom GET API returning LRC text or configurable JSON fields.

See the [lyrics plugin guide](plugins/netease-lyrics/README.md), [plugin specification](docs/mplg-spec.md) and [desktop icon guide](src/niri-desktop-layer/README.md).
These component guides are currently primarily in Chinese and may contain development-era notes; use this README for installation.

### License

Original MNWS code is licensed under **GNU GPL version 3 or any later version (GPL-3.0-or-later)**.
Third-party and separately licensed components retain their own licenses and copyright notices.
See [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Development checks / 开发检查

```sh
python3 -m unittest discover -s tests -p 'test_netease_lyrics.py'
xvfb-run -a env GDK_BACKEND=x11 python3 tests/check_plugin_settings_gui.py
xvfb-run -a env GDK_BACKEND=x11 python3 tests/check_layout_order_gui.py
make -C src/panel-rows check
```

GUI checks require Xvfb. These checks do not replace testing in a real Niri session.
