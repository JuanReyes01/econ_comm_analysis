# ProQuest Web Scraping Documentation

## Overview

This module automates the process of scraping newspaper articles from ProQuest through the Universidad de los Andes institutional access. The scraper uses DrissionPage (a Python library for web automation) to navigate the ProQuest interface, apply filters, and download articles in batches.

## Prerequisites

### Required Libraries
- `DrissionPage`: Web automation library for controlling Chromium browsers
- `json`: For handling credentials -> soon a part of .env
- Standard Python libraries: `os`, `glob`, `re`, `datetime` -> soon a part of pyproject.toml

### Installation
```bash
pip install DrissionPage
```

### Credentials Setup
Create a `credentials.json` file in the same directory with the following structure:
```json
{
    "username": "your_institutional_email@uniandes.edu.co",
    "password": "your_uniandes_password",
    "password2": "your_proquest_password"
}
```

**Note**: Keep this file private and never commit it to version control. Add it to `.gitignore`.

## ProQuest Search Configuration

### Access Method
The scraper accesses ProQuest through Universidad de los Andes EZProxy:
- URL: `https://ezproxy.uniandes.edu.co/login?url=https://www.proquest.com/usnews?accountid=34489`

### Search Query and Filters

#### Publications (Exact Match)
The scraper searches within the following major U.S. newspapers:
- **Star Tribune** (Minneapolis, MN) - including blogs
- **Chicago Tribune** - including blogs and pre-1997 fulltext
- **New York Post**
- **Tampa Bay Times** - including online version
- **New York Times** - including online, magazine, and book review editions
- **Newsday**
- **Boston Globe** - including online and pre-1997 fulltext
- **The Washington Post** - including online, blogs, and pre-1997 fulltext
- **USA Today** - including online and pre-1997 fulltext
- **Los Angeles Times** - including blogs, online, and pre-1997 fulltext
- **Wall Street Journal** - including online and magazine editions

#### Content Type Filters
The query searches for articles containing opinion-related content:
- Search term: `noft(opinion OR op-ed OR editorial)`
- This searches within the full text (excluding certain fields) for these keywords

#### Source Type
- **Newspapers**: Enabled
- **Blogs, Podcasts, & Websites**: Disabled
It is a common practice to republish the newspaper content online again, this decreases the amount of scraped articles and also the amount of (very hard) cleaning down the chain.

#### Document Type
The scraper filters for three specific document types:
- **Commentary**: Opinion pieces and analysis articles
- **Editorial**: Editorial opinions
- **News**: Standard news articles

**Note**: Blog posts and other web content are explicitly excluded.

#### Language
- **English only** (ENG)

#### Date Range
The scraper uses an incremental approach:
- Uses the `get_most_recent_file_date()` function to read the most recent downloaded file
- Extracts the publication date from the last article
- Sets the start date to the day after the last downloaded article
- This ensures no gaps or duplicates in the data collection

### Search Strategy
```
Exact("<publication names>") AND noft(opinion OR op-ed OR editorial)
```
Combined with the filters above, this ensures comprehensive coverage of opinion and editorial content from major U.S. newspapers.

## How the Scraper Works

### 1. Authentication Flow

The scraper handles a two-stage authentication process:

#### Stage 1: Universidad de los Andes Login
1. Navigates to the EZProxy login page
2. Clicks on the institutional login button
3. Enters university credentials (username and password)
4. Handles two possible login flows depending on the authentication page variant

#### Stage 2: ProQuest Personal Account
1. Waits for the ProQuest interface to load
2. Clicks on the account dropdown menu
3. Navigates to the sign-in option
4. Enters ProQuest-specific credentials
5. Completes the login process

### 2. Search Setup

After authentication, the scraper:
1. Navigates to the advanced search interface
2. Enters the complex query string with all publication names
3. Unchecks blog/podcast sources (only newspapers are kept checked)
4. Checks the three document types: Commentary, Editorial, and News
5. Selects English as the language filter
6. Sets the date range starting from the last downloaded article's date + 1 day
7. Submits the search and waits for results

### 3. Pagination and Download Process

The scraper implements an efficient batch download strategy:

#### Display Configuration
- Sets results per page to 100 (maximum allowed)
- This minimizes the number of pages to process

#### Batch Selection Loop
The scraper processes results in batches:
- **Every 1-4 pages**: Selects all 100 results on the current page, then moves to the next page
- **Every 5th page**: After selecting results, triggers a download of the accumulated 500 articles

#### Download Mechanism
1. Clicks "Select All" checkbox (`#mlcbAll`) for the current page
2. Navigates to the next page using the page number field
3. Every 5 pages (500 articles):
   - Opens the "Save Options" menu
   - Selects the export format (appears to be text format based on `.txt` file pattern)
   - Deselects unnecessary options
   - Submits the download request
   - Waits for the download to complete (up to 120 seconds)
   - Closes the download tab
   - Continues to the next page

#### Loop Termination
- The scraper processes up to 100 pages (10,000 articles total)
- Configurable by modifying the `if i>=100` condition

