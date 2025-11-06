# ===== IMPORTS =====

import sys
from professional_profiler.logging.logger import setup_logging, get_logger
from professional_profiler.config import load_app_config
from professional_profiler.scraping.wikipedia_search import get_wikipedia, search_html
import pandas as pd

setup_logging()
conf = load_app_config()
logger = get_logger(__name__)

# ===== FUNCTIONS =====


def load_subject_list(path: str) -> list[str]:
    logger.debug("Loading subjects from %s", path)
    # import and create a list of subjects
    try:
        subjects = pd.read_csv(path)
        logger.debug("Loaded %d subjects", len(subjects))
        return subjects
    except FileNotFoundError:
        logger.error("File not found: %s", path)
        return []
    except Exception as e:
        logger.error("Error loading subjects: %s", e)
        return []


def fetch_wikipedia(subject):
    logger.debug("Processing subject: %s", subject)
    wiki_conf = conf.scraping.wikipedia
    result = get_wikipedia(
        subject,
        lang=wiki_conf.language,
        retry=wiki_conf.max_retries,
        timeout=wiki_conf.timeout,
        rc=wiki_conf.response_code,
    )
    logger.info("Result for %s: %s", subject, result)
    return result


def fetch_source(key):
    logger.debug("fetching key: %s", key)
    wiki_conf = conf.scraping.wikipedia
    result = search_html(
        key,
        lang=wiki_conf.language,
        retry=wiki_conf.max_retries,
        timeout=wiki_conf.timeout,
        rc=wiki_conf.response_code,
    )
    logger.info("Result for %s: %s", key, result[1:10])
    return result


# ===== MAIN =====
def main():

    logger.info("Starting wikipedia link gathering")
    # Load the subject list
    logger.debug("Loading subject list from %s", conf.scraping.paths.authors)
    subjects = load_subject_list(conf.scraping.paths.authors)
    if len(subjects) == 0:
        logger.error("No subjects found in the file.")
        return
    logger.debug("Loaded %d subjects", len(subjects))
    # Process each subject
    # It will be a concat into a dataframe
    subjects["key"] = subjects[conf.scraping.file.name_column].apply(fetch_wikipedia)
    subjects["source"] = subjects["key"].apply(fetch_source)
    # Save the results to a CSV file
    output_path = conf.scraping.paths.processed_data
    logger.debug("Saving results to %s", output_path)
    subjects.to_csv(output_path + conf.scraping.file.name, index=False)

    logger.info("Finished processing subjects")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger = get_logger(__name__)
        logger.exception("Fatal error in scraping")
        sys.exit(1)
