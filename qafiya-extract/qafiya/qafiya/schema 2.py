"""Schema inference + typed coercion for extracted records (spec §1.2)."""
import re
from datetime import date

_BOOL = {"true", "false", "yes", "no", "t", "f"}
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _is_number(v: str) -> bool:
    try:
        float(v)
        return True
    except (ValueError, TypeError):
        return False


def infer_type(values) -> str:
    vals = [str(v).strip() for v in values if v is not None and str(v).strip() != ""]
    if not vals:
        return "string"
    if all(v.lower() in _BOOL for v in vals):
        return "boolean"
    if all(_is_number(v) for v in vals):
        return "number"
    if all(_DATE.match(v) for v in vals):
        return "timestamp"
    return "string"


def coerce(v: str, typ: str):
    s = "" if v is None else str(v).strip()
    if s == "":
        return None
    if typ == "number":
        return float(s)
    if typ == "boolean":
        return s.lower() in {"true", "yes", "t"}
    return s  # string / timestamp kept as text


def infer_schema(header, data_rows):
    cols = [h.strip() for h in header]
    fields = {}
    for i, name in enumerate(cols):
        sample = [r[i] for r in data_rows if len(r) > i]
        fields[name] = infer_type(sample)
    lower = {c.lower(): c for c in cols}
    id_field = lower.get("id", None)  # synthetic id is always added by the importer
    return {"id_field": id_field, "fields": fields}
