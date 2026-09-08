from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from desktop_layer import model


class ThunarTests(unittest.TestCase):
    def test_folder_with_shell_characters_is_a_single_uri(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'a & b; c'
            target.mkdir()
            entry = model.scan_desktop(Path(folder))[0]
            with patch.object(model, 'open_in_thunar', return_value=True) as opened:
                model.launch_entry(entry)
                opened.assert_called_once_with(target.as_uri(), None)

    def test_navigation_shortcuts_route_to_thunar_without_changing_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for uri in ('computer:///', 'network:///', 'trash:///'):
                path = root / 'location.desktop'
                content = f'[Desktop Entry]\nType=Application\nName=Location\nExec=pcmanfm-qt {uri}\n'
                path.write_text(content)
                with patch.object(model.Gio.DesktopAppInfo, 'new_from_filename', return_value=Mock()), patch.object(model, 'open_in_thunar', return_value=True) as opened:
                    model.launch_entry(model.scan_desktop(root)[0])
                    opened.assert_called_once_with(uri, None)
                self.assertEqual(path.read_text(), content)
                self.assertFalse(path.stat().st_mode & 0o111)

    def test_thunar_uses_installed_app_and_uri_arguments(self):
        app = Mock()
        with patch.object(model.Gio.DesktopAppInfo, 'new', return_value=app) as lookup:
            model.open_in_thunar('file:///tmp/a%20b')
            lookup.assert_called_once_with('thunar.desktop')
            app.launch_uris.assert_called_once_with(['file:///tmp/a%20b'], None)

    def test_extra_launcher_arguments_are_not_reinterpreted(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'custom.desktop'
            path.write_text('[Desktop Entry]\nType=Application\nName=Custom\nExec=pcmanfm-qt --some-option /tmp\n')
            self.assertIsNone(model._file_manager_location(path))
