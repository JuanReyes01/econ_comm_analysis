# Article Processing Pipeline (ET Pipeline)

## What is an ETL/ET Pipeline?

**ETL** stands for **Extract, Transform, Load**:
- **Extract**: Get data from source systems
- **Transform**: Clean, validate, and reshape the data
- **Load**: Store the processed data into a database

This pipeline is technically an **ET pipeline** because there's no "Load" step into a database like PostgreSQL or MySQL. Instead, we just save the transformed data back into CSV files (haha). But the Extract and Transform steps are fully implemented and robust.

Also technically the extract is actually the scraper but we are beign **that** technical are we?
---

## Pipeline Overview

This pipeline processes raw article data scraped from ProQuest, performing entity extraction, deduplication, normalization, and relationship building. The goal is to convert messy, real-world data into clean, structured tables ready for analysis.

**Input**: `data/raw/articulos_proquest_raw.csv`  
**Outputs** (saved to `data/processed/`):
- `articles.csv` - Cleaned and deduplicated articles
- `authors.csv` - Unique author entities with IDs
- `rel_authors.csv` - Article-author relationships (many-to-many)
- `tags.csv` - Unique tags (topics, companies, people, locations)
- `rel_tags.csv` - Article-tag relationships (many-to-many)

---

## Pipeline Architecture

The pipeline follows a sequential data flow orchestrated by `run_pipeline.py`:

```
Raw Data → Load → Clean → Author Extraction → Author Normalization 
         → Article Deduplication → Tag Extraction → Save Outputs
```

Each module is self-contained and handles a specific transformation step.

---

## Module Breakdown

### 1. `make_dataset.py` - Data Loading

**Problem**: Need a simple, reusable way to load the raw CSV data with error handling.

**Solution**:
```python
def load_data(path: str) -> pd.DataFrame
```

**What it does**:
- Loads the raw CSV file into a pandas DataFrame
- Handles file not found errors gracefully
- Prints the row count for verification

**Why this approach**: Keep it simple. A dedicated loader makes the pipeline modular and easier to test.

---

### 2. `clean_dataset.py` - Basic Data Cleaning

**Problem**: Raw scraped data has missing values, wrong data types, irrelevant columns, and non-English articles.

**Solution**:
```python
def clean_data(df: pd.DataFrame) -> pd.DataFrame
```

**What it does**:
1. Converts `fecha_de_publicacion` to datetime format
2. Fills missing titles with 'Unknown'
3. Drops rows missing critical fields (author, text, publication, date, etc.)
4. Filters to keep only English articles
5. Removes unnecessary columns (`resumen`, `seccion`, `url`, `copyright`, etc.)

**Why this approach**: 
- Ensures downstream modules work with complete, valid records
- Removes noise early to reduce processing overhead
- Language filtering ensures consistent analysis (English-only corpus)

---

### 3. `authors.py` - Author Entity Extraction & Normalization

**Problem**: Author names are inconsistent and messy:
- Multiple authors in one field, separated by `;` or `and`
- All-caps names: `JOHN SMITH`
- Organizations listed as authors: `Editorial Board`, `Staff Reporter`
- Name order variations: `Smith, John` vs `John Smith`
- Duplicate authors with slight variations: `J. Smith`, `John Smith`, `Smith John`

**Solution**: Multi-stage processing with NER and fuzzy matching.

#### Stage 1: Entity Extraction (`process_authors`)

**Heuristic-based NER triggering**:
```python
def should_apply_ner(text: str) -> bool
```
Decides whether to use GLiNER (deep learning NER model) based on:
- Presence of keywords like "editorial", "staff", "press", "university", etc.
- All-caps formatting
- Delimiter symbols (`;`, `/`, `and`)
- Suspicious length (too short or too long)

**Why this approach**: 
- GLiNER is expensive (GPU/CPU intensive), so only use it when needed
- Simple semicolon-split works fine for clean names
- NER catches real people when mixed with organizations

**Entity extraction**:
```python
model_gliner = GLiNER.from_pretrained("urchade/gliner_multi_pii-v1")
entities = model_gliner.predict_entities(text, ['Person'])
```
- Uses GLiNER multi-PII model trained to detect person entities
- Capitalizes names properly (`JOHN SMITH` → `John Smith`)
- Filters to keep only names with 2+ words (removes junk like "Staff")

