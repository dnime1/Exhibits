import os, io
from pypdf import PdfWriter, PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.units import inch

w, h = letter
repo = '/home/ubuntu/exhibits'
OUT  = '/home/ubuntu/exhibits/Exhibits_Merged_v9.pdf'

def make_title():
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=letter)
    y = h - 2.5*inch
    c.setFont("Times-Roman", 14)
    c.drawCentredString(w/2, y,      "IN THE CIRCUIT COURT OF THE STATE OF OREGON")
    c.drawCentredString(w/2, y - 24, "FOR THE COUNTY OF CLACKAMAS")
    left_x = 1.1*inch; mid_x = 4.4*inch; y_top = y - 75; lh = 18
    left_lines = [
        "VIKTORIYA A. PULLIAM, an individual,", "",
        "Plaintiff,", "", "    v.", "",
        "SUSAN DIANE GREEN, an individual, or",
        "the unidentified driver identified and",
        "described herein; and DORANE DACHTLER,",
        "an individual, or the unidentified driver",
        "identified and described herein", "", "Defendants.",
    ]
    c.setFont("Times-Roman", 12)
    y_cur = y_top
    for line in left_lines:
        c.drawString(left_x, y_cur, line); y_cur -= lh
    y_bottom = y_cur + lh - 4
    c.setLineWidth(0.75)
    c.line(left_x - 4, y_bottom, mid_x + 10, y_bottom)
    c.line(mid_x + 10, y_top + 16, mid_x + 10, y_bottom)
    c.setFont("Times-Roman", 12)
    c.drawString(mid_x + 24, y_top, "Case No. 21CV44058")
    c.setFont("Times-Bold", 26)
    c.drawCentredString(w/2, h * 0.28, "PLAINTIFF'S EVIDENCE BOOK")
    c.save(); buf.seek(0); return buf

def make_sep(label):
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=letter)
    c.setFont("Times-Bold", 28)
    c.drawCentredString(w/2, h * (2/3), label)
    c.save(); buf.seek(0); return buf

def make_toc(entries):
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=letter)
    link_rects = []
    c.setFont("Times-Bold", 16)
    c.drawCentredString(w/2, h - 1.0*inch, "TABLE OF CONTENTS")
    c.setLineWidth(0.5)
    c.line(1.0*inch, h - 1.2*inch, w - 1.0*inch, h - 1.2*inch)
    y = h - 1.55*inch; row_h = 0.235*inch; fs = 11
    for label, pg in entries:
        if y < 0.6*inch:
            c.showPage(); y = h - 1.0*inch
        pg_str = str(pg)
        c.setFont("Times-Roman", fs)
        c.drawString(1.0*inch, y, label)
        c.drawRightString(w - 1.0*inch, y, pg_str)
        lw = c.stringWidth(label, "Times-Roman", fs)
        rw = c.stringWidth(pg_str, "Times-Roman", fs)
        dots = ""
        while c.stringWidth(dots + ".", "Times-Roman", fs) < (w - 1.0*inch - rw - 4 - 1.0*inch - lw - 4):
            dots += "."
        c.drawString(1.0*inch + lw + 4, y, dots)
        link_rects.append((1.0*inch, y - 4, w - 1.0*inch, y + 13, pg - 1))
        y -= row_h
    c.save(); buf.seek(0)
    return buf, link_rects

# Files
index_pdf = os.path.join(repo, 'Exhibit_List.pdf')
if not os.path.exists(index_pdf):
    raise FileNotFoundError(f"MISSING: {index_pdf}")
index_pages = len(PdfReader(index_pdf).pages)
print(f"Exhibit Index: {index_pages} pages")

exhibit_files = sorted([f for f in os.listdir(repo)
                        if f.lower().endswith('.pdf') and f.upper().startswith('EXHIBIT')
                        and 'Merged' not in f and 'List' not in f])
print(f"Found {len(exhibit_files)} exhibit PDFs")

page_counts = []
for fname in exhibit_files:
    try:
        r = PdfReader(os.path.join(repo, fname))
        page_counts.append(len(r.pages))
    except:
        page_counts.append(1)

# Layout: p1=title, p2=TOC, p3=Index sep, p4+=index, then exhibits
current = 3
toc_entries = [("Exhibit Index", current)]
current += 1 + index_pages
for i, pc in enumerate(page_counts):
    toc_entries.append((f"Exhibit {i+1}", current))
    current += 1 + pc

toc_buf, link_rects = make_toc(toc_entries)

# Assemble
writer = PdfWriter()
for pg in PdfReader(make_title()).pages: writer.add_page(pg)
toc_buf.seek(0)
for pg in PdfReader(toc_buf).pages: writer.add_page(pg)
for pg in PdfReader(make_sep("Exhibit Index")).pages: writer.add_page(pg)
for pg in PdfReader(index_pdf).pages: writer.add_page(pg)
for i, fname in enumerate(exhibit_files):
    for pg in PdfReader(make_sep(f"Exhibit {i+1}")).pages: writer.add_page(pg)
    try:
        r = PdfReader(os.path.join(repo, fname))
        for pg in r.pages: writer.add_page(pg)
        print(f"OK: Exhibit {i+1} ({len(r.pages)}p)")
    except Exception as e:
        print(f"SKIP: {fname}: {e}")

total = len(writer.pages)
print(f"Total pages: {total}")

# Page numbers
def num_overlay(n):
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica", 9)
    c.setFillColorRGB(0.0, 0.2, 0.7)
    c.drawCentredString(w/2, 0.4*inch, str(n))
    c.save(); buf.seek(0); return buf

writer2 = PdfWriter()
for i, page in enumerate(writer.pages):
    page.merge_page(PdfReader(num_overlay(i+1)).pages[0])
    writer2.add_page(page)

with open(OUT, 'wb') as f:
    writer2.write(f)
print("First write done")

# Hyperlinks via pikepdf
import pikepdf
from pikepdf import Dictionary, Array, Name

pdf = pikepdf.open(OUT, allow_overwriting_input=True)
toc_pg = pdf.pages[1]
n = 0
for (x1, y1, x2, y2, tgt) in link_rects:
    if tgt >= len(pdf.pages): continue
    dest = Array([
        pdf.pages[tgt].obj, Name.XYZ,
        pikepdf.Object.parse(b"null"),
        pikepdf.Object.parse(b"null"),
        pikepdf.Object.parse(b"0"),
    ])
    annot = pdf.make_indirect(Dictionary(
        Type=Name.Annot, Subtype=Name.Link,
        Rect=Array([x1, y1, x2, y2]),
        Border=Array([0, 0, 0]),
        Dest=dest,
    ))
    if "/Annots" not in toc_pg:
        toc_pg["/Annots"] = Array()
    toc_pg["/Annots"].append(annot)
    n += 1

pdf.save(OUT)
print(f"Links added: {n}")
print(f"\nDONE: {OUT} ({os.path.getsize(OUT)/1024/1024:.1f} MB, {total} pages)")
