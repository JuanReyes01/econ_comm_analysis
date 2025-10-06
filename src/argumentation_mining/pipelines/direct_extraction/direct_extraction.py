"""
Direct Extraction Argumentation Mining Implementation.

Implements a two-phase approach for extracting premises and conclusions
from arguments using large language models. Unlike the Socratic method,
this approach directly extracts conclusions and their supporting premises
from the text.

Pipeline:
    Phase 1: Extract all conclusions (claims) from the text
    Phase 2: For each conclusion, extract its specific supporting premises
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from typing import TYPE_CHECKING, Any

import yaml

from argumentation_mining.utils.openai_calls import (
    OpenAIClient,
    build_batch_request,
    extract_batch_result,
)

if TYPE_CHECKING:
    from logging import Logger


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class DirectExtractionResult:
    """Results from direct extraction argumentation mining."""

    text: str
    article_id: str | None = None
    conclusions: list[str] | None = None
    arguments: list[dict[str, Any]] | None = None
    success: bool = False
    error_message: str | None = None


@dataclass
class _BatchConfig:
    """Internal configuration for batch result combination."""

    articles: list[dict[str, Any]]
    phase_results: dict[str, list[dict[str, Any]]]
    text_column: str
    id_column: str | None


# ---------------------------------------------------------------------------
# Main Extractor Class
# ---------------------------------------------------------------------------


class DirectArgumentExtractor:
    """
    Direct extraction of argument structure.

    Pipeline:
    1. Extract conclusions from text
    2. Extract premises for each conclusion
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        prompts_path: str | Path | None = None,
        logger: Logger | None = None,
    ) -> None:
        """
        Initialize the extractor.

        Args:
            api_key: OpenAI API key (reads from env if not provided).
            model: OpenAI model to use.
            prompts_path: Path to prompts YAML file.
            logger: Logger instance for logging.

        """
        self.client = OpenAIClient(api_key=api_key, model=model)
        self.model = model
        self.logger = logger

        # Load prompts
        if prompts_path is None:
            prompts_path = Path(__file__).parent / "prompt.yaml"
        else:
            prompts_path = Path(prompts_path)

        with prompts_path.open("r", encoding="utf-8") as f:
            prompts_data = yaml.safe_load(f)

        self.conclusion_extraction_prompt = prompts_data[
            "conclusion_extraction"
        ]
        self.premise_extraction_prompt = prompts_data["premise_extraction"]

    # --------------------------- Single Processing --------------------------

    def extract_conclusions(self, text: str) -> list[str]:
        """Extract all conclusions from text."""
        prompt = self.conclusion_extraction_prompt.format(text=text)
        response = self.client.call(prompt, temperature=0.1)
        return self._parse_list_items(response)

    def extract_premises(self, text: str, conclusion: str) -> list[str]:
        """Extract premises that support a specific conclusion."""
        prompt = self.premise_extraction_prompt.format(
            text=text,
            conclusion=conclusion,
        )
        response = self.client.call(prompt, temperature=0.1)
        return self._parse_list_items(response)

    def process_single(
        self,
        text: str,
        article_id: str | None = None,
    ) -> DirectExtractionResult:
        """
        Process a single article synchronously.

        Args:
            text: The article text.
            article_id: Optional article identifier.

        Returns:
            DirectExtractionResult with extracted information.

        """
        result = DirectExtractionResult(text=text, article_id=article_id)

        try:
            # Phase 1: Extract conclusions
            result.conclusions = self.extract_conclusions(text)

            # Phase 2: Extract premises for each conclusion
            result.arguments = self._process_conclusions(
                result.conclusions,
                text,
            )
            result.success = True

        except (ValueError, KeyError, RuntimeError) as e:
            result.error_message = str(e)

        return result

    def _process_conclusions(
        self,
        conclusions: list[str],
        text: str,
    ) -> list[dict[str, Any]]:
        """Process conclusions to extract their supporting premises."""
        arguments_list = []

        for conclusion in conclusions:
            premises = self.extract_premises(text, conclusion)
            arguments_list.append(
                {
                    "conclusion": conclusion,
                    "premises": premises,
                },
            )

        return arguments_list

    # ---------------------------- Batch Processing --------------------------

    def process_batch(
        self,
        articles: list[dict[str, Any]],
        *,
        text_column: str = "text",
        id_column: str | None = None,
        output_dir: str | Path = "data/interim",
    ) -> list[DirectExtractionResult]:
        """
        Process multiple articles using batch API.

        Args:
            articles: List of article dicts with text content.
            text_column: Column name containing article text.
            id_column: Column name containing article IDs.
            output_dir: Directory to save batch files.

        Returns:
            List of DirectExtractionResult objects.

        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        self._log(f"Processing {len(articles)} articles in batch mode...")

        # Two phases: conclusions -> premises
        phase1_results = self._batch_phase1(articles, text_column, output_dir)
        phase2_results = self._batch_phase2(
            articles,
            phase1_results,
            text_column,
            output_dir,
        )

        config = _BatchConfig(
            articles=articles,
            phase_results={
                "phase1": phase1_results,
                "phase2": phase2_results,
            },
            text_column=text_column,
            id_column=id_column,
        )
        return self._combine_results(config)

    def _batch_phase1(
        self,
        articles: list[dict[str, Any]],
        text_column: str,
        output_dir: Path,
    ) -> list[dict[str, Any]]:
        """Phase 1: Extract conclusions."""
        self._log("Phase 1: Conclusion extraction...")

        requests = [
            build_batch_request(
                custom_id=f"c_{i}",
                prompt=self.conclusion_extraction_prompt.format(
                    text=article[text_column],
                ),
                model=self.model,
                temperature=0.1,
            )
            for i, article in enumerate(articles)
            if text_column in article
        ]

        batch_file = output_dir / "phase1_conclusions.jsonl"
        status = self.client.send_batch(requests, batch_file)
        return self._wait_for_batch(status.job_id)

    def _batch_phase2(
        self,
        articles: list[dict[str, Any]],
        phase1_results: list[dict[str, Any]],
        text_column: str,
        output_dir: Path,
    ) -> list[dict[str, Any]]:
        """Phase 2: Extract premises for each conclusion."""
        self._log("Phase 2: Premise extraction...")

        conclusions_map = self._build_conclusions_map(phase1_results)
        requests = []

        for i, article in enumerate(articles):
            if text_column not in article:
                continue

            text = article[text_column]
            conclusions = conclusions_map.get(f"c_{i}", [])

            for j, conclusion in enumerate(conclusions):
                requests.append(
                    build_batch_request(
                        custom_id=f"p_{i}_{j}",
                        prompt=self.premise_extraction_prompt.format(
                            text=text,
                            conclusion=conclusion,
                        ),
                        model=self.model,
                        temperature=0.1,
                    ),
                )

        if not requests:
            self._log("No valid conclusions extracted in Phase 1", "warning")
            return []

        batch_file = output_dir / "phase2_premises.jsonl"
        status = self.client.send_batch(requests, batch_file)
        return self._wait_for_batch(status.job_id)

    def _wait_for_batch(self, batch_id: str) -> list[dict[str, Any]]:
        """Wait for batch completion and return results."""
        self._log(f"Batch job created: {batch_id}")

        status = self.client.check_batch(batch_id)
        while not status.is_complete:
            time.sleep(30)
            status = self.client.check_batch(batch_id)
            self._log(f"Status: {status.status}")

        return self.client.get_batch_results(batch_id)

    def _build_conclusions_map(
        self,
        phase1_results: list[dict[str, Any]],
    ) -> dict[str, list[str]]:
        """Build mapping of custom_id to conclusions."""
        conclusions_map = {}
        for result in phase1_results:
            custom_id = result.get("custom_id", "")
            content = extract_batch_result(result)
            if content:
                conclusions_map[custom_id] = self._parse_list_items(content)
        return conclusions_map

    def _combine_results(
        self,
        config: _BatchConfig,
    ) -> list[DirectExtractionResult]:
        """Combine all phase results into DirectExtractionResult objects."""
        conclusions_map = self._build_conclusions_map(
            config.phase_results["phase1"],
        )
        premises_map = self._build_premises_map(
            config.phase_results["phase2"],
        )

        results = []
        for i, article in enumerate(config.articles):
            article_id = (
                article.get(config.id_column) if config.id_column else None
            )
            text = article.get(config.text_column, "")

            result = DirectExtractionResult(text=text, article_id=article_id)
            conclusions = conclusions_map.get(f"c_{i}", [])
            result.conclusions = conclusions

            arguments_list = []
            for j, conclusion in enumerate(conclusions):
                premise_id = f"p_{i}_{j}"
                premises = premises_map.get(premise_id, [])

                arguments_list.append(
                    {
                        "conclusion": conclusion,
                        "premises": premises,
                    },
                )

            result.arguments = arguments_list
            result.success = len(arguments_list) > 0

            if not result.success:
                result.error_message = "No arguments extracted"

            results.append(result)

        return results

    def _build_premises_map(
        self,
        phase2_results: list[dict[str, Any]],
    ) -> dict[str, list[str]]:
        """Build mapping of custom_id to premises."""
        premises_map = {}
        for result in phase2_results:
            custom_id = result.get("custom_id", "")
            content = extract_batch_result(result)
            if content:
                premises_map[custom_id] = self._parse_list_items(content)
        return premises_map

    # ---------------------------- Helper Methods ----------------------------

    def _parse_list_items(self, text: str) -> list[str]:
        """Parse items from numbered or bulleted list."""
        items = []
        for raw_line in text.split("\n"):
            cleaned_line = raw_line.strip()
            if not cleaned_line:
                continue

            is_numbered = cleaned_line[0].isdigit() if cleaned_line else False
            is_bulleted = cleaned_line.startswith("-")

            if is_numbered or is_bulleted:
                if "." in cleaned_line:
                    item = cleaned_line.split(".", 1)[-1].strip()
                else:
                    item = cleaned_line

                item = item.lstrip("- ").strip()
                if item:
                    items.append(item)

        return items

    def _log(self, message: str, level: str = "info") -> None:
        """Log message if logger is available."""
        if self.logger:
            if level == "warning":
                self.logger.warning(message)
            else:
                self.logger.info(message)
