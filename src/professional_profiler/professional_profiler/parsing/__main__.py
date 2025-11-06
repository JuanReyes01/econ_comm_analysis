import sys
import pandas as pd
from professional_profiler.logging.logger import get_logger, setup_logging
from professional_profiler.config import load_app_config
from professional_profiler.parsing.extractors import extract_degrees_markdown

# Initialize first thing in main
setup_logging()
logger = get_logger(__name__)
config = load_app_config()


# ===== MAIN =====


def main():
    logger.info("Starting parsing")
    # Load the configuration
    logger.debug("Configuration loaded: %s", config)
    # Load the dataset
    dataset_path = config.scraping.paths.processed_data + config.scraping.file.name

    db = pd.read_csv(dataset_path)
    logger.info("Loading HTML from DataFrame")
    db["sentences"] = db["source"].apply(extract_degrees_markdown)
    # Save the results just the id, name and sentences
    db = db[["id", "author_name", "sentences"]]
    # Save the results to a CSV file
    output_path = config.parsing.paths.results_path + config.parsing.file.file_name
    db.to_csv(output_path, index=False)
    logger.info("Parsing completed successfully")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger = get_logger(__name__)
        logger.exception("Fatal error in parsing")
        sys.exit(1)
