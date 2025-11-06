# ProfessionalProfiler

Maybe this code will not be usable by the time you get it (I hope it will be fixed by just adjusting some addresses and libs) but if not the central idea I believe is already a good solution to the problem (hopefully).
- Try to find the names in wikipedia.
- Then parse through the wikipedia pages searching from any reference to education.
- Extract a degree

I believe the biggest pitfall here is the use of the wikipedia API instead of the periodical release of all the articles, I did this because I did not know wikipedia did that.

---

## Objective

Extract the professional degrees (type and field) of U.S. opinion-article authors who have a Wikipedia page using a three-stage pipeline: scraping, parsing, and LLM extraction.

---

## Pipeline Architecture

The ProfessionalProfiler consists of three independent modules that can be run separately:

### 1. **Scraping Module** (`professional_profiler/scraping/`)

**Purpose:** Retrieve Wikipedia HTML content for author names.

**How it works:**
- Reads a CSV file with author names
- Uses Wikipedia API to search for matching pages
- Implements fuzzy matching (RapidFuzz) to find the best page match
- Handles disambiguation pages and multiple matches
- Fetches full HTML content for matched pages
- Includes rate limiting (83 req/min) and retry logic (3 attempts with exponential backoff)

**Key functions:**
- `get_wikipedia()`: Searches Wikipedia API and returns the page key
- `search_html()`: Fetches HTML content for a given page key
- Handles edge cases: NO_RESULTS, MULTIPLE_MATCHES, NO_MATCH, HTTP errors

**Output:** CSV with columns: `id`, `author_name`, `key`, `source` (HTML)

**Run:**
```bash
python -m professional_profiler.scraping
```

---

### 2. **Parsing Module** (`professional_profiler/parsing/`)

**Purpose:** Extract education-related text from Wikipedia HTML using regex patterns.

**How it works:**
- Parses HTML using BeautifulSoup (html5lib parser)
- Extracts specific sections: lead paragraph, education, early life, career, infobox
- Uses regex patterns to identify degree mentions (Bachelor, Master, Ph.D., J.D., etc.)
- Applies section blacklist to ignore irrelevant sections
- Converts extracted text to markdown format with section headers

**Key components:**
- `extract_all_sections()`: Identifies and extracts relevant Wikipedia sections
- `parse_degree_paragraphs()`: Finds paragraphs containing degree keywords
- `extract_degrees_markdown()`: Main function that outputs structured markdown

**Regex patterns (loaded from config files):**
- `DEGREE_PATTERN`: Strict pattern for explicit degree mentions
- `LOOSE_DEGREE_RE`: Broader pattern for potential degree mentions
- `BLACKLIST_SECTIONS`: Sections to ignore (e.g., "See also", "References")

**Output:** CSV with columns: `id`, `author_name`, `sentences` (markdown)

**Run:**
```bash
python -m professional_profiler.parsing
```

---

### 3. **Extraction Module** (`professional_profiler/extraction/`)

**Purpose:** Use LLM to extract structured degree information from markdown text.

**How it works:**
- Loads markdown text from parsing output
- Uses Pydantic AI agent with structured output validation
- Currently supports Gemini (gemini-2.5-flash-preview) and DeepSeek models
- Async processing for efficient batch processing
- Tracks token usage and cost (for DeepSeek pricing)

**Pydantic Schema:**
```python
class Degree(BaseModel):
    degree_type: str   # e.g., "Bachelor of Arts", "Ph.D.", "Professional"
    degree_field: List[str]  # e.g., ["History", "French literature"]

class AuthorDegrees(BaseModel):
    studies: List[Degree]
```

**Prompt strategy:**
- Identifies degree types and fields from markdown
- Ignores incomplete degrees ("dropped out", "did not graduate")
- Returns "NONE" if no completed degree found
- Uses few-shot examples for better accuracy

**Output:** JSON file with structured degree information per author

**Run:**
```bash
python -m professional_profiler.extraction
```

---

## Configuration

If there are any problems I bet it's this

All configuration is managed through `config/app.yaml`:

