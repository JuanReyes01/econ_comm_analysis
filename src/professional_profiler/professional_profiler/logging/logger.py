# professional_profiler/logging/logger.py
"""
The above code defines functions for setting up
logging configuration from a YAML file and getting
a logger instance.

:param config_path: The `config_path` parameter in
the `setup_logging` function is used to specify
the path to the logging configuration file in YAML
format. By default, it is set to `_LOG_YAML`, which
is a Path object pointing to the logging configuration
file located in the "config" directory relative to
:type config_path: str | Path
"""
import logging.config
from pathlib import Path
import yaml

_LOG_YAML = Path(__file__).parent.parent.parent / "config" / "logging.yaml"


def setup_logging(config_path: str | Path = _LOG_YAML) -> None:
    try:
        cfg = yaml.safe_load(Path(config_path).read_text())
        logging.config.dictConfig(cfg)
    except Exception as e:
        logging.basicConfig(level=logging.INFO)
        logging.getLogger(__name__).warning(
            "Failed to load %r: %s—using basicConfig", config_path, e
        )


def get_logger(name: str = None):
    return logging.getLogger(name or __name__)
