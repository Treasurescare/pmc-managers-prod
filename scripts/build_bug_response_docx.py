"""Build annotated DOCX — inject a Response paragraph after each bug in the
V6 screenshots document.
"""
from docx import Document
from docx.shared import RGBColor, Pt
from copy import deepcopy
from pathlib import Path
import re

SRC = Path("/tmp/originals/original_screenshots.docx")
OUT = Path("/app/deliverables/PMC_Bugs_Screenshots_V6_with_Responses.docx")
OUT.parent.mkdir(exist_ok=True)

# Reuse RESPONSES from the xlsx script
import sys
sys.path.insert(0, '/app/scripts')
from build_bug_response_xlsx import RESPONSES

doc = Document(SRC)

# Iterate through body elements. For each paragraph whose text starts with a
# bug number ("1.", "2.", "23.", "60." etc.), insert a Response paragraph
# immediately after it.

def _extract_bug_no(text: str) -> int | None:
    m = re.match(r"^\s*(\d{1,2})[\.\)\s]", text)
    if not m:
        return None
    try:
        n = int(m.group(1))
        if 1 <= n <= 99:
            return n
    except Exception:
        pass
    return None


body = doc.element.body

# Collect paragraphs and their bug numbers in order
to_annotate = []  # (paragraph, bug_no)
for p in doc.paragraphs:
    txt = p.text.strip()
    if not txt:
        continue
    n = _extract_bug_no(txt)
    if n and n in RESPONSES and RESPONSES[n][0]:
        to_annotate.append((p, n))

print(f"Found {len(to_annotate)} bug paragraphs to annotate")

# Insert response paragraph after each. Iterate in reverse so we don't shift
# indices during insertion.
for p, n in reversed(to_annotate):
    status, action = RESPONSES[n]
    # Create a new paragraph element
    new_p = deepcopy(p._p)
    # Wipe all children (runs)
    for child in list(new_p):
        new_p.remove(child)
    p._p.addnext(new_p)
    # Now add runs via python-docx helper
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement

    # Build simple runs
    def _add_run(paragraph_element, text, bold=False, color=None):
        r = OxmlElement("w:r")
        rPr = OxmlElement("w:rPr")
        if bold:
            b = OxmlElement("w:b"); rPr.append(b)
        if color:
            col = OxmlElement("w:color"); col.set(qn("w:val"), color); rPr.append(col)
        sz = OxmlElement("w:sz"); sz.set(qn("w:val"), "20"); rPr.append(sz)
        r.append(rPr)
        t = OxmlElement("w:t")
        t.text = text
        t.set(qn("xml:space"), "preserve")
        r.append(t)
        paragraph_element.append(r)

    _add_run(new_p, "→ Response · ", bold=True, color="0F1B3D")
    _add_run(new_p, status + " — ", bold=True, color="1F6F3F" if "FIXED" in status or "CONFIRMED" in status
                                                  else "8B6D00" if "PARTIAL" in status or "MITIGATED" in status
                                                  else "7A2C2C" if "OPEN" in status
                                                  else "555555")
    _add_run(new_p, action, color="333333")

doc.save(OUT)
print(f"Written {OUT}  size={OUT.stat().st_size / 1024:.1f} KB")