```yaml
scraping:
  paths:
    authors: "data/test/test_wikipedia_normalized.csv"
    processed_data: "data/processed/wikipedia_files"
  wikipedia:
    rate_limit: 83  # requests per minute
    max_retries: 3
    response_code: 429  # rate limit response code
    timeout: 1800  # retry timeout (30 min)
    language: "en"
  file:
    name: "/authors_wikipedia.csv"
    name_column: "author_name"

parsing:
  paths:
    keywords_path: "data/parsing/keywords.txt"
    degree_re_path: "data/parsing/degree_pattern.txt"
    degree_loose_re_path: "data/parsing/loose_degree.txt"
    blacklist_path: "data/parsing/section_blacklist.txt"
    results_path: "data/processed/parsed_files"
  file:
    file_name: "/parsed_results.csv"

extraction:
  paths:
    prompt_path: "data/prompt.txt"
    results_path: "data/processed/author_profiles"
  file:
    file_name: "/extracted_results_gemini.json"
```

---

## Environment Variables

Create a `.env` file in the module root:

```env
WP_ACCESS_TOKEN=your_wikipedia_api_token
DEEPSEEK_API_KEY=your_deepseek_key  # if using DeepSeek
GEMINI_API_KEY=your_gemini_key      # if using Gemini
```

---

## Installation

```bash
cd src/professional_profiler
pip install -r requirements.txt
```

**Key dependencies:**
- `requests`: Wikipedia API calls
- `beautifulsoup4`: HTML parsing
- `rapidfuzz`: Fuzzy string matching
- `pydantic-ai`: LLM agent framework
- `pandas`: Data processing
- `python-dotenv`: Environment management
- `nltk`: Sentence tokenization

---

## Usage

### Full Pipeline

I was gearing up to build an orchestrator but life got in the way.

You need to run all three stages sequentially:

```bash
# 1. Scrape Wikipedia pages
python -m professional_profiler.scraping

# 2. Parse HTML and extract degree mentions
python -m professional_profiler.parsing

# 3. Extract structured degrees with LLM
python -m professional_profiler.extraction
```

### Individual Stages

Each module can be run independently if you have intermediate outputs.

---

## Input/Output Flow

```
Input CSV (authors)
    ↓
[SCRAPING] → CSV with HTML
    ↓
[PARSING] → CSV with markdown
    ↓
[EXTRACTION] → JSON with structured degrees
```

**Final output format:**
```json
[
  {
    "id": 1,
    "author_name": "Harry Litman",
    "degrees": [
      {
        "degree_type": "Bachelor of Arts",
        "degree_field": []
      },
      {
        "degree_type": "Professional",
        "degree_field": ["Juris Doctor"]
      }
    ]
  }
]
```

---

## Logging

Logs are configured via `config/logging.yaml` and written to `logs/profiler.log`.

Log levels can be adjusted per module in the logging configuration.

---

## Current LLM Configuration

**Model:** Gemini 2.5 Flash Preview (04-17)
- Provider: Google Generative Language API
- Max retries: 3
- Temperature: 0.0 (deterministic output)

**Note:** The code supports both Gemini and DeepSeek. Switch models by modifying the `agent` initialization in `extraction/llm.py`.

---

## Known Limitations

1. **Wikipedia Coverage:** Only works for authors with Wikipedia pages
2. **Fuzzy Matching:** May occasionally match wrong person with similar name
3. **HTML Structure:** Depends on Wikipedia's HTML structure remaining consistent
4. **LLM Accuracy:** May misclassify degree types or miss degrees in complex text
5. **Rate Limiting:** Wikipedia API limited to 83 requests/minute
6. **Language:** Currently only supports English Wikipedia
---

## Testing

Test files are located in `data/test/`:
- `test_wikipedia_normalized.csv`: Sample author names
- Gold standard annotations can be added for evaluation

---

## Future Enhancements

- [ ] Add evaluation metrics against gold standard
- [ ] Support for multiple languages
- [ ] Capture institution and year information
- [ ] Implement caching to avoid re-scraping
- [ ] Add batch processing with progress bars
- [ ] Improve disambiguation handling
- [ ] Add unit tests for each module

---