**Output**:
- `df_autores`: exploded table with `id_articulo` and `autor` (one row per author-article pair)
- `unique_authors`: initial author list before deduplication
- `relacion_autores`: relationship table linking articles to authors

#### Stage 2: Name Normalization (`standardize_author_names`)

**Step 1: String preprocessing** (`preprocess_author_strings`)
- Handles "Last, First; Middle" format → "First Middle Last"
- Cleans extra whitespace and punctuation
- Example: `Smith, John; Michael` → `John Michael Smith`

**Step 2: Fuzzy clustering** (`cluster_author_names`)
```python
vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4))
db = DBSCAN(eps=1 - threshold, min_samples=1, metric='cosine')
```
- Uses **character n-grams** (2-4 chars) to represent names
- **DBSCAN clustering** groups similar names using cosine similarity
- Threshold: 0.85 (85% similarity required)
- Selects shortest name as canonical: `John Smith` beats `Smith, John A.`

**Why this approach**:
- Character-level TF-IDF catches typos and variations
- DBSCAN doesn't require pre-specifying number of clusters
- Cosine similarity handles name length differences gracefully

**Step 3: Filtering** (`filter_invalid_authors`)
Removes junk that slipped through:
- Single-word names
- All-caps names
- Names with special chars: `|`, `/`, `#`
- Organizational keywords: "foundation", "team", "board"

**Final output**:
- `df_clean`: Unique author table with `id_autor`
- `relacion_autores`: Clean article-author relationships

---

### 4. `deduplicate.py` - Article Deduplication

**Problem**: ProQuest scraping can result in duplicate articles with slight variations (formatting differences, metadata updates, typos).

**Challenge**: Exact string matching won't work. Need semantic similarity detection on large corpus (potentially thousands of articles).

**Solution**: MinHash + Locality-Sensitive Hashing (LSH)

```python
model = SentenceTransformer('all-MiniLM-L6-v2')
lsh = MinHashLSH(threshold=0.9, num_perm=64)
```

**How it works**:
1. **Embedding generation**: Convert full text to semantic embeddings using Sentence-BERT
2. **MinHash creation**: Create compact fingerprint (64 permutations) from embeddings
3. **LSH indexing**: Insert fingerprints into LSH index for fast similarity lookup
4. **Duplicate detection**: For each article, query LSH to find similar articles (>90% similar)
5. **Deduplication**: Keep first occurrence, mark others as duplicates

**Why this approach**:
- **Semantic understanding**: Catches duplicates even with minor text differences
- **Scalability**: LSH enables O(1) average-case lookup instead of O(n²) pairwise comparison
- **Memory efficiency**: MinHash compresses embeddings to 64 integers
- **Persistence**: Saves `duplicate_indices.csv` to avoid recomputation on reruns

**Optimization tricks**:
- Process sequentially to control memory usage
- Convert embeddings to float16 to save memory
- Garbage collection every 1000 articles
- Early return if duplicate_indices.csv exists (caching)

---

### 5. `tags.py` - Tag Extraction and Relationship Building

**Problem**: Articles have multiple metadata fields that should be treated as tags:
- `materia` - Subject matter (e.g., "Economics", "Trade Policy")
- `lugar_articulo` - Geographic locations mentioned
- `personas` - People mentioned in the article
- `empresa` - Companies mentioned (with "Nombre: " prefix to remove)

Need to extract these into a normalized tag table with many-to-many relationships.

**Solution**: Explode and normalize

**What it does**:
1. **Combine tag columns**: Merge all tag fields into one semicolon-separated list
2. **Clean company tags**: Remove `Nombre: ` prefix
3. **Explode**: Split on `;` and create one row per tag
4. **Clean**: Strip whitespace, remove empty/null values
5. **Create tag table**: Unique tags with `id_tags`
6. **Build relationships**: Map `id_articulo` → `id_tags`
7. **Filter articles**: Keep only articles with at least one valid tag

