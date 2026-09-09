"""Start and stop MNWS components without matching unrelated command lines."""
import argparse
import os
from pathlib import Path
import signal
import subprocess
import time
import sys

ROOT = Path(__file__).resolve().parent.parent


def matches(component, argv):
    if not argv:
        return False
    name = Path(argv[0]).name
    if component == "desktop":
        script = argv[1] if name.startswith("python") and len(argv) > 1 else argv[0]
        return Path(script).name == "desktop-layer" and "--preview" not in argv
    if name != "waybar":
        return False
    for i, arg in enumerate(argv):
        value = argv[i + 1] if arg in ("-c", "--config") and i + 1 < len(argv) else arg.removeprefix("--config=") if arg.startswith("--config=") else ""
        if value and Path(value).name == "config-bottom.jsonc":
            return True
    return False


def pids(component):
    result = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if entry.stat().st_uid != os.getuid():
                continue
            argv = (entry / 'cmdline').read_bytes().decode(errors='replace').rstrip('\0').split('\0')
            if matches(component, argv):
                result.append(int(entry.name))
        except OSError:
            continue
    return result



def help_text(component=None):
    title = "MNWS — My Niri Workspace Solution"
    if component:
        commands = ""
        usage = f"mnws {component} <选项>"
    else:
        usage = "mnws <命令> [选项]"
        commands = """全局选项：
  --status             同时查看桌面和任务栏状态

命令：
  desktop              管理桌面图标和桌面右键菜单
  taskbar              管理底部任务栏
  config               打开设置（--tab desktop|taskbar|components）
  check                检查组件与配置状态
  install              安装配置和命令入口
  autostart            桌面登录自启：on / off / status
  layout               组件布局：show / render / apply / gui
  mplg                 插件管理：init / build / add / list / run / validate
  build-taskbar        编译并安装任务栏模块
  restart              重启组件：desktop / taskbar
  help                 显示此帮助

"""
    target = component or "desktop"
    return f"""{title}
用法：{usage}

{commands}组件选项（desktop / taskbar；每次选择一项）：
  -s, --start           后台启动；已运行时不重复启动
  -S, --stop            正常停止
  -k, --kill            强制结束
  -r, --restart         正常停止后重新启动
  -d, --debug           在当前终端运行并输出日志；Ctrl+C 结束
      --status          查询运行状态与 PID
  -h, --help, -?        显示帮助

日志级别（仅用于 --debug，默认 -4）：
  -1 致命   -2 错误   -3 警告   -4 信息   -5 调试   -6 跟踪

示例：
  mnws {target} -s
  mnws {target} -d -6
  mnws {target} --status

启动成功不输出提示；失败时输出错误。
调试模式先停止旧实例；结束后用 -s 恢复后台运行。
停止 desktop 后桌面右键失效；--status 未运行时返回 1。
"""


class HelpParser(argparse.ArgumentParser):
    def format_help(self):
        return help_text(self.component_help)

