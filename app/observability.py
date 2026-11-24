import json
import logging


class JsonFormatter(logging.Formatter):
    """Emit concise structured events without exception messages or credentials."""

    def format(self, record):
        payload = {
            "level": record.levelname.lower(),
            "logger": record.name,
            "event": getattr(record, "event", "application_event"),
        }
        error_type = getattr(record, "error_type", None)
        if error_type:
            payload["error_type"] = error_type
        return json.dumps(payload, ensure_ascii=False)


def configure_logging():
    logger = logging.getLogger("nfl")
    if not any(isinstance(handler, logging.StreamHandler) and isinstance(handler.formatter, JsonFormatter)
               for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
