import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import mnws_commands as commands


class CommandTests(unittest.TestCase):
    def test_link_and_repeat(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            directory = home / '.local/bin'
            with patch.dict(os.environ, {'HOME': temporary, 'PATH':str(directory)+os.pathsep+os.environ['PATH']}), patch.object(commands, 'read_inventory', return_value={}), patch.object(commands, 'save_inventory'):
                commands.install()
                commands.install()
            self.assertEqual((directory/'mnws').resolve(), commands.ROOT/'mnws')

    def test_foreign_command_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)/'.local/bin'
            directory.mkdir(parents=True)
            (directory/'mnws').write_text('foreign')
            with patch.dict(os.environ, {'HOME':temporary, 'PATH':str(directory)}), patch.object(commands, 'read_inventory', return_value={}):
                with self.assertRaises(RuntimeError):
                    commands.install()
            self.assertEqual((directory/'mnws').read_text(), 'foreign')

    def test_decline_system_install(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            with patch.dict(os.environ, {'PATH':str(directory)}), patch.object(commands, 'SYSTEM_BIN', directory), patch.object(commands, 'ask', return_value='n'), patch.object(commands, 'run') as run:
                with self.assertRaises(RuntimeError):
                    commands.install()
                run.assert_not_called()

    def test_sudo_when_required(self):
        with patch.object(commands.os, 'access', return_value=False), patch.object(commands.shutil, 'which', return_value='/usr/bin/sudo'), patch.object(commands.subprocess, 'run') as run:
            commands.run(['ln', '-s', '/source', '/usr/local/bin/mnws'], Path('/usr/local/bin'))
            run.assert_called_once_with(['sudo', 'ln', '-s', '/source', '/usr/local/bin/mnws'], check=True)
