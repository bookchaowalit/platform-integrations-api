"""Registry parsing rules: one record per line, strict fields, fail closed on anything unreadable."""

from __future__ import annotations

import pytest

from server import parse_registry


def registry(*lines: str) -> str:
    body = "\n".join(lines)
    return f"export const EXTERNAL_APP_REGISTRY: ExternalAppRecord[] = [\n{body}\n];\n"


GMAIL = "  { id: 'gmail', name: 'Gmail', category: 'communication', status: 'live', apiDocs: 'https://developers.google.com/gmail/api' },"


def test_a_record_line_becomes_a_json_record_with_snake_case_docs_link():
    (record,) = parse_registry(registry(GMAIL))
    assert record == {
        "id": "gmail",
        "name": "Gmail",
        "category": "communication",
        "status": "live",
        "api_docs": "https://developers.google.com/gmail/api",
        "note": None,
        "section": "Other",
    }


def test_section_comment_names_the_records_below_it_without_the_count():
    records = parse_registry(
        registry(
            "  // Communication (2)",
            GMAIL,
            "",
            "  // Planned commerce",
            "  { id: 'shop', name: 'Shop', category: 'commerce', status: 'planned', apiDocs: 'https://shop.example' },",
        )
    )
    assert [(r["id"], r["section"]) for r in records] == [
        ("gmail", "Communication"),
        ("shop", "Planned commerce"),
    ]


def test_escaped_quotes_are_unescaped_and_an_empty_note_is_none():
    (with_note, empty_note) = parse_registry(
        registry(
            "  { id: 'a', name: 'Owner\\'s app', category: 'x', status: 'paused', apiDocs: 'https://a.example', note: 'It\\'s off' },",
            "  { id: 'b', name: 'B', category: 'x', status: 'paused', apiDocs: 'https://b.example', note: '' },",
        )
    )
    assert with_note["name"] == "Owner's app"
    assert with_note["note"] == "It's off"
    assert empty_note["note"] is None


def test_long_values_are_cut_to_their_public_limits():
    name, category, note = "n" * 120, "c" * 60, "x" * 400
    docs = "https://d.example/" + "p" * 400
    (record,) = parse_registry(
        registry(
            f"  {{ id: 'long', name: '{name}', category: '{category}', status: 'planned', apiDocs: '{docs}', note: '{note}' }},"
        )
    )
    assert len(record["name"]) == 80
    assert len(record["category"]) == 40
    assert len(record["api_docs"]) == 300
    assert len(record["note"]) == 300


@pytest.mark.parametrize(
    ("line", "reason"),
    [
        (
            "  { id: 'a', name: 'A', category: 'x', status: 'live' },",
            "missing a field",
        ),
        (
            "  { id: 'Bad_Id', name: 'A', category: 'x', status: 'live', apiDocs: 'https://a.example' },",
            "invalid registry record",
        ),
        (
            "  { id: 'a', name: 'A', category: 'x', status: 'beta', apiDocs: 'https://a.example' },",
            "invalid registry record",
        ),
        (
            "  { id: 'a', name: 'A', category: 'x', status: 'live', apiDocs: 'ftp://a.example' },",
            "must be https",
        ),
        (
            "  { id: 'a', name: \"A\", category: 'x', status: 'live', apiDocs: 'https://a.example' },",
            "unreadable registry field",
        ),
        ("  id: 'a', name: 'A'", "unreadable registry line"),
    ],
)
def test_one_bad_record_rejects_the_whole_registry(line, reason):
    with pytest.raises(ValueError, match=reason):
        parse_registry(registry(GMAIL, line))


def test_duplicate_ids_reject_the_whole_registry():
    with pytest.raises(ValueError, match="duplicate registry id"):
        parse_registry(registry(GMAIL, GMAIL))


def test_a_file_without_the_registry_array_is_rejected():
    with pytest.raises(ValueError, match="registry array not found"):
        parse_registry("export const OTHER = [];\n")
