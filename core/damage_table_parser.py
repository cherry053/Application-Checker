from decimal import Decimal
from typing import Optional

from core.field_parser import parse_currency
from core.models import DamageItem

# Values the form offers for the leading Asset Category column; each occurrence
# starts a new damage item record.
ASSET_CATEGORY_VALUES = frozenset({
    "Public Infrastructure",
    "Transport Infrastructure",
})

# Full option list of the Asset Sub-Category checkbox group. The text export
# dumps every option; the selected value appears after the group's Clear line.
SUB_CATEGORY_OPTIONS = frozenset({
    "Road/s",
    "Road Infrastructure",
    "Bridge/s",
    "Tunnel/s",
    "Culverts",
    "Public Hospitals",
    "Public Schools",
    "Public Housing",
    "Prison/Correctional Facilities",
    "Police, Fire and Emergency Services' Stations",
    "Levees (incl. flood gates)",
    "State/Territory or Local Government Offices",
    "Storm Water Infrastructure",
    "Other:",
})

# Full option list of the Asset Material checkbox group.
MATERIAL_OPTIONS = frozenset({
    "Sealed",
    "Concrete",
    "Gravel",
    "Unsealed - Formed",
    "Unsealed - Unformed",
    "Footpath or Bikeways",
    "Cycleway",
    "Embankment",
    "Barriers",
    "Signage",
    "Signalling",
    "Lighting",
    "Noise Attenuation",
    "Drainage",
    "Other:",
})

# Interface chrome emitted by the web form that carries no data.
NOISE_LINES = frozenset({
    "",
    "*Required",
    "Response required.",
    "Open Calendar",
    "Show map",
    "Prefill",
    "Enter a location",
    "Upload new file",
    "No file chosen",
    "Select stored file",
})
NOISE_PREFIXES = (
    "Attach a file",
    "Use the arrow keys",
)

CLEAR_MARKER = "selected value for"
REQUIRED_SUFFIX = "*Required"

FILE_SIZE_UNITS = {"b": 1, "kb": 1_000, "mb": 1_000_000, "gb": 1_000_000_000}

DATE_SEPARATOR = "/"

EXPECTED_COORDINATE_COUNT = 7  # chainage focal/from/to + lon/lat (from) + lon/lat (to)


def _clean(raw: str) -> str:
    line = raw.strip()
    while line.endswith(REQUIRED_SUFFIX):
        line = line[: -len(REQUIRED_SUFFIX)].strip()
        if line.endswith("*"):
            line = line[:-1].strip()
    return line


def _is_clear_anchor(line: str) -> bool:
    return line.startswith("Clear") and CLEAR_MARKER in line


def _is_noise(line: str) -> bool:
    return line in NOISE_LINES or any(line.startswith(prefix) for prefix in NOISE_PREFIXES)


def _to_float(line: str) -> Optional[float]:
    try:
        return float(line)
    except ValueError:
        return None


def _looks_like_date(line: str) -> bool:
    parts = line.split(DATE_SEPARATOR)
    return len(parts) == 3 and all(part.strip().isdigit() for part in parts)


def _is_address(line: str) -> bool:
    return ", Australia" in line or line.endswith("Australia")


def _size_to_bytes(text: str) -> Optional[int]:
    parts = text.split()
    if len(parts) != 2:
        return None
    value = _to_float(parts[0])
    multiplier = FILE_SIZE_UNITS.get(parts[1].lower())
    if value is None or multiplier is None:
        return None
    return int(value * multiplier)


def _relevant_lines(text: str) -> list[str]:
    """Cleaned content lines, keeping the Clear/Filename/File size anchors."""
    lines = []
    for raw in text.splitlines():
        line = _clean(raw)
        if line and not _is_noise(line):
            lines.append(line)
    return lines


def count_table_records(text: str) -> int:
    """Number of damage-item records present in the pasted table text.

    Each record starts with an Asset Category line, so counting those anchors
    gives the row count the source text contains - independently of whether
    parsing each record succeeds. Used to check whether a paste looks complete.
    """
    return sum(1 for line in _relevant_lines(text) if line in ASSET_CATEGORY_VALUES)


