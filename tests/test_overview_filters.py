"""Overview rules: summary counts, signals order, guide lookup, and how filters combine."""

from __future__ import annotations

from pathlib import Path

import pytest

from server import MAX_FILTER_LENGTH, MAX_QUERY_LENGTH, IntegrationsApi

REGISTRY = """export const EXTERNAL_APP_REGISTRY: ExternalAppRecord[] = [
  // Communication (3)
  { id: 'gmail', name: 'Gmail', category: 'communication', status: 'live', apiDocs: 'https://g.example' },
  { id: 'slack', name: 'Slack', category: 'communication', status: 'mcp_only', apiDocs: 'https://s.example', note: 'Workspace MCP' },
  { id: 'discord', name: 'Discord', category: 'communication', status: 'paused', apiDocs: 'https://d.example' },
  // Calendar (2)
  { id: 'google-calendar', name: 'Google Calendar', category: 'calendar', status: 'live', apiDocs: 'https://c.example' },
  { id: 'zoom', name: 'Zoom', category: 'calendar', status: 'planned', apiDocs: 'https://z.example', note: 'Needs a gmail-style contract' },
];
"""


@pytest.fixture
def api(tmp_path: Path) -> IntegrationsApi:
    for guide in ("gmail", "google"):
        (tmp_path / "integrations" / guide).mkdir(parents=True)
        (tmp_path / "integrations" / guide / "README.md").write_text("# guide\n")
    path = tmp_path / "registry.ts"
    path.write_text(REGISTRY, encoding="utf-8")
    return IntegrationsApi(path, token="", environment="development", root=tmp_path)


def overview(api: IntegrationsApi, query: str = "") -> dict:
    response = api.handle("GET", "/api/v1/integrations" + query)
    assert response.status == 200
    return response.payload


def ids(payload: dict) -> list[str]:
    return [app["id"] for app in payload["apps"]]


def test_summary_counts_connected_as_live_plus_mcp_only(api):
    summary = overview(api)["summary"]
    assert summary == {
        "apps_total": 5,
        "apps_matched": 5,
        "categories": 2,
        "connected": 3,
        "live": 2,
        "mcp_only": 1,
        "paused": 1,
        "planned": 1,
        "with_guide": 2,
    }


def test_summary_describes_the_whole_registry_even_when_filtered(api):
    payload = overview(api, "?status=live")
    assert payload["summary"]["apps_total"] == 5
    assert payload["summary"]["apps_matched"] == 2
    assert payload["filters"] == {"status": "live", "category": "", "q": ""}


def test_status_signals_follow_the_fixed_status_order_and_skip_zero_counts(api):
    payload = overview(api)
    assert payload["signals"]["statuses"] == [
        {"value": "live", "count": 2},
        {"value": "mcp_only", "count": 1},
        {"value": "paused", "count": 1},
        {"value": "planned", "count": 1},
    ]


def test_category_and_section_signals_sort_by_count_then_name(api):
    signals = overview(api)["signals"]
    assert signals["categories"] == [
        {"value": "communication", "count": 3},
        {"value": "calendar", "count": 2},
    ]
    assert [item["value"] for item in signals["sections"]] == [
        "Communication",
        "Calendar",
    ]


def test_a_guide_is_found_by_full_id_or_by_the_id_prefix(api):
    guides = {app["id"]: app["guide"] for app in overview(api)["apps"]}
    assert guides["gmail"] == "integrations/gmail/README.md"
    assert guides["google-calendar"] == "integrations/google/README.md"
    assert guides["zoom"] is None


def test_filters_combine_with_and(api):
    assert ids(overview(api, "?category=calendar&status=live")) == ["google-calendar"]
    assert ids(overview(api, "?category=calendar&status=mcp_only")) == []


def test_text_search_is_case_insensitive_over_id_name_category_and_note(api):
    assert ids(overview(api, "?q=WORKSPACE")) == ["slack"]
    assert ids(overview(api, "?q=gmail")) == ["gmail", "zoom"]
    assert ids(overview(api, "?q=Calendar")) == ["google-calendar", "zoom"]
    assert overview(api, "?q=%20%20")["filters"]["q"] == ""


@pytest.mark.parametrize(
    ("field", "limit"),
    [
        ("status", MAX_FILTER_LENGTH),
        ("category", MAX_FILTER_LENGTH),
        ("q", MAX_QUERY_LENGTH),
    ],
)
def test_a_filter_longer_than_its_limit_is_a_400(api, field, limit):
    assert (
        api.handle("GET", f"/api/v1/integrations?{field}={'x' * limit}").status == 200
    )
    response = api.handle("GET", f"/api/v1/integrations?{field}={'x' * (limit + 1)}")
    assert response.status == 400
    assert response.payload["error"] == {
        "code": "invalid_field",
        "message": f"{field} is too long",
    }


def test_the_payload_says_a_listed_app_is_not_a_working_connector(api):
    payload = overview(api)
    assert payload["schema_version"] == "solo-empire.integrations.v1"
    assert "not proof of a working connector" in payload["boundary"]
    assert [d["value"] for d in payload["source"]["status_definitions"]] == [
        "live",
        "mcp_only",
        "paused",
        "planned",
    ]
