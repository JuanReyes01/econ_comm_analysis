# ruff: noqa: T201

"""Example of using the Direct Extraction pipeline for argument mining."""

from __future__ import annotations

from argumentation_mining.pipelines.direct_extraction import (
    DirectArgumentExtractor,
)


def main() -> None:
    """Demonstrate direct extraction on a sample text."""
    # Initialize the extractor
    extractor = DirectArgumentExtractor(model="gpt-4o-mini")

    # Sample text in Spanish (from the paper examples)
    sample_text = """La educación virtual es más efectiva que la presencial.
Los estudiantes pueden aprender a su propio ritmo y tienen acceso a
recursos digitales ilimitados. Además, elimina las barreras geográficas
y permite a estudiantes de áreas rurales acceder a educación de calidad."""

    print("=" * 70)
    print("Direct Extraction Example")
    print("=" * 70)
    print(f"\nOriginal text:\n{sample_text}\n")

    # Process the text
    result = extractor.process_single(text=sample_text, article_id="example_1")

    # Display results
    if result.success:
        print("Extraction successful!\n")

        print("Conclusions extracted:")
        if result.conclusions:
            for i, conclusion in enumerate(result.conclusions, 1):
                print(f"  {i}. {conclusion}")
        else:
            print("  None")

        print("\nArguments (Conclusion-Premise pairs):")
        if result.arguments:
            for i, arg in enumerate(result.arguments, 1):
                print(f"\n  Argument {i}:")
                print(f"    Conclusion: {arg['conclusion']}")
                print("    Premises:")
                if arg["premises"]:
                    for j, premise in enumerate(arg["premises"], 1):
                        print(f"      {j}. {premise}")
                else:
                    print("      None")
        else:
            print("  None")
    else:
        print(f"Extraction failed: {result.error_message}")

    print("\n" + "=" * 70)

    # batch
    print("Batch Processing Example")
    articles = [
        {
            "id": "article_1",
            "text": """La educación es un derecho fundamental que debe ser
            accesible para todos los ciudadanos.""",
        },
        {
            "id": "article_2",
            "text": """El cambio climático representa una amenaza seria
            que requiere acción inmediata.""",
        },
    ]

    # Process the batch
    results = extractor.process_batch(articles)

    # Display batch results
    for result in results:
        if result.success:
            print(f"Extraction successful for article {result.article_id}!\n")

            print("Conclusions extracted:")
            if result.conclusions:
                for i, conclusion in enumerate(result.conclusions, 1):
                    print(f"  {i}. {conclusion}")
            else:
                print("  None")

            print("\nArguments (Conclusion-Premise pairs):")
            if result.arguments:
                for i, arg in enumerate(result.arguments, 1):
                    print(f"\n  Argument {i}:")
                    print(f"    Conclusion: {arg['conclusion']}")
                    print("    Premises:")
                    if arg["premises"]:
                        for j, premise in enumerate(arg["premises"], 1):
                            print(f"      {j}. {premise}")
                    else:
                        print("      None")
            else:
                print("  None")
        else:
            print(
                f"Extraction failed for article \
                  {result.article_id}: {result.error_message}"
            )


if __name__ == "__main__":
    main()
