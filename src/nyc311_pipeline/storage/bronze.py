"""Short, replay-safe Bronze transactions on one caller-owned locked session.

The caller supplies an idle autocommit connection. This repository owns its
transactions, never a caller transaction, and never reconnects behind a lost lock.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from functools import wraps
from uuid import UUID

import psycopg
from psycopg.pq import TransactionStatus
from psycopg.types.json import Jsonb

from nyc311_pipeline.bronze_contracts import (
    Checkpoint,
    CommitResult,
    IngestRun,
    IngestScope,
    RunConflict,
    StorageError,
    fingerprint,
)
from nyc311_pipeline.ingestion.cursor import validate_records
from nyc311_pipeline.ingestion.models import IngestionError, Page, utc_time


def _database_errors(method):
    @wraps(method)
    def call(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except psycopg.Error as error:
            raise StorageError(retryable=isinstance(error, psycopg.OperationalError)) from None

    return call


def dataset_lock_key(dataset_id: str) -> int:
    import hashlib

    return int.from_bytes(
        hashlib.sha256(f"nyc311:run:{dataset_id}".encode()).digest()[:8], "big", signed=True
    )


class BronzeRepository:
    def __init__(self, connection: psycopg.Connection) -> None:
        self.connection = connection
        self._dataset: str | None = None
        self._idle()

    def _idle(self) -> None:
        if (
            self.connection.closed
            or not self.connection.autocommit
            or self.connection.info.transaction_status != TransactionStatus.IDLE
        ):
            raise StorageError(retryable=self.connection.closed)

    @contextmanager
    def dataset_lock(self, dataset_id: str = "erm2-nwe9") -> Iterator[None]:
        """Fail fast on contenders; same session must perform every mutation."""
        self._idle()
        if self._dataset is not None:
            raise RunConflict()
        try:
            acquired = self.connection.execute(
                "SELECT pg_try_advisory_lock(%s)", (dataset_lock_key(dataset_id),)
            ).fetchone()[0]
        except psycopg.Error:
            raise StorageError(retryable=True) from None
        if not acquired:
            raise RunConflict()
        self._dataset = dataset_id
        try:
            yield
        finally:
            self._dataset = None
            if not self.connection.closed:
                try:
                    self.connection.execute(
                        "SELECT pg_advisory_unlock(%s)", (dataset_lock_key(dataset_id),)
                    )
                except psycopg.Error:
                    # A lost session releases its locks; never hide the original failure.
                    self.connection.close()

    def _require_lock(self, dataset_id: str) -> None:
        if self._dataset != dataset_id:
            raise RunConflict()

    def _run(self, run_id: UUID, *, lock: bool = False) -> IngestRun:
        row = self.connection.execute(
            "SELECT config,status,ingest_complete,received_count,raw_inserted_count,generation "
            "FROM ops.pipeline_runs WHERE run_id=%s" + (" FOR UPDATE" if lock else ""),
            (run_id,),
        ).fetchone()
        if row is None:
            raise RunConflict()
        return IngestRun(run_id, IngestScope.from_document(row[0]), *row[1:])

    @_database_errors
    def load_run(self, run_id: UUID) -> IngestRun:
        self._idle()
        return self._run(run_id)

    def _event(
        self, run_id: UUID, event: str, category: str | None = None, retryable: bool = False
    ) -> None:
        self.connection.execute(
            "INSERT INTO ops.run_events (run_id,event,category,retryable) VALUES (%s,%s,%s,%s)",
            (run_id, event, category, retryable),
        )

    @_database_errors
    def begin_run(
        self,
        run_id: UUID,
        scope: IngestScope,
        *,
        resume: bool = False,
        settings: dict | None = None,
    ) -> IngestRun:
        """Thin pre-Spec07 adapter to the canonical table; no independent run manager."""
        self._idle()
        self._require_lock(scope.dataset_id)
        with self.connection.transaction():
            existing = self.connection.execute(
                "SELECT run_id FROM ops.pipeline_runs WHERE run_id=%s", (run_id,)
            ).fetchone()
            if resume:
                run = self._run(run_id, lock=True)
                if run.scope.scope_id != scope.scope_id:
                    raise RunConflict()
                if run.ingest_complete:
                    return run
                allowed = self.connection.execute(
                    "SELECT status <> 'succeeded' AND (status <> 'failed' OR retryable) "
                    "FROM ops.pipeline_runs WHERE run_id=%s",
                    (run_id,),
                ).fetchone()[0]
                if not allowed:
                    raise RunConflict()
                self.connection.execute(
                    "UPDATE ops.pipeline_runs SET status='running',error_category=NULL,"
                    "retryable=false,heartbeat_at=clock_timestamp() WHERE run_id=%s",
                    (run_id,),
                )
                self._event(run_id, "resumed")
            else:
                if (
                    existing is not None
                    or self.connection.execute(
                        "SELECT 1 FROM ops.pipeline_runs "
                        "WHERE dataset_id=%s AND NOT ingest_complete "
                        "AND (status IN ('pending','running','paused') OR retryable)",
                        (scope.dataset_id,),
                    ).fetchone()
                ):
                    raise RunConflict()
                self.connection.execute(
                    "INSERT INTO ops.pipeline_runs "
                    "(run_id,dataset_id,contract_version,mode,scope_id,config,status) "
                    "VALUES (%s,%s,'bronze-v1',%s,%s,%s,'running')",
                    (
                        run_id,
                        scope.dataset_id,
                        "backfill" if scope.kind == "creation" else "incremental",
                        scope.scope_id,
                        Jsonb(scope.document()),
                    ),
                )
                self.connection.execute(
                    "INSERT INTO ops.ingest_checkpoints (run_id,segment_id) "
                    "SELECT %s, value FROM jsonb_array_elements_text(%s)",
                    (run_id, Jsonb(scope.segment_ids)),
                )
                if settings is not None:
                    self.connection.execute(
                        "INSERT INTO ops.run_settings(run_id,config,config_hash) VALUES (%s,%s,%s)",
                        (run_id, Jsonb(settings), fingerprint(settings)),
                    )
                self._event(run_id, "started")
            return self._run(run_id)

    def _checkpoint(self, run_id: UUID, segment_id: str, *, lock: bool = False) -> Checkpoint:
        row = self.connection.execute(
            "SELECT page_no,cursor,generation,exhausted FROM ops.ingest_checkpoints "
            "WHERE run_id=%s AND segment_id=%s" + (" FOR UPDATE" if lock else ""),
            (run_id, segment_id),
        ).fetchone()
        if row is None:
            raise RunConflict()
        from nyc311_pipeline.bronze_contracts import parse_cursor

        return Checkpoint(run_id, segment_id, row[0], parse_cursor(row[1]), row[2], row[3])

    @_database_errors
    def load_checkpoint(self, run_id: UUID, segment_id: str) -> Checkpoint:
        self._idle()
        return self._checkpoint(run_id, segment_id)

    def _validate_page(self, run: IngestRun, expected: Checkpoint, page: Page) -> list[dict]:
        generation = utc_time(page.generation)
        utc_time(page.received_at_utc)
        if run.generation is not None and run.generation != generation:
            raise IngestionError("source_generation_changed")
        try:
            if (
                page.http_metadata["out_of_date"] != "false"
                or utc_time(page.http_metadata["truth_last_modified"]) != generation
                or utc_time(page.http_metadata["secondary_last_modified"]) < generation
            ):
                raise IngestionError("source_stale", retryable=True)
        except KeyError:
            raise IngestionError("source_freshness_unknown") from None
        records, cursor = validate_records(
            [dict(r) for r in page.records],
            run.scope.request(expected.segment_id, cursor=expected.cursor),
        )
        if cursor != page.next_cursor or page.exhausted != (not records):
            raise IngestionError("source_contract")
        return [
            dict(
                unique_key=r["unique_key"],
                raw_hash=fingerprint(r),
                payload=r,
                source_updated_at=r.get(":updated_at"),
            )
            for r in records
        ]

    @_database_errors
    def commit_page(
        self, run_id: UUID, expected_checkpoint: Checkpoint, page: Page
    ) -> CommitResult:
        self._idle()
        expected = expected_checkpoint
        if expected.run_id != run_id:
            raise RunConflict()
        with self.connection.transaction():
            run = self._run(run_id, lock=True)
            self._require_lock(run.scope.dataset_id)
            current = self._checkpoint(run_id, expected.segment_id, lock=True)
            rows = self._validate_page(run, expected, page)
            after = Checkpoint(
                run_id,
                expected.segment_id,
                expected.page_no + 1,
                page.next_cursor,
                utc_time(page.generation),
                page.exhausted,
            )
            page_hash = fingerprint(
                dict(
                    records=[r["raw_hash"] for r in rows],
                    before=expected.document(),
                    after=after.document(),
                )
            )
            receipt = self.connection.execute(
                "SELECT page_hash,checkpoint_after,received_count,inserted_raw_versions "
                "FROM ops.ingest_page_receipts WHERE run_id=%s AND segment_id=%s AND page_no=%s",
                (run_id, expected.segment_id, after.page_no),
            ).fetchone()
            if receipt:
                if receipt[0] != page_hash:
                    raise RunConflict()
                return CommitResult(
                    Checkpoint.from_document(receipt[1]),
                    receipt[2],
                    receipt[3],
                    after.page_no,
                    replayed=True,
                )
            if (
                current != expected
                or current.exhausted
                or run.status != "running"
                or run.ingest_complete
            ):
                raise RunConflict()
            inserted = self.connection.execute(
                "INSERT INTO bronze.raw_service_requests "
                "(dataset_id,unique_key,raw_hash,payload,first_observed_at) "
                "SELECT %s,r.unique_key,r.raw_hash,r.payload,%s "
                "FROM jsonb_to_recordset(%s) AS r(unique_key text,raw_hash text,payload jsonb) "
                "ON CONFLICT (dataset_id,unique_key,raw_hash) DO NOTHING RETURNING raw_id",
                (run.scope.dataset_id, page.received_at_utc, Jsonb(rows)),
            ).fetchall()
            self.connection.execute(
                "INSERT INTO ops.ingest_page_receipts (run_id,segment_id,page_no,page_hash,"
                "checkpoint_before,checkpoint_after,received_count,inserted_raw_versions,"
                "received_at,request_id,http_metadata) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    run_id,
                    expected.segment_id,
                    after.page_no,
                    page_hash,
                    Jsonb(expected.document()),
                    Jsonb(after.document()),
                    len(rows),
                    len(inserted),
                    page.received_at_utc,
                    page.request_id,
                    Jsonb(dict(page.http_metadata)),
                ),
            )
            self.connection.execute(
                "INSERT INTO ops.run_records "
                "(run_id,segment_id,page_no,row_ordinal,raw_id,source_updated_at,observed_at) "
                "SELECT %s,%s,%s,r.n,b.raw_id,(r.value->>'source_updated_at')::timestamptz,%s "
                "FROM jsonb_array_elements(%s) WITH ORDINALITY AS r(value,n) "
                "JOIN bronze.raw_service_requests b ON b.dataset_id=%s "
                "AND b.unique_key=r.value->>'unique_key' AND b.raw_hash=r.value->>'raw_hash'",
                (
                    run_id,
                    expected.segment_id,
                    after.page_no,
                    page.received_at_utc,
                    Jsonb(rows),
                    run.scope.dataset_id,
                ),
            )
            self.connection.execute(
                "UPDATE ops.ingest_checkpoints SET page_no=%s,cursor=%s,generation=%s,exhausted=%s "
                "WHERE run_id=%s AND segment_id=%s",
                (
                    after.page_no,
                    Jsonb(after.document()["cursor"]) if after.cursor else None,
                    after.generation,
                    after.exhausted,
                    run_id,
                    expected.segment_id,
                ),
            )
            self.connection.execute(
                "UPDATE ops.pipeline_runs SET generation=COALESCE(generation,%s),"
                "received_count=received_count+%s,raw_inserted_count=raw_inserted_count+%s,"
                "heartbeat_at=clock_timestamp() WHERE run_id=%s",
                (after.generation, len(rows), len(inserted), run_id),
            )
            return CommitResult(after, len(rows), len(inserted), after.page_no)

    @_database_errors
    def finish_ingestion(
        self, run_id: UUID, *, outcome: str, category: str | None = None, retryable: bool = False
    ) -> IngestRun:
        """Only ingestion state: completed extraction is paused/unpublished pipeline work."""
        self._idle()
        if outcome not in {"completed", "paused", "failed"}:
            raise RunConflict()
        with self.connection.transaction():
            run = self._run(run_id, lock=True)
            self._require_lock(run.scope.dataset_id)
            if run.status != "running" or run.ingest_complete:
                raise RunConflict()
            if (
                outcome == "completed"
                and self.connection.execute(
                    "SELECT 1 FROM ops.ingest_checkpoints WHERE run_id=%s AND NOT exhausted",
                    (run_id,),
                ).fetchone()
            ):
                raise RunConflict()
            self.connection.execute(
                "UPDATE ops.pipeline_runs SET status=%s,ingest_complete=%s,error_category=%s,"
                "retryable=%s,heartbeat_at=clock_timestamp() WHERE run_id=%s",
                (
                    "failed" if outcome == "failed" else "paused",
                    outcome == "completed",
                    category,
                    retryable,
                    run_id,
                ),
            )
            self._event(
                run_id,
                "ingest_complete" if outcome == "completed" else outcome,
                category,
                retryable,
            )
            return self._run(run_id)
