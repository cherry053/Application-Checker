import pdfplumber

# Lines appearing near the top of at least this share of pages are treated as
# repeated page headers and removed everywhere.
_HEADER_PAGE_SHARE = 0.5
_HEADER_SCAN_DEPTH = 4


def extract_pages(file) -> list[list[str]]:
    """Extract text from a SmartyGrants PDF export as stripped lines, grouped per page.

    `file` is anything pdfplumber.open() accepts (path, bytes, or a
    file-like object such as Streamlit's UploadedFile).
    """
    pages: list[list[str]] = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            pages.append([line.strip() for line in text.split("\n")] if text else [])
    return pages


def _is_page_footer(line: str) -> bool:
    """Match footers of the form 'Page 3 of 21' without regex."""
    tokens = line.split()
    return (
        len(tokens) == 4
        and tokens[0] == "Page"
        and tokens[2] == "of"
        and tokens[1].isdigit()
        and tokens[3].isdigit()
    )


def _repeated_header_lines(pages: list[list[str]]) -> set[str]:
    """Lines that recur at the top of most pages (title, application number, etc.)."""
    counts: dict[str, int] = {}
    for page in pages:
        for line in set(page[:_HEADER_SCAN_DEPTH]):
            if line:
                counts[line] = counts.get(line, 0) + 1
    threshold = max(2, int(len(pages) * _HEADER_PAGE_SHARE))
    return {line for line, count in counts.items() if count >= threshold}


def clean_lines(pages: list[list[str]]) -> list[str]:
    """Flatten pages into one line list with repeated headers and page footers removed."""
    headers = _repeated_header_lines(pages)
    lines: list[str] = []
    for page in pages:
        for position, line in enumerate(page):
            if position < _HEADER_SCAN_DEPTH and line in headers:
                continue
            if _is_page_footer(line):
                continue
            lines.append(line)
    return lines
