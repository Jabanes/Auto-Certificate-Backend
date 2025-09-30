import json
from main import render_pdf_for_student, FIELDS_CONFIG, TEMPLATE_PATH  # assuming file is main.py
from PIL import Image
import io

# Load student test data
with open("students.json", "r", encoding="utf-8") as f:
    data = json.load(f)

student = data["students"][0]

# Render certificate
pdf_bytes = render_pdf_for_student(student, FIELDS_CONFIG)

# Save as PDF for inspection
with open("test_certificate.pdf", "wb") as f:
    f.write(pdf_bytes)

print("PDF saved -> test_certificate.pdf")

