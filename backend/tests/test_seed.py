"""data/seed.py: the --force path must wipe suppliers and bids before seeding, and the
non-forced path must skip (naming the flag) when suppliers already exist."""

from types import SimpleNamespace

from data.seed import SKIP_MESSAGE, mock_bids, mock_suppliers, seed, seed_database, seed_if_empty


class _FakeCollection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])
        self.delete_many_calls = 0

    async def count_documents(self, filt, limit=None):
        return len(self.docs)

    async def insert_one(self, doc):
        self.docs.append(doc)
        return SimpleNamespace(inserted_id=doc["_id"])

    async def delete_many(self, filt):
        assert filt == {}
        self.delete_many_calls += 1
        self.docs.clear()


class _FakeDB:
    def __init__(self, suppliers=None, bids=None):
        self.suppliers = _FakeCollection(suppliers)
        self.bids = _FakeCollection(bids)


async def test_seed_if_empty_inserts_all_fixtures_and_links_bids_to_suppliers():
    db = _FakeDB()

    assert await seed_if_empty(db) is True

    assert len(db.suppliers.docs) == len(mock_suppliers)
    assert len(db.bids.docs) == len(mock_bids)
    supplier_ids = {s["_id"] for s in db.suppliers.docs}
    assert all(b["supplier_id"] in supplier_ids for b in db.bids.docs)
    assert all("category" in b for b in db.bids.docs)


async def test_seed_if_empty_skips_when_suppliers_exist():
    db = _FakeDB(suppliers=[{"_id": "stale"}], bids=[{"_id": "stale-bid"}])

    assert await seed_if_empty(db) is False
    assert await seed(db, force=False) is False

    assert db.suppliers.docs == [{"_id": "stale"}]
    assert db.bids.docs == [{"_id": "stale-bid"}]
    assert db.suppliers.delete_many_calls == 0


async def test_seed_force_wipes_both_collections_before_seeding():
    db = _FakeDB(suppliers=[{"_id": "stale"}], bids=[{"_id": "stale-bid"}])

    assert await seed(db, force=True) is True

    assert db.suppliers.delete_many_calls == 1
    assert db.bids.delete_many_calls == 1
    assert "stale" not in {s["_id"] for s in db.suppliers.docs}
    assert len(db.suppliers.docs) == len(mock_suppliers)
    assert len(db.bids.docs) == len(mock_bids)


async def test_seed_force_can_run_twice_in_one_process():
    # The module-level Bid fixtures must keep their placeholder supplier ids so a
    # second forced run can map them onto the freshly inserted suppliers again.
    db = _FakeDB()
    await seed(db, force=True)
    first_ids = {b["supplier_id"] for b in db.bids.docs}

    await seed(db, force=True)

    assert len(db.bids.docs) == len(mock_bids)
    assert {b["supplier_id"] for b in db.bids.docs} == first_ids
    assert {b.supplier_id for b in mock_bids} == {str(i) for i in range(1, 13)}


async def test_seed_database_skip_message_names_the_force_flag(monkeypatch, capsys):
    fake_client = SimpleNamespace(procureai=_FakeDB(suppliers=[{"_id": "stale"}]))
    monkeypatch.setattr("data.seed.AsyncIOMotorClient", lambda _url: fake_client)
    monkeypatch.setattr("data.seed.load_dotenv", lambda: None)

    await seed_database()

    out = capsys.readouterr().out.strip()
    assert out == SKIP_MESSAGE
    assert "--force" in out


def test_multi_bid_categories_have_distinct_suppliers_and_totals_are_unchanged():
    # A category with 2+ bids must not compare a supplier against itself.
    by_category: dict[str, list[str]] = {}
    for bid in mock_bids:
        by_category.setdefault(bid.category, []).append(bid.supplier_id)
    for category, supplier_ids in by_category.items():
        if len(supplier_ids) >= 2:
            assert len(set(supplier_ids)) == len(supplier_ids), (category, supplier_ids)

    # Docs, golden-set evals and the report tool depend on these figures.
    assert len(mock_suppliers) == 12
    assert len(mock_bids) == 16
    assert round(sum(s.rating for s in mock_suppliers) / len(mock_suppliers), 2) == 4.29
    assert sum(b.total_price for b in mock_bids) == 199_200.0
    assert round(sum(b.delivery_days for b in mock_bids) / len(mock_bids), 1) == 14.9
    statuses = [b.status.value for b in mock_bids]
    assert statuses.count("pending") == 10
    assert statuses.count("accepted") == 4
    assert statuses.count("rejected") == 2
