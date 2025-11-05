import pandas as pd

def load_data(path: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(path)
        print("Data loaded successfully.")
        print(len(df))
        return df
    except Exception as e:
        raise e
    except FileNotFoundError:
        print(f"File not found: {path}")
        return pd.DataFrame()