def main(argv=None, quiet=False):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv == ["--status"]:
        return max(main(["desktop", "--status"]), main(["taskbar", "--status"]))
    parser = HelpParser(prog="mnws", add_help=False)
    parser.component_help = argv[0] if argv and argv[0] in ('desktop', 'taskbar') else None
    parser.add_argument('-h', '--help', '-?', action='help')
    parser.add_argument('component', choices=('desktop', 'taskbar'))
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--start', '-s', action='store_true')
    action.add_argument('--stop', '-S', action='store_true')
    action.add_argument('--kill', '-k', action='store_true')
    action.add_argument('--debug', '-d', action='store_true', help='在当前终端运行并输出调试日志')
    action.add_argument('--status', action='store_true', help='查询运行状态')
    action.add_argument('--restart', '-r', action='store_true', help='正常停止后重新启动')
    verbosity = parser.add_mutually_exclusive_group()
    for level in range(1, 7):
        verbosity.add_argument(f'-{level}', dest='log_level', action='store_const', const=level,
                               help=('致命', '错误', '警告', '信息（默认）', '调试', '跟踪')[level - 1])
    args = parser.parse_args(argv)
    if args.log_level is not None and not args.debug:
        parser.error('-1 到 -6 仅用于 --debug/-d')
    level = args.log_level or 4
    targets = pids(args.component)
    if args.status:
        print(f'{args.component}: ' + ('运行中，PID: ' + ', '.join(map(str, targets)) if targets else '未运行'))
        return 0 if targets else 1
    if args.debug or args.restart:
        env = dict(os.environ)
        env.pop('GDK_BACKEND', None)
        if args.debug:
            env['PYTHONUNBUFFERED'] = '1'
            env['MNWS_LOG_LEVEL'] = str(level)
            env.pop('MNWS_PANEL_DEBUG', None)
            if args.component == 'desktop':
                command = [str(ROOT / 'src/niri-desktop-layer/desktop-layer'), '--debug', '--log-level', str(level)]
                options = {}
                for pid in targets:
                    try:
                        running = (Path('/proc') / str(pid) / 'cmdline').read_bytes().decode().rstrip('\0').split('\0')
                        for flag in ('--state', '--config', '--directory', '--monitor'):
                            if flag in running:
                                options[flag] = running[running.index(flag) + 1]
                        break
                    except (OSError, ValueError, IndexError):
                        continue
                options.setdefault('--state', str(ROOT / 'src/niri-desktop-layer/state/layout.json'))
                for flag, value in options.items():
                    command.extend([flag, value])
            else:
                folder = Path.home() / '.config/waybar'
                config, style = folder / 'config-bottom.jsonc', folder / 'style-bottom.css'
                if not config.is_file() or not style.is_file():
                    parser.exit(1, '缺少任务栏配置，请先运行 mnws install。\n')
                command = ['waybar', '-c', str(config), '-s', str(style), '-l', ('critical', 'error', 'warning', 'info', 'debug', 'trace')[level - 1]]
                env['RUST_LOG'] = ('off', 'error', 'warn', 'info', 'debug', 'trace')[level - 1]
                if level >= 5:
                    env['MNWS_PANEL_DEBUG'] = '1'
        if targets:
            if main([args.component, '--stop'], quiet=True) != 0:
                return 1
        if args.restart:
            return main([args.component, '--start'])
        try:
            os.execvpe(command[0], command, env)
        except OSError as error:
            parser.exit(1, f'调试启动失败：{error}\n')
        return 0
    if args.start:
        if targets:
            return 0
        if args.component == 'desktop':
            env = dict(os.environ)
            env.pop('GDK_BACKEND', None)
            return subprocess.call([str(ROOT / 'src/niri-desktop-layer/start-desktop-layer')], env=env, stdout=subprocess.DEVNULL)
        folder = Path.home() / '.config/waybar'
        config, style = folder / 'config-bottom.jsonc', folder / 'style-bottom.css'
        if not config.is_file() or not style.is_file():
            parser.exit(1, '缺少任务栏配置，请先运行 mnws install。\n')
        env = dict(os.environ)
        env.pop('GDK_BACKEND', None)
        try:
            child = subprocess.Popen(['waybar', '-c', str(config), '-s', str(style)], env=env,
                                     start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as error:
            parser.exit(1, f'启动失败：{error}\n')
        time.sleep(.3)
        if child.poll() is not None:
            parser.exit(1, '任务栏启动后退出，请检查 Waybar 配置和模块。\n')
        return 0
    for pid in targets:
        try:
            os.kill(pid, signal.SIGKILL if args.kill else signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + 3
    while set(targets) & set(pids(args.component)):
        if time.monotonic() >= deadline:
            parser.exit(1, '组件尚未退出，可使用 --kill / -k 强制结束。\n')
        time.sleep(.05)
    if not quiet:
        print('组件已停止。' if targets else '组件未运行。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
