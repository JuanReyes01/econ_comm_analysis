import re
from professional_profiler.config import load_app_config
import textwrap

config = load_app_config()

# load & strip regex patterns
with open(config.parsing.paths.degree_re_path, encoding="utf-8") as f:
    raw = f.read()

pattern_src = textwrap.dedent(raw).strip()

# 2) compile under VERBOSE so comments and line-breaks work
DEGREE_PATTERN = re.compile(pattern_src, re.IGNORECASE | re.VERBOSE)

with open(config.parsing.paths.degree_loose_re_path, encoding="utf-8") as f:
    loose = textwrap.dedent(f.read()).strip()

LOOSE_DEGREE_RE = re.compile(loose, re.IGNORECASE | re.VERBOSE)


# load blacklist as a set of lines
with open(config.parsing.paths.blacklist_path, "r", encoding="utf-8") as f:
    BLACKLIST_SECTIONS = {line.strip() for line in f if line.strip()}
