import requests
import json
import re
import io
from datetime import date
from bs4 import BeautifulSoup

# ── 1. Pobierz strone JAS-FBG ─────────────────────────────
URL = "https://www.jasfbg.com.pl/dokumenty/spedycja-drogowa-krajowa/"
headers = {"User-Agent": "Mozilla/5.0"}

resp = requests.get(URL, headers=headers, timeout=15)
resp.raise_for_status()
soup = BeautifulSoup(resp.text, "html.parser")

# ── 2. Znajdz link do PDF z dodatkiem paliwowym ───────────
pdf_url = None
pdf_label = None
for a in soup.find_all("a", href=True):
    href = a["href"]
    text = a.get_text(strip=True)
    if "Wysoko" in href and "dodatku-paliwowego" in href:
        pdf_url = href
        pdf_label = text
        break

if not pdf_url:
    print("BLAD: Nie znaleziono linku do PDF!")
    exit(1)

print(f"Znaleziono PDF: {pdf_url}")

# ── 3. Pobierz PDF i wyciagnij procent ────────────────────
pdf_resp = requests.get(pdf_url, headers=headers, timeout=15)
pdf_resp.raise_for_status()

import pdfplumber
with pdfplumber.open(io.BytesIO(pdf_resp.content)) as pdf:
    text = ""
    for page in pdf.pages:
        text += page.extract_text() or ""

print(f"Tekst z PDF:\n{text}")

# Wyciagnij procent (np. "31,50 %")
match = re.search(r'wynosi\s+([\d,]+)\s*%', text)
if not match:
    print("BLAD: Nie znaleziono procentu w PDF!")
    exit(1)

percent = float(match.group(1).replace(",", "."))
print(f"Procent: {percent}")

# ── 4. Wyciagnij daty z URL do PDF ───────────────────────
# np. "od-29.06.2026-r.do-05.07.2026-r."
date_match = re.search(r'od-(\d{2}[\.\-]\d{2}[\.\-]\d{4}).*?do-(\d{2}[\.\-]\d{2}[\.\-]\d{4})', pdf_url)
if date_match:
    date_from = date_match.group(1).replace("-", ".")
    date_to   = date_match.group(2).replace("-", ".")
else:
    # Sprobuj z tekstu PDF
    date_match2 = re.search(r'(\d{2}\.\d{2}\.\d{4})', text)
    date_from = date_match2.group(1) if date_match2 else ""
    date_to   = ""

print(f"Data od: {date_from}, Data do: {date_to}")

# ── 5. Zapisz fuel.json ───────────────────────────────────
label = f"Wysokosc dodatku paliwowego od {date_from} r. do {date_to} r."

fuel = {
    "percent":  percent,
    "dateFrom": date_from,
    "dateTo":   date_to,
    "label":    label,
    "pdfUrl":   pdf_url,
    "updated":  date.today().isoformat()
}

with open("fuel.json", "w", encoding="utf-8") as f:
    json.dump(fuel, f, ensure_ascii=False, indent=2)

print(f"fuel.json zaktualizowany: {percent}% ({date_from} - {date_to})")
