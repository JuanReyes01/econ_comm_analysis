from bs4 import BeautifulSoup, Tag, NavigableString
from nltk.tokenize import sent_tokenize
import re
from .utils import is_html
from .constants import DEGREE_PATTERN, LOOSE_DEGREE_RE, BLACKLIST_SECTIONS
from .formatter import degrees_to_markdown
from professional_profiler.logging.logger import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)


def extract_all_sections(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html5lib")
    # strip site-wide junk
    for sel in ["style", "script", "table.navbox", "sup.reference", "span.mw-cite-backlink", "ol.references", "div.reflist", "div.hatnote", "div#toc"]:
        for el in soup.select(sel):
            el.decompose()

    body = soup.select_one("div.mw-parser-output") or soup
    sections = []
    # Lead paragraph(s)
    lead_pars = []
    first_h = body.find(re.compile(r"^h[1-6]$"))
    for sib in body.children:
        if sib is first_h:
            break
        if isinstance(sib, Tag) and sib.name == 'p':
            lead_pars.append(sib)
    if lead_pars:
        sections.append({"title":"_lead_", "paragraphs":lead_pars})

    # Heading-based sections
    for h in body.find_all(re.compile(r"^h[1-6]$")):
        title = h.get_text(strip=True)
        if title in BLACKLIST_SECTIONS: continue
        paras = []
        for sib in h.next_siblings:
            if isinstance(sib, Tag) and re.fullmatch(r"h[1-6]", sib.name):
                break
            if isinstance(sib, Tag) and sib.name=='p':
                paras.append(sib)
        if paras:
            sections.append({"title":title, "paragraphs":paras})


    # Infobox education as a pseudo-section
    infobox = soup.find("table", class_="infobox")
    if infobox:
        edu_texts = []
        for row in infobox.find_all("tr"):
            hdr = row.find("th")
            cell = row.find("td")
            if hdr and cell and ("education" in hdr.get_text(" ", strip=True).lower() or "alma mater" in hdr.get_text(" ", strip=True).lower()):
                edu_texts.append(cell.get_text(" ", strip=True))
        if edu_texts:
            paras = []
            for txt in "; ".join(edu_texts).split("; "):
                # create a <p> tag so it matches your other sections
                bs = BeautifulSoup(f"<p>{txt}</p>", "html5lib")
                paras.append(bs.find("p"))
            sections.append({
            "title": "_infobox_education_",
            "paragraphs": paras
    })
    return sections


# Heading-based sections
def extract_section_text(tag: Tag) -> str:
    logger.debug(f"Extracting text for section: {tag.get_text(strip=True)}")
    level = int(tag.name[1])
    texts = []
    for sib in tag.next_siblings:
        if isinstance(sib, Tag) and re.fullmatch(r"h[1-6]", sib.name):
            if int(sib.name[1]) <= level:
                break
        if isinstance(sib, Tag) and sib.name == "p":
            texts.append(sib.get_text(" ", strip=True))
        elif isinstance(sib, NavigableString) and sib.strip():
            texts.append(str(sib).strip())
    section_text = " ".join(texts).strip()
    if not section_text:
        logger.warning(f"No content found for section: {tag.get_text(strip=True)}")
    return section_text


def parse_degree_paragraphs(sections: list[dict]) -> dict[str, list[str]]:
    out = {}
    for sec in sections:
        for p in sec["paragraphs"]:
            txt = p.get_text(" ", strip=True)
            if DEGREE_PATTERN.search(txt):
                out.setdefault(sec["title"], []).append(txt)
    return out

def extract_every_degree_sentence(html: str) -> list[str]:
    sections = extract_all_sections(html)
    hits = []

    for sec in sections:
        # pick the text from either content or paragraphs
        if "content" in sec:
            text = sec["content"]
        elif "paragraphs" in sec:
            text = " ".join(
                p.get_text(" ", strip=True) for p in sec["paragraphs"]
            )
        else:
            # nothing to scan
            continue

        for sent in sent_tokenize(text):
            if LOOSE_DEGREE_RE.search(sent):
                hits.append(sent.strip())

    # dedupe while preserving order
    return list(dict.fromkeys(hits))


def extract_degrees_markdown(html: str) -> str:
    logger.info("Extracting degrees and converting to markdown.")
    if not is_html(html):
        logger.debug("Input is not HTML, skipping parsing.")
        return "NOT HTML"
    sections = extract_all_sections(html)
    sec_map = parse_degree_paragraphs(sections)
    if sec_map:
        logger.info("Successfully parsed degrees from sections.")
        return degrees_to_markdown(sec_map)

    # fallback
    logger.warning("No structured degree mentions found, falling back to loose mentions.")
    fallback = extract_every_degree_sentence(html)
    md = "## Degree Mentions"
    for s in fallback:
        md += f"\n- {s}"
    return md
