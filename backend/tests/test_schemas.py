from datetime import datetime

import pytest
from models.bid import Bid, BidItem, BidStatus
from models.supplier import Supplier
from models.user import User
from pydantic import ValidationError
from schemas.auth import Token, TokenPayload
from schemas.chat import ChatRequest
from schemas.user import UserCreate, UserRead, UserUpdate


def test_chat_request_valid():
    req = ChatRequest(message="Hello")
    assert req.message == "Hello"
    assert req.conversation_id is None


def test_chat_request_with_conversation_id():
    req = ChatRequest(message="Hello", conversation_id="abc-123")
    assert req.conversation_id == "abc-123"


def test_chat_request_empty_message():
    req = ChatRequest(message="")
    assert req.message == ""


def test_user_create_valid():
    u = UserCreate(email="user@test.com", password="secret123", full_name="Alice")
    assert u.email == "user@test.com"
    assert u.full_name == "Alice"


def test_user_create_default_full_name():
    u = UserCreate(email="user@test.com", password="secret123")
    assert u.full_name == ""


def test_user_read_alias():
    data = {
        "_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
        "email": "test@test.com",
        "full_name": "Test User",
        "is_active": True,
        "is_superuser": False,
        "created_at": datetime.utcnow(),
    }
    user = UserRead.model_validate(data)
    assert user.id == "507f1f77bcf86cd799439011"  # pragma: allowlist secret


def test_user_read_all_fields():
    now = datetime.utcnow()
    data = {
        "_id": "abc123",
        "email": "a@b.com",
        "full_name": "Name",
        "is_active": True,
        "is_superuser": False,
        "created_at": now,
    }
    user = UserRead.model_validate(data)
    assert user.email == "a@b.com"
    assert user.full_name == "Name"
    assert user.is_active is True
    assert user.is_superuser is False
    assert user.created_at == now


def test_user_update_partial():
    u = UserUpdate(full_name="New Name")
    assert u.full_name == "New Name"
    assert u.password is None


def test_user_update_empty():
    u = UserUpdate()
    assert u.full_name is None
    assert u.password is None


def test_token_default_type():
    t = Token(access_token="eyJhbGciOiJIUzI1NiJ9")
    assert t.token_type == "bearer"


def test_token_payload_with_exp():
    p = TokenPayload(sub="user@test.com", exp=9999999999)
    assert p.sub == "user@test.com"
    assert p.exp == 9999999999


def test_token_payload_without_exp():
    p = TokenPayload(sub="user@test.com")
    assert p.exp is None


def test_supplier_valid():
    s = Supplier(name="Acme Corp", category="Electronics", contact="acme@test.com", rating=4.5)
    assert s.name == "Acme Corp"
    assert s.rating == 4.5


def test_supplier_rating_too_high():
    with pytest.raises(ValidationError):
        Supplier(name="Acme", category="Electronics", contact="acme@test.com", rating=5.1)


def test_supplier_rating_negative():
    with pytest.raises(ValidationError):
        Supplier(name="Acme", category="Electronics", contact="acme@test.com", rating=-0.1)


def test_supplier_auto_id():
    s1 = Supplier(name="A", category="B", contact="c@d.com", rating=3.0)
    s2 = Supplier(name="A", category="B", contact="c@d.com", rating=3.0)
    assert s1.id is not None
    assert s1.id != s2.id


def test_bid_item_valid():
    item = BidItem(name="Widget", quantity=10, unit_price=5.50)
    assert item.name == "Widget"
    assert item.quantity == 10
    assert item.unit_price == 5.50


def test_bid_status_values():
    assert BidStatus.PENDING == "pending"
    assert BidStatus.ACCEPTED == "accepted"
    assert BidStatus.REJECTED == "rejected"


def test_bid_valid():
    item = BidItem(name="Widget", quantity=2, unit_price=10.0)
    bid = Bid(
        supplier_id="sup-001",
        items=[item],
        total_price=20.0,
        delivery_days=7,
        terms="Net 30",
    )
    assert bid.supplier_id == "sup-001"
    assert len(bid.items) == 1
    assert bid.id is not None


def test_bid_default_status():
    item = BidItem(name="Widget", quantity=1, unit_price=5.0)
    bid = Bid(
        supplier_id="sup-001",
        items=[item],
        total_price=5.0,
        delivery_days=14,
        terms="Net 15",
    )
    assert bid.status == BidStatus.PENDING


def test_user_model_defaults():
    u = User(email="user@test.com", hashed_password="$2b$12$hashed")
    assert u.is_active is True
    assert u.is_superuser is False
    assert u.full_name == ""
    assert u.id is not None
    assert u.created_at is not None
