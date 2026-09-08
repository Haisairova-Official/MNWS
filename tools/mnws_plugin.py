#!/usr/bin/env python3
"""mnws-plugin — .mplg 插件包工具（drop-in 模式）

.mplg = zip，内含 plugin.json 与本体实现。把 .mplg 直接丢进插件目录即可被
MNWS 扫描加载，不需要“安装/注册”。规范见 docs/mplg-spec.md。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

MANIFEST = "plugin.json"
API_NAME = "mnws-plugin"
API_VERSION = 1

KINDS = {"panel", "desktop", "menu", "utility"}
LANGUAGES = {"python", "shell", "binary"}
INTERFACES = {"panel.json-v1", "panel.rows-v1", "desktop.json-v1"}
SLOTS = {"left", "center", "right"}

ID_RE = re.compile(r"^[a-z0-9]+(?:\.[a-z0-9]+)*$")
VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")

PACK_EXTRA = {".pyc", ".pyo", "__pycache__"}
SKIP_DIRS = {"__pycache__", ".git", ".mypy_cache", ".pytest_cache"}

EXAMPLE_PLUGIN_JSON = '''{
  "api": "mnws-plugin",
  "apiVersion": 1,
  "id": "org.mnws.hello",
  "name": "Hello",
  "version": "0.1.0",
  "kind": "panel",
  "language": "python",
  "entry": "main.py",
  "interfaces": ["panel.json-v1"],
  "author": "",
  "description": "任务栏示例插件（panel.json-v1）",
  "license": "MIT",
  "defaults": {
    "slot": "right",
    "width": 0,
    "interval": 1.0
  }
}
'''

EXAMPLE_MAIN_PY = '''#!/usr/bin/env python3
"""MNWS panel.json-v1 示例插件。