### 4. Incremental Updates

The `get_most_recent_file_date()` function enables incremental scraping:
```python
def get_most_recent_file_date():
    # Finds the most recent ProQuestDocuments-*.txt file
    # Extracts the publication date from the file content
    # Returns a datetime object for the next scraping session
```

This ensures:
- No duplicate downloads
- Continuous data collection over time
- Efficient use of resources

## Output Format

### File Naming Pattern
```
ProQuestDocuments-<timestamp>.txt
```

### Content Structure
Each downloaded file contains:
- Publication metadata
- Publication date (`Fecha de publicación: MMM DD, YYYY`)
- Article title
- Author information
- Full text content
- Source publication name

## Handling CAPTCHAs and Anti-Bot Measures

At the end I dint't use this as at the time I was very cheap and didn't like the idea of using 2captcha or other paid service, basically I just solved the captchas manually and I was happy with that, but if someone in the future finds this problem I did find a good solution:

ProQuest and institutional authentication systems may implement CAPTCHA challenges to prevent automated access. This scraper can be enhanced with CAPTCHA bypass solutions.

### Option 1: FlareSolverr

**FlareSolverr** is a proxy server that solves Cloudflare challenges automatically.

#### Setup
1. Install FlareSolverr using Docker:
```bash
docker run -d \
  --name=flaresolverr \
  -p 8191:8191 \
  -e LOG_LEVEL=info \
  --restart unless-stopped \
  ghcr.io/flaresolverr/flaresolverr:latest
```

2. Configure DrissionPage to use FlareSolverr as a proxy:
```python
from DrissionPage import ChromiumPage, ChromiumOptions

co = ChromiumOptions()
co.set_proxy('http://localhost:8191')
driver = ChromiumPage(chromium_options=co)
```

#### When to Use
- Cloudflare challenge pages
- JavaScript-based bot detection
- TLS fingerprinting challenges

#### Limitations
- Only works for Cloudflare and similar challenges
- Does not solve image-based CAPTCHAs
- May not work with reCAPTCHA v2/v3

### Option 2: 2Captcha

**2Captcha** is a human-based CAPTCHA solving service that can handle various CAPTCHA types.

