# Helper: generates a multi-page text DPR PDF and a blank (image-only-like) PDF for DPR tests.
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def make_dpr(path="/tmp/test_dpr_25p.pdf", pages=25):
    c = canvas.Canvas(path, pagesize=A4)
    for p in range(pages):
        y = 800
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, f"Detailed Project Report - Construction of 12 km Rural Road - Page {p + 1}")
        c.setFont("Helvetica", 10)
        for i in range(55):
            y -= 13
            c.drawString(50, y, (f"Section {p + 1}.{i + 1}: The project involves earthwork, sub-base, bituminous "
                                 f"surfacing, culverts and drainage. Estimated cost INR 45 crore. Period 18 months."))
        c.showPage()
    c.save()
    return path


def make_blank(path="/tmp/test_blank.pdf", pages=3):
    c = canvas.Canvas(path, pagesize=A4)
    for _ in range(pages):
        c.rect(100, 100, 300, 300, fill=1)
        c.showPage()
    c.save()
    return path


if __name__ == "__main__":
    print(make_dpr(), make_blank())
