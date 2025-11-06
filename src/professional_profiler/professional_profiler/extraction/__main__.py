from professional_profiler.logging.logger import get_logger, setup_logging
import sys
import pandas as pd
from professional_profiler.config import load_app_config
from professional_profiler.extraction.llm import extract_degrees_async
import asyncio
import json

setup_logging()
logger = get_logger(__name__)
config = load_app_config()


async def process_degrees(df):
    df["degrees"] = await asyncio.gather(
        *(extract_degrees_async(sentence) for sentence in df["sentences"])
    )
    return df

def parse_output(degrees, id, author_name):
    out = {
        "id":           id,
        "author_name":  author_name,
        "degrees":      []
    }
    for degree in degrees.output.studies:
        out["degrees"].append({
            "degree_type":  degree.degree_type,
            "degree_field": degree.degree_field
        })
    return out


def main():
    logger.info("Starting extraction")
    logger.debug("Configuration loaded: %s", config)
    df = pd.read_csv(config.parsing.paths.results_path + config.parsing.file.file_name)
    df = asyncio.run(process_degrees(df))
    # Save the results just the id, name and sentences
    df = df[["id", "author_name", "degrees"]]
    # Save the results to a CSV file
    logger.info("Saving results to JSON file")
    #parse output
    
    parsed_series  = df.apply(lambda x: parse_output(x["degrees"], x["id"], x["author_name"]), axis=1)
    parsed_list = parsed_series.tolist()

    output_path = config.extraction.paths.results_path + config.extraction.file.file_name

    with open(output_path, "w", encoding="utf-8") as fp:
        fp.write("[\n")
        for i, record in enumerate(parsed_list):
            # dump each record and add a comma except after the last one
            fp.write(json.dumps(record, ensure_ascii=False))
            if i < len(parsed_list) - 1:
                fp.write(",\n")
        fp.write("\n]")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger = get_logger(__name__)
        logger.exception("Fatal error in parsing")
        sys.exit(1)