**Why this approach**:
- Pandas `explode()` handles the heavy lifting
- Centralized tag table avoids redundancy
- Relationship table enables efficient many-to-many queries
- Filtering ensures downstream analysis works with complete records

**Output**:
- `df_filtered`: Articles that have tags
- `tag_df`: Unique tag table
- `relacion_tags`: Article-tag relationships

---

## Orchestration: `run_pipeline.py`

The orchestrator chains all modules together in the correct order:

```python
def main():
    # 1. Extract: Load raw data
    df_raw = load_data(RAW_DATA_PATH)
    
    # 2. Transform: Clean
    df_clean = clean_data(df_raw)
    df_clean['id_articulo'] = range(len(df_clean))  # Assign IDs
    
    # 3. Transform: Author extraction (NER + split)
    df_clean, df_autores_raw, rel_autores_raw = process_authors(df_clean)
    
    # 4. Transform: Author normalization (fuzzy clustering)
    df_autores_final, rel_autores_final = standardize_author_names(df_autores_raw)
    
    # 5. Transform: Article deduplication (MinHash LSH)
    df_deduped = deduplicate_articles(df_clean, column='texto_completo')
    
    # 6. Transform: Tag extraction and relationship building
    df_tagged, tag_df, rel_tags = extract_tags(df_deduped)
    
    # 7. "Load": Save to CSV (no database, so just write files)
    df_tagged.to_csv(PROCESSED_PATH / "articles.csv", index=False)
    df_autores_final.to_csv(PROCESSED_PATH / "authors.csv", index=False)
    rel_autores_final.to_csv(PROCESSED_PATH / "rel_authors.csv", index=False)
    tag_df.to_csv(PROCESSED_PATH / "tags.csv", index=False)
    rel_tags.to_csv(PROCESSED_PATH / "rel_tags.csv", index=False)
```

**Key design principles**:
- **Location agnostic**: Uses `pathlib.Path` for cross-platform compatibility
- **Sequential processing**: Each step depends on the previous one's output
- **Immutable operations**: Modules return new DataFrames instead of modifying in-place
- **Progress feedback**: Print statements at each stage for visibility
- **Error tolerance**: Individual modules handle their own errors

**Why this orchestration approach**:
- Single entry point makes the pipeline easy to run
- Clear separation of concerns (each module has one job)
- Easy to debug (run up to any step and inspect intermediate outputs)
- Modular: Can swap out or add modules without breaking the flow

---

## Running the Pipeline

```bash
python src/article_processing_pipeline/run_pipeline.py
```

Or if you've moved the folder elsewhere:
```bash
python -m run_pipeline
```

Make sure `data/raw/articulos_proquest_raw.csv` exists before running!

---

## Output Schema

### `articles.csv`
- `id_articulo`: Unique article identifier
- `titulo`: Article title
- `texto_completo`: Full text
- `publicacion`: Publication name
- `fecha_de_publicacion`: Publication date
- `editorial`: Publisher
- `tipo_fuente`: Source type

### `authors.csv`
- `id_autor`: Unique author identifier
- `autor`: Normalized author name

### `rel_authors.csv`
- `id_articulo`: Foreign key to articles
- `id_autor`: Foreign key to authors

### `tags.csv`
- `id_tags`: Unique tag identifier
- `tags`: Tag text

### `rel_tags.csv`
- `id_articulo`: Foreign key to articles
- `id_tags`: Foreign key to tags

---

## Technical Stack

- **pandas**: Core data manipulation
- **GLiNER**: Named entity recognition for person detection
- **scikit-learn**: TF-IDF vectorization and DBSCAN clustering
- **sentence-transformers**: Semantic embeddings for deduplication
- **datasketch**: MinHash and LSH for efficient similarity search
- **torch**: GPU acceleration for GLiNER

---

## Future Improvements

- [ ] Add database loading (PostgreSQL) for true ETL (maybe if necessary)
- [ ] alternatively save into parquet files
- [ ] Parallel processing for author NER (currently sequential)
- [ ] Better heuristics for organizational entity filtering
- [ ] Add article language detection as separate module
- [ ] Implement incremental updates (process only new articles)
- [ ] Add data quality metrics and validation reports
