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

Results are grouped into the six form-navigation sections (Grant Program
Information, Eligible Delivery Agency Details, EPAR Project Details, Damage
Information, EPAR Funding Request, Declaration and Authorisation), each an
expandable drop-down showing which criteria passed. Raised flags are also
shown as a ranked list of severity cards (most severe first) on the results
page. The full feedback can be downloaded as a PDF report.

Before the check runs, the upload page compares the pasted damage-table text
against the item count the PDF itself declares. If the paste looks
incomplete (no recognisable rows, or fewer rows than declared), the user is
warned and asked to confirm whether to continue anyway before the checker
proceeds.

Checking an application navigates to a dedicated Processing page that runs
the pipeline with a live staged progress checklist (Reading document →
Parsing application fields → Extracting damage table → Validating criteria →
Generating report), then hands off to the results page.

## Layout

- `core/pdf_extract.py` — PDF text extraction, page header/footer removal
- `core/section_splitter.py` — cuts the PDF at the damage table boundaries
- `core/field_parser.py` — application-level field parsing (labels, radios, checkboxes)
- `core/damage_table_parser.py` — damage-table text export parsing
- `core/validators.py` — all validation rules and scoring
- `core/paste_check.py` — flags an incompletely pasted damage table before checking
- `core/sections.py` — form-section constants and criteria grouping
- `core/report_pdf.py` — downloadable PDF feedback report
- `core/pipeline.py` — `check_application(pdf, table_text)` orchestration with staged progress
- `utils/ui.py` — NSW-branded rendering helpers (templates in `static/html`)
- `app.py` — upload form and the incomplete-paste confirmation gate
- `pages/2_Processing.py` — dedicated loading page that runs the check
- `pages/1_Results.py` — processed-applications list, filters, and detail view

## Styling

The NSW Design System stylesheet (v3.24.10, MIT licensed) is vendored at
`static/vendor/` and served through Streamlit's static file route
(`server.enableStaticServing` in `.streamlit/config.toml`), so branding does
not depend on CDN availability inside firewalled networks. Application-specific
styles live in `static/css/main.css`.

## Running

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Tests

```bash
python -m pytest tests/
```
