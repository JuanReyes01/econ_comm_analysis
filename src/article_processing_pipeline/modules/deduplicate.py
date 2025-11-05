import os
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from datasketch import MinHash, MinHashLSH
import gc

def deduplicate_articles(df: pd.DataFrame, column: str = 'texto_completo') -> pd.DataFrame:
    """
    Deduplicates articles using MinHash and LSH on a given text column.
    If duplicate_indices.csv exists, uses that instead of recalculating.
    """
    dir_path = './data/interim/duplicate_indices.csv'
    if os.path.isfile(dir_path):
        print("Found duplicate_indices.csv. Using it to remove duplicates.")
        duplicate_indices = pd.read_csv(dir_path, header=None)[0].tolist()
        duplicate_indices = list(map(int, duplicate_indices))
        mask = [i not in duplicate_indices for i in range(len(df))]
        df_clean = df.iloc[mask].reset_index(drop=True)
        print(f"Original: {df.shape[0]} articles | Cleaned: {df_clean.shape[0]} articles")
        return df_clean

    print("Loading SentenceTransformer model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')

    num_perm = 64
    lsh_threshold = 0.9
    lsh = MinHashLSH(threshold=lsh_threshold, num_perm=num_perm)

    def create_minhash(embedding):
        m = MinHash(num_perm=num_perm)
        for value in embedding:
            m.update(value.tobytes())
        return m

    articles = df[column].astype(str)
    unique_indices = []
    duplicate_indices = set()

    print("Processing articles sequentially...")
    tot = len(articles)
    i = 1
    for idx, article in enumerate(articles):
        print(f"Processing {i}/{tot}")
        try:
            embedding = model.encode([article], show_progress_bar=False, batch_size=1)
        except Exception as e:
            print(f"Error processing article {idx}: {e}")
            continue

        embedding = np.array(embedding, dtype=np.float16)[0]
        mh = create_minhash(embedding)
        similar = lsh.query(mh)

        if similar:
            duplicate_indices.add(idx)
        else:
            lsh.insert(idx, mh)
            unique_indices.append(idx)

        del embedding, mh
        if idx % 1000 == 0 and idx > 0:
            gc.collect()
        if idx % 10000 == 0 and idx > 0:
            print(f"Processed {idx} articles...")
        i += 1

    print("Processing completed.")
    print(f"Total articles: {len(articles)}")
    print(f"Unique articles: {len(unique_indices)}")
    print(f"Duplicate articles: {len(duplicate_indices)}")

    df_clean = df.iloc[unique_indices].reset_index(drop=True)

    # Save for future re-use
    df_clean.to_csv('./data/interim/clean_articles.csv', index=False)
    pd.Series(unique_indices).to_csv('./data/interim/unique_indices.csv', index=False)
    pd.Series(list(duplicate_indices)).to_csv('./data/interim/duplicate_indices.csv', index=False)

    return df_clean
