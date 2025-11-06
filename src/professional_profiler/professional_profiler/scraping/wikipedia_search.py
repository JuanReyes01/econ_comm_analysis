# professional_profiler/scraping/wikipedia_search.py

from professional_profiler.logging.logger import get_logger
import os
import requests
from dotenv import load_dotenv
import time
from rapidfuzz import process, fuzz

load_dotenv()

logger = get_logger(__name__)


"""
This Python function retrieves information from
Wikipedia based on a given name and language,
handling retry logic and error cases.

:param name: The `name` parameter is a required
string input representing the search query for the
Wikipedia page you want to retrieve
:type name: str
:param lang: The `lang` parameter in the `get_wikipedia`
function specifies the language for the Wikipedia search.
By default, it is set to "en" for English. You can provide
a different language code if you want to search in a
different language, defaults to en
:type lang: str (optional)
:param retry: The `retry` parameter in the `get_wikipedia`
function specifies the number of retry attempts that will
be made in case of certain errors, such as a rate limit being hit.
If the initial request fails, the function will retry making the
request up to the specified number of times before giving up,
defaults to 3
:type retry: int (optional)
:param timeout: The `timeout` parameter in the `get_wikipedia`
function specifies the maximum number of seconds to wait for a
response from the Wikipedia API before raising a timeout error. In the
provided code snippet, the default value for `timeout` is set to 60 seconds.
This means that if the API, defaults to 60
:type timeout: int (optional)
:param rc: The `rc` parameter in the `get_wikipedia` function stands
for "retry count." It specifies the number of times the function will
retry making a request in case it encounters a rate limit
from the Wikipedia API. If the rate limit is hit, the function, defaults to 429
:type rc: int (optional)
:return: The function `get_wikipedia` returns the key of the best
matching Wikipedia page based on the search query provided.
"""


def get_wikipedia(
    name: str, lang: str = "en", retry: int = 3, timeout: int = 60, rc: int = 429
) -> str:
    logger.debug("Scraping %r", name)
    BASE_URL = "https://api.wikimedia.org/core/v1/wikipedia"
    HEADERS = {"Authorization": os.getenv("WP_ACCESS_TOKEN", "")}
    SEARCH_TIMEOUT = 5

    url = f"{BASE_URL}/{lang}/search/page"
    params = {"q": name, "limit": 1}
    rs = None
    try:
        # Retry logic
        for attempt in range(retry):
            try:
                rs = requests.get(url, headers=HEADERS, params=params, timeout=SEARCH_TIMEOUT)
                rs.raise_for_status()
                break
            except requests.HTTPError as e:
                if rs.status_code == rc and attempt < retry - 1:
                    logger.warning("Rate limit hit, retrying... (%d/%d)", attempt + 1, retry)
                    # Wait before retrying
                    logger.debug("Waiting for %d seconds before retrying...", timeout)
                    time.sleep(timeout)
                    continue
                else:
                    raise e
        data = rs.json()
    except requests.HTTPError:
        logger.error("HTTP error: %s", rs.status_code)
        return "HTTP error"
    except requests.RequestException:
        logger.error("Network error: %s", rs.status_code)
        return "Network error"
    except ValueError:
        logger.error("Invalid JSON response")
        return "Invalid JSON"

    pages = data.get("pages", [])
    if not pages:
        return "NO_RESULTS"

    # detection of disambiguation remains the same for the first result
    if pages[0].get("description") == "Topics referred to by the same term":
        return "MULTIPLE_MATCHES"

    # normalize query
    normalized_query = (
        name.lower().replace(" ", "_").replace(".", "")  # strip dots from initials/suffixes
    )

    # build candidate list from all returned pages
    choices = [p["key"].lower().replace(" ", "_") for p in pages]

    # fuzzy‐match
    best, score, idx = process.extractOne(normalized_query, choices, scorer=fuzz.ratio)

    if score < 50:
        return "NO_MATCH"

    # we accept pages[idx]
    match = pages[idx]

    return match["key"]


"""
The function `search_html` fetches HTML
content from a Wikipedia API based on a given key
with retry logic for handling rate limits.

:param key: The `key` parameter in the `search_html`
function is a required string parameter that
represents the search term or key for fetching HTML
content from a Wikipedia API
:type key: str
:param lang: The `lang` parameter in the `search_html`
function is used to specify the language for
the Wikipedia page search. It has a default value of
"en" (English), but you can provide a different
language code if needed, defaults to en
:type lang: str (optional)
:param retry: The `retry` parameter in the `search_html`
function specifies the number of retry attempts that will
be made in case of certain HTTP errors, such as rate limiting.
If the initial request fails due to a specific HTTP error
status code (specified by `rc`), the function will retry
making the, defaults to 3
:type retry: int (optional)
:param timeout: The `timeout` parameter in the `search_html`
function specifies the maximum number of seconds the function
will wait for a response from the API before timing out. In
this case, the default timeout value is set to 60 seconds.
If the API does not respond within this time frame, the
function, defaults to 60
:type timeout: int (optional)
:param rc: The `rc` parameter in the `search_html` function
stands for "Retry Count". It is used to specify the number of
times the function should retry making a request in case a
rate limit is hit, defaults to 429
:type rc: int (optional)
:return: The function `search_html` returns a string, which
is the HTML content fetched from a specified URL. If there
are any HTTP errors or network errors during the request,
it will return an error message instead. If the key
parameter is "NO_MATCH", "MULTIPLE_MATCHES", or "NO_RESULTS", it
will return the key itself without making the request.
"""


def search_html(
    key: str, lang: str = "en", retry: int = 3, timeout: int = 60, rc: int = 429
) -> str:
    logger.debug("Fetching %r", key)
    if key != "NO_MATCH" and key != "MULTIPLE_MATCHES" and key != "NO_RESULTS":
        url = "https://api.wikimedia.org/core/v1/wikipedia/" + lang + "/page/" + key + "/html"
        HEADERS = {
            "Authorization": os.getenv("WP_ACCESS_TOKEN"),
        }
        SEARCH_TIMEOUT = 5
        rs = None
        try:
            # Retry logic
            for attempt in range(retry):
                try:
                    rs = requests.get(url, headers=HEADERS, timeout=SEARCH_TIMEOUT)
                    rs.raise_for_status()
                    break
                except requests.HTTPError as e:
                    if rs.status_code == rc and attempt < retry - 1:
                        logger.warning(
                            "Rate limit hit, retrying... (%d/%d)", attempt + 1, retry
                        )
                        # Wait before retrying
                        logger.debug("Waiting for %d seconds before retrying...", timeout)
                        time.sleep(timeout)
                        continue
                    else:
                        raise e
            data = rs.text
        except requests.HTTPError:
            logger.error("HTTP error: %s", rs.status_code)
            return "HTTP error"
        except requests.RequestException:
            logger.error("Network error: %s", rs.status_code)
            return "Network error"
        return data
    else:
        return key
