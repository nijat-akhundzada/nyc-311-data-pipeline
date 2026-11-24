"""Fixture-backed HTTP transport still exercises the real API client and query builder."""

import json
from datetime import UTC, datetime
from email.utils import format_datetime
from pathlib import Path

import httpx

from nyc311_pipeline.bronze_contracts import fingerprint
from nyc311_pipeline.ingestion.client import ApiClient
from nyc311_pipeline.ingestion.cursor import cursor_key
from nyc311_pipeline.ingestion.models import CreationCursor, UpdateCursor, source_time, utc_time


class FixtureSource:
    def __init__(self, document: dict):
        self.document = document
        self.fixture_hash = fingerprint(document)
        self.request = None
        self.observed = utc_time(document.get("observed_at", "2026-11-24T12:00:00Z"))
        self.client = ApiClient(
            transport=httpx.MockTransport(self._respond), utc_now=lambda: self.observed
        )

    @classmethod
    def from_path(cls, path: str):
        return cls(json.loads(Path(path).read_text()))

    def _respond(self, http_request):
        request = self.request
        start, end = (
            source_time(request.creation_start_source),
            source_time(request.creation_end_source),
        )
        selected = []
        for row in self.document["records"]:
            if not start <= source_time(row["created_date"]) < end:
                continue
            cursor = CreationCursor(row["created_date"], row["unique_key"])
            if request.kind == "update":
                updated = utc_time(row[":updated_at"])
                if not request.update_lower_utc <= updated < request.update_upper_utc:
                    continue
                cursor = UpdateCursor(updated, row["unique_key"])
            if request.cursor is None or cursor_key(cursor) > cursor_key(request.cursor):
                selected.append((cursor_key(cursor), row))
        selected.sort(key=lambda pair: pair[0])
        generation = format_datetime(
            utc_time(self.document.get("generation", datetime(2026, 11, 24, tzinfo=UTC))),
            usegmt=True,
        )
        return httpx.Response(
            200,
            json=[r for _, r in selected[: request.limit]],
            headers={
                "X-SODA2-Data-Out-Of-Date": "false",
                "X-SODA2-Truth-Last-Modified": generation,
                "X-SODA2-Secondary-Last-Modified": generation,
            },
        )

    async def fetch_page(self, request):
        self.request = request
        return await self.client.fetch_page(request)

    async def aclose(self):
        await self.client.aclose()
