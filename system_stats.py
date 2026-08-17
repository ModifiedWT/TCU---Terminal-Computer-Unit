"""Pulls CPU / RAM / disk usage via psutil."""

import psutil


class SystemStats:
    @staticmethod
    def cpu_percent() -> float:
        # non-blocking; call regularly on a timer instead of using interval=1
        return psutil.cpu_percent(interval=None)

    @staticmethod
    def ram_percent() -> float:
        return psutil.virtual_memory().percent

    @staticmethod
    def disk_percent(path: str = "C:\\") -> float:
        try:
            return psutil.disk_usage(path).percent
        except FileNotFoundError:
            return 0.0

    @staticmethod
    def cpu_temp_celsius() -> float | None:
        # Not reliably available on Windows without extra drivers (e.g. LibreHardwareMonitor).
        # Left as a hook for later — see README.
        try:
            temps = psutil.sensors_temperatures()
            if not temps:
                return None
            for entries in temps.values():
                if entries:
                    return entries[0].current
        except (AttributeError, NotImplementedError):
            return None
        return None