#### Setup
1. Create an account at [2captcha.com](https://2captcha.com/)
2. Install the Python library:
```bash
pip install 2captcha-python
```

3. Implement CAPTCHA detection and solving:
```python
from twocaptcha import TwoCaptcha
import time

# Initialize 2Captcha solver
solver = TwoCaptcha('YOUR_API_KEY')

def solve_recaptcha_if_present(driver, site_key=None):
    """
    Detects and solves reCAPTCHA challenges on the page
    """
    try:
        # Check if reCAPTCHA is present
        captcha_element = driver.ele('@class:g-recaptcha', timeout=2)
        
        if captcha_element:
            print("CAPTCHA detected, solving...")
            
            # Get the site key from the page
            if not site_key:
                site_key = captcha_element.attr('data-sitekey')
            
            # Get current URL
            url = driver.url
            
            # Solve the CAPTCHA
            result = solver.recaptcha(
                sitekey=site_key,
                url=url
            )
            
            # Inject the solution
            captcha_response = result['code']
            driver.run_js(f'document.getElementById("g-recaptcha-response").innerHTML="{captcha_response}";')
            
            # Submit the form or trigger validation
            driver.ele('@id:submit-button').click()
            
            print("CAPTCHA solved successfully")
            return True
    except:
        return False

# Use in the authentication flow
driver.get('https://ezproxy.uniandes.edu.co/login?url=...')
solve_recaptcha_if_present(driver)
# Continue with normal flow...
```

#### Supported CAPTCHA Types
- reCAPTCHA v2
- reCAPTCHA v3
- hCaptcha
- Image CAPTCHAs
- Text CAPTCHAs

#### Cost Considerations
- reCAPTCHA v2: ~$2.99 per 1000 solves
- reCAPTCHA v3: ~$2.99 per 1000 solves
- Check current pricing at [2captcha.com/2captcha-api#rates](https://2captcha.com/2captcha-api#rates)

### Combined Approach: FlareSolverr + 2Captcha

For maximum reliability, use both services together:

```python
from DrissionPage import ChromiumPage, ChromiumOptions
from twocaptcha import TwoCaptcha

# Setup FlareSolverr proxy for initial connection
co = ChromiumOptions()
co.set_proxy('http://localhost:8191')
driver = ChromiumPage(chromium_options=co)

# Initialize 2Captcha for complex CAPTCHAs
solver = TwoCaptcha('YOUR_API_KEY')

def navigate_with_protection(url, driver, solver):
    """
    Navigate with both FlareSolverr and 2Captcha protection
    """
    driver.get(url)
    driver.wait(2)
    
    # Check for Cloudflare challenge (handled by FlareSolverr)
    if "checking your browser" in driver.html.lower():
        print("Cloudflare challenge detected, waiting for FlareSolverr...")
        driver.wait(10)
    
    # Check for reCAPTCHA (handled by 2Captcha)
    solve_recaptcha_if_present(driver)
    
    return driver

# Use in the scraper
driver = navigate_with_protection(
    'https://ezproxy.uniandes.edu.co/login?url=...',
    driver,
    solver
)
```

#### Benefits of Combined Approach
- **FlareSolverr**: Handles automated challenges (free, fast)
- **2Captcha**: Handles human-verification CAPTCHAs (reliable, but costs money)
- **Redundancy**: If one fails, the other may still work

### Best Practices for Avoiding Detection

1. **Add Random Delays**
```python
import random
driver.wait(random.uniform(1, 3))  # Random wait between 1-3 seconds
```

2. **Mimic Human Behavior**
```python
# Scroll the page
driver.scroll.to_bottom()
driver.wait(1)

# Move mouse naturally
# Random mouse movements between actions
```

3. **Use Residential Proxies** (optional, for heavy use)
- Consider services like BrightData, Smartproxy, or Oxylabs
- Rotate IP addresses to avoid rate limiting

4. **Respect Rate Limits**
- Don't scrape too aggressively
- Add appropriate delays between downloads
- Monitor for rate limit errors

5. **Session Management**
```python
# Save cookies to avoid re-authentication
driver.cookies.save('session_cookies.json')

# Load cookies in subsequent runs
driver.cookies.load('session_cookies.json')
```

## Troubleshooting

### Common Issues

1. **Element Not Found Errors**
   - ProQuest may update their UI
   - Check XPath selectors and update if necessary
   - Add longer wait times: `driver.wait(5)`

2. **Download Not Starting**
   - Ensure download directory exists and has write permissions
   - Check browser download settings
   - Increase timeout: `driver.wait.download_begin(timeout=180)`

3. **Authentication Failures**
   - Verify credentials are correct
   - Check if institutional access is active
   - Look for CAPTCHA challenges
   - May need to manually complete first login to set up session

4. **Checkbox Not Checking Consistently**
   - The original code has redundant checks for this known issue
   - UI elements may load asynchronously
   - Current implementation uses `#mlcbAll` which is more reliable

5. **CAPTCHA Challenges**
   - Implement FlareSolverr for Cloudflare challenges
   - Use 2Captcha for reCAPTCHA and image CAPTCHAs
   - Add manual intervention option if automated solving fails
   - Consider reducing scraping frequency to avoid triggering challenges

## Configuration Options

### Modifying Download Size
Change the number of pages processed:
```python
if i >= 100:  # Change this number
    break
```

### Changing Results Per Page
Modify the combo selection (max is 100):
```python
driver('xpath:itemsPerPage-combo-3').click()  # This selects 100 per page
```

### Adjusting Download Path
```python
driver.set.download_path('/your/custom/path')
```

### Modifying Date Range
Instead of incremental updates, set a specific date range:
```python
# Example: Set to January 1, 2023
driver('xpath://*[@id="year1"]').input(2023)
driver(f'xpath://*[@id="day1"]/option[2]').click()  # Day 1
driver(f'xpath://*[@id="month1"]/option[2]').click()  # January (month+1)
```

## Performance Considerations

- **Processing Time**: Approximately 10-20 seconds per page (100 articles)
- **Download Time**: 10-20 seconds per batch of 500 articles
- **Full Run**: 100 pages = ~30-40 minutes total
- **Network Dependency**: Requires stable internet connection
- **Memory Usage**: Moderate (browser automation)

## Future Improvements

1. **Error Recovery**: Implement checkpoint system to resume from interruption
2. **Parallel Processing**: Download multiple batches simultaneously (requires multiple accounts)
3. **Data Validation**: Verify downloaded files are complete and uncorrupted
4. **Logging**: Add comprehensive logging for monitoring and debugging
5. **Configuration File**: Move hardcoded values to a config file
6. **Notification System**: Email/Slack alerts when downloads complete or fail
7. **Advanced CAPTCHA Handling**: Integrate flaresolverr with 2captcha

## References

- [ProQuest Search Guide](https://proquest.libguides.com/proquestplatform/search)
- [ProQuest Advanced Search Help](https://www.proquest.com/help/academic/advanced_search_prod_specific.html)
- [DrissionPage Documentation](https://drissionpage.cn/)
- [FlareSolverr GitHub](https://github.com/FlareSolverr/FlareSolverr)
- [2Captcha API Documentation](https://2captcha.com/2captcha-api)
- [2Captcha Python Package](https://github.com/2captcha/2captcha-python)

## License and Ethical Considerations

**Important**: This scraper is designed for academic research purposes through institutional access. Users must:
- Have legitimate institutional access to ProQuest
- Comply with ProQuest's Terms of Service
- Respect copyright and fair use guidelines
- Use downloaded data only for authorized research purposes
- Not redistribute or commercialize the scraped content
- Follow Universidad de los Andes data usage policies

Automated scraping should be conducted responsibly and ethically. Always check with your institution's library and legal departments before large-scale data collection.
