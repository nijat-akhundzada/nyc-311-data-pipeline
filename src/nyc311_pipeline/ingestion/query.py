"""Pure Socrata query generation; fixed identifiers, encoded by the HTTP client."""

from .models import ApiPageRequest, CreationCursor, UpdateCursor, utc_text, validate_key

PROJECTION = (
    "unique_key,created_date,closed_date,agency,agency_name,complaint_type,"
    "descriptor,status,borough,incident_zip,resolution_action_updated_date,:updated_at"
)


def literal(value: str) -> str:
    validate_key(value)
    return "'" + value.replace("'", "''") + "'"


def build_query(request: ApiPageRequest) -> dict[str, str]:
    parts = [
        f"created_date >= {literal(request.creation_start_source)}",
        f"created_date < {literal(request.creation_end_source)}",
    ]
    order = "created_date ASC,unique_key ASC"
    if request.kind == "update":
        parts.extend(
            [
                f":updated_at >= {literal(utc_text(request.update_lower_utc))}",
                f":updated_at < {literal(utc_text(request.update_upper_utc))}",
            ]
        )
        order = ":updated_at ASC,unique_key ASC"
    if isinstance(request.cursor, CreationCursor):
        column, value = "created_date", request.cursor.created_date_source
    elif isinstance(request.cursor, UpdateCursor):
        column, value = ":updated_at", utc_text(request.cursor.updated_at_utc)
    else:
        column, value = "", ""
    if request.cursor is not None:
        parts.append(
            f"({column} > {literal(value)} OR ({column} = {literal(value)} "
            f"AND unique_key > {literal(request.cursor.unique_key)}))"
        )
    return {
        "$select": PROJECTION,
        "$where": " AND ".join(parts),
        "$order": order,
        "$limit": str(request.limit),
    }
