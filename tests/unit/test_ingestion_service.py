"""Orchestration decisions with synthetic in-memory doubles, not durability proof."""

from contextlib import nullcontext
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from nyc311_pipeline.bronze_contracts import Checkpoint, CommitResult, IngestRun, IngestScope
from nyc311_pipeline.ingestion.models import CreationCursor, IngestionError, Page
from nyc311_pipeline.ingestion.service import ingest

SCOPE = IngestScope((("2025-01-01T00:00:00", "2025-01-02T00:00:00"),), page_size=2)
GEN = datetime(2026, 1, 1, tzinfo=UTC)


class MemoryRepository:
    def dataset_lock(self, dataset):
        return nullcontext()

    def begin_run(self, run_id, scope, resume=False):
        self.run = IngestRun(run_id, scope, "running", False, 0, 0, None)
        self.checkpoint = Checkpoint(run_id, "0")
        self.commits = 0
        return self.run

    def load_run(self, run_id):
        return self.run

    def load_checkpoint(self, run_id, segment):
        return self.checkpoint

    def commit_page(self, run_id, cp, page):
        assert cp == self.checkpoint
        self.commits += 1
        self.checkpoint = replace(
            cp,
            page_no=cp.page_no + 1,
            cursor=page.next_cursor,
            generation=page.generation,
            exhausted=page.exhausted,
        )
        self.run = replace(
            self.run,
            generation=page.generation,
            received_count=self.run.received_count + len(page.records),
        )
        return CommitResult(self.checkpoint, len(page.records), len(page.records), self.commits)

    def finish_ingestion(self, run_id, *, outcome, category=None, retryable=False):
        self.outcome, self.category, self.retryable = outcome, category, retryable
        self.run = replace(
            self.run,
            status="failed" if outcome == "failed" else "paused",
            ingest_complete=outcome == "completed",
        )
        return self.run


class Client:
    def __init__(self, count=1):
        self.requests = []
        self.count = count

    async def fetch_page(self, request):
        self.requests.append(request)
        records = tuple({"unique_key": str(i)} for i in range(self.count))
        cursor = CreationCursor("2025-01-01T12:00:00", "10") if records else request.cursor
        self.count = 0
        return Page(records, cursor, not records, GEN, GEN, None, {})


@pytest.mark.asyncio
@pytest.mark.parametrize("cap", [0, -1, True, 1.5, "1"])
async def test_invalid_cap_never_opens_run(cap):
    with pytest.raises(IngestionError, match="configuration"):
        await ingest(Client(), object(), SCOPE, max_records=cap)


@pytest.mark.asyncio
async def test_ambiguous_run_identity_rejected_before_storage():
    with pytest.raises(IngestionError):
        await ingest(Client(), object(), SCOPE, run_id=uuid4(), resume_run_id=uuid4())


@pytest.mark.asyncio
async def test_short_page_requires_empty_page_and_pins_generation():
    repo, client = MemoryRepository(), Client()
    result = await ingest(client, repo, SCOPE)
    assert result.outcome == "completed" and not result.published
    assert len(client.requests) == 2 and repo.commits == 2
    assert client.requests[1].pinned_generation == GEN
    assert client.requests[1].cursor.unique_key == "10"


@pytest.mark.asyncio
async def test_cap_is_exact_and_not_completion():
    repo, client = MemoryRepository(), Client()
    result = await ingest(client, repo, SCOPE, max_records=1)
    assert result.outcome == "paused" and not result.run.ingest_complete
    assert client.requests[0].limit == 1 and len(client.requests) == 1
    assert repo.category == "record_cap"


@pytest.mark.asyncio
async def test_client_cannot_return_more_than_invocation_cap():
    repo = MemoryRepository()
    with pytest.raises(IngestionError, match="source_contract"):
        await ingest(Client(count=2), repo, SCOPE, max_records=1)
    assert repo.commits == 0 and repo.outcome == "failed"
