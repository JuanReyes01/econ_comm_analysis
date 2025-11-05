"""
Main entry point for the argumentation mining pipeline.

This module provides the main function to run the argumentation mining
extraction on a dataset.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from argumentation_mining.pipelines.direct_extraction.direct_extraction import (
    DirectArgumentExtractor,
    DirectExtractionResult,
)
from argumentation_mining.pipelines.socratic_extraction.socratic_extraction import (  # noqa: E501
    QAArgumentExtractor,
    QAResult,
)
from argumentation_mining.utils.logger import setup_logger
from argumentation_mining.utils.output_formatter import (
    print_statistics,
    save_as_csv,
    save_as_json,
)

if TYPE_CHECKING:
    from logging import Logger


def main(  # noqa: PLR0915, PLR0913
    data_file: str = "./data/raw/columns_chi2_w_inter.xlsx",
    text_column: str = "Cuerpo",
    id_column: str = "id",
    pipeline_name: str = "socratic_extraction",
    output_dir: str = "./data/processed",
    output_format: str = "both",  # "json", "csv", or "both"
    log_file: str = "./reports/argumentation_mining.log",
    *,
    run_batch: bool = True,
    num_rows: int | None = None,
    start_row: int = 0,  # New parameter for start index
    end_row: int | None = None,  # New parameter for end index
) -> list[dict[str, Any]]:
    """
    Active runner of the pipeline.

    It will load the data, preprocess it and then use the AM pipeline to
    extract arguments.
    Finally, it will save the results to a specified output file.

    Args:
        data_file: Path to the input data file.
        text_column: Name of the column containing the text data.
        id_column: Name of the column containing the unique identifier
                   for each text entry.
        pipeline_name: Name of the pipeline to use for argument
                       extraction.
        output_dir: Directory where output files will be saved.
        output_format: Output format - "json", "csv", or "both".
        log_file: Path to the log file.
        run_batch: Whether to run the pipeline in batch mode (True)
                   or sequential single mode (False).
        num_rows: Number of rows to process. If None, process all rows.
        start_row: Starting row index (0-based) for processing.
        end_row: Ending row index (exclusive) for processing. If None,
                 process to end.

    Returns:
        List of result dictionaries.

    """
    # 1. Setup logger
    logger = setup_logger(
        name="argumentation_mining",
        log_file=log_file,
        console=True,
    )

    logger.info("=" * 70)
    logger.info("Argumentation Mining Pipeline")
    logger.info("=" * 70)
    logger.info("Configuration:")
    logger.info("  Data file: %s", data_file)
    logger.info("  Text column: %s", text_column)
    logger.info("  ID column: %s", id_column)
    logger.info("  Pipeline: %s", pipeline_name)
    logger.info("  Output directory: %s", output_dir)
    logger.info("  Output format: %s", output_format)
    logger.info("  Batch mode: %s", run_batch)
    logger.info("  Rows to process: %s", num_rows or "all")

    # 2. Load and preprocess the data
    logger.info("Loading data...")
    data = load_data(data_file)
    logger.info("Loaded %d rows", len(data))

    # Slice data based on start_row and end_row
    if end_row is not None:
        data = data.iloc[start_row:end_row]
    elif num_rows is not None:
        data = data.iloc[start_row : start_row + num_rows]
    else:
        data = data.iloc[start_row:]
    logger.info(
        "Processing rows from %d to %d", start_row, len(data) + start_row - 1
    )

    preprocessed_data = preprocess_data(data, text_column, id_column, logger)
    logger.info("Preprocessed %d rows", len(preprocessed_data))

    # 3. Pipeline selection and initialization
    logger.info("Initializing pipeline: %s", pipeline_name)
    if pipeline_name == "socratic_extraction":
        extractor = QAArgumentExtractor(logger=logger)
    elif pipeline_name == "direct_extraction":
        extractor = DirectArgumentExtractor(logger=logger)
    else:
        error_msg = f"Unsupported pipeline: {pipeline_name}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    # 4. Run the pipeline
    logger.info("Starting extraction...")
    results = run_pipeline(
        extractor,
        preprocessed_data,
        text_column,
        id_column,
        run_batch=run_batch,
        logger=logger,
    )

    logger.info("Extraction completed!")

    # 5. Convert results to dictionary format
    results_dict = _convert_results_to_dict(results)

    # 6. Print statistics
    print_statistics(results_dict, logger)

    # 7. Save results
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    base_filename = Path(data_file).stem

    if output_format in ("json", "both"):
        json_file = output_path / f"{base_filename}_results.json"
        logger.info("Saving results to JSON: %s", json_file)
        save_as_json(results_dict, json_file, logger)

    if output_format in ("csv", "both"):
        csv_file = output_path / f"{base_filename}_results.csv"
        logger.info("Saving results to CSV: %s", csv_file)
        save_as_csv(results_dict, csv_file, logger)

    logger.info("=" * 70)
    logger.info("Pipeline completed successfully!")
    logger.info("=" * 70)

    return results_dict


def load_data(file_path: str) -> pd.DataFrame:
    """
    Load data from a specified file.

    Args:
        file_path: Path to the input data file.

    Returns:
        data: Loaded data as a pandas DataFrame.

    Raises:
        ValueError: If file format is not supported.

    """
    file_path_obj = Path(file_path)

    if file_path_obj.suffix == ".xlsx":
        data = pd.read_excel(file_path)
    elif file_path_obj.suffix == ".csv":
        data = pd.read_csv(file_path)
    else:
        msg = f"Unsupported file format: {file_path_obj.suffix}"
        raise ValueError(msg)

    return data


def preprocess_data(
    data: pd.DataFrame,
    text_column: str,
    id_column: str,
    logger: Logger | None = None,
) -> pd.DataFrame:
    """
    Preprocess the input data.

    Args:
        data: Input data as a pandas DataFrame.
        text_column: Name of the column containing the text data.
        id_column: Name of the column containing the unique identifier
                   for each text entry.
        logger: Optional logger for logging.

    Returns:
        preprocessed_data: Preprocessed data.

    Raises:
        ValueError: If required columns are not found.

    """
    # Check if the required columns are present
    if text_column not in data.columns:
        msg = f"Text column '{text_column}' not found in data"
        if logger:
            logger.error(msg)
        raise ValueError(msg)

    if id_column not in data.columns:
        msg = f"ID column '{id_column}' not found in data"
        if logger:
            logger.error(msg)
        raise ValueError(msg)

    # Drop all other columns and return a DataFrame
    # with only the required columns
    return data[[id_column, text_column]].copy()


def run_pipeline(  # noqa: PLR0913
    extractor: QAArgumentExtractor | DirectArgumentExtractor,
    data: pd.DataFrame,
    text_column: str,
    id_column: str,
    *,
    run_batch: bool = True,
    logger: Logger | None = None,
) -> list[QAResult | DirectExtractionResult]:
    """
    Run the extraction pipeline.

    Args:
        extractor: Initialized extractor instance.
        data: Preprocessed data.
        text_column: Name of the text column.
        id_column: Name of the ID column.
        run_batch: Whether to run in batch mode.
        logger: Optional logger for logging.

    Returns:
        List of result objects (QAResult or DirectExtractionResult).

    """
    # Convert DataFrame to list of dictionaries
    articles = data.rename(
        columns={text_column: "text", id_column: "article_id"},
    ).to_dict("records")

    if run_batch:
        if logger:
            logger.info("Running pipeline in BATCH mode...")
        results = extractor.process_batch(
            articles=articles,
            text_column="text",
            id_column="article_id",
            output_dir="data/interim",
        )
    else:
        if logger:
            logger.info("Running pipeline in SEQUENTIAL mode...")
        results = []
        for i, article in enumerate(articles):
            if logger:
                logger.info(
                    "Processing article %d/%d: %s",
                    i + 1,
                    len(articles),
                    article.get("article_id", "unknown"),
                )
            result = extractor.process_single(
                text=article["text"],
                article_id=article.get("article_id"),
            )
            results.append(result)

    return results


def _convert_results_to_dict(
    results: list[QAResult | DirectExtractionResult],
) -> list[dict[str, Any]]:
    """
    Convert result objects to dictionaries for serialization.

    Args:
        results: List of result objects (QAResult or DirectExtractionResult).

    Returns:
        List of result dictionaries.

    """
    output = []
    for r in results:
        result_dict = {
            "article_id": r.article_id,
            "text": r.text,
            "success": r.success,
            "error_message": r.error_message,
            "arguments": r.arguments,
        }

        # Add pipeline-specific fields
        if isinstance(r, QAResult):
            result_dict["questions"] = r.questions
        elif isinstance(r, DirectExtractionResult):
            result_dict["conclusions"] = r.conclusions

        output.append(result_dict)

    return output


if __name__ == "__main__":
    # Example usage:
    # Process first 10 rows in batch mode, output both JSON and CSV
    main(
        start_row=100,
        num_rows=50,
        run_batch=True,
        output_format="both",
        pipeline_name="direct_extraction",
    )
    # TODO @Juan: Implement the CLI interface
