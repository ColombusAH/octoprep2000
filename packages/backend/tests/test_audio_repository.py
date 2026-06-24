from __future__ import annotations

import uuid

import pytest

from db.models import AudioWarning, TranscriptEntry
from db.repository import PostgreSQLRepository


class _FakeResult:
    def __init__(self, row):
        self.row = row

    def scalar_one_or_none(self):
        return self.row


class _FakeDb:
    def __init__(self, existing=None) -> None:
        self.existing = existing
        self.added = []
        self.commits = 0

    async def execute(self, statement):
        return _FakeResult(self.existing)

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_insert_transcript_entry_skips_existing_natural_key():
    db = _FakeDb(existing=object())
    repo = PostgreSQLRepository(db)

    await repo.insert_transcript_entry(
        session_id=uuid.uuid4(),
        start_ms=0,
        end_ms=2000,
        text="um hello",
        filler_flags=["um"],
    )

    assert db.added == []
    assert db.commits == 0


@pytest.mark.asyncio
async def test_insert_transcript_entry_persists_new_natural_key():
    db = _FakeDb(existing=None)
    repo = PostgreSQLRepository(db)

    await repo.insert_transcript_entry(
        session_id=uuid.uuid4(),
        start_ms=0,
        end_ms=2000,
        text="um hello",
        filler_flags=["um"],
    )

    assert len(db.added) == 1
    assert isinstance(db.added[0], TranscriptEntry)
    assert db.commits == 1


@pytest.mark.asyncio
async def test_insert_audio_warning_skips_existing_natural_key():
    db = _FakeDb(existing=object())
    repo = PostgreSQLRepository(db)

    await repo.insert_audio_warning(
        session_id=uuid.uuid4(),
        timestamp_ms=1500,
        event_type="FILLER_WORDS",
        severity="LOW",
        message="Filler word: um",
    )

    assert db.added == []
    assert db.commits == 0


@pytest.mark.asyncio
async def test_insert_audio_warning_persists_new_natural_key():
    db = _FakeDb(existing=None)
    repo = PostgreSQLRepository(db)

    await repo.insert_audio_warning(
        session_id=uuid.uuid4(),
        timestamp_ms=1500,
        event_type="FILLER_WORDS",
        severity="LOW",
        message="Filler word: um",
    )

    assert len(db.added) == 1
    assert isinstance(db.added[0], AudioWarning)
    assert db.commits == 1
