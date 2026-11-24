"""Bounded Bronze extraction only. No scheduler, publication or pipeline-success claim."""

from contextlib import nullcontext
from dataclasses import dataclass
from typing import Literal, Protocol
from uuid import UUID, uuid4

from nyc311_pipeline.bronze_contracts import (
    BronzeStore,
    Checkpoint,
    CommitResult,
    IngestRun,
    IngestScope,
    StorageError,
)

from .models import ApiPageRequest, IngestionError, Page


class PageClient(Protocol):
    async def fetch_page(self, request: ApiPageRequest) -> Page: ...


@dataclass(frozen=True)
class IngestResult:
    run: IngestRun
    outcome: Literal["completed", "paused"]
    received_this_invocation: int
    published: Literal[False] = False


def _commit_with_recovery(
    repository: BronzeStore, run_id: UUID, checkpoint: Checkpoint, page: Page
) -> CommitResult:
    try:
        return repository.commit_page(run_id, checkpoint, page)
    except StorageError as error:
        if not error.retryable:
            raise
        # Keep the exact Page. A dead session fails here and requires a fresh
        # lock + explicit resume; never reconnect or re-fetch-and-skip internally.
        repository.load_checkpoint(run_id, checkpoint.segment_id)
        return repository.commit_page(run_id, checkpoint, page)


async def ingest(
    client: PageClient,
    repository: BronzeStore,
    scope: IngestScope,
    *,
    run_id: UUID | None = None,
    resume_run_id: UUID | None = None,
    max_records: int | None = None,
    acquire_lock: bool = True,
) -> IngestResult:
    """Resume immutable scope from durable truth, capping only this invocation.

    Source errors persist a categorized ingestion failure then propagate. Storage
    failures propagate without asserting a status write succeeded. Cancellation /
    process death releases the session lock, leaving explicit resume possible.
    """
    if (
        (run_id is not None and resume_run_id is not None)
        or (run_id is not None and not isinstance(run_id, UUID))
        or (resume_run_id is not None and not isinstance(resume_run_id, UUID))
        or (max_records is not None and (type(max_records) is not int or max_records <= 0))
    ):
        raise IngestionError("configuration")
    identity = resume_run_id or run_id or uuid4()
    received = 0
    with repository.dataset_lock(scope.dataset_id) if acquire_lock else nullcontext():
        run = repository.begin_run(identity, scope, resume=resume_run_id is not None)
        if run.ingest_complete:
            return IngestResult(run, "completed", 0)
        try:
            for segment_id in scope.segment_ids:
                checkpoint = repository.load_checkpoint(identity, segment_id)
                while not checkpoint.exhausted:
                    if max_records is not None and received >= max_records:
                        run = repository.finish_ingestion(
                            identity, outcome="paused", category="record_cap"
                        )
                        return IngestResult(run, "paused", received)
                    remaining = scope.page_size if max_records is None else max_records - received
                    # Read generation from persisted run too: new segments have
                    # no checkpoint generation until their first committed page.
                    generation = repository.load_run(identity).generation
                    request = scope.request(
                        segment_id,
                        cursor=checkpoint.cursor,
                        limit=min(scope.page_size, remaining),
                        pinned_generation=generation,
                    )
                    page = await client.fetch_page(request)
                    if len(page.records) > request.limit:
                        raise IngestionError("source_contract")
                    committed = _commit_with_recovery(repository, identity, checkpoint, page)
                    checkpoint = committed.checkpoint
                    received += committed.received_count
            run = repository.finish_ingestion(identity, outcome="completed")
            return IngestResult(run, "completed", received)
        except IngestionError as error:
            repository.finish_ingestion(
                identity, outcome="failed", category=error.category, retryable=error.retryable
            )
            raise
        except StorageError as error:
            try:
                repository.finish_ingestion(
                    identity, outcome="failed", category=error.category, retryable=error.retryable
                )
            except StorageError:
                pass  # Do not claim a status write succeeded on a lost session.
            raise
