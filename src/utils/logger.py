import logging
import time

from settings import settings


class UTCFormatter(logging.Formatter):
    converter = staticmethod(lambda ts=None: time.gmtime(ts))


def setup_logging():
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)sZ [%(levelname)s] %(name)s: %(message)s",
    )

    for handler in logging.getLogger().handlers:
        handler.setFormatter(
            UTCFormatter("%(asctime)sZ [%(levelname)s] %(name)s: %(message)s")
        )
