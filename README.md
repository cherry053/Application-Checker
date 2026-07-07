# Application-Checker
Updated version with the new txt file upload.

## How it works

The checker takes two inputs from the upload page:

1. **The SmartyGrants PDF export** of an EPAR application. It is parsed up to the
   *Damage Information* section, and again from *Number of Damage Items* onward.
   The damage table pages in between are skipped — their rotated column layout
   does not survive PDF text extraction.
2. **The damage table as text** — the table copied out of the web form (pasted
   into the text box, or uploaded as a `.txt` file alongside the PDF). This
   supplies the damage items the PDF cannot.

Both sources are parsed without regular expressions (anchor lines, ordered
cursor walks, and plain string operations only), merged, and run through the
validation rules: required fields, email/phone/date formats, NSW addresses and
coordinate bounds, chainage ranges, cost component sums, evidence file naming
conventions and size limits, plus cross-document reconciliation of the damage
item count and the total amount requested.

## Layout

- `core/pdf_extract.py` — PDF text extraction, page header/footer removal
- `core/section_splitter.py` — cuts the PDF at the damage table boundaries
- `core/field_parser.py` — application-level field parsing (labels, radios, checkboxes)
- `core/damage_table_parser.py` — damage-table text export parsing
- `core/validators.py` — all validation rules and scoring
- `core/pipeline.py` — `check_application(pdf, table_text)` orchestration
- `app.py`, `pages/1_Results.py` — Streamlit upload and results pages

## Running

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Tests

```bash
python -m pytest tests/
```
