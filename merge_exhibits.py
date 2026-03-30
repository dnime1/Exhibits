import os, io
from pypdf import PdfWriter, PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.units import inch

w, h = letter
repo = '/home/ubuntu/exhibits'

# ── Title page (v5 approved) ─────────────────────────────────────────────────
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

# ── Separator page ────────────────────────────────────────────────────────────
def make_sep(num):
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=letter)
    c.setFont("Times-Bold", 28)
    c.drawCentredString(w/2, h * (2/3), f"Exhibit {num}")
    c.save(); buf.seek(0); return buf

# ── TOC page ──────────────────────────────────────────────────────────────────
def make_toc(entries):
    # entries: list of (num, start_page)
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=letter)
    c.setFont("Times-Bold", 16)
    c.drawCentredString(w/2, h - 1.2*inch, "TABLE OF CONTENTS")
    c.setLineWidth(0.5)
    c.line(1.0*inch, h - 1.4*inch, w - 1.0*inch, h - 1.4*inch)
    y = h - 1.8*inch; row_h = 0.28*inch
    for num, pg in entries:
        if y < 0.8*inch: break
        label = f"Exhibit {num}"
        pg_str = str(pg)
        c.setFont("Times-Roman", 12)
        c.drawString(1.0*inch, y, label)
        c.drawRightString(w - 1.0*inch, y, pg_str)
        # dots
        lw = c.stringWidth(label, "Times-Roman", 12)
        rw = c.stringWidth(pg_str, "Times-Roman", 12)
        dot_s = 1.0*inch + lw + 4
        dot_e = w - 1.0*inch - rw - 4
        dots = ""
        while c.stringWidth(dots + ".", "Times-Roman", 12) < (dot_e - dot_s):
            dots += "."
        c.drawString(dot_s, y, dots)
        y -= row_h
    c.save(); buf.seek(0); return buf

# ── Count pages per exhibit ───────────────────────────────────────────────────
files = sorted([f for f in os.listdir(repo) if f.lower().endswith('.pdf') and f.startswith('EXHIBIT')])
print(f"Found {len(files)} exhibit PDFs")

page_counts = []
for fname in files:
    try:
        r = PdfReader(os.path.join(repo, fname))
        page_counts.append(len(r.pages))
    except:
        page_counts.append(1)

# ── Compute layout ────────────────────────────────────────────────────────────
# Page 1 = title, Page 2 = TOC, then sep+exhibit for each
current = 3  # first separator is page 3
toc_entries = []
exhibit_starts = []
for i, pc in enumerate(page_counts):
    num = i + 1
    toc_entries.append((num, current))
    exhibit_starts.append(current)
    current += 1 + pc  # sep page + exhibit pages

# ── Assemble ──────────────────────────────────────────────────────────────────
writer = PdfWriter()

# Title page
for pg in PdfReader(make_title()).pages: writer.add_page(pg)

# TOC
for pg in PdfReader(make_toc(toc_entries)).pages: writer.add_page(pg)

# Exhibits
for i, fname in enumerate(files):
    num = i + 1
    # Separator
    for pg in PdfReader(make_sep(num)).pages: writer.add_page(pg)
    # Exhibit pages
    path = os.path.join(repo, fname)
    try:
        r = PdfReader(path)
        for pg in r.pages: writer.add_page(pg)
        print(f"OK: Exhibit {num} — {fname} ({len(r.pages)}p)")
    except Exception as e:
        print(f"SKIP: {fname}: {e}")

total = len(writer.pages)
print(f"Total pages before numbering: {total}")

# ── Write first pass ──────────────────────────────────────────────────────────
out = '/home/ubuntu/exhibits/Exhibits_Merged.pdf'
with open(out, 'wb') as f:
    writer.write(f)

# ── Add page numbers via reportlab overlay ────────────────────────────────────
import pikepdf

def make_number_overlay(page_num):
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica", 9)
    c.setFillColorRGB(0.0, 0.2, 0.7)  # blue
    c.drawCentredString(w/2, 0.45*inch, str(page_num))
    c.save(); buf.seek(0); return buf

# Merge overlays using pypdf
reader_main = PdfReader(out)
writer2 = PdfWriter()
for i, page in enumerate(reader_main.pages):
    overlay_buf = make_number_overlay(i + 1)
    overlay_page = PdfReader(overlay_buf).pages[0]
    page.merge_page(overlay_page)
    writer2.add_page(page)

with open(out, 'wb') as f:
    writer2.write(f)

size_mb = os.path.getsize(out)/1024/1024
print(f"\nDONE: {out} ({size_mb:.1f} MB, {total} pages)")
