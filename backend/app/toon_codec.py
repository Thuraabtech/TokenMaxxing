"""Minimal TOON (Token-Oriented Object Notation) codec.

Only implements the one shape this project actually needs: an array of
uniform objects (same keys, no nesting) -- e.g. retrieved chunks or the
routing table. That's TOON's sweet spot; for anything nested or irregular,
just use JSON instead of reaching for this module.

Format:
    [N]{field1,field2}:
      val1,val2
      val1,val2

N is the row count, the header lists field names once, and each row is a
comma-separated line. A field value containing a comma is wrapped in double
quotes (doubled internal quotes), same escaping rule as CSV.
"""

import csv
import io


def encode_table(rows: list[dict]) -> str:
    if not rows:
        return "[0]{}:"

    fields = list(rows[0].keys())
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    for row in rows:
        writer.writerow([row.get(f, "") for f in fields])

    header = f"[{len(rows)}]{{{','.join(fields)}}}:"
    body = "\n".join(f"  {line}" for line in buf.getvalue().splitlines())
    return f"{header}\n{body}" if body else header


def decode_table(text: str) -> list[dict]:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return []

    header = lines[0].strip()
    if "{" not in header or "}" not in header:
        raise ValueError(f"malformed TOON header: {header!r}")

    fields_part = header[header.index("{") + 1 : header.index("}")]
    fields = [f for f in fields_part.split(",") if f]

    rows = []
    reader = csv.reader(line.strip() for line in lines[1:])
    for values in reader:
        if not values:
            continue
        rows.append(dict(zip(fields, values)))
    return rows
