"""Bounded Bulk writes. No document reads or index administration."""

import json
import logging
import time

from core.exceptions import ConfigurationError

RETRY_STATUSES = {429, 500, 502, 503, 504}


LOGGER = logging.getLogger(__name__)


def create_client(settings):
    from opensearchpy import OpenSearch

    if not settings.opensearch_url:
        raise ConfigurationError("OPENSEARCH_URL is required")
    return OpenSearch(
        hosts=[settings.opensearch_url],
        http_auth=(settings.opensearch_username, settings.opensearch_password)
        if settings.opensearch_username
        else None,
        verify_certs=settings.opensearch_verify_ssl,
        ca_certs=settings.opensearch_ca_cert or None,
        timeout=settings.opensearch_timeout,
        max_retries=0,
        retry_on_timeout=False,
    )


def operation(kind, identifier, document, settings):
    metadata = {"_index": f"backup-{kind}", "_id": identifier}
    if kind == "images-contents":
        # Insert only: a partial scan cannot erase existing paths or initial dates.
        return [{"create": metadata}, document]
    script_id = (
        settings.opensearch_script_jobs
        if kind == "jobs"
        else settings.opensearch_script_images
        if kind == "images"
        else settings.opensearch_script_configurations
    )
    params = {"document": document}
    if kind in {"policies", "slps"}:
        params.update(kind=kind, max_history_versions=settings.history_max_versions)
    return [
        {"update": metadata},
        {"scripted_upsert": True, "upsert": {}, "script": {"id": script_id, "params": params}},
    ]


def encode_operation(op):
    return "".join(
        json.dumps(line, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n"
        for line in op
    )


class BulkWriter:
    def __init__(self, client, settings, counts, errors, *, batch_size=None):
        self.client, self.settings = client, settings
        self.counts, self.errors = counts, errors
        self.pending, self.size = [], 0
        self.batch_size = settings.opensearch_batch_size if batch_size is None else batch_size
        if self.batch_size < 1 or settings.opensearch_max_batch_mb <= 0:
            raise ConfigurationError("Bulk limits must be positive")
        if settings.opensearch_max_retries < 0 or settings.history_max_versions < 0:
            raise ConfigurationError("Retry and history limits must be nonnegative")

    def add(self, op):
        body = encode_operation(op)
        size = len(body.encode("utf-8"))
        limit = self.settings.opensearch_max_batch_mb * 1024 * 1024
        if size > limit:
            self.fail("document_exceeds_batch_limit")
            return
        if self.pending and (len(self.pending) >= self.batch_size or self.size + size > limit):
            self.flush()
        # Keep only the action name and serialized body, not a second copy of
        # the normalized document graph while waiting for the batch to fill.
        self.pending.append((next(iter(op[0])), body))
        self.size += size
        if len(self.pending) >= self.batch_size:
            self.flush()

    def fail(self, reason):
        self.counts.failed += 1
        LOGGER.debug("Bulk document failed code=%s", reason)
        if len(self.errors) < 20:
            self.errors.append({"stage": "storage", "code": reason})

    def flush(self):
        from opensearchpy.exceptions import ConnectionError, ConnectionTimeout, TransportError

        pending, self.pending = self.pending, []
        self.size = 0
        for attempt in range(self.settings.opensearch_max_retries + 1):
            if not pending:
                return
            retry = []
            LOGGER.debug(
                "Bulk attempt=%d documents=%d bytes=%d",
                attempt + 1,
                len(pending),
                sum(len(body.encode("utf-8")) for _, body in pending),
            )
            try:
                response = self.client.bulk(
                    body="".join(body for _, body in pending),
                    params={"require_alias": "true"},
                    request_timeout=self.settings.opensearch_timeout,
                )
                items = response.get("items", [])
                if len(items) != len(pending):
                    for _ in pending:
                        self.fail("invalid_bulk_response")
                    return
                for (action, body), item in zip(pending, items):
                    result = item.get(action, {})
                    status = result.get("status", 0)
                    outcome = result.get("result")
                    if 200 <= status < 300 and outcome in {"created", "updated", "noop"}:
                        setattr(self.counts, outcome, getattr(self.counts, outcome) + 1)
                    elif action == "create" and status == 409:
                        # Existing image path; this is a confirmed insert-only replay.
                        self.counts.noop += 1
                    elif (
                        status in RETRY_STATUSES and attempt < self.settings.opensearch_max_retries
                    ):
                        retry.append((action, body))
                    else:
                        error = result.get("error", {})
                        LOGGER.debug("Bulk failure status=%s details=%s", status, error)
                        self.fail(
                            error.get("type", f"bulk_http_{status}")
                            if isinstance(error, dict)
                            else f"bulk_http_{status}"
                        )
            except (ConnectionError, ConnectionTimeout):
                LOGGER.debug("Bulk connection failure", exc_info=True)
                if attempt < self.settings.opensearch_max_retries:
                    retry = pending
                else:
                    for _ in pending:
                        self.fail("bulk_transport_failure_unconfirmed")
            except TransportError as exc:
                LOGGER.debug("Bulk transport failure", exc_info=True)
                if (
                    exc.status_code in RETRY_STATUSES
                    and attempt < self.settings.opensearch_max_retries
                ):
                    retry = pending
                else:
                    for _ in pending:
                        self.fail(f"bulk_http_{exc.status_code}")
            pending = retry
            LOGGER.debug(
                "Bulk totals created=%d updated=%d noop=%d failed=%d retrying=%d",
                self.counts.created,
                self.counts.updated,
                self.counts.noop,
                self.counts.failed,
                len(pending),
            )
            if pending:
                time.sleep(min(0.5 * 2**attempt, 8))
