"""
Output formatting utilities for argumentation mining results.

Provides functions to save extraction results in JSON and CSV formats.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from logging import Logger


@dataclass
class _ArticleData:
    """Internal class to group article-related data for row creation."""

    article_id: str
    text: str
    success: bool
    error_message: str


def save_as_json(
    results: list[dict[str, Any]],
    output_path: str | Path,
    logger: Logger | None = None,
) -> None:
    """
    Save results to JSON file.

    Args:
        results: List of result dictionaries.
        output_path: Path to output JSON file.
        logger: Optional logger for logging.

    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        if logger:
            logger.info("Results saved to JSON: %s", output_path)

    except Exception as e:
        error_msg = f"Error writing JSON file: {e}"
        if logger:
            logger.exception(error_msg)
        raise


def save_as_csv(
    results: list[dict[str, Any]],
    output_path: str | Path,
    logger: Logger | None = None,
    max_premises: int = 5,
) -> None:
    """
    Save results to CSV file with flattened structure.

    Each argument becomes a row with article info + argument details.
    Premises are split into separate columns (up to max_premises).

    Args:
        results: List of result dictionaries containing articles and arguments.
        output_path: Path to output CSV file.
        logger: Optional logger for logging.
        max_premises: Maximum number of premise columns to create.

    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    flattened_rows = _flatten_results_for_csv(results, max_premises)

    if not flattened_rows:
        msg = "No data to write to CSV."
        if logger:
            logger.warning(msg)
        return

    fieldnames = [
        "article_id",
        "text",
        "success",
        "error_message",
        "argument_index",
        "question",
        "answer",
        "claim",
        "premises_count",
        "premises_concatenated",
    ]
    # Add premise columns
    fieldnames.extend([f"premise_{i + 1}" for i in range(max_premises)])

    try:
        with output_path.open("w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(flattened_rows)

        if logger:
            logger.info(
                "Successfully converted %d rows to %s",
                len(flattened_rows),
                output_path,
            )

    except Exception as e:
        error_msg = f"Error writing CSV file: {e}"
        if logger:
            logger.exception(error_msg)
        raise


def _flatten_results_for_csv(
    results: list[dict[str, Any]],
    max_premises: int = 5,
) -> list[dict[str, Any]]:
    """
    Flatten nested JSON structure to create rows for CSV.

    Each row contains article info + one argument with premises flattened.

    Args:
        results: List of result dictionaries.
        max_premises: Maximum number of premise columns to create.

    Returns:
        List of flattened row dictionaries.

    """
    rows = []

    for article in results:
        article_id = article.get("article_id", "")
        text = article.get("text", "")
        success = article.get("success", False)
        error_message = article.get("error_message", "")
        arguments = article.get("arguments", [])

        # If there are no arguments, create one row with just article data
        if not arguments:
            article_data = _ArticleData(
                article_id=article_id,
                text=text,
                success=success,
                error_message=error_message,
            )
            row = _create_empty_row(article_data, max_premises)
            rows.append(row)
        else:
            # Create one row per argument
            for arg_index, argument in enumerate(arguments):
                article_data = _ArticleData(
                    article_id=article_id,
                    text=text,
                    success=success,
                    error_message=error_message,
                )
                row = _create_argument_row(
                    article_data,
                    arg_index,
                    argument,
                    max_premises,
                )
                rows.append(row)

    return rows


def _create_empty_row(
    article_data: _ArticleData,
    max_premises: int,
) -> dict[str, Any]:
    """Create an empty row for articles with no arguments."""
    row = {
        "article_id": article_data.article_id,
        "text": article_data.text,
        "success": article_data.success,
        "error_message": article_data.error_message,
        "argument_index": "",
        "question": "",
        "answer": "",
        "claim": "",
        "premises_count": 0,
        "premises_concatenated": "",
    }

    # Add empty premise columns
    for i in range(max_premises):
        row[f"premise_{i + 1}"] = ""

    return row


def _create_argument_row(
    article_data: _ArticleData,
    arg_index: int,
    argument: dict[str, Any],
    max_premises: int,
) -> dict[str, Any]:
    """Create a row for a single argument."""
    question = argument.get("question", "")
    answer = argument.get("answer", "")
    claim = argument.get("claim", "")
    premises = argument.get("premises", [])

    # Prepare premise columns (up to max_premises)
    premise_cols = [""] * max_premises
    for i, premise in enumerate(premises[:max_premises]):
        premise_cols[i] = premise

    row = {
        "article_id": article_data.article_id,
        "text": article_data.text,
        "success": article_data.success,
        "error_message": article_data.error_message,
        "argument_index": arg_index + 1,
        "question": question,
        "answer": answer,
        "claim": claim,
        "premises_count": len(premises),
        "premises_concatenated": " | ".join(premises),
    }

    # Add premise columns
    for i in range(max_premises):
        row[f"premise_{i + 1}"] = premise_cols[i]

    return row


def print_statistics(
    results: list[dict[str, Any]],
    logger: Logger | None = None,
) -> None:
    """
    Print statistics about the results.

    Args:
        results: List of result dictionaries.
        logger: Optional logger for logging.

    """
    total_articles = len(results)
    successful_articles = sum(1 for r in results if r.get("success", False))
    total_arguments = sum(
        len(r.get("arguments", [])) for r in results if r.get("arguments")
    )
    avg_args = total_arguments / total_articles if total_articles > 0 else 0

    stats = f"""
Statistics:
- Total articles: {total_articles}
- Successful extractions: {successful_articles}
- Failed extractions: {total_articles - successful_articles}
- Total arguments: {total_arguments}
- Average arguments per article: {avg_args:.2f}
"""

    if logger:
        logger.info(stats)
