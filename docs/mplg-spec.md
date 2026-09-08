# MPlg 插件包规范（MNWS Plugin Package）

> 版本：v1 草案
> 状态：任务栏 `panel` 接口已定稿；桌面 `desktop` 接口随桌面宿主演进

## 1. 一句话定义

`.mplg` 本质上就是一个 **zip 压缩包**，包内至少包含：

```text
my-plugin.mplg
├── plugin.json      # 清单（唯一必需元数据）
├── main.py          # 本体实现（示例，接口见下文）
├── assets/          # 可选：图标、字体等资源
└── README.md        # 可选
```

MNWS 不规定开发者必须用任何特定语言；v1 提供 Python 面板插件接口，
同时保留 `shell` / `binary` / 未来原生 GTK 的位置，由 `plugin.json` 声明。

## 2. plugin.json 清单

```json
{
  "api": "mnws-plugin",
  "apiVersion": 1,

  "id": "org.mnws.hello",
  "name": "Hello",
  "version": "0.1.0",
  "kind": "panel",

  "language": "python",
  "entry": "main.py",
  "interfaces": ["panel.json-v1"],

  "author": "akizuki",
  "description": "任务栏示例插件",
  "license": "MIT",

  "defaults": {
    "slot": "right",
    "width": 0,
    "interval": 1.0
  }
}
```

### 2.1 字段

| 字段 | 必需 | 说明 |
| --- | --- | --- |
| `api` | 是 | 固定 `"mnws-plugin"` |
| `apiVersion` | 是 | 当前为 `1` |
| `id` | 是 | 反向域名风格，小写：`org.mnws.hello` |
| `name` | 是 | 显示名 |
| `version` | 是 | `主.次.修订`，可带 `-pre` 后缀 |
| `kind` | 是 | `panel` / `desktop` / `menu` / `utility` |
| `language` | 是 | `python` / `shell` / `binary` |
| `entry` | 是 | 相对包根的入口文件，禁止绝对路径与 `..` |
| `interfaces` | 推荐 | 声明实现的宿主接口（见 §3） |
| `author` / `email` / `homepage` | 否 | 开发者信息 |
| `description` | 否 | 人类可读说明 |
| `license` | 否 | SPDX 许可证标识 |
| `defaults` | 否 | 宿主安装时的默认参数（可被用户在设置里覆盖） |

### 2.2 defaults 约定

- `slot`：`left` / `center` / `right`（面板位置）。
- `width`：像素宽，`0` 表示自适应。
- `interval`：刷新秒数；`0` 表示事件驱动/不自动刷新。
- 其余键属于插件私有配置，宿主会原样透传给插件。

## 3. 接口

### 3.1 `panel.json-v1`（当前可用）

插件入口通过命令行参数运行，往 **stdout 输出一行 JSON**：

```bash
python3 <插件目录>/main.py --output-json
```

输出示例：

```json
{"text":"👋","alt":"hello","class":"normal","tooltip":"Hello MNWS"}
```

支持的键：

| 键 | 说明 |
| --- | --- |
| `text` | 显示文本（支持 Pango 标记） |
| `tooltip` | 悬浮提示 |
| `class` | CSS 类名，可切换状态样式 |
| `alt` | 备用状态，宿主可用它做样式分支 |

交互（点击/滚轮）由宿主统一接走；后续接口版本会增加
`--click left|right|middle|scroll-up|scroll-down` 交互模式，
当前 v1 只约定输出 JSON 的只读状态。

### 3.2 `desktop.json-v1`（规划中）

桌面小组件接口。MNWS 桌面层未来用进程外渲染或受限 GTK 容器托管；
KDE Plasma 原生 `.plasmoid` 无法被 Python GTK 宿主直接加载，见 §6。

## 4. 命名与安装位置

- 构建产物：`<id>_<version>.mplg`，例如 `org.mnws.hello_0.1.0.mplg`。
- 安装目录（可用环境变量 `MNWS_PLUGIN_DIR` 覆盖）：

```text
~/.local/share/mnws/plugins/
├── installed.json            # 注册表
├── archives/                 # 原始 .mplg 归档
└── packages/<id>/<version>/  # 解包后的本体
```

- 插件只能写自己的包目录；不得在安装/更新时执行入口以外的代码。

## 5. 任务栏组件模型

任务栏不再把“开始按钮 / 工作区 / 窗口图标 / 时钟”当成魔法配置，而是统一的
**内置组件表**，每个组件都有 `slot` 与 `order`：

| 内置 id | 显示名 | 默认位置 |
| --- | --- | --- |
| `start` | 开始按钮 | 左 |
| `workspaces` | 工作区 | 左（默认关闭，由用户开启） |
| `windows` | 窗口图标（任务栏本体） | 左 |
| `clock` | 时钟 | 右 |

布局状态保存在 `taskbar-layout.json`：

```json
{
  "apiVersion": 1,
  "items": [
    {"id": "start", "slot": "left", "order": 0, "enabled": true},
    {"id": "windows", "slot": "left", "order": 1, "enabled": true},
    {"id": "clock", "slot": "right", "order": 0, "enabled": true}
  ],
  "plugins": [
    {"package": "org.mnws.hello", "slot": "right", "order": 1,
     "enabled": false, "width": 0, "settings": {}}
  ]
}
```

设置应用只改这份状态；宿主适配层根据它生成实际运行配置。

## 6. KDE 桌面小组件的现实约束

KDE Plasma 6 的 plasmoid 是 QML + Plasma 框架组件，要求宿主提供
`plasmoid` 上下文并实现 Plasma shell 协议。它不是“能嵌入任意 GTK 桌面”的格式：

- MNWS 桌面层（GTK3）**不能**直接加载 `.plasmoid`。
- 可行的三条路线：
  1. `plasmoidviewer --applet <id>` 单独跑一个普通窗口，再由 niri 固定为桌面浮窗
     （体验最弱，无背景层语义，窗口会参与焦点/平铺管理）；
  2. 用 KDE Frameworks 6 + QtQuick 写一个独立 plasmoid 宿主进程，走
     `gtk-layer-shell` 之外的 Plasma 层协议（工程量大，属独立子项目）；
  3. MNWS 自定义 `desktop.json-v1`：插件用 Python/GTK 实现，桌面层原生托管
     （社区插件生态从零开始，但体验与当前架构一致）。

MNWS 对 KDE 的“兼容”先定义为第 3 条 + 可选的菜单/图标走 KDE 应用
（kclock/korganizer 等），不伪装成能直接吃掉 plasmoid。

## 7. 设置与双行渲染扩展

插件可在清单中声明 `settingsSchema` 数组，每项包含 `key`、`label`、`type`、`default`，
当前设置界面支持 `font`、`color`、`choice`、`number`、`url`、`string`。
配置保存在布局条目的 `settings` 中；移动、保存布局时保留所有键。
声明 schema 的插件收到 `--settings-json '<JSON>'`，可据此更改行为。

`panel.rows-v1` 在 `panel.json-v1` 基础上增加纯文本 `primary` 和 `secondary` 字段。
适配器通过 `libmnws_panel.so` 将它们显示为原生 GTK 双行，自动省略过长文本。
`secondary` 为空时隐藏译文和分隔线。渲染器读取 `font_family`、`primary_color`、
`secondary_color`、`separator_color` 设置，留空继承主题。字体随实时分配高度测量，始终保持 3:2。
