#!/usr/bin/env python3
"""Read-only projection of the Solo Empire external app registry.

``data/external_app_registry.ts`` stays the canonical source that the
dashboard, humans, and AI agents use; this service parses its one-record-per-
line literal into JSON for the Solo Web ``/integrations`` module.  Parsing is
strict: if any record line cannot be read the service answers 503 instead of
returning a partial list.  It never reads credentials or calls a provider.

Run locally from the repository root with::

    python3 server.py

Set ``INTEGRATIONS_API_REGISTRY_PATH`` to use another registry file and
the ``INTEGRATIONS_API_AUTH_*`` policy before exposing the service outside local development.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import RLock
from typing import Any
from urllib.parse import parse_qs, urlsplit

from service_auth import AuthError, AuthPolicy, check_read_auth, is_loopback, readiness

from _sentry import capture, init_sentry

init_sentry()

SERVICE_NAME = "solo-empire-integrations-api"
SCHEMA_VERSION = "solo-empire.integrations.v1"
STATUSES = ("live", "mcp_only", "paused", "planned")
MAX_QUERY_LENGTH = 80
MAX_FILTER_LENGTH = 40
RECORD_RE = re.compile(r"^\s*\{(?P<body>.*)\},?\s*$")
FIELD_RE = re.compile(
    r"\s*(?P<key>[A-Za-z]+):\s*'(?P<value>(?:[^'\\]|\\.)*)'\s*(?:,|$)"
)
SECTION_RE = re.compile(r"^\s*//\s*(?P<label>.+?)\s*(?:\(\d+\))?\s*$")
SAFE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
STATUS_DEFINITIONS = [
    {
        "value": "live",
        "description": "The direct read-only health checker already supports the provider.",
    },
    {
        "value": "mcp_only",
        "description": "An MCP boundary exists, but the REST API does not proxy it.",
    },
    {
        "value": "paused",
        "description": "Intentionally disabled until the account and safety gate are reopened.",
    },
    {
        "value": "planned",
        "description": "Discovery inventory only; no connector should be implied.",
    },
]


class ApiError(Exception):
    """An expected client or service error with a safe public message."""

    def __init__(
        self, status: int, message: str, *, code: str = "request_error"
    ) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.code = code


@dataclass(frozen=True)
class Response:
    status: int
    payload: dict[str, Any]


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def repository_root() -> Path:
    return Path(__file__).resolve().parent


def default_registry_path() -> Path:
    configured = os.environ.get("INTEGRATIONS_API_REGISTRY_PATH")
    return (
        Path(configured).expanduser()
        if configured
        else repository_root() / "data" / "external_app_registry.ts"
    )


def query_value(query: Mapping[str, list[str]], field: str, max_length: int) -> str:
    value = (query.get(field) or [""])[0].strip()
    if len(value) > max_length:
        raise ApiError(400, f"{field} is too long", code="invalid_field")
    return value


def counts(values: Any) -> list[dict[str, Any]]:
    return [
        {"value": key, "count": count}
        for key, count in sorted(
            Counter(values).items(), key=lambda item: (-item[1], item[0])
        )
    ]


def parse_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    position = 0
    while position < len(body):
        match = FIELD_RE.match(body, position)
        if not match:
            raise ValueError("unreadable registry field")
        fields[match["key"]] = re.sub(r"\\(.)", r"\1", match["value"])
        position = match.end()
    return fields


def parse_registry(source: str) -> list[dict[str, Any]]:
    """Parse the registry array literal; raise ValueError on any unreadable record."""
    start = source.find("= [", source.find("EXTERNAL_APP_REGISTRY"))
    end = source.find("];", start)
    if start < 0 or end < 0:
        raise ValueError("registry array not found")
    records: list[dict[str, Any]] = []
    section = "Other"
    for line in source[start + 3 : end].splitlines():
        if not line.strip():
            continue
        if heading := SECTION_RE.match(line):
            section = heading["label"]
            continue
        match = RECORD_RE.match(line)
        if not match:
            raise ValueError("unreadable registry line")
        fields = parse_fields(match["body"])
        if {"id", "name", "category", "status", "apiDocs"} - fields.keys():
            raise ValueError("registry record is missing a field")
        if fields["status"] not in STATUSES or not SAFE_ID_RE.fullmatch(fields["id"]):
            raise ValueError("invalid registry record")
        if not fields["apiDocs"].startswith("https://"):
            raise ValueError("registry docs link must be https")
        records.append(
            {
                "id": fields["id"],
                "name": fields["name"][:80],
                "category": fields["category"][:40],
                "status": fields["status"],
                "api_docs": fields["apiDocs"][:300],
                "note": fields.get("note", "")[:300] or None,
                "section": section[:80],
            }
        )
    if len({record["id"] for record in records}) != len(records):
        raise ValueError("duplicate registry id")
    return records


def guide_path(root: Path, app_id: str) -> str | None:
    """Return the integrations/<name>/README.md that documents this app, if any."""
    for name in (app_id, app_id.split("-")[0]):
        if (root / "integrations" / name / "README.md").is_file():
            return f"integrations/{name}/README.md"
    return None


class RegistryStore:
    """Reload the registry only when its modification time changes."""

    def __init__(
        self, path: str | Path | None = None, root: Path | None = None
    ) -> None:
        self.path = Path(path) if path else default_registry_path()
        self.root = root or repository_root()
        self._lock = RLock()
        self._mtime: float | None = None
        self._snapshot: tuple[list[dict[str, Any]], dict[str, Any]] | None = None

    def snapshot(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        with self._lock:
            mtime = self.path.stat().st_mtime
            if self._snapshot is None or mtime != self._mtime:
                source_text = self.path.read_text(encoding="utf-8")
                records = parse_registry(source_text)
                for record in records:
                    record["guide"] = guide_path(self.root, record["id"])
                metadata = {
                    "path": "data/external_app_registry.ts",
                    "revision": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
                    "modified_at": datetime.fromtimestamp(mtime, UTC)
                    .replace(microsecond=0)
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "status_definitions": STATUS_DEFINITIONS,
                }
                self._snapshot = (records, metadata)
                self._mtime = mtime
            return self._snapshot


class IntegrationsApi:
    """Transport-independent, read-only handler used by HTTP and tests."""

    def __init__(
        self,
        registry_path: str | Path | None = None,
        *,
        token: str | None = None,
        environment: str | None = None,
        allowed_origins: tuple[str, ...] | None = None,
        auth_policy: AuthPolicy | None = None,
        root: Path | None = None,
    ) -> None:
        self.store = RegistryStore(registry_path, root)
        self.token = (
            token
            if token is not None
            else os.environ.get("INTEGRATIONS_API_TOKEN", "").strip()
        )
        self.environment = (
            (environment or os.environ.get("INTEGRATIONS_API_ENV", "development"))
            .strip()
            .lower()
        )
        self.auth_policy = auth_policy or AuthPolicy.from_env(
            "INTEGRATIONS_API_", "integrations-api", "integrations:read"
        )
        configured_origins = os.environ.get(
            "INTEGRATIONS_API_CORS_ORIGINS",
            "http://127.0.0.1:3600,http://localhost:3600",
        )
        self.allowed_origins = allowed_origins or tuple(
            item.strip() for item in configured_origins.split(",") if item.strip()
        )

    def _check_read_auth(self, headers: Mapping[str, str]) -> None:
        try:
            check_read_auth(
                self.auth_policy,
                headers,
                environment=self.environment,
                token=self.token,
            )
        except AuthError as exc:
            raise ApiError(exc.status, exc.message, code=exc.code) from None

    def _ready(self) -> Response:
        status, payload = readiness(self.auth_policy, self.environment, self.store)
        return Response(status, payload)

    def _overview(self, query: Mapping[str, list[str]]) -> Response:
        status = query_value(query, "status", MAX_FILTER_LENGTH)
        category = query_value(query, "category", MAX_FILTER_LENGTH)
        q = query_value(query, "q", MAX_QUERY_LENGTH).casefold()
        records, metadata = self.store.snapshot()
        matched = [
            record
            for record in records
            if (not status or record["status"] == status)
            and (not category or record["category"] == category)
            and (
                not q
                or any(
                    q in str(record[field] or "").casefold()
                    for field in ("id", "name", "category", "note")
                )
            )
        ]
        by_status = Counter(record["status"] for record in records)
        return Response(
            200,
            {
                "schema_version": SCHEMA_VERSION,
                "generated_at": utc_now(),
                "source": metadata,
                "summary": {
                    "apps_total": len(records),
                    "apps_matched": len(matched),
                    "categories": len({record["category"] for record in records}),
                    "connected": by_status["live"] + by_status["mcp_only"],
                    "live": by_status["live"],
                    "mcp_only": by_status["mcp_only"],
                    "paused": by_status["paused"],
                    "planned": by_status["planned"],
                    "with_guide": sum(1 for record in records if record["guide"]),
                },
                "signals": {
                    "statuses": [
                        {"value": key, "count": by_status[key]}
                        for key in STATUSES
                        if by_status[key]
                    ],
                    "categories": counts(record["category"] for record in records),
                    "sections": counts(record["section"] for record in records),
                },
                "filters": {"status": status, "category": category, "q": q},
                "apps": matched,
                "boundary": "registry metadata only; a listed app is not proof of a working connector",
            },
        )

    def handle(
        self, method: str, target: str, *, headers: Mapping[str, str] | None = None
    ) -> Response:
        request_headers = {
            str(key).lower(): str(value) for key, value in (headers or {}).items()
        }
        parsed = urlsplit(target)
        path = parsed.path.rstrip("/") or "/"
        try:
            if method == "OPTIONS":
                return Response(204, {})
            if method == "GET" and path == "/ready":
                return self._ready()
            if method == "GET" and path == "/health":
                return Response(
                    200,
                    {
                        "status": "ok",
                        "service": SERVICE_NAME,
                        "schema_version": SCHEMA_VERSION,
                        "timestamp": utc_now(),
                    },
                )
            if path == "/api/v1/integrations":
                self._check_read_auth(request_headers)
                if method != "GET":
                    raise ApiError(
                        405,
                        "integration registry is read-only",
                        code="method_not_allowed",
                    )
                return self._overview(parse_qs(parsed.query))
            raise ApiError(404, "route not found", code="not_found")
        except ApiError as exc:
            return Response(
                exc.status, {"error": {"code": exc.code, "message": exc.message}}
            )
        except (OSError, ValueError, TypeError):
            return Response(
                503,
                {
                    "error": {
                        "code": "registry_unavailable",
                        "message": "External app registry could not be read",
                    }
                },
            )
        except Exception as exc:  # noqa: BLE001 - last-resort 500 that never echoes internal error text
            capture(exc)  # no-op unless SENTRY_DSN is set
            return Response(
                500,
                {
                    "error": {
                        "code": "internal_error",
                        "message": "Integrations service could not complete the request",
                    }
                },
            )


class IntegrationsRequestHandler(BaseHTTPRequestHandler):
    api = IntegrationsApi()

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _dispatch(self) -> None:
        origin = self.headers.get("Origin")
        if origin and origin not in self.api.allowed_origins:
            self._write(
                Response(
                    403,
                    {
                        "error": {
                            "code": "origin_not_allowed",
                            "message": "origin is not allowed",
                        }
                    },
                ),
                origin=None,
            )
            return
        self._write(
            self.api.handle(
                self.command, self.path, headers=dict(self.headers.items())
            ),
            origin=origin,
        )

    def _write(self, response: Response, *, origin: str | None) -> None:
        encoded = (
            b""
            if response.status == HTTPStatus.NO_CONTENT
            else json.dumps(
                response.payload, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
        )
        self.send_response(response.status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(encoded)))
        if origin and origin in self.api.allowed_origins:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        if self.command == "OPTIONS":
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Accept, Authorization")
        self.end_headers()
        if response.status != HTTPStatus.NO_CONTENT:
            self.wfile.write(encoded)

    do_GET = _dispatch
    do_OPTIONS = _dispatch
    do_POST = _dispatch
    do_PUT = _dispatch
    do_PATCH = _dispatch
    do_DELETE = _dispatch


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Solo Empire external app registry API"
    )
    parser.add_argument(
        "--host", default=os.environ.get("INTEGRATIONS_API_HOST", "127.0.0.1")
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(
            os.environ.get("INTEGRATIONS_API_PORT", os.environ.get("PORT", "3480"))
        ),
    )
    parser.add_argument(
        "--registry",
        default=None,
        help="registry TS file; defaults to INTEGRATIONS_API_REGISTRY_PATH or data/external_app_registry.ts",
    )
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    if args.registry:
        IntegrationsRequestHandler.api = IntegrationsApi(args.registry)
    if not is_loopback(args.host):
        IntegrationsRequestHandler.api.environment = "production"
        if not IntegrationsRequestHandler.api.auth_policy.ready:
            parser.error(
                "a non-loopback --host requires valid INTEGRATIONS_API_AUTH_* configuration"
            )
    server = ThreadingHTTPServer((args.host, args.port), IntegrationsRequestHandler)
    print(f"{SERVICE_NAME} running on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
