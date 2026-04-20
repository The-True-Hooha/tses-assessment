import json
import logging
import threading
import traceback

_local = threading.local()


def set_request_context(
    request_id=None,
    correlation_id=None,
    user_id=None,
    ip=None,
    endpoint=None,
):
    _local.request_id = request_id
    _local.correlation_id = correlation_id
    _local.user_id = user_id
    _local.ip = ip
    _local.endpoint = endpoint


def get_request_context():
    return {
        "request_id": getattr(_local, "request_id", None),
        "correlation_id": getattr(_local, "correlation_id", None),
        "user_id": getattr(_local, "user_id", None),
        "ip": getattr(_local, "ip", None),
        "endpoint": getattr(_local, "endpoint", None),
    }


def clear_request_context():
    for attr in ("request_id", "correlation_id", "user_id", "ip", "endpoint"):
        try:
            delattr(_local, attr)
        except AttributeError:
            pass


class JSONFormatter(logging.Formatter):
    def format(self, record):
        ctx = get_request_context()
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": ctx["request_id"],
            "correlation_id": ctx["correlation_id"],
            "user_id": ctx["user_id"],
            "ip": ctx["ip"],
            "endpoint": ctx["endpoint"],
        }
        if record.exc_info:
            log_entry["exception"] = traceback.format_exception(*record.exc_info)
        return json.dumps(log_entry)
