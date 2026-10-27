"""Text normalisation shared by institution matching (BACKEND_PLAN section 6.1).

Scope now: casefold, strip punctuation, collapse spaces, expand common abbreviations.
Devanagari transliteration (V-B3) is NOT done; Devanagari text is matched only as-is.
"""
import re
import unicodedata

ABBREVIATIONS = {
    "inst": "institute", "instt": "institute", "engg": "engineering", "eng": "engineering",
    "tech": "technology", "technol": "technology", "coll": "college", "univ": "university",
    "mgmt": "management", "govt": "government", "poly": "polytechnic", "sci": "science",
}
STOPWORDS = {"the", "of", "and"}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    text = re.sub(r"[^\w\s]", " ", text)
    words = [ABBREVIATIONS.get(w, w) for w in text.split()]
    return " ".join(w for w in words if w not in STOPWORDS)
