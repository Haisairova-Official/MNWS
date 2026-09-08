"""Display-free tests for Niri overview event parsing and GLib lifecycle."""

import errno
import os
import unittest
from unittest.mock import Mock, patch

from gi.repository import GLib

from desktop_layer.overview import OverviewWatcher


class PipeSocket:
    """Socket fixture backed by a real nonblocking pipe for GLib readiness."""

    def __init__(self):
        self.reader, self.writer = os.pipe()
        os.set_blocking(self.reader, False)
        os.set_blocking(self.writer, False)
        self.sent = bytearray()
        self.closed = False

    def setblocking(self, value):
        if value:
            raise AssertionError("IPC must stay nonblocking")

    def connect_ex(self, path):
        self.connected_path = path
        return 0

    def fileno(self):
        return self.reader

    def send(self, data):
        self.sent.extend(data)
        return len(data)

    def recv(self, count):
        return os.read(self.reader, count)

    def getsockopt(self, *_):
        return 0

    def feed(self, data):
        os.write(self.writer, data)

    def disconnect_peer(self):
        if self.writer is not None:
            os.close(self.writer)
            self.writer = None

    def close(self):
        if not self.closed:
            os.close(self.reader)
            self.closed = True

    def cleanup(self):
        self.close()
        self.disconnect_peer()


class OverviewTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {"NIRI_SOCKET": "/fake/niri.sock"})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.callback = Mock()
        self.watcher = OverviewWatcher(self.callback)
        self.addCleanup(self.watcher.close)

    def start_with_pipe(self):
        peer = PipeSocket()
        self.addCleanup(peer.cleanup)
        with patch("desktop_layer.overview.socket.socket", return_value=peer):
            self.assertIs(self.watcher.start(), self.watcher)
        return peer

    @staticmethod
    def drain():
        context = GLib.MainContext.default()
        for _ in range(100):
            if not context.pending():
                return
            context.iteration(False)
        raise AssertionError("GLib source is spinning instead of waiting for input")

    def test_event_stream_request_and_fragmented_glib_delivery(self):
        peer = self.start_with_pipe()
        self.assertEqual(peer.sent, b'"EventStream"\n')
        peer.feed(b'{"Ok":"Handled"}\n{"WindowsChanged":{"windows":[]}}\n{"OverviewOpenedOr')
        self.drain()
        self.callback.assert_not_called()
        peer.feed(b'Closed":{"is_open":false}}\n{"OverviewOpenedOrClosed":{"is_open":true}}\n')
        self.drain()
        self.assertEqual([call.args[0] for call in self.callback.call_args_list], [False, True])
        self.assertEqual(self.watcher._buffer, b"")
        self.assertFalse(self.watcher._pending)

    def test_only_boolean_overview_events_and_changes_are_delivered(self):
        self.start_with_pipe()
        self.watcher._feed(
            b'not-json\nnull\n[]\n{"OverviewOpenedOrClosed":null}\n'
            b'{"OverviewOpenedOrClosed":{"is_open":1}}\n'
            b'{"OverviewOpenedOrClosed":{"is_open":"true"}}\n'
            b'{"OverviewOpenedOrClosed":{"is_open":true}}\n'
            b'{"OverviewOpenedOrClosed":{"is_open":true}}\n'
            b'{"OverviewOpenedOrClosed":{"is_open":false}}\n'
        )
        self.assertEqual([call.args[0] for call in self.callback.call_args_list], [True, False])

    def test_absent_environment_never_creates_socket_or_timer(self):
        with patch.dict(os.environ, {}, clear=True), patch("desktop_layer.overview.socket.socket") as factory, patch("desktop_layer.overview.GLib.timeout_add") as timer:
            self.watcher.start()
            self.watcher.start()
        factory.assert_not_called()
        timer.assert_not_called()
        self.callback.assert_not_called()

    def test_close_removes_source_closes_socket_and_is_idempotent(self):
        peer = self.start_with_pipe()
        source = self.watcher._watch
        self.assertIsNotNone(GLib.MainContext.default().find_source_by_id(source))
        self.watcher.close()
        self.watcher.close()
        self.assertTrue(peer.closed)
        self.assertEqual(self.watcher._watch, 0)
        self.assertIsNone(GLib.MainContext.default().find_source_by_id(source))
        self.drain()

    def test_disconnection_clears_overview_and_schedules_one_retry(self):
        peer = self.start_with_pipe()
        peer.feed(b'{"OverviewOpenedOrClosed":{"is_open":true}}\n')
        self.drain()
        peer.disconnect_peer()
        self.drain()
        self.assertEqual([call.args[0] for call in self.callback.call_args_list], [True, False])
        self.assertTrue(peer.closed)
        self.assertGreater(self.watcher._retry_source, 0)
        retry_source = self.watcher._retry_source
        self.watcher.close()
        self.assertIsNone(GLib.MainContext.default().find_source_by_id(retry_source))
        self.assertEqual(self.watcher._retry_source, 0)

    def test_retries_are_exponential_bounded_and_do_not_poll(self):
        scheduled = []

        def add_timer(delay, callback):
            scheduled.append((delay, callback))
            return len(scheduled)

        with patch("desktop_layer.overview.socket.socket", side_effect=PermissionError("blocked")), patch("desktop_layer.overview.GLib.timeout_add", side_effect=add_timer), self.assertLogs("desktop-layer.overview", level="WARNING"):
            self.watcher.start()
            for index in range(6):
                self.assertEqual(len(scheduled), index + 1)
                scheduled[index][1]()
        self.assertEqual([delay for delay, _ in scheduled], [500, 1000, 2000, 4000, 8000, 16000])
        self.assertEqual(self.watcher._retry_source, 0)
        self.assertIsNone(self.watcher._socket)

    def test_connection_failure_closes_socket(self):
        peer = PipeSocket()
        self.addCleanup(peer.cleanup)
        peer.connect_ex = Mock(return_value=errno.ENOENT)
        with patch("desktop_layer.overview.socket.socket", return_value=peer):
            self.watcher.start()
        self.assertTrue(peer.closed)
        self.assertGreater(self.watcher._retry_source, 0)

    def test_stream_buffer_limit_disconnects_without_unbounded_growth(self):
        peer = self.start_with_pipe()
        with patch("desktop_layer.overview._MAX_LINE_BYTES", 64):
            peer.feed(b"x" * 65)
            self.drain()
        self.assertTrue(peer.closed)
        self.assertEqual(self.watcher._buffer, b"")
        self.assertGreater(self.watcher._retry_source, 0)

    def test_error_response_is_not_treated_as_event(self):
        peer = self.start_with_pipe()
        peer.feed(b'{"Err":"unsupported request"}\n')
        self.drain()
        self.callback.assert_not_called()
        self.assertTrue(peer.closed)

    def test_callback_can_close_watcher_during_read(self):
        peer = self.start_with_pipe()
        self.callback.side_effect = lambda state: self.watcher.close()
        peer.feed(b'{"OverviewOpenedOrClosed":{"is_open":true}}\n{"OverviewOpenedOrClosed":{"is_open":false}}\n')
        self.drain()
        self.callback.assert_called_once_with(True)
        self.assertTrue(peer.closed)
        self.assertEqual(self.watcher._retry_source, 0)

    def test_partial_write_leaves_only_pending_request_bytes(self):
        peer = PipeSocket()
        self.addCleanup(peer.cleanup)
        original_send = peer.send
        calls = [3, BlockingIOError()]

        def send(data):
            if calls:
                result = calls.pop(0)
                if isinstance(result, Exception):
                    raise result
                return original_send(data[:result])
            return original_send(data)

        peer.send = send
        with patch("desktop_layer.overview.socket.socket", return_value=peer):
            self.watcher.start()
        self.assertEqual(peer.sent, b'"Ev')
        self.assertEqual(self.watcher._pending, b'entStream"\n')
        # Pipe readers are never writable, so directly dispatch the OUT callback
        # after removing its real source; socket descriptors receive it normally.
        GLib.source_remove(self.watcher._watch)
        self.watcher._watch = 0
        self.assertFalse(self.watcher._io_ready(None, GLib.IOCondition.OUT))
        self.assertEqual(peer.sent, b'"EventStream"\n')
        self.assertEqual(self.watcher._pending, b"")
        self.drain()


if __name__ == "__main__":
    unittest.main()
