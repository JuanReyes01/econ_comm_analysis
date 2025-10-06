# ruff: noqa: T201

"""Example usage of the Socratic extraction pipeline."""

from argumentation_mining.pipelines.socratic_extraction import (
    QAArgumentExtractor,
)


def main() -> None:
    """Run example extraction pipeline."""
    # Initialize extractor
    extractor = QAArgumentExtractor(model="gpt-4o-mini")

    # Example 1: Process single article
    print("=" * 60)
    print("Example 1: Single Article Processing")
    print("=" * 60)

    sample_text = """
    En días pasados, el presidente Gustavo Petro hizo un llamado a los
    jóvenes para que organizaran asambleas estudiantiles y participaran
    del debate que ha de conducir a la reforma a la educación superior
    en Colombia. Esta convocatoria resulta oportuna para mejorar los
    índices de gobernabilidad. La reforma de la Ley 30, que rige desde
    1992 los destinos de la educación superior, es una necesidad urgente
    si queremos superar la forma inequitativa como se distribuyen las
    oportunidades.
    """

    result = extractor.process_single(sample_text, article_id="example_1")

    print(f"\nSuccess: {result.success}")
    print(f"\nExtracted {len(result.questions)} questions:")
    for i, q in enumerate(result.questions or [], 1):
        print(f"  {i}. {q}")

    print(f"\nExtracted {len(result.arguments or [])} arguments:")
    for i, arg in enumerate(result.arguments or [], 1):
        print(f"\n  Argument {i}:")
        print(f"    Question: {arg['question']}")
        print(f"    Claim: {arg['claim']}")
        print(f"    Premises: {len(arg['premises'])}")

    # Example 2: Batch Processing
    print("\n" + "=" * 60)
    print("Example 2: Batch Processing Multiple Articles")
    print("=" * 60)

    # Create sample articles for batch processing
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

    print(f"\nProcessing {len(articles)} articles in batch mode...")
    print("Note: This uses OpenAI Batch API which takes time to complete.")

    # Uncomment to run batch processing:
    results = extractor.process_batch(
        articles=articles,
        text_column="text",
        id_column="id",
        output_dir="data/interim",
    )
    for result in results:
        print(f"\nArticle: {result.article_id}")
        print(f"Success: {result.success}")
        print(f"Arguments extracted: {len(result.arguments or [])}")


if __name__ == "__main__":
    main()
