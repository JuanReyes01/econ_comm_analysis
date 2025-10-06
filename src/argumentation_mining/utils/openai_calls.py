"""Simple OpenAI API wrapper for single calls and batch processing."""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

try:
    from openai import OpenAI
except ImportError as e:
    msg = "Install openai package: uv add openai"
    raise ImportError(msg) from e


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class BatchJobStatus(BaseModel):
    """Batch job status information."""

    job_id: str
    status: str
    input_file_id: str
    output_file_id: str | None = None
    error_file_id: str | None = None

    @property
    def is_complete(self) -> bool:
        """Check if batch is in terminal state."""
        return self.status in {"completed", "failed", "expired", "cancelled"}


# ---------------------------------------------------------------------------
# OpenAI Client Wrapper
# ---------------------------------------------------------------------------


class OpenAIClient:
    """
    Simple wrapper for OpenAI API calls.

    Handles both single requests and batch processing.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
    ) -> None:
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key (reads from env if not provided).
            model: Default model to use.

        """
        load_dotenv()
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            msg = "OPENAI_API_KEY is required"
            raise ValueError(msg)

        self.client = OpenAI(api_key=api_key)
        self.model = model

    # --------------------------- Single Requests ----------------------------

    def call(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.0,
    ) -> str:
        """
        Make a single chat completion call.

        Args:
            prompt: The prompt text.
            model: Model to use (uses default if None).
            temperature: Sampling temperature.

        Returns:
            The completion text.

        """
        response = self.client.chat.completions.create(
            model=model or self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return response.choices[0].message.content or ""

    # ----------------------------- Batch API --------------------------------

    def send_batch(
        self,
        requests: list[dict],
        output_path: str | Path,
    ) -> BatchJobStatus:
        """
        Submit a batch of requests.

        Args:
            requests: List of request dicts in OpenAI batch format.
            output_path: Path to save the JSONL file.

        Returns:
            BatchJobStatus with job information.

        Example requests format:
            [
                {
                    "custom_id": "request-1",
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": "Hello"}],
                        "temperature": 0.1
                    }
                }
            ]

        """
        # Write JSONL file
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as f:
            for request in requests:
                f.write(json.dumps(request, ensure_ascii=False) + "\n")

        # Upload file
        with output_path.open("rb") as f:
            uploaded_file = self.client.files.create(file=f, purpose="batch")

        # Create batch job
        batch = self.client.batches.create(
            input_file_id=uploaded_file.id,
            endpoint="/v1/chat/completions",
            completion_window="24h",
        )

        return BatchJobStatus(
            job_id=batch.id,
            status=batch.status,
            input_file_id=uploaded_file.id,
            output_file_id=getattr(batch, "output_file_id", None),
            error_file_id=getattr(batch, "error_file_id", None),
        )

    def check_batch(self, job_id: str) -> BatchJobStatus:
        """
        Check the status of a batch job.

        Args:
            job_id: The batch job ID.

        Returns:
            Updated BatchJobStatus.

        """
        batch = self.client.batches.retrieve(job_id)
        return BatchJobStatus(
            job_id=batch.id,
            status=batch.status,
            input_file_id=batch.input_file_id,
            output_file_id=getattr(batch, "output_file_id", None),
            error_file_id=getattr(batch, "error_file_id", None),
        )

    def get_batch_results(self, job_id: str) -> list[dict]:
        """
        Retrieve results from a completed batch job.

        Args:
            job_id: The batch job ID.

        Returns:
            List of result dicts.

        """
        status = self.check_batch(job_id)

        if not status.output_file_id:
            return []

        content = self.client.files.content(status.output_file_id)
        text = content.text if hasattr(content, "text") else content.read()

        if isinstance(text, bytes):
            text = text.decode("utf-8")

        return [json.loads(line) for line in text.splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def build_batch_request(
    custom_id: str,
    prompt: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.2,
) -> dict:
    """
    Build a single batch request.

    Args:
        custom_id: Unique identifier for this request.
        prompt: The prompt text.
        model: Model to use.
        temperature: Sampling temperature.

    Returns:
        Request dict in OpenAI batch format.

    """
    return {
        "custom_id": custom_id,
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        },
    }


def extract_batch_result(result: dict) -> str:
    """
    Extract the completion text from a batch result.

    Args:
        result: A single result dict from batch results.

    Returns:
        The completion text.

    """
    try:
        body = result.get("response", {}).get("body", {})
        choices = body.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "").strip()
    except (KeyError, IndexError, AttributeError):
        pass
    return ""