--output-json  向 stdout 打印一行 JSON（宿主要求）
--click <键>    处理点击（可选，可空实现）
"""
import argparse
import json
from datetime import datetime


def render() -> dict:
    now = datetime.now()
    return {
        "text": "\\U0001f44b",
        "alt": "hello",
        "class": "normal",
        "tooltip": "Hello MNWS\\n%s" % now.strftime("%Y-%m-%d %H:%M:%S"),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="MNWS panel plugin")
    parser.add_argument("--output-json", action="store_true")
    parser.add_argument("--click", choices=("left", "right", "middle",
                                            "scroll-up", "scroll-down"))
    args = parser.parse_args(argv)
    if args.click:
        return 0  # 示例插件不响应点击
    payload = render()
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def plugin_dir() -> Path:
    """扫描目录：用户把 .mplg 直接丢进来。"""
    override = os.environ.get("MNWS_PLUGIN_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".local/share/mnws/plugins"


def cache_dir() -> Path:
    """运行缓存：zip 里的入口没法直接执行，宿主按需解包到这里。"""
    override = os.environ.get("MNWS_CACHE_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".cache/mnws/plugins"


def scan_packages(folder: Path | None = None) -> list[Path]:
    folder = folder or plugin_dir()
    if not folder.is_dir():
        return []
    return sorted(path for path in folder.glob("*.mplg") if path.is_file())


def archive_name(manifest: dict) -> str:
    return "%s_%s.mplg" % (manifest["id"], manifest["version"])


def safe_members(names: list[str]) -> list[str]:
    members = []
    for raw in names:
        name = raw.replace("\\", "/")
        if not name or name.startswith("/") or ".." in Path(name).parts:
            continue
        members.append(name)
    return sorted(set(members))


def validate_manifest(manifest, members: set[str] | None = None) -> list[str]:
    errors = []
    if not isinstance(manifest, dict):
        return ["plugin.json 必须是 JSON 对象"]
    if manifest.get("api") != API_NAME:
        errors.append('api 必须为 "%s"' % API_NAME)
    if manifest.get("apiVersion") != API_VERSION:
        errors.append("apiVersion 必须为 %d" % API_VERSION)
    for key in ("id", "name", "version", "kind", "language", "entry"):
        if not isinstance(manifest.get(key), str) or not manifest[key].strip():
            errors.append("缺少字符串字段 %s" % key)
    if not errors:
        if not ID_RE.fullmatch(manifest["id"]):
            errors.append("id 必须为小写反向域名风格，如 org.mnws.hello")
        if not VERSION_RE.fullmatch(manifest["version"]):
            errors.append("version 必须为 主.次.修订 或带 -pre 后缀")
        if manifest["kind"] not in KINDS:
            errors.append("kind 必须是 %s 之一" % ", ".join(sorted(KINDS)))
        if manifest["language"] not in LANGUAGES:
            errors.append("language 必须是 %s 之一" % ", ".join(sorted(LANGUAGES)))
        entry = manifest["entry"]
        if entry.startswith("/") or ".." in Path(entry).parts:
            errors.append("entry 必须是包内相对路径，禁止绝对路径或 ..")
        if members is not None and entry not in members:
            errors.append("entry %r 不在包内" % entry)
    interfaces = manifest.get("interfaces")
    if interfaces is not None:
        if not isinstance(interfaces, list) or not all(
            isinstance(item, str) for item in interfaces
        ):
            errors.append("interfaces 必须是字符串数组")
        else:
            unknown = sorted(set(interfaces) - INTERFACES)
            if unknown:
                errors.append("未知接口: %s" % ", ".join(unknown))
    defaults = manifest.get("defaults")
    if defaults is not None:
        if not isinstance(defaults, dict):
            errors.append("defaults 必须是对象")
        else:
            slot = defaults.get("slot")
            if slot is not None and slot not in SLOTS:
                errors.append("defaults.slot 必须是 left/center/right")
    return errors


def load_manifest(path: Path) -> dict:
    if not path.is_file() or path.suffix.lower() != ".mplg":
        raise ValueError("不是 .mplg 文件: %s" % path)
    try:
        with zipfile.ZipFile(path) as archive:
            raw = archive.read(MANIFEST)
    except (KeyError, zipfile.BadZipFile) as exc:
        raise ValueError("无法读取 %s: %s" % (MANIFEST, exc))
    try:
        return json.loads(raw.decode("utf-8"))
    except ValueError as exc:
        raise ValueError("plugin.json 不是合法 JSON: %s" % exc)


def validate_package(path: Path) -> tuple[bool, list[str], dict | None]:
    if not path.is_file() or path.suffix.lower() != ".mplg":
        return False, ["不是 .mplg 文件"], None
    errors = []
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            members = []
            for info in infos:
                name = info.filename.replace("\\", "/")
                if info.is_dir():
                    continue
                members.append(name)
                if name.startswith("/") or ".." in Path(name).parts:
                    errors.append("非法路径: %s" % info.filename)
            if MANIFEST not in members:
                return False, ["包内缺少 plugin.json"], None
            if errors:
                return False, errors, None
            try:
                manifest = json.loads(archive.read(MANIFEST).decode("utf-8"))
            except (ValueError, KeyError) as exc:
                return False, ["plugin.json 无法解析：%s" % exc], None
            errors = validate_manifest(manifest, members=set(members))
            if errors:
                return False, errors, manifest
            if sum(info.file_size for info in infos) > 200 * 1024 * 1024:
                return False, ["包超过 200 MiB 上限"], manifest
            return True, [], manifest
    except zipfile.BadZipFile:
        return False, ["不是合法 zip"], None


def collect_source_files(source: Path) -> list[str]:
    files = []
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(source)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if rel.suffix in PACK_EXTRA or path.name == MANIFEST + ".tmp":
            continue
        files.append(str(rel).replace(os.sep, "/"))
    return files


def build_package(source: Path, output: Path | None = None) -> Path:
    source = source.resolve()
    if not (source / MANIFEST).is_file():
        raise SystemExit("错误：%s 下找不到 plugin.json" % source)
    try:
        manifest = json.loads((source / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit("错误：plugin.json 无法解析：%s" % exc)
    files = collect_source_files(source)
    errors = validate_manifest(manifest, members=set(files))
    if errors:
        raise SystemExit("校验失败：\n" + "\n".join(" - " + item for item in errors))
    if output is None:
        output = source.parent / archive_name(manifest)
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        staged = Path(tmp) / "pkg"
        staged.mkdir()
        for name in files:
            target = staged / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / name, target)
        temp_zip = staged.with_suffix(".mplg")
        with zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as archive:
            for name in collect_source_files(staged):
                archive.write(staged / name, arcname=name)
        shutil.move(str(temp_zip), str(output))
    return output


def materialize(path: Path, cache: Path | None = None) -> Path:
    """把 .mplg 解包到缓存并返回入口目录；zip 更新后自动重建。"""
    ok, errors, manifest = validate_package(path)
    if not ok:
        raise ValueError("；".join(errors))
    manifest = load_manifest(path)
    cache = cache or cache_dir()
    dest = cache / manifest["id"] / manifest["version"]
    stamp = dest / ".mnws-stamp.json"
    try:
        mtime = path.stat().st_mtime
    except OSError as exc:
        raise ValueError("无法读取 %s: %s" % (path, exc))
    fresh = False
    if stamp.is_file():
        try:
            data = json.loads(stamp.read_text(encoding="utf-8"))
            fresh = data.get("mtime") == mtime and data.get("size") == path.stat().st_size
        except (OSError, ValueError):
            fresh = False
    if fresh:
        return dest
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(path) as archive:
            for name in safe_members([info.filename for info in archive.infolist()]):
                if archive.getinfo(name).is_dir():
                    continue
                target = dest / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(name) as src, open(target, "wb") as out:
                    shutil.copyfileobj(src, out)
        entry = dest / manifest["entry"]
        if entry.is_file():
            os.chmod(entry, 0o755)
        stamp.write_text(json.dumps({
            "source": str(path.resolve()),
            "mtime": mtime,
            "size": path.stat().st_size,
            "id": manifest["id"],
            "version": manifest["version"],
        }, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        shutil.rmtree(dest, ignore_errors=True)
        raise
    return dest


def copy_into(folder: Path, path: Path, replace: bool = True) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / path.name
    if target.exists() and not replace:
        raise FileExistsError("%s 已存在" % target)
    shutil.copy2(path, target)
    return target


def cmd_init(args) -> int:
    target = Path(args.directory).expanduser().resolve()
    if target.exists() and any(target.iterdir()):
        print("错误：目录非空：%s" % target, file=sys.stderr)
        return 2
    target.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^a-z0-9]", "", target.name.lower())
    pkg_id = args.id or ("org.mnws." + stem if stem else "org.mnws.plugin")
    manifest = json.loads(EXAMPLE_PLUGIN_JSON)
    manifest["id"] = pkg_id
    if args.name:
        manifest["name"] = args.name
    (target / MANIFEST).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (target / "main.py").write_text(EXAMPLE_MAIN_PY, encoding="utf-8")
    (target / "README.md").write_text(
        "# %s\n\nMNWS %s 插件。运行 `mnws mplg build %s` 打包，\n"
        "然后把生成的 .mplg 丢到 `mnws mplg dir` 显示的文件夹即可。\n"
        % (manifest["name"], manifest["kind"], target), encoding="utf-8"
    )
    print("已创建插件源：%s" % target)
    print("打包：mnws mplg build %s" % target)
    return 0


def cmd_build(args) -> int:
    source = Path(args.source).expanduser().resolve()
    if not source.is_dir():
        print("错误：目录不存在：%s" % source, file=sys.stderr)
        return 2
    output = Path(args.output).expanduser().resolve() if args.output else None
    try:
        built = build_package(source, output)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print("已打包：%s" % built)
    print("把它丢进 %s 即可被 MNWS 扫描加载。" % plugin_dir())
    return 0


def cmd_validate(args) -> int:
    path = Path(args.package).expanduser().resolve()
    ok, errors, manifest = validate_package(path)
    if ok:
        print("OK：%s  %s %s" % (path, manifest["id"], manifest["version"]))
        return 0
    print("无效：%s" % path, file=sys.stderr)
    for item in errors:
        print(" - %s" % item, file=sys.stderr)
    return 1


def cmd_inspect(args) -> int:
    path = Path(args.package).expanduser().resolve()
    ok, errors, _ = validate_package(path)
    if not ok:
        print("无效：%s" % path, file=sys.stderr)
        for item in errors:
            print(" - %s" % item, file=sys.stderr)
        return 1
    print(json.dumps(load_manifest(path), ensure_ascii=False, indent=2))
    return 0


def cmd_dir(_args) -> int:
    print(plugin_dir())
    return 0


def cmd_add(args) -> int:
    path = Path(args.package).expanduser().resolve()
    ok, errors, _ = validate_package(path)
    if not ok:
        print("无效：%s" % path, file=sys.stderr)
        for item in errors:
            print(" - %s" % item, file=sys.stderr)
        return 1
    target = copy_into(plugin_dir(), path)
    print("已放入扫描目录：%s" % target)
    return 0


def cmd_remove(args) -> int:
    folder = plugin_dir()
    target = folder / args.filename
    if not target.is_file():
        print("不存在：%s" % target, file=sys.stderr)
        return 1
    target.unlink()
    print("已删除：%s" % target)
    return 0


def cmd_list(_args) -> int:
    folder = plugin_dir()
    if not folder.is_dir():
        print("（插件目录尚不存在：%s）" % folder)
        return 0
    files = scan_packages(folder)
    if not files:
        print("（空：把 .mplg 丢到 %s）" % folder)
        return 0
    for path in files:
        ok, errors, manifest = validate_package(path)
        if ok:
            print("%s  %-12s v%-9s %s  %s" % (
                "OK ", manifest["kind"], manifest["version"],
                manifest["name"], path.name))
        else:
            print("ERR %-17s %s  (%s)" % ("?", "?", path.name, errors[0]))
    return 0


def resolve_package(ref: str) -> Path:
    """ref 可以是 .mplg 路径，也可以是目录里的包 id 或文件名。"""
    candidate = Path(ref).expanduser()
    if candidate.is_file():
        return candidate.resolve()
    folder = plugin_dir()
    for path in scan_packages(folder):
        if path.name == ref:
            return path
        try:
            manifest = load_manifest(path)
        except ValueError:
            continue
        if manifest["id"] == ref:
            return path
    raise SystemExit("找不到 .mplg：%s（目录：%s）" % (ref, folder))


def cmd_run(args) -> int:
    try:
        path = resolve_package(args.ref)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 1
    ok, errors, _ = validate_package(path)
    if not ok:
        print("无效：%s" % path, file=sys.stderr)
        for item in errors:
            print(" - %s" % item, file=sys.stderr)
        return 1
    try:
        root = materialize(path)
        manifest = load_manifest(path)
    except ValueError as exc:
        print("准备运行失败：%s" % exc, file=sys.stderr)
        return 1
    if manifest["language"] != "python":
        print("当前 run 仅支持 python 插件", file=sys.stderr)
        return 1
    script = root / manifest["entry"]
    command = [sys.executable, str(script), "--output-json"]
    try:
        result = subprocess.run(command, cwd=script.parent, capture_output=True,
                                text=True, timeout=float(args.timeout))
    except (OSError, subprocess.TimeoutExpired) as exc:
        print("运行失败：%s" % exc, file=sys.stderr)
        return 1
    if result.returncode != 0:
        print("退出码 %d：%s" % (result.returncode, result.stderr.strip()),
              file=sys.stderr)
        return result.returncode or 1
    print(result.stdout.strip())
    return 0


def arguments(argv=None):
    parser = argparse.ArgumentParser(
        prog="mnws-plugin",
        description=".mplg 插件包工具：init / build / validate / 目录扫描",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="生成插件源脚手架")
    p.add_argument("directory")
    p.add_argument("--id", help="插件 id（默认 org.mnws.<目录名>）")
    p.add_argument("--name", help="显示名")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("build", help="把插件目录打包成 .mplg")
    p.add_argument("source")
    p.add_argument("-o", "--output", help="输出路径")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("validate", help="校验 .mplg")
    p.add_argument("package")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("inspect", help="查看 .mplg 的 plugin.json")
    p.add_argument("package")
    p.set_defaults(func=cmd_inspect)

    p = sub.add_parser("dir", help="打印插件扫描目录")
    p.set_defaults(func=cmd_dir)

    p = sub.add_parser("add", help="把一个 .mplg 复制进扫描目录")
    p.add_argument("package")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("remove", help="从扫描目录删除文件")
    p.add_argument("filename")
    p.set_defaults(func=cmd_remove)

    p = sub.add_parser("list", help="列出扫描目录中的 .mplg")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("run", help="试跑已就位的 .mplg（--output-json）")
    p.add_argument("ref", help=".mplg 路径 / 文件名 / 包 id")
    p.add_argument("--timeout", default=10.0)
    p.set_defaults(func=cmd_run)

    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = arguments(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
