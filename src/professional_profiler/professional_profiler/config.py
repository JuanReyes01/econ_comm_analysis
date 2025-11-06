# professional_profiler/config.py
from pathlib import Path
from pydantic import BaseModel
import yaml

_APP_YAML = Path(__file__).parent.parent / "config" / "app.yaml"


class srapingPaths(BaseModel):
    authors: str
    processed_data: str


class scrapingfile(BaseModel):
    name: str
    name_column: str


class wikipediaSettings(BaseModel):
    rate_limit: int
    max_retries: int
    timeout: int
    response_code: int
    language: str


class scrapingConfig(BaseModel):
    paths: srapingPaths
    wikipedia: wikipediaSettings
    file: scrapingfile


class parsingPaths(BaseModel):
    keywords_path: str
    degree_re_path: str
    degree_loose_re_path: str
    blacklist_path: str
    results_path: str


class parsingFile(BaseModel):
    file_name: str


class parsingConfig(BaseModel):
    paths: parsingPaths
    file: parsingFile

class extractionFile(BaseModel):
    file_name: str
class extractionPaths(BaseModel):
    prompt_path: str
    results_path: str
    
class extractionConfig(BaseModel):
    paths: extractionPaths
    file: extractionFile
class AppConfig(BaseModel):
    scraping: scrapingConfig
    parsing: parsingConfig
    extraction: extractionConfig

def load_app_config(path: str | Path = _APP_YAML) -> AppConfig:
    raw = yaml.safe_load(Path(path).read_text())
    return AppConfig(**raw)
