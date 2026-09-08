"""Regression: open/save preserves a mixed builtin/plugin order."""
import copy
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import mnws_layout_gui as gui
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

manifest = json.loads((ROOT / "plugins/netease-lyrics/plugin.json").read_text())
ids = ["test.zfirst", "test.alast", "test.center"]
packages = []
for package_id in ids:
    item = copy.deepcopy(manifest)
    item["id"] = package_id
    packages.append({"ok": True, "manifest": item, "file": Path("/tmp") / (package_id + ".mplg")})
gui.scan_available_plugins = lambda: packages

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "layout.json"
    data = {
        "builtins": [
            {"id": "start", "slot": "left", "order": 0, "enabled": True},
            {"id": "windows", "slot": "left", "order": 1, "enabled": True},
            {"id": "workspaces", "slot": "right", "order": 1, "enabled": True},
            {"id": "clock", "slot": "right", "order": 2, "enabled": True},
        ],
        "plugins": [
            {"package": ids[0], "slot": "right", "order": 0, "enabled": True, "settings": {"primary_color": "#123456"}},
            {"package": ids[1], "slot": "right", "order": 3, "enabled": True},
            {"package": ids[2], "slot": "center", "order": 0, "enabled": True},
        ],
    }
    path.write_text(json.dumps(data))
    app = gui.LayoutWindow(str(path))
    expected = ["start", "windows", ids[2], ids[0], "workspaces", "clock", ids[1]]
    stable = None
    for _ in range(5):
        assert [row["key"] for row in app.rows] == expected
        saved = app.collect_layout()
        if stable is not None:
            assert saved == stable
        stable = saved
        assert next(item for item in saved["plugins"] if item["package"] == ids[0])["settings"] == {"primary_color": "#123456"}
        path.write_text(json.dumps(saved))
        app.reload()
    row = next(row for row in app.rows if row["key"] == ids[1])
    app.move_row(row, -1)
    assert [row["key"] for row in app.rows][-2:] == [ids[1], "clock"]
    row["widgets"]["slot"].set_active_id("center")
    assert [r["key"] for r in app.rows if r["slot"] == "center"] == [ids[2], ids[1]]
    app.move_row(row, -1)
    assert [r["key"] for r in app.rows if r["slot"] == "center"] == [ids[1], ids[2]]
    expected = [r["key"] for r in app.rows]
    path.write_text(json.dumps(app.collect_layout()))
    app.reload()
    assert [r["key"] for r in app.rows] == expected
    app.window.disconnect_by_func(Gtk.main_quit)
    app.window.destroy()
print("Mixed order survived five open/save cycles, cross-type moves, and section changes.")