def parse_damage_table(text: str) -> tuple[list[DamageItem], list[str]]:
    """Parse the pasted damage-table text export into damage items.

    The export is the web form copied as plain text: a tab-separated header
    row, guidance sentences, then one block per damage item starting with the
    Asset Category value. Parsing is anchor- and order-based; anything that
    cannot be placed is recorded as a warning instead of raising.
    """
    warnings: list[str] = []
    lines = _relevant_lines(text)

    boundaries = [i for i, line in enumerate(lines) if line in ASSET_CATEGORY_VALUES]
    if not boundaries:
        warnings.append("No damage item records found in the pasted table text.")
        return [], warnings

    items: list[DamageItem] = []
    for n, start in enumerate(boundaries):
        end = boundaries[n + 1] if n + 1 < len(boundaries) else len(lines)
        item = _parse_record(lines[start:end])
        items.append(item)
        warnings.extend(f"{item.damage_item_id or f'Item {n + 1}'}: {w}" for w in item.parse_warnings)

    return items, warnings


def _parse_record(lines: list[str]) -> DamageItem:
    item = DamageItem(asset_category=lines[0])
    cursor = 1

    cursor = _parse_identity(item, lines, cursor)
    cursor = _parse_locations(item, lines, cursor)
    cursor = _parse_sub_category(item, lines, cursor)
    cursor = _parse_asset_attributes(item, lines, cursor)
    cursor = _parse_material_and_function(item, lines, cursor)
    cursor = _parse_evidence_and_costs(item, lines, cursor)

    return item


def _parse_identity(item: DamageItem, lines: list[str], cursor: int) -> int:
    """Damage item ID, asset ID, asset name, and accessibility date."""
    head: list[str] = []
    while cursor < len(lines) and len(head) < 8:
        line = lines[cursor]
        if _looks_like_date(line):
            item.date_accessible = line
            cursor += 1
            break
        if line in SUB_CATEGORY_OPTIONS or _is_clear_anchor(line):
            break
        head.append(line)
        cursor += 1

    if head:
        item.damage_item_id = head[0]
    if len(head) > 1:
        item.asset_id = head[1]
    if len(head) > 2:
        item.asset_name = " ".join(head[2:])
    if item.date_accessible is None:
        item.parse_warnings.append("No 'Date Asset Accessible' value found.")
    return cursor


def _parse_locations(item: DamageItem, lines: list[str], cursor: int) -> int:
    """Damage start/end addresses, chainage values, and the four coordinates.

    The segment runs from the date to the sub-category option dump. Each
    address is followed by its map-pin latitude/longitude pair, so the
    chainage and from/to coordinates are always the last seven numbers.
    """
    segment: list[str] = []
    while cursor < len(lines) and lines[cursor] not in SUB_CATEGORY_OPTIONS and not _is_clear_anchor(lines[cursor]):
        segment.append(lines[cursor])
        cursor += 1

    addresses = [line for line in segment if _is_address(line)]
    item.location_start = addresses[0] if addresses else None
    item.location_end = addresses[1] if len(addresses) > 1 else None

    numbers = [value for line in segment if (value := _to_float(line)) is not None]
    if len(numbers) >= EXPECTED_COORDINATE_COUNT:
        (
            item.chainage_focal,
            item.chainage_from,
            item.chainage_to,
            item.longitude_from,
            item.latitude_from,
            item.longitude_to,
            item.latitude_to,
        ) = numbers[-EXPECTED_COORDINATE_COUNT:]
    else:
        item.parse_warnings.append(
            f"Expected {EXPECTED_COORDINATE_COUNT} chainage/coordinate values, found {len(numbers)}."
        )
    return cursor


def _parse_sub_category(item: DamageItem, lines: list[str], cursor: int) -> int:
    """Skip the option dump; the selected value follows the group's Clear line."""
    while cursor < len(lines) and lines[cursor] in SUB_CATEGORY_OPTIONS:
        cursor += 1
    if cursor < len(lines) and _is_clear_anchor(lines[cursor]) and "Asset Sub-Category" in lines[cursor]:
        cursor += 1
        if cursor < len(lines) and not _is_clear_anchor(lines[cursor]):
            item.sub_category = lines[cursor]
            cursor += 1
    if item.sub_category is None:
        item.parse_warnings.append("No Asset Sub-Category selection found.")
    return cursor


