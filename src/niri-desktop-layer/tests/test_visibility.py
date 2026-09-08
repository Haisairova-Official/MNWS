import tempfile
import time
import unittest
from pathlib import Path
from gi.repository import GLib
from desktop_layer.visibility import MarkerVisibility


class VisibilityTests(unittest.TestCase):
    def wait_for(self, predicate):
        deadline = time.monotonic() + 2
        context = GLib.MainContext.default()
        while time.monotonic() < deadline:
            while context.pending():
                context.iteration(False)
            if predicate():
                return
            time.sleep(.01)
        self.fail("marker update was not delivered")

    def test_initial_state_and_create_delete_atomic_replace(self):
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder) / 'hidden'
            states = []
            watcher = MarkerVisibility(marker, states.append).start()
            self.addCleanup(watcher.close)
            self.assertEqual(states, [False])
            marker.touch()
            self.wait_for(lambda: states[-1] is True)
            marker.unlink()
            self.wait_for(lambda: states[-1] is False)
            other = marker.with_name('temporary')
            other.touch()
            other.replace(marker)
            self.wait_for(lambda: states[-1] is True)
            watcher.close()
            self.assertEqual(watcher.pending, 0)
            self.assertIsNone(watcher.monitor)

    def test_hidden_at_start_and_idempotent_states(self):
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder) / 'hidden'
            marker.touch()
            states = []
            watcher = MarkerVisibility(marker, states.append).start()
            self.addCleanup(watcher.close)
            self.assertEqual(states, [True])
            watcher.sync()
            self.assertEqual(states, [True, True])
            watcher.close()
            watcher.sync()
            self.assertEqual(states, [True, True])
