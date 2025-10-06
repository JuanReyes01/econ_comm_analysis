# ruff: noqa: T201
"""Test script for OpenAI API integration - single and batch calls."""

from __future__ import annotations

from pathlib import Path
import time
import traceback

from argumentation_mining.utils.openai_calls import (
    OpenAIClient,
    build_batch_request,
    extract_batch_result,
)


def test_single_call() -> None:
    """Test a single API call."""
    print("\n" + "=" * 70)
    print("TEST 1: Single API Call")
    print("=" * 70)

    client = OpenAIClient(model="gpt-4o-mini")

    prompt = "Say 'Hello from OpenAI!' in exactly those words."
    print(f"\nPrompt: {prompt}")

    print("\nCalling API...")
    response = client.call(prompt, temperature=0.0)

    print(f"Response: {response}")
    print("\nSingle call test completed!")


def test_batch_call() -> None:
    """Test batch API submission and checking."""
    print("\n" + "=" * 70)
    print("TEST 2: Batch API Call")
    print("=" * 70)

    client = OpenAIClient(model="gpt-4o-mini")

    # Create test requests
    prompts = [
        "What is 1+1? Answer with just the number.",
        "What is 2+2? Answer with just the number.",
        "What is 3+3? Answer with just the number.",
    ]

    print(f"\nCreating {len(prompts)} batch requests...")
    requests = [
        build_batch_request(
            custom_id=f"math_{i}",
            prompt=prompt,
            model="gpt-4o-mini",
            temperature=0.0,
        )
        for i, prompt in enumerate(prompts)
    ]

    # Submit batch
    output_path = Path("./data/interim/test_batch.jsonl")
    print(f"\nSubmitting batch to: {output_path}")

    job = client.send_batch(requests=requests, output_path=output_path)

    print("\nBatch submitted successfully!")
    print(f"   Job ID: {job.job_id}")
    print(f"   Status: {job.status}")
    print(f"   Input File ID: {job.input_file_id}")

    # Check status
    print("\nChecking batch status...")
    status = client.check_batch(job.job_id)
    print(f"   Current status: {status.status}")
    print(f"   Is complete: {status.is_complete}")

    # Note about completion
    print("\nNote: Batch processing can take up to 24 hours.")
    print("   To check status later, use:")
    print(f"   >>> client.check_batch('{job.job_id}')")
    print("\n   To get results when complete:")
    print(f"   >>> results = client.get_batch_results('{job.job_id}')")

    # If you want to wait and poll (not recommended for long batches)
    if input("\nWait and poll for completion? (y/N): ").lower() == "y":
        print("\nPolling every 10 seconds (press Ctrl+C to stop)...")
        try:
            while not status.is_complete:
                time.sleep(10)
                status = client.check_batch(job.job_id)
                print(f"   Status: {status.status}")

            if status.status == "completed":
                print("\nBatch completed! Getting results...")
                results = client.get_batch_results(job.job_id)

                print(f"\nResults ({len(results)} items):")
                for result in results:
                    custom_id = result.get("custom_id", "unknown")
                    answer = extract_batch_result(result)
                    print(f"   {custom_id}: {answer}")
            else:
                print(f"\nBatch ended with status: {status.status}")

        except KeyboardInterrupt:
            print("\n\nPolling interrupted by user.")
            print(f"Job ID for later: {job.job_id}")

    print("\nBatch test completed!")


def test_batch_result_retrieval() -> None:
    """Test retrieving results from an existing batch job."""
    print("\n" + "=" * 70)
    print("TEST 3: Retrieve Existing Batch Results")
    print("=" * 70)

    job_id = input("\nEnter batch job ID (or press Enter to skip): ").strip()

    if not job_id:
        print("Skipped")
        return

    client = OpenAIClient()

    print(f"\nChecking status for job: {job_id}")
    status = client.check_batch(job_id)

    print(f"   Status: {status.status}")
    print(f"   Is complete: {status.is_complete}")

    if status.is_complete and status.status == "completed":
        print("\nRetrieving results...")
        results = client.get_batch_results(job_id)

        print(f"\nResults ({len(results)} items):")
        for result in results:
            custom_id = result.get("custom_id", "unknown")
            answer = extract_batch_result(result)
            print(f"   {custom_id}: {answer}")

        print("\nResults retrieved!")
    elif status.is_complete:
        print(f"\nBatch ended with status: {status.status}")
    else:
        print(f"\nBatch still processing (status: {status.status})")


def main() -> None:
    """Run all tests."""
    print("=" * 70)
    print("OpenAI API Integration Test Suite")
    print("=" * 70)
    print("\nMake sure you have:")
    print("  1. Set OPENAI_API_KEY in .env file")
    print("  2. Installed dependencies: uv add openai pydantic python-dotenv")

    try:
        # Test 1: Single call
        test_single_call()

        # Test 2: Batch submission
        proceed = input("\nRun batch test? (Y/n): ").lower()
        if proceed != "n":
            test_batch_call()

        # Test 3: Retrieve existing batch
        proceed = input(
            "\nRetrieve results from existing batch? (y/N): ",
        ).lower()
        if proceed == "y":
            test_batch_result_retrieval()

        print("\n" + "=" * 70)
        print("All tests completed!")
        print("=" * 70)

    except ValueError as e:
        print(f"\nConfiguration Error: {e}")
        print("\nMake sure OPENAI_API_KEY is set in your .env file:")
        print("  OPENAI_API_KEY=sk-your-key-here")

        print(f"\nError: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
