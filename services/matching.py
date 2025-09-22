# services/matching.py
import re
from unidecode import unidecode
from rapidfuzz import fuzz

# Clean out common junk added by YouTube rips etc.
NOISE_PATTERNS = [
    r'\(official.*?\)', r'\[official.*?\]',
    r'\(lyrics.*?\)', r'\[lyrics.*?\]',
    r'\(audio.*?\)', r'\[audio.*?\]',
    r'\(explicit.*?\)', r'\[explicit.*?\]',
    r'\(clean.*?\)', r'\[clean.*?\]',
    r'\(hd.*?\)', r'\[hd.*?\]', r'\(hq.*?\)', r'\[hq.*?\]',
    r'\(remaster.*?\)', r'\[remaster.*?\]',
    r'\(live.*?\)', r'\[live.*?\]',
    r'\(visualizer.*?\)', r'\[visualizer.*?\]',
    r'\(sped up.*?\)', r'\[sped up.*?\]',
    r'\(slowed.*?\)', r'\[slowed.*?\]',
    r'official video', r'official audio', r'visualizer',
    r'lyric video', r'full album', r'album version',
    r'hq', r'hd'
]

def normalize(s: str) -> str:
    if not s:
        return ""
    s = unidecode(s.lower())
    s = s.replace("–", "-").replace("—", "-").replace("_", " ")
    for pat in NOISE_PATTERNS:
        s = re.sub(pat, "", s, flags=re.I)
    s = re.sub(r'[\[\]\(\)\{\}]', ' ', s)             # strip brackets
    s = re.sub(r'[^a-z0-9&\'\-\s]', ' ', s)           # allowed chars
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def parse_filename(filename: str) -> tuple[str, str | None]:
    """
    Try to extract (title, artist) from a filename like:
    '01 - Travis Scott - DUMBO (Explicit).flac'
    'Travis Scott - DUMBO.flac'
    'Title by Artist.mp3'
    Fallback: (basename, None)
    """
    base = re.sub(r'\.[a-z0-9]{2,5}$', '', filename, flags=re.I)
    base = normalize(base)

    # drop leading track numbers: "01 - ..." / "07. ..."
    base = re.sub(r'^\s*\d+\s*[-_. ]\s*', '', base)

    # pattern "artist - title"
    m = re.match(r'^(?P<artist>.+?)\s*-\s*(?P<title>.+)$', base)
    if m:
        return (m.group('title').strip(), m.group('artist').strip())

    # pattern "title by artist"
    m = re.match(r'^(?P<title>.+?)\s+by\s+(?P<artist>.+)$', base)
    if m:
        return (m.group('title').strip(), m.group('artist').strip())

    # otherwise just a title guess
    return (base, None)

def fuzzy_score(a: str, b: str) -> int:
    a = normalize(a)
    b = normalize(b)
    if not a or not b:
        return 0
    # token_set_ratio is forgiving about word order / extra tokens
    return fuzz.token_set_ratio(a, b)
