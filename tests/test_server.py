#!/usr/bin/env python3
"""Focused offline tests for the external app registry projection."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from service_auth import AuthPolicy

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT
sys.path.insert(0, str(ROOT))
from server import IntegrationsApi, parse_registry  # noqa: E402 - after the repo root is on sys.path

REGISTRY = """export const EXTERNAL_APP_REGISTRY: ExternalAppRecord[] = [
  // Existing direct integrations (2)
  { id: 'gmail', name: 'Gmail', category: 'communication', status: 'live', apiDocs: 'https://developers.google.com/gmail/api' },
  { id: 'supabase', name: 'Supabase', category: 'database', status: 'mcp_only', apiDocs: 'https://supabase.com/docs', note: 'Owner\\'s MCP only' },

  // Commerce (1)
  { id: 'shop-x', name: 'Shop X', category: 'commerce', status: 'planned', apiDocs: 'https://shop.example/docs' },
];
"""


class IntegrationsApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "integrations" / "gmail").mkdir(parents=True)
        (self.root / "integrations" / "gmail" / "README.md").write_text(
            "# Gmail\n", encoding="utf-8"
        )
        self.path = self.root / "registry.ts"
        self.path.write_text(REGISTRY, encoding="utf-8")
        self.api = IntegrationsApi(
            self.path, token="", environment="development", root=self.root
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def get(self, target: str, **kwargs):
        return self.api.handle("GET", target, **kwargs)

    def test_scoped_production_auth_and_safe_errors(self) -> None:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public = (
            key.public_key()
            .public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode()
        )
        policy = AuthPolicy(
            "https://solo.example",
            "integrations-api",
            public,
            frozenset({"fixture-owner"}),
            "integrations:read",
        )
        api = IntegrationsApi(
            self.path, environment="production", auth_policy=policy, root=self.root
        )
        now = int(time.time())
        claims = {
            "iss": "https://solo.example",
            "aud": "integrations-api",
            "sub": "fixture-owner",
            "tenant_id": "owner",
            "scope": "integrations:read",
            "iat": now,
            "nbf": now,
            "exp": now + 120,
            "jti": "fixture-request",
        }

        def headers(changes=None):
            return {
                "Authorization": "Bearer "
                + jwt.encode({**claims, **(changes or {})}, key, algorithm="RS256")
            }

        assert api.handle("GET", "/health").status == 200
        assert api.handle("GET", "/ready").status == 200
        assert api.handle("GET", "/api/v1/integrations").status == 401
        response = api.handle("GET", "/api/v1/integrations", headers=headers())
        assert response.status == 200
        assert len(response.payload["source"]["revision"]) == 64
        for changes, expected in (
            ({"scope": "other:read"}, 403),
            ({"tenant_id": "other"}, 403),
            ({"sub": "other-owner"}, 403),
            ({"iss": "https://other.example"}, 401),
            ({"aud": "other-api"}, 401),
            ({"exp": now - 300}, 401),
            ({"nbf": now + 300}, 401),
        ):
            with self.subTest(changes=changes):
                denied = api.handle(
                    "GET", "/api/v1/integrations", headers=headers(changes)
                )
                assert denied.status == expected
                assert set(denied.payload) == {"error"}
                assert "Bearer" not in json.dumps(denied.payload)
        assert (
            api.handle(
                "GET",
                "/api/v1/integrations",
                headers={"Authorization": "Bearer " + "x" * 9000},
            ).status
            == 401
        )

    def test_static_token_is_never_production_authorization(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            api = IntegrationsApi(
                self.path, token="development-only", environment="production"
            )
        assert (
            api.handle(
                "GET",
                "/api/v1/integrations",
                headers={"Authorization": "Bearer development-only"},
            ).status
            == 503
        )
        assert api.handle("GET", "/health").status == 200
        assert api.handle("GET", "/ready").payload["auth"] == "disabled"

    def test_readiness_and_remote_bind_fail_closed(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            api = IntegrationsApi(self.path, environment="development")
        assert api.handle("GET", "/ready").payload["auth"] == "development"
        assert api.handle("GET", "/ready").status == 503
        self.path.unlink()
        assert api.handle("GET", "/ready").payload["source"] == "unavailable"
        assert api.handle("GET", "/health").status == 200
        env = {
            **os.environ,
            "INTEGRATIONS_API_TOKEN": "legacy-token",
            "INTEGRATIONS_API_ENV": "development",
        }
        for suffix in ("AUTH_ISSUER", "AUTH_PUBLIC_KEY", "AUTH_SUBJECTS"):
            env.pop("INTEGRATIONS_API_" + suffix, None)
        result = subprocess.run(
            [sys.executable, str(ROOT / "server.py"), "--host", "0.0.0.0"],
            env=env,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,  # the test asserts the non-zero exit code itself
        )
        assert result.returncode == 2
        assert "INTEGRATIONS_API_AUTH_*" in result.stderr

    def test_overview(self) -> None:
        payload = self.get("/api/v1/integrations").payload
        assert payload["schema_version"] == "solo-empire.integrations.v1"
        assert payload["summary"]["apps_total"] == 3
        assert payload["summary"]["connected"] == 2
        assert payload["summary"]["with_guide"] == 1
        apps = {app["id"]: app for app in payload["apps"]}
        assert apps["gmail"]["guide"] == "integrations/gmail/README.md"
        assert apps["gmail"]["section"] == "Existing direct integrations"
        assert apps["supabase"]["note"] == "Owner's MCP only"
        assert apps["shop-x"]["section"] == "Commerce"
        assert [item["value"] for item in payload["signals"]["statuses"]] == [
            "live",
            "mcp_only",
            "planned",
        ]

    def test_filters(self) -> None:
        assert [
            app["id"]
            for app in self.get("/api/v1/integrations?status=planned").payload["apps"]
        ] == ["shop-x"]
        assert [
            app["id"]
            for app in self.get("/api/v1/integrations?category=database").payload[
                "apps"
            ]
        ] == ["supabase"]
        assert [
            app["id"]
            for app in self.get("/api/v1/integrations?q=GMAIL").payload["apps"]
        ] == ["gmail"]
        assert self.get("/api/v1/integrations?q=" + "x" * 81).status == 400

    def test_strict_parsing_fails_closed(self) -> None:
        for broken in (
            REGISTRY.replace("status: 'live'", "status: 'unknown'"),
            REGISTRY.replace(
                "apiDocs: 'https://developers", "apiDocs: 'http://developers"
            ),
            REGISTRY.replace("{ id: 'shop-x'", "{ id: shopX"),
            REGISTRY.replace("id: 'supabase'", "id: 'gmail'"),
        ):
            with (
                self.subTest(broken=broken[:0]),
                pytest.raises(ValueError, match="registry"),
            ):
                parse_registry(broken)
        self.path.write_text(
            REGISTRY.replace("{ id: 'shop-x'", "{ id: shopX"), encoding="utf-8"
        )
        response = self.get("/api/v1/integrations")
        assert response.status == 503
        assert response.payload["error"]["code"] == "registry_unavailable"

    def test_read_only_and_auth(self) -> None:
        assert self.api.handle("POST", "/api/v1/integrations").status == 405
        assert self.get("/api/v1/other").status == 404
        guarded = IntegrationsApi(
            self.path, token="t0ken", environment="development", root=self.root
        )
        assert guarded.handle("GET", "/api/v1/integrations").status == 401
        assert (
            guarded.handle(
                "GET", "/api/v1/integrations", headers={"Authorization": "Bearer t0ken"}
            ).status
            == 200
        )
        assert (
            IntegrationsApi(self.path, token="", environment="production")
            .handle("GET", "/api/v1/integrations")
            .status
            == 503
        )

    def test_real_registry_parses_every_record(self) -> None:
        real = REPO / "data" / "external_app_registry.ts"
        records = parse_registry(real.read_text(encoding="utf-8"))
        assert len(records) == real.read_text(encoding="utf-8").count("{ id: '")


if __name__ == "__main__":
    unittest.main()
