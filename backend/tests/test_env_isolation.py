"""
Guard: backend/.env points at a real MongoDB Atlas cluster. conftest.py
overrides MONGODB_URI before config/db get imported, specifically so the
test suite can never write to it. This test fails loudly if that override
is ever removed or bypassed.
"""

from config import settings


def test_mongodb_uri_is_never_the_real_atlas_cluster():
    uri = settings.MONGODB_URI
    assert "mongodb+srv" not in uri, f"settings.MONGODB_URI looks like a real Atlas SRV URI: {uri}"
    assert "7dre2" not in uri, f"settings.MONGODB_URI points at the real Atlas cluster: {uri}"
