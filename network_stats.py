"""Tracks network throughput (bytes/sec up and down) via psutil."""

import time
import psutil


class NetworkStats:
    def __init__(self):
        counters = psutil.net_io_counters()
        self._last_sent = counters.bytes_sent
        self._last_recv = counters.bytes_recv
        self._last_time = time.monotonic()

    def sample(self) -> tuple[float, float]:
        """Returns (upload_KBps, download_KBps) since the last sample."""
        counters = psutil.net_io_counters()
        now = time.monotonic()
        elapsed = max(now - self._last_time, 0.001)

        up_kbps = (counters.bytes_sent - self._last_sent) / 1024 / elapsed
        down_kbps = (counters.bytes_recv - self._last_recv) / 1024 / elapsed

        self._last_sent = counters.bytes_sent
        self._last_recv = counters.bytes_recv
        self._last_time = now

        return up_kbps, down_kbps