"""
Socratic Question-Answer Argumentation Mining Implementation.

Implements a three-phase pipeline:
1. Extract questions from text using few-shot prompting
2. Answer questions using full article context
3. Convert Q&A pairs to argument structure (claim + premises)
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
class QAResult:
    """Results from question-answer argumentation extraction."""

    text: str
    article_id: str | None = None
    questions: list[str] | None = None
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


class QAArgumentExtractor:
    """
    Socratic question-answer based argument extraction.

    Pipeline:
    1. Extract questions from text
    2. Answer questions using full article
    3. Convert Q&A pairs to argument structure
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

        self.question_extraction_prompt = prompts_data["question_extraction"]
        self.question_answering_prompt = prompts_data["question_answering"]
        self.argument_construction_prompt = prompts_data[
            "argument_construction"
        ]

    # --------------------------- Single Processing --------------------------

    def extract_questions(self, text: str) -> list[str]:
        """Extract questions from text."""
        prompt = self.question_extraction_prompt.format(text=text)
        response = self.client.call(prompt, temperature=0.1)
        return self._parse_questions(response)

    def answer_question(self, question: str, article: str) -> str:
        """Answer a question using full article."""
        prompt = self.question_answering_prompt.format(
            question=question,
            article=article,
        )
        return self.client.call(prompt, temperature=0.1)

    def construct_argument(
        self,
        question: str,
        answer: str,
    ) -> dict[str, Any]:
        """Construct argument from Q&A pair."""
        prompt = self.argument_construction_prompt.format(
            question=question,
            answer=answer,
        )
        response = self.client.call(prompt, temperature=0.1)
        return self._parse_argument(response)

    def process_single(
        self,
        text: str,
        article_id: str | None = None,
    ) -> QAResult:
        """
        Process a single article synchronously.

        Args:
            text: The article text.
            article_id: Optional article identifier.

        Returns:
            QAResult with extracted information.

        """
        result = QAResult(text=text, article_id=article_id)

        try:
            result.questions = self.extract_questions(text)
            result.arguments = self._process_questions(
                result.questions,
                text,
            )
            result.success = True

        except (ValueError, KeyError, RuntimeError) as e:
            result.error_message = str(e)

        return result

    def _process_questions(
        self,
        questions: list[str],
        text: str,
    ) -> list[dict[str, Any]]:
        """Process questions to generate arguments."""
        arguments_list = []

        for question in questions:
            answer = self.answer_question(question, text)
            arg = self.construct_argument(question, answer)
            arguments_list.append(
                {
                    "question": question,
                    "answer": answer,
                    "claim": arg["claim"],
                    "premises": arg["premises"],
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
    ) -> list[QAResult]:
        """
        Process multiple articles using batch API.

        Args:
            articles: List of article dicts with text content.
            text_column: Column name containing article text.
            id_column: Column name containing article IDs.
            output_dir: Directory to save batch files.

        Returns:
            List of QAResult objects.

        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        self._log(f"Processing {len(articles)} articles in batch mode...")

        # Three phases: questions -> answers -> arguments
        phase1_results = self._batch_phase1(articles, text_column, output_dir)
        phase2_results = self._batch_phase2(
            articles,
            phase1_results,
            text_column,
            output_dir,
        )
        phase3_results = self._batch_phase3(
            articles,
            phase1_results,
            phase2_results,
            text_column,
            output_dir,
        )

        config = _BatchConfig(
            articles=articles,
            phase_results={
                "phase1": phase1_results,
                "phase2": phase2_results,
                "phase3": phase3_results,
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
        """Phase 1: Extract questions."""
        self._log("Phase 1: Question extraction...")

        requests = [
            build_batch_request(
                custom_id=f"q_{i}",
                prompt=self.question_extraction_prompt.format(
                    text=article[text_column],
                ),
                model=self.model,
                temperature=0.1,
            )
            for i, article in enumerate(articles)
            if text_column in article
        ]

        batch_file = output_dir / "phase1_questions.jsonl"
        status = self.client.send_batch(requests, batch_file)
        return self._wait_for_batch(status.job_id)

    def _batch_phase2(
        self,
        articles: list[dict[str, Any]],
        phase1_results: list[dict[str, Any]],
        text_column: str,
        output_dir: Path,
    ) -> list[dict[str, Any]]:
        """Phase 2: Answer questions."""
        self._log("Phase 2: Question answering...")

        questions_map = self._build_questions_map(phase1_results)
        requests = []

        for i, article in enumerate(articles):
            if text_column not in article:
                continue

            text = article[text_column]
            questions = questions_map.get(f"q_{i}", [])

            for j, question in enumerate(questions):
                requests.append(
                    build_batch_request(
                        custom_id=f"qa_{i}_{j}",
                        prompt=self.question_answering_prompt.format(
                            question=question,
                            article=text,
                        ),
                        model=self.model,
                        temperature=0.1,
                    ),
                )

        if not requests:
            self._log("No valid questions extracted in Phase 1", "warning")
            return []

        batch_file = output_dir / "phase2_answers.jsonl"
        status = self.client.send_batch(requests, batch_file)
        return self._wait_for_batch(status.job_id)

    def _batch_phase3(
        self,
        articles: list[dict[str, Any]],
        phase1_results: list[dict[str, Any]],
        phase2_results: list[dict[str, Any]],
        text_column: str,
        output_dir: Path,
    ) -> list[dict[str, Any]]:
        """Phase 3: Construct arguments."""
        self._log("Phase 3: Argument construction...")

        questions_map = self._build_questions_map(phase1_results)
        answers_map = self._build_answers_map(phase2_results)
        requests = []

        for i, article in enumerate(articles):
            if text_column not in article:
                continue

            questions = questions_map.get(f"q_{i}", [])

            for j, question in enumerate(questions):
                qa_id = f"qa_{i}_{j}"
                answer = answers_map.get(qa_id)

                if answer:
                    requests.append(
                        build_batch_request(
                            custom_id=f"arg_{i}_{j}",
                            prompt=self.argument_construction_prompt.format(
                                question=question,
                                answer=answer,
                            ),
                            model=self.model,
                            temperature=0.1,
                        ),
                    )

        if not requests:
            self._log("No valid Q&A pairs from Phase 2", "warning")
            return []

        batch_file = output_dir / "phase3_arguments.jsonl"
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

    def _build_questions_map(
        self,
        phase1_results: list[dict[str, Any]],
    ) -> dict[str, list[str]]:
        """Build mapping of custom_id to questions."""
        questions_map = {}
        for result in phase1_results:
            custom_id = result.get("custom_id", "")
            content = extract_batch_result(result)
            if content:
                questions_map[custom_id] = self._parse_questions(content)
        return questions_map

    def _build_answers_map(
        self,
        phase2_results: list[dict[str, Any]],
    ) -> dict[str, str]:
        """Build mapping of custom_id to answers."""
        answers_map = {}
        for result in phase2_results:
            custom_id = result.get("custom_id", "")
            content = extract_batch_result(result)
            if content:
                answers_map[custom_id] = content
        return answers_map

    def _combine_results(self, config: _BatchConfig) -> list[QAResult]:
        """Combine all phase results into QAResult objects."""
        questions_map = self._build_questions_map(
            config.phase_results["phase1"],
        )
        answers_map = self._build_answers_map(config.phase_results["phase2"])
        arguments_map = self._build_arguments_map(
            config.phase_results["phase3"],
        )

        results = []
        for i, article in enumerate(config.articles):
            article_id = (
                article.get(config.id_column) if config.id_column else None
            )
            text = article.get(config.text_column, "")

            result = QAResult(text=text, article_id=article_id)
            questions = questions_map.get(f"q_{i}", [])
            result.questions = questions

            arguments_list = []
            for j, question in enumerate(questions):
                qa_id = f"qa_{i}_{j}"
                arg_id = f"arg_{i}_{j}"

                answer = answers_map.get(qa_id)
                arg = arguments_map.get(arg_id)

                if answer and arg:
                    arguments_list.append(
                        {
                            "question": question,
                            "answer": answer,
                            "claim": arg["claim"],
                            "premises": arg["premises"],
                        },
                    )

            result.arguments = arguments_list
            result.success = len(arguments_list) > 0

            if not result.success:
                result.error_message = "No arguments extracted"

            results.append(result)

        return results

    def _build_arguments_map(
        self,
        phase3_results: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        """Build mapping of custom_id to arguments."""
        arguments_map = {}
        for result in phase3_results:
            custom_id = result.get("custom_id", "")
            content = extract_batch_result(result)
            if content:
                arguments_map[custom_id] = self._parse_argument(content)
        return arguments_map

    # ---------------------------- Helper Methods ----------------------------

    def _parse_questions(self, text: str) -> list[str]:
        """Parse questions from numbered list."""
        questions = []
        for raw_line in text.split("\n"):
            cleaned_line = raw_line.strip()
            if not cleaned_line:
                continue

            is_numbered = cleaned_line[0].isdigit()
            is_bulleted = cleaned_line.startswith("-")

            if is_numbered or is_bulleted:
                if "." in cleaned_line:
                    question = cleaned_line.split(".", 1)[-1].strip()
                else:
                    question = cleaned_line

                question = question.lstrip("- ").strip()
                if question:
                    questions.append(question)

        return questions[:10]

    def _parse_argument(self, text: str) -> dict[str, Any]:
        """Parse argument structure from text."""
        lines = text.split("\n")
        claim = ""
        premises = []

        current_section = None
        for raw_line in lines:
            cleaned_line = raw_line.strip()
            if cleaned_line.startswith("Claim:"):
                claim = cleaned_line.split(":", 1)[-1].strip()
                current_section = "claim"
            elif cleaned_line.startswith("Premises:"):
                current_section = "premises"
            elif current_section == "premises" and cleaned_line:
                is_numbered = cleaned_line[0].isdigit()
                is_bulleted = cleaned_line.startswith("-")

                if is_numbered or is_bulleted:
                    if "." in cleaned_line:
                        premise = cleaned_line.split(".", 1)[-1].strip()
                    else:
                        premise = cleaned_line

                    premise = premise.lstrip("- ").strip()
                    if premise:
                        premises.append(premise)

        return {"claim": claim, "premises": premises}

    def _log(self, message: str, level: str = "info") -> None:
        """Log message if logger is available."""
        if self.logger:
            if level == "warning":
                self.logger.warning(message)
            else:
                self.logger.info(message)
