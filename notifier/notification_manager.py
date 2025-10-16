try:
    from dashboard.notifier.notification_manager import (
        get_notification_manager as _real_get_notification_manager
    )
except Exception:
    _real_get_notification_manager = None


class _NoopNotifier:
    def send(self, *a, **k): return False
    def info(self, *a, **k): return False
    def warn(self, *a, **k): return False
    def error(self, *a, **k): return False


def get_notification_manager(*args, **kwargs):
    if _real_get_notification_manager:
        try:
            return _real_get_notification_manager(*args, **kwargs)
        except Exception:
            pass
    return _NoopNotifier()


# compat: o boot espera este nome
get_safe_notification_manager = get_notification_manager
