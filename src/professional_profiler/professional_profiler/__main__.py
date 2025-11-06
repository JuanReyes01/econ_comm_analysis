# professional_profiler/__main__.py
"""
    This module is the entry point for professional profiler pipeline that runs
    - wikipedia 'scraping' (I'm using the API)
    - professional studies data extraction agent
"""
# ===== IMPORTS =====
import sys
from professional_profiler.logging.logger import setup_logging, get_logger

logger = get_logger(__name__)

# ===== FUNCTIONS =====

# ===== MAIN =====


def main():
    # 1) Boot logging
    setup_logging()

    logger.info("Starting full pipeline")
    # cfg = load_app_config()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Fatal error, exiting")
        sys.exit(1)
