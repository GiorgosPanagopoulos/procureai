#!/usr/bin/env python3
"""Create a ProcureAI user directly in MongoDB.

Usage (from the repo root, with the backend venv active and backend/.env filled in):
    python scripts/create_user.py --email user@procureai.local --role viewer
    python scripts/create_user.py --email user@procureai.local --role admin --password 'somepass123'
"""

import argparse
import asyncio
import getpass
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
os.chdir(_BACKEND)
sys.path.insert(0, str(_BACKEND))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from auth.security import get_password_hash  # noqa: E402
from crud.user import get_user_by_email  # noqa: E402
from models.user import User  # noqa: E402
from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

ROLES = ("viewer", "procurement_officer", "admin")


async def create_user(
    mongodb_uri: str, email: str, password: str, role: str, full_name: str
) -> int:
    client = AsyncIOMotorClient(mongodb_uri)
    db = client.procureai

    if await get_user_by_email(db, email):
        print(f"User {email} already exists", file=sys.stderr)
        return 1

    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        full_name=full_name,
        role=role,
    )
    await db.users.insert_one(user.model_dump(by_alias=True))
    print(f"Created {email} ({role})")
    return 0


def _parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a ProcureAI user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", default="viewer", choices=ROLES)
    parser.add_argument("--full-name", default="")
    parser.add_argument("--password", help="omit to be prompted securely")
    return parser.parse_args(argv)


def main() -> int:
    args = _parse_args()

    password = args.password or getpass.getpass("Password: ")
    if len(password) < 12:
        print("Password must be at least 12 characters", file=sys.stderr)
        return 1

    mongodb_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    return asyncio.run(create_user(mongodb_uri, args.email, password, args.role, args.full_name))


if __name__ == "__main__":
    raise SystemExit(main())
