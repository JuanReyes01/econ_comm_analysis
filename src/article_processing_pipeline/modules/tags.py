import pandas as pd

def extract_tags(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Extract and explode article tags. Returns:
    - df_filtered: filtered article DataFrame with at least one tag
    - tag_df: unique tag table (id_tags, tags)
    - relacion_tags: article-tag relationship table
    """
    assert 'id_articulo' in df.columns, "df must contain 'id_articulo' before extracting tags"
    df = df.copy()

    # Step 1: Extract tag fields and fill missing values
    tag_cols = ['materia', 'lugar_articulo', 'personas', 'empresa']
    df_tags = df[['id_articulo'] + tag_cols].copy()
    df_tags = df_tags.fillna('').astype(str)
    df_tags['empresa'] = df_tags['empresa'].str.replace('Nombre: ', '', regex=False)

    # Step 2: Combine into one "tags" column
    df_tags['tags'] = df_tags['materia'] + ';' + df_tags['lugar_articulo'] + ';' + df_tags['personas'] + ';' + df_tags['empresa']
    df_tags['tags'] = df_tags['tags'].str.split(';')

    # Step 3: Explode
    df_tags = df_tags.explode('tags').reset_index(drop=True)
    df_tags['tags'] = df_tags['tags'].str.strip()
    df_tags = df_tags[df_tags['tags'].notna() & (df_tags['tags'] != '') & (df_tags['tags'].str.lower() != 'nan')]

    if df_tags.empty:
        print("⚠️ No tags found. Returning empty results.")
        empty_df = pd.DataFrame(columns=df.columns)
        return empty_df, pd.DataFrame(columns=['id_tags', 'tags']), pd.DataFrame(columns=['id_articulo', 'id_tags'])

    # Step 4: Create unique tag table
    tag_df = pd.DataFrame(df_tags['tags'].unique(), columns=['tags']).reset_index()
    tag_df.rename(columns={'index': 'id_tags'}, inplace=True)

    # Step 5: Merge and create relationship
    df_tags = df_tags.merge(tag_df, on='tags', how='left')
    if 'id_tags' not in df_tags.columns:
        raise ValueError("id_tags not created during merge. Check tag format.")

    relacion_tags = df_tags[['id_articulo', 'id_tags']].dropna().astype({'id_articulo': int, 'id_tags': int})

    # Step 6: Filter articles to those with valid tags
    df_filtered = df[df['id_articulo'].isin(relacion_tags['id_articulo'])].reset_index(drop=True)

    print(f"✅ Articles with tags: {len(df_filtered)}")
    print(f"✅ Unique tags identified: {len(tag_df)}")
    print(f"🔗 Article-tag links: {len(relacion_tags)}")

    return df_filtered, tag_df, relacion_tags