def _parse_asset_attributes(item: DamageItem, lines: list[str], cursor: int) -> int:
    """Classification type, capacity, layout, and dimensions, in column order."""
    scalars: list[str] = []
    while cursor < len(lines) and lines[cursor] not in MATERIAL_OPTIONS and not _is_clear_anchor(lines[cursor]):
        scalars.append(lines[cursor])
        cursor += 1

    if scalars:
        item.classification_type = scalars[0]
    if len(scalars) > 1:
        item.capacity = scalars[1]
    if len(scalars) > 2:
        item.layout = scalars[2]
    if len(scalars) > 3:
        item.dimensions = " ".join(scalars[3:])
    if len(scalars) < 4:
        item.parse_warnings.append(
            f"Expected 4 asset attribute values (classification, capacity, layout, dimensions), found {len(scalars)}."
        )
    return cursor


def _parse_material_and_function(item: DamageItem, lines: list[str], cursor: int) -> int:
    """The material checkboxes and pre-disaster-function radio.

    The plain-text export dumps every option without marking the selection,
    so these two answers are unrecoverable; that is recorded as a warning.
    """
    while cursor < len(lines) and lines[cursor] in MATERIAL_OPTIONS:
        cursor += 1
    if cursor < len(lines) and _is_clear_anchor(lines[cursor]) and "Asset Material" in lines[cursor]:
        cursor += 1
        item.parse_warnings.append("Asset Material selection cannot be determined from the text export.")

    while cursor < len(lines) and lines[cursor] in {"Yes", "No"}:
        cursor += 1
    if cursor < len(lines) and _is_clear_anchor(lines[cursor]):
        cursor += 1
        item.parse_warnings.append(
            "Answer to 'same pre-disaster function' cannot be determined from the text export."
        )
    return cursor


def _parse_evidence_and_costs(item: DamageItem, lines: list[str], cursor: int) -> int:
    """Evidence uploads, damage description, estimation method, and costs."""
    skipped: list[str] = []
    item.pre_disaster_evidence_file, item.pre_disaster_evidence_bytes, cursor = _upload_at(lines, cursor, skipped)
    if skipped:
        item.deviation_reason = " ".join(skipped)

    item.damage_evidence_file, item.damage_evidence_bytes, cursor = _upload_at(lines, cursor, [])

    description: list[str] = []
    while cursor < len(lines) and not lines[cursor].startswith("$"):
        description.append(lines[cursor])
        cursor += 1
    if description and "cost estimat" in description[-1].lower():
        item.estimation_method = description.pop()
    item.damage_description = " ".join(description) or None

    amounts: list[Decimal] = []
    while cursor < len(lines) and lines[cursor].startswith("$"):
        amount = parse_currency(lines[cursor])
        if amount is not None:
            amounts.append(amount)
        cursor += 1
    if len(amounts) == 5:
        (
            item.cost_construction,
            item.cost_pm_design,
            item.cost_contingency,
            item.cost_escalation,
            item.cost_total,
        ) = amounts
    else:
        item.parse_warnings.append(f"Expected 5 cost amounts, found {len(amounts)}.")
        if amounts:
            item.cost_total = amounts[-1]

    trailing: list[str] = []
    item.cost_evidence_file, item.cost_evidence_bytes, cursor = _upload_at(lines, cursor, trailing)
    item.methodology = " ".join(lines[cursor:]) or None
    return len(lines)


def _upload_at(lines: list[str], cursor: int, skipped: list[str]) -> tuple[Optional[str], Optional[int], int]:
    """Consume the next 'Filename'/'File size' pair, collecting skipped lines.

    When no upload block remains, nothing is consumed: the cursor is returned
    unchanged and `skipped` is left empty so the caller reprocesses the lines.
    """
    scan = cursor
    while scan < len(lines) and lines[scan] != "Filename":
        skipped.append(lines[scan])
        scan += 1
    if scan >= len(lines):
        skipped.clear()
        return None, None, cursor

    filename = lines[scan + 1] if scan + 1 < len(lines) else None
    size = None
    scan += 2
    if scan < len(lines) and lines[scan] == "File size":
        if scan + 1 < len(lines):
            size = _size_to_bytes(lines[scan + 1])
        scan += 2
    return filename, size, scan
