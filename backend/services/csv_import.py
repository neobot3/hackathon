import csv
import io

from fastapi import HTTPException, Request, status
from pydantic import ValidationError

MAX_CSV_BYTES = 1_000_000
MAX_CSV_ROWS = 5_000

# Documents the raw text/csv request body in OpenAPI.
CSV_BODY = {
    "requestBody": {
        "required": True,
        "content": {"text/csv": {"schema": {"type": "string"}}},
    }
}


async def csv_rows(request: Request) -> list[tuple[int, dict[str, str]]]:
    """Read a text/csv body into (line number, row) pairs with lower-case headers."""
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_CSV_BYTES:
            raise HTTPException(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"CSV over {MAX_CSV_BYTES} bytes",
            )
    try:
        text = body.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail="CSV must be UTF-8"
        ) from None
    reader = csv.DictReader(io.StringIO(text))
    rows: list[tuple[int, dict[str, str]]] = []
    for row in reader:
        if len(rows) >= MAX_CSV_ROWS:
            raise HTTPException(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"CSV over {MAX_CSV_ROWS} rows",
            )
        cleaned = {
            k.strip().lower(): (v or "").strip()
            for k, v in row.items()
            if isinstance(k, str)
        }
        if any(cleaned.values()):
            rows.append((reader.line_num, cleaned))
    if not rows:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail="CSV has no rows"
        )
    return rows


def validation_message(exc: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()
    )


def raise_row_errors(errors: list[tuple[int, str]]) -> None:
    """Reject the whole file, listing each bad line, so nothing is half imported."""
    if errors:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[{"loc": [f"line {line}"], "msg": msg} for line, msg in errors],
        )
