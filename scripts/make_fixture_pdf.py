from __future__ import annotations

from pathlib import Path

PAGES = [
    "Page one: The capital of France is Paris. "
    "The Eiffel Tower was completed in 1889.",
    "Page two: Python is a programming language created by Guido van Rossum "
    "and first released in 1991.",
    "Page three: The maximum upload size for this knowledge base is 20 MB, "
    "and files are stored with generated names.",
]

def build_pdf(path: Path) -> Path:
    font_id = 3
    bodies: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }

    page_ids: list[int] = []
    next_id = 4
    for i, text in enumerate(PAGES, start=1):
        safe = text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        stream = f"BT /F1 14 Tf 50 750 Td ({safe} (page {i})) Tj ET"
        content_id = next_id
        bodies[content_id] = (
            f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream".encode(
                "latin-1"
            )
        )
        next_id += 1
        page_id = next_id
        next_id += 1
        bodies[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {content_id} 0 R "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> >>"
        ).encode("latin-1")
        page_ids.append(page_id)

    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    bodies[2] = (
        f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>"
    ).encode("latin-1")

    out = bytearray(b"%PDF-1.4\n")
    offsets: dict[int, int] = {}
    for num in sorted(bodies):
        offsets[num] = len(out)
        out += f"{num} 0 obj\n".encode() + bodies[num] + b"\nendobj\n"

    size = max(bodies) + 1
    xref_pos = len(out)
    out += f"xref\n0 {size}\n".encode()
    out += b"0000000000 65535 f \n"
    for num in range(1, size):
        out += f"{offsets[num]:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {size} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    ).encode()

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(out))
    return path

if __name__ == "__main__":
    target = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "sample.pdf"
    build_pdf(target)
    print(f"wrote {target} ({target.stat().st_size} bytes)")
