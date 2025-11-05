import pandas as pd
import torch
import re
from gliner import GLiNER
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN

DEFAULT_AUTHOR_HEURISTIC_KEYWORDS = [
    # non-person orgs
    "editorial", "press", "news", "bureau", "staff", "team", "times", "media",
    "university", "school", "department", "foundation", "center", "centre",
    "institute", "committee", "council", "network", "desk", "journal", "Today"

    # roles / contributors
    "guest", "contributor", "columnist", "reporter", "editor", "journalist",

    # delimiters / plural signals
    ";", " and ", "/", "with", "by"
]

def fix_capitalization(name: str) -> str:
    return ' '.join([
        part.capitalize() if part.isupper() else part
        for part in re.split(r'(\s+)', name)
    ])

def should_apply_ner(text: str) -> bool:
    """
    Decide if GLiNER should be used based on keywords and structure.
    """
    if not isinstance(text, str):
        return False

    text_clean = text.lower()
    keyword_hit = any(kw in text_clean for kw in DEFAULT_AUTHOR_HEURISTIC_KEYWORDS)
    all_caps = text.isupper()
    too_short = len(text.strip()) < 5
    too_long = len(text.strip().split()) > 6
    contains_symbols = any(sym in text for sym in [';', '/', ' and ', '#'])

    return keyword_hit or all_caps or too_short or too_long or contains_symbols

def process_authors(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df = df.copy()
    assert 'id_articulo' in df.columns, "df must have 'id_articulo' before running process_authors()"

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model_gliner = GLiNER.from_pretrained("urchade/gliner_multi_pii-v1").to(device)

    author_lists = []
    for i, autor in enumerate(df['autor'], start=1):
        print(f"processing: {i}/{len(df)}")

        if pd.isna(autor) or autor.strip() == "":
            author_lists.append([])
            continue

        autor = str(autor).strip()
        if should_apply_ner(autor):
            print(f"NER is applied to: {autor}")
            try:
                entities = model_gliner.predict_entities(fix_capitalization(autor), ['Person'])
                authors = [fix_capitalization(e["text"]) for e in entities if e["label"] == "Person"]
                print(f"Result: {authors}")
            except Exception as e:
                print(f"[GLiNER ERROR] Fallback failed on: {autor} — {e}")
                authors = []
        else:
            authors = [fix_capitalization(name.strip()) for name in autor.split(';') if name.strip()]

        author_lists.append(authors)

    # Explode authors
    df_autores = df[['id_articulo']].copy()
    df_autores['autor'] = author_lists
    df_autores = df_autores.explode('autor').dropna()
    df_autores = df_autores[df_autores['autor'].str.split().apply(len) > 1]

    # Create unique author mapping
    unique_authors = pd.DataFrame(df_autores['autor'].unique(), columns=['autor'])
    unique_authors['id_autor'] = unique_authors.index

    # Article-author relationship
    relacion_autores = df_autores.merge(unique_authors, on='autor')[['id_articulo', 'id_autor']]

    # Keep only valid articles
    valid_articles = relacion_autores['id_articulo'].unique()
    df = df[df['id_articulo'].isin(valid_articles)].reset_index(drop=True)

    print(f"Identified {len(unique_authors)} raw authors before deduplication (NER + split)")
    return df, df_autores, relacion_autores

def preprocess_author_strings(df_autores: pd.DataFrame) -> pd.DataFrame:
    names = df_autores['autor'].str.split(', ', expand=True)

    if names.shape[1] < 2:
        df_autores['author_name'] = df_autores['autor'].str.strip()
        return df_autores

    split1 = names[1].str.split(';', n=1, expand=True)
    names[1] = split1[0].str.strip()

    if 2 in names.columns:
        names[2] = (
            split1[1].fillna('')
            .str.strip()
            .where(split1[1].notna(), '')
            .add('; ' + names[2].fillna(''))
            .str.strip('; ')
        )
    else:
        names[2] = split1[1].fillna('').str.strip()

    def normalize_names(row):
        if pd.notnull(row[1]):
            base = f"{row[1].strip('.;')} {row[0].strip(';. ')}"
            return f"{base} {row[2].strip(';.')}" if pd.notnull(row[2]) else base
        return row[0]

    names[0] = names.apply(normalize_names, axis=1)
    names = names.rename(columns={0: 'author_name'})
    names['author_name'] = names['author_name'].str.replace(r'\s+', ' ', regex=True)
    names['author_name'] = names['author_name'].str.replace('\t', ' ')
    names['author_name'] = names['author_name'].str.strip()

    df_autores = df_autores.copy()
    df_autores['author_name'] = names['author_name']
    return df_autores

def cluster_author_names(author_names: pd.Series, threshold: float = 0.85) -> dict:
    names = author_names.dropna().unique().tolist()
    if not names:
        return {}

    vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4))
    tfidf_matrix = vectorizer.fit_transform(names)

    db = DBSCAN(eps=1 - threshold, min_samples=1, metric='cosine').fit(tfidf_matrix)
    labels = db.labels_

    clusters = {}
    for label, name in zip(labels, names):
        clusters.setdefault(label, []).append(name)

    canonical_map = {}
    for group in clusters.values():
        canonical = min(group, key=len)
        for alias in group:
            canonical_map[alias] = canonical

    return canonical_map

def filter_invalid_authors(df_authors: pd.DataFrame) -> pd.DataFrame:
    def is_valid(name):
        if not isinstance(name, str):
            return False
        name = name.strip()
        if len(name.split()) < 2:
            return False
        if name.isupper():
            return False
        if re.search(r'[|/#]', name):
            return False
        if name.lower() in {'staff', 'editorial', 'press', 'guest'}:
            return False
        junk_terms = ['foundation', 'team', 'house', 'board', 'reporters']
        return not any(kw in name.lower() for kw in junk_terms)

    return df_authors[df_authors['autor'].apply(is_valid)].reset_index(drop=True)

def standardize_author_names(df_autores: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df_autores = preprocess_author_strings(df_autores)
    mapping = cluster_author_names(df_autores['author_name'])

    df_autores['autor'] = df_autores['author_name'].map(mapping)
    df_autores.drop(columns=['author_name'], inplace=True)

    # Final filter to remove junk
    df_autores = filter_invalid_authors(df_autores)

    unique_authors = df_autores['autor'].dropna().unique()
    df_clean = pd.DataFrame(unique_authors, columns=['autor'])
    df_clean['id_autor'] = df_clean.index

    relacion_autores = df_autores.merge(df_clean, on='autor')[['id_articulo', 'id_autor']]

    print(f"Final deduplicated authors: {len(df_clean)}")
    return df_clean, relacion_autores
