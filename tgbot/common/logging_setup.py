import contextvars
import json
import logging
import sys
import time

request_id_var = contextvars.ContextVar("request_id", default="-")
tenant_id_var = contextvars.ContextVar("tenant_id", default="-")
user_id_var = contextvars.ContextVar("user_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "ts": int(time.time() * 1000),
            "request_id": request_id_var.get(),
            "tenant_id": tenant_id_var.get(),
            "user_id": user_id_var.get(),
        }
        if record.exc_info:
            base["exc_info"] = self.formatException(record.exc_info)
        # добавим любые extra
        for k, v in getattr(record, "__dict__", {}).items():
            if k not in (
                "args",
                "msg",
                "levelno",
                "levelname",
                "name",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "pathname",
                "filename",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "process",
                "processName",
            ):
                base[k] = v
        return json.dumps(base, ensure_ascii=False)


def setup_logging(level="INFO"):
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(h)


log = logging.getLogger("general")
