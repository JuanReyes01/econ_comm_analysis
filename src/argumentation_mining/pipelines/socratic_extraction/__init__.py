"""Socratic question-answer argumentation mining pipeline."""

from .socratic_extraction import QAArgumentExtractor, QAResult

__all__ = [
    "QAArgumentExtractor",
    "QAResult",
]
