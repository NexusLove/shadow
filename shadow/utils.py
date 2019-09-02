import logging
from typing import Optional

import coloredlogs  # pylint: disable=import-error


def get_colored_logger(
    name: str,
    level: str = 'INFO',
    fmt: Optional[str] = '[%(asctime)s] %(levelname)s - %(message)s',
) -> logging.Logger:
    """Factory method for coloredlogs loggers.

    Parameters
    ----------
    name : :class:`str`
        The name of the logger.
    level : :class:`str`
        The level of the logger.
    fmt : Optional[:class:`str`]
        The format string for the logger.
        A default format string is provided

    Returns
    -------
    logger : :class:`logging.Logger`
        The logger instance generated.
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level))
    coloredlogs.install(fmt=fmt, level=level, logger=logger)
    return logger
