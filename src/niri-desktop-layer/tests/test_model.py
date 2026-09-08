"""Run with /usr/bin/python3 -m unittest discover -s tests -v (no display)."""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from gi.repository import Gio, GLib

from desktop_layer.model import (
    EntryLaunchError,
    UntrustedLauncher,
    arrange_grid,
    atomic_save_json,
    desktop_directory,
    launch_entry,
    scan_desktop,
)


class DesktopModelTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.desktop = self.root / "Desktop"
        self.desktop.mkdir()

    def launcher(self, name="app.desktop", contents=None):
        path = self.desktop / name
        path.write_text(contents or "[Desktop Entry]\nType=Application\nName=Example\nExec=/bin/true\n", encoding="utf-8")
        return path

    def test_scan_never_runs_exec(self):
        marker = self.root / "must-not-exist"
        self.launcher(contents=f'[Desktop Entry]\nType=Application\nName=Untrusted\nExec=/bin/sh -c "touch {marker}"\n')
        entries = scan_desktop(self.desktop)
        self.assertEqual(len(entries), 1)
        self.assertIsNone(entries[0].error)
        self.assertEqual(entries[0].kind, "application")
        self.assertFalse(marker.exists())

    def test_names_are_localized_by_glib(self):
        self.launcher(contents="[Desktop Entry]\nType=Application\nName=English\nName[zh_CN]=本地化名称\nExec=/bin/true\n")
        code = "from pathlib import Path; from desktop_layer.model import scan_desktop; import sys; print(scan_desktop(Path(sys.argv[1]))[0].name)"
        environment = dict(os.environ, LANGUAGE="zh_CN", LANG="zh_CN.UTF-8", LC_ALL="zh_CN.UTF-8")
        result = subprocess.run(
            [sys.executable, "-c", code, str(self.desktop)],
            cwd=Path(__file__).resolve().parents[1], env=environment,
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(result.stdout.strip(), "本地化名称")

    def test_invalid_launchers_remain_visible_with_errors(self):
        samples = {
            "syntax.desktop": "not a desktop file",
            "missing-name.desktop": "[Desktop Entry]\nType=Application\nExec=/bin/true\n",
            "missing-exec.desktop": "[Desktop Entry]\nType=Application\nName=No command\n",
            "bad-type.desktop": "[Desktop Entry]\nType=Device\nName=Device\n",
            "bad-boolean.desktop": "[Desktop Entry]\nType=Application\nName=Bad bool\nHidden=maybe\nExec=/bin/true\n",
            "unsafe-link.desktop": "[Desktop Entry]\nType=Link\nName=Unsafe\nURL=javascript:alert(1)\n",
            "relative-link.desktop": "[Desktop Entry]\nType=Link\nName=Relative\nURL=file:relative/path\n",
            "malformed-link.desktop": "[Desktop Entry]\nType=Link\nName=Malformed\nURL=https:///missing-host\n",
        }
        for name, contents in samples.items():
            self.launcher(name, contents)
        entries = scan_desktop(self.desktop)
        self.assertEqual({entry.path.name for entry in entries}, set(samples))
        for entry in entries:
            with self.subTest(path=entry.path.name):
                self.assertTrue(entry.error)
                with self.assertRaises(EntryLaunchError):
                    launch_entry(entry)

    def test_hidden_metadata_and_dot_files(self):
        self.launcher("hidden.desktop", "[Desktop Entry]\nHidden=true\n")
        self.launcher("nodisplay.desktop", "[Desktop Entry]\nNoDisplay=true\n")
        (self.desktop / ".hidden.txt").write_text("hidden")
        (self.desktop / "visible.txt").write_text("visible")
        self.assertEqual([entry.path.name for entry in scan_desktop(self.desktop)], ["visible.txt"])
        self.assertEqual({entry.path.name for entry in scan_desktop(self.desktop, show_hidden=True)}, {"visible.txt", ".hidden.txt"})

    def test_symlinked_applications_folders_and_broken_links(self):
        applications = self.root / "share" / "applications"
        applications.mkdir(parents=True)
        installed = self.launcher()
        installed.rename(applications / "app.desktop")
        (self.desktop / "app.desktop").symlink_to(applications / "app.desktop")
        (self.desktop / "broken.txt").symlink_to(self.root / "missing")
        (self.desktop / "broken.desktop").symlink_to(self.root / "missing.desktop")
        (self.desktop / "linked-folder").symlink_to(applications, target_is_directory=True)
        entries = {entry.path.name: entry for entry in scan_desktop(self.desktop)}
        self.assertIsNone(entries["app.desktop"].error)
        self.assertEqual(entries["app.desktop"].path, self.desktop / "app.desktop")
        self.assertEqual(entries["linked-folder"].kind, "directory")
        self.assertTrue(entries["broken.txt"].error)
        self.assertTrue(entries["broken.desktop"].error)

        app = Mock()
        app.launch.return_value = True
        with patch.object(GLib, "get_user_data_dir", return_value=str(self.root / "share")), patch.object(GLib, "get_system_data_dirs", return_value=[]), patch.object(Gio.DesktopAppInfo, "new_from_filename", return_value=app):
            self.assertTrue(launch_entry(entries["app.desktop"]))
        app.launch.assert_called_once_with([], None)

    def test_directory_with_desktop_suffix_is_a_directory(self):
        (self.desktop / "folder.desktop").mkdir()
        entry = scan_desktop(self.desktop)[0]
        self.assertEqual(entry.kind, "directory")
        self.assertIsNone(entry.error)

    def test_untrusted_launcher_requires_consent_without_chmod(self):
        path = self.launcher()
        path.chmod(0o600)
        original_mode = path.stat().st_mode
        entry = scan_desktop(self.desktop)[0]
        app = Mock()
        app.launch.return_value = True
        with patch.object(Gio.DesktopAppInfo, "new_from_filename", return_value=app):
            with self.assertRaises(UntrustedLauncher):
                launch_entry(entry)
            app.launch.assert_not_called()
            self.assertTrue(launch_entry(entry, allow_untrusted=True))
        app.launch.assert_called_once_with([], None)
        self.assertEqual(path.stat().st_mode, original_mode)

    def test_executable_launcher_launches_through_gio(self):
        path = self.launcher()
        path.chmod(0o700)
        entry = scan_desktop(self.desktop)[0]
        app = Mock()
        app.launch.return_value = True
        context = Mock()
        with patch.object(Gio.DesktopAppInfo, "new_from_filename", return_value=app):
            self.assertTrue(launch_entry(entry, context))
        app.launch.assert_called_once_with([], context)

    def test_rechecks_launcher_after_edit(self):
        path = self.launcher()
        entry = scan_desktop(self.desktop)[0]
        path.write_text("[Desktop Entry]\nType=Link\nName=Changed\nURL=javascript:alert(1)\n")
        with patch.object(Gio.AppInfo, "launch_default_for_uri") as launch:
            with self.assertRaises(EntryLaunchError):
                launch_entry(entry, allow_untrusted=True)
            launch.assert_not_called()

    def test_link_uses_gio_and_preserves_escaped_uri(self):
        self.launcher(contents="[Desktop Entry]\nType=Link\nName=Web\nURL=https://example.org/a%20b?q=hello\n")
        entry = scan_desktop(self.desktop)[0]
        self.assertIsNone(entry.error)
        self.assertEqual(entry.kind, "link")
        with patch.object(Gio.AppInfo, "launch_default_for_uri", return_value=True) as launch:
            self.assertTrue(launch_entry(entry))
        launch.assert_called_once_with("https://example.org/a%20b?q=hello", None)

    def test_executable_script_opens_as_text(self):
        path = self.desktop / "script"
        path.write_text("#!/bin/sh\nprintf unsafe\n")
        path.chmod(0o700)
        entry = scan_desktop(self.desktop)[0]
        editor = Mock()
        editor.launch.return_value = True
        with patch.object(Gio.AppInfo, "get_default_for_type", return_value=editor) as lookup, patch.object(Gio.AppInfo, "launch_default_for_uri") as default_launch:
            self.assertTrue(launch_entry(entry))
        lookup.assert_called_once_with("text/plain", False)
        default_launch.assert_not_called()
        self.assertEqual(editor.launch.call_args.args[0][0].get_path(), str(path))

    def test_script_without_editor_does_not_fall_back_to_execution(self):
        path = self.desktop / "script.sh"
        path.write_text("#!/bin/sh\nprintf unsafe\n")
        path.chmod(0o700)
        entry = scan_desktop(self.desktop)[0]
        with patch.object(Gio.AppInfo, "get_default_for_type", return_value=None), patch.object(Gio.AppInfo, "launch_default_for_uri") as launch:
            with self.assertRaises(EntryLaunchError):
                launch_entry(entry)
            launch.assert_not_called()

    def test_binary_is_passed_to_file_handler_not_executed(self):
        path = self.desktop / "example.AppImage"
        path.write_bytes(b"\x7fELF\x00\x02" + bytes(128))
        path.chmod(0o700)
        entry = scan_desktop(self.desktop)[0]
        with patch.object(Gio.AppInfo, "launch_default_for_uri", return_value=True) as launch:
            self.assertTrue(launch_entry(entry))
        launch.assert_called_once_with(path.as_uri(), None)

    def test_missing_desktop_is_empty_and_not_created(self):
        missing = self.root / "not-created"
        self.assertEqual(scan_desktop(missing), [])
        self.assertFalse(missing.exists())

    def test_xdg_desktop_fallback_does_not_expose_home(self):
        with patch.object(GLib, "get_user_special_dir", return_value=str(Path.home())):
            self.assertEqual(desktop_directory(), Path.home() / "Desktop")
        with patch.object(GLib, "get_user_special_dir", return_value=None):
            self.assertEqual(desktop_directory(), Path.home() / "Desktop")
        with patch.object(GLib, "get_user_special_dir", return_value=str(self.root / "桌面")):
            self.assertEqual(desktop_directory(), self.root / "桌面")


class GridTests(unittest.TestCase):
    def test_new_icons_fill_down_columns(self):
        self.assertEqual(arrange_grid(["a", "b", "c", "d"], {}, 2, 3), {"a": (0, 0), "b": (0, 1), "c": (0, 2), "d": (1, 0)})

    def test_saved_cells_reserved_before_automatic_placement(self):
        self.assertEqual(arrange_grid(["a", "b"], {"b": [0, 0]}, 2, 2), {"a": (0, 1), "b": (0, 0)})

    def test_collisions_invalid_cells_and_removed_keys(self):
        keys = ["a", "b", "c", "d", "e", "f", "g"]
        saved = {"a": [1, 1], "b": [1, 1], "c": [-1, 0], "d": [2, 0], "e": [True, 0], "f": [1], "g": "0,0", "removed": [0, 0]}
        positions = arrange_grid(keys, saved, 2, 4)
        self.assertEqual(positions["a"], (1, 1))
        self.assertEqual(positions["b"], (0, 0))
        self.assertEqual(len(positions), len(keys))
        self.assertEqual(len(set(positions.values())), len(keys))
        self.assertTrue(all(0 <= column < 2 and 0 <= row < 4 for column, row in positions.values()))
        self.assertEqual(positions, arrange_grid(keys, saved, 2, 4))

    def test_overflow_duplicates_and_empty_capacity(self):
        self.assertEqual(arrange_grid(["a", "a", "b", "c"], {}, 1, 2), {"a": (0, 0), "b": (0, 1)})
        self.assertEqual(arrange_grid(["a"], {}, 0, 1), {})
        self.assertEqual(arrange_grid(["a"], {}, 1, 0), {})


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_json_is_private_atomic_and_unicode(self):
        path = self.root / "state" / "layout.json"
        atomic_save_json(path, {"桌面": [1, 2]})
        self.assertEqual(json.loads(path.read_text()), {"桌面": [1, 2]})
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
        atomic_save_json(path, {"new": [0, 0]})
        self.assertEqual(json.loads(path.read_text()), {"new": [0, 0]})
        self.assertEqual(list(path.parent.iterdir()), [path])

    def test_failed_serialization_preserves_saved_layout(self):
        path = self.root / "layout.json"
        atomic_save_json(path, {"saved": [0, 0]})
        before = path.read_bytes()
        with self.assertRaises(TypeError):
            atomic_save_json(path, {"bad": object()})
        self.assertEqual(path.read_bytes(), before)

    def test_failed_replace_cleans_temporary_file(self):
        path = self.root / "layout.json"
        atomic_save_json(path, {"saved": [0, 0]})
        before = path.read_bytes()
        with patch("desktop_layer.model.os.replace", side_effect=OSError("simulated failure")):
            with self.assertRaises(OSError):
                atomic_save_json(path, {"new": [1, 1]})
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(list(self.root.iterdir()), [path])

    def test_existing_symlink_is_replaced_without_touching_target(self):
        target = self.root / "unrelated.json"
        target.write_text("untouched")
        path = self.root / "layout.json"
        path.symlink_to(target)
        atomic_save_json(path, {"icon": [1, 2]})
        self.assertFalse(path.is_symlink())
        self.assertEqual(target.read_text(), "untouched")
        self.assertEqual(json.loads(path.read_text()), {"icon": [1, 2]})


if __name__ == "__main__":
    unittest.main()
