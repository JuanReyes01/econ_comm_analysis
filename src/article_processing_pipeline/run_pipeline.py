# run_pipeline.py

import pandas as pd
from pathlib import Path

from src.data.make_dataset import load_data
from src.data.clean_dataset import clean_data
from src.data.authors import process_authors, standardize_author_names
from src.data.deduplicate import deduplicate_articles
from src.data.tags import extract_tags

# Optional: Set paths
RAW_DATA_PATH = Path("data/raw/articulos_proquest_raw.csv")
PROCESSED_PATH = Path("data/processed/")
PROCESSED_PATH.mkdir(parents=True, exist_ok=True)

def main():
    print("Starting data pipeline...")

    # Step 1: Load data
    print("Loading raw data...")
    df_raw = load_data(RAW_DATA_PATH)

    # Step 2: Basic column cleanup and filtering
    print("Cleaning dataset...")
    df_clean = clean_data(df_raw)
    df_clean.reset_index(drop=True, inplace=True)
    df_clean['id_articulo'] = range(len(df_clean))


    # Step 3: Extract and explode author entities
    print("Processing author names...")
    df_clean, df_autores_raw, rel_autores_raw = process_authors(df_clean)

    # Step 4: Deduplicate & normalize author identities
    print("Standardizing author identities...")
    df_autores_final, rel_autores_final = standardize_author_names(df_autores_raw)

    # Step 5: Deduplicate articles using MinHash / LSH
    print("Deduplicating articles...")
    df_deduped = deduplicate_articles(df_clean, column='texto_completo')

    # Step 6: Tag processing (e.g., materia, personas, empresa)
    print("Extracting tag relationships...")

    df_tagged, tag_df, rel_tags = extract_tags(df_deduped)
    

    # Step 7: Save outputs
    print("Saving processed datasets...")
    df_tagged.to_csv(PROCESSED_PATH / "articles.csv", index=False)
    df_autores_final.to_csv(PROCESSED_PATH / "authors.csv", index=False)
    rel_autores_final.to_csv(PROCESSED_PATH / "rel_authors.csv", index=False)
    tag_df.to_csv(PROCESSED_PATH / "tags.csv", index=False)
    rel_tags.to_csv(PROCESSED_PATH / "rel_tags.csv", index=False)

    print("✅ Pipeline finished successfully.")


if __name__ == "__main__":
    main()
