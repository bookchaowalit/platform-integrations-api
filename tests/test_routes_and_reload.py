"""Routing, reload and HTTP rules: read-only routes, mtime reload, safe 500s, CORS allowlist."""

from __future__ import annotations

import http.client
import json
import os
import threading
from collections.abc import Iterator
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

import server
from server import IntegrationsApi, IntegrationsRequestHandler

LINE = "  {{ id: '{id}', name: '{id}', category: 'x', status: 'live', apiDocs: 'https://x.example' }},"


def write_registry(path: Path, *app_ids: str, mtime: int | None = None) -> None:
    lines = "\n".join(LINE.format(id=app_id) for app_id in app_ids)
    path.write_text(
        f"export const EXTERNAL_APP_REGISTRY: ExternalAppRecord[] = [\n{lines}\n];\n",
        encoding="utf-8",
    )
    if mtime is not None:
        os.utime(path, (mtime, mtime))


@pytest.fixture
def registry(tmp_path: Path) -> Path:
    path = tmp_path / "registry.ts"
    write_registry(path, "gmail", mtime=1_700_000_000)
    return path


@pytest.fixture
def api(registry: Path, tmp_path: Path) -> IntegrationsApi:
    return IntegrationsApi(
        registry,
        token="",
        environment="development",
        allowed_origins=("https://solo.example",),
        root=tmp_path,
    )


def test_health_is_public_and_names_the_service(api):
    response = api.handle("GET", "/health/")
    assert response.status == 200
    assert response.payload["status"] == "ok"
    assert response.payload["service"] == "solo-empire-integrations-api"


def test_preflight_options_is_an_empty_204(api):
    assert api.handle("OPTIONS", "/api/v1/integrations") == server.Response(204, {})


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_every_write_method_is_refused_as_read_only(api, method):
    response = api.handle(method, "/api/v1/integrations")
    assert response.status == 405
    assert response.payload["error"]["code"] == "method_not_allowed"


def test_an_unknown_route_is_a_404(api):
    assert api.handle("GET", "/api/v2/integrations").payload == {
        "error": {"code": "not_found", "message": "route not found"}
    }


def test_the_registry_reloads_only_when_its_mtime_changes(api, registry):
    first = api.handle("GET", "/api/v1/integrations").payload
    assert first["source"]["modified_at"] == "2023-11-14T22:13:20Z"
    write_registry(registry, "gmail", "slack", mtime=1_700_000_000)
    same = api.handle("GET", "/api/v1/integrations").payload
    assert (
        same["summary"]["apps_total"] == 1
    )  # same mtime: the cached snapshot is served
    write_registry(registry, "gmail", "slack", mtime=1_700_000_060)
    reloaded = api.handle("GET", "/api/v1/integrations").payload
    assert reloaded["summary"]["apps_total"] == 2
    assert reloaded["source"]["revision"] != first["source"]["revision"]


def test_a_missing_registry_is_a_503_not_a_partial_list(api, registry):
    registry.unlink()
    response = api.handle("GET", "/api/v1/integrations")
    assert response.status == 503
    assert response.payload["error"]["code"] == "registry_unavailable"


def test_an_unexpected_error_is_a_generic_500_reported_to_sentry(api, monkeypatch):
    reported: list[BaseException] = []
    monkeypatch.setattr(server, "capture", reported.append)

    def boom(_query):
        raise RuntimeError("internal detail postgres://u:pw@h/db")

    monkeypatch.setattr(api, "_overview", boom)
    response = api.handle("GET", "/api/v1/integrations")
    assert response.status == 500
    assert response.payload["error"]["code"] == "internal_error"
    assert "internal detail" not in json.dumps(response.payload)
    assert [str(exc) for exc in reported] == ["internal detail postgres://u:pw@h/db"]


@pytest.fixture
def http_server(api, monkeypatch) -> Iterator[int]:
    monkeypatch.setattr(IntegrationsRequestHandler, "api", api)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), IntegrationsRequestHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield httpd.server_address[1]
    finally:
        httpd.shutdown()
        httpd.server_close()


def request(port: int, method: str, path: str, headers: dict[str, str] | None = None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        conn.request(method, path, headers=headers or {})
        response = conn.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        conn.close()


def test_http_responses_are_uncached_json_with_nosniff(http_server):
    status, headers, body = request(http_server, "GET", "/health")
    assert status == 200
    assert headers["Content-Type"] == "application/json; charset=utf-8"
    assert headers["Cache-Control"] == "no-store"
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert json.loads(body)["status"] == "ok"


def test_an_allowed_origin_gets_cors_headers(http_server):
    status, headers, _ = request(
        http_server, "GET", "/health", {"Origin": "https://solo.example"}
    )
    assert status == 200
    assert headers["Access-Control-Allow-Origin"] == "https://solo.example"
    assert headers["Vary"] == "Origin"


def test_an_unlisted_origin_is_refused_before_routing(http_server):
    status, headers, body = request(
        http_server, "GET", "/health", {"Origin": "https://evil.example"}
    )
    assert status == 403
    assert "Access-Control-Allow-Origin" not in headers
    assert json.loads(body)["error"]["code"] == "origin_not_allowed"


def test_preflight_lists_only_get_and_options(http_server):
    status, headers, body = request(
        http_server,
        "OPTIONS",
        "/api/v1/integrations",
        {"Origin": "https://solo.example"},
    )
    assert status == 204
    assert body == b""
    assert headers["Access-Control-Allow-Methods"] == "GET, OPTIONS"
    assert headers["Access-Control-Allow-Headers"] == "Accept, Authorization"
