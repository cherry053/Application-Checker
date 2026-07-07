import pdfplumber


def extract_lines(file) -> list[str]:
    """Extract text from a SmartyGrants PDF export as a flat list of stripped lines.

    `file` is anything pdfplumber.open() accepts (path, bytes, or a
    file-like object such as Streamlit's UploadedFile).
    """
    lines: list[str] = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                lines.extend(line.strip() for line in text.split("\n"))
    return lines
