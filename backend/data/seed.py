import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from models import Supplier, Bid, BidItem, BidStatus
import os

# Mock suppliers data
mock_suppliers = [
    Supplier(name="TechSupply Inc.", category="IT Hardware", contact="contact@techsupply.com", rating=4.5),
    Supplier(name="OfficeMart", category="Office Supplies", contact="sales@officemart.com", rating=4.2),
    Supplier(name="BuildPro Materials", category="Construction", contact="info@buildpro.com", rating=4.0),
    Supplier(name="GreenEnergy Solutions", category="Energy Equipment", contact="support@greenenergy.com", rating=4.8),
    Supplier(name="MediEquip Corp", category="Medical Supplies", contact="orders@mediequip.com", rating=4.3),
    Supplier(name="AutoParts Plus", category="Automotive Parts", contact="parts@autopartsplus.com", rating=3.9),
    Supplier(name="FoodService Direct", category="Food & Beverage", contact="orders@foodservicedirect.com", rating=4.1),
    Supplier(name="SecureTech Systems", category="Security Equipment", contact="security@securetech.com", rating=4.6),
    Supplier(name="CleanCorp", category="Cleaning Supplies", contact="info@cleancorp.com", rating=4.4),
    Supplier(name="LogiTrans", category="Logistics Services", contact="logistics@logitrans.com", rating=4.7),
    Supplier(name="EduResources", category="Educational Materials", contact="edu@eduresources.com", rating=4.2),
    Supplier(name="FashionForward", category="Apparel", contact="sales@fashionforward.com", rating=3.8),
]

# Mock bids data
mock_bids = [
    Bid(
        supplier_id="1",  # Will be set after inserting suppliers
        items=[
            BidItem(name="Laptop", quantity=10, unit_price=1200.0),
            BidItem(name="Monitor", quantity=10, unit_price=300.0)
        ],
        total_price=15000.0,
        delivery_days=7,
        terms="Net 30 days",
        status=BidStatus.PENDING
    ),
    Bid(
        supplier_id="2",
        items=[BidItem(name="Office Chairs", quantity=50, unit_price=150.0)],
        total_price=7500.0,
        delivery_days=14,
        terms="Net 60 days",
        status=BidStatus.ACCEPTED
    ),
    Bid(
        supplier_id="3",
        items=[
            BidItem(name="Cement", quantity=100, unit_price=10.0),
            BidItem(name="Steel Beams", quantity=20, unit_price=500.0)
        ],
        total_price=11000.0,
        delivery_days=21,
        terms="Cash on delivery",
        status=BidStatus.PENDING
    ),
    Bid(
        supplier_id="4",
        items=[BidItem(name="Solar Panels", quantity=100, unit_price=200.0)],
        total_price=20000.0,
        delivery_days=30,
        terms="50% upfront, 50% on delivery",
        status=BidStatus.PENDING
    ),
    Bid(
        supplier_id="5",
        items=[BidItem(name="Medical Gloves", quantity=1000, unit_price=0.5)],
        total_price=500.0,
        delivery_days=3,
        terms="Net 15 days",
        status=BidStatus.ACCEPTED
    ),
    Bid(
        supplier_id="6",
        items=[BidItem(name="Car Tires", quantity=200, unit_price=80.0)],
        total_price=16000.0,
        delivery_days=10,
        terms="Net 30 days",
        status=BidStatus.REJECTED
    ),
    Bid(
        supplier_id="7",
        items=[BidItem(name="Coffee Beans", quantity=500, unit_price=5.0)],
        total_price=2500.0,
        delivery_days=5,
        terms="Cash on delivery",
        status=BidStatus.PENDING
    ),
    Bid(
        supplier_id="8",
        items=[
            BidItem(name="Security Cameras", quantity=20, unit_price=250.0),
            BidItem(name="Alarm System", quantity=5, unit_price=1000.0)
        ],
        total_price=6000.0,
        delivery_days=14,
        terms="Net 45 days",
        status=BidStatus.PENDING
    ),
    Bid(
        supplier_id="9",
        items=[BidItem(name="Cleaning Detergent", quantity=1000, unit_price=2.0)],
        total_price=2000.0,
        delivery_days=7,
        terms="Net 30 days",
        status=BidStatus.ACCEPTED
    ),
    Bid(
        supplier_id="10",
        items=[BidItem(name="Shipping Containers", quantity=50, unit_price=300.0)],
        total_price=15000.0,
        delivery_days=20,
        terms="50% upfront",
        status=BidStatus.PENDING
    ),
    Bid(
        supplier_id="11",
        items=[BidItem(name="Textbooks", quantity=200, unit_price=50.0)],
        total_price=10000.0,
        delivery_days=14,
        terms="Net 60 days",
        status=BidStatus.PENDING
    ),
    Bid(
        supplier_id="12",
        items=[BidItem(name="T-Shirts", quantity=500, unit_price=10.0)],
        total_price=5000.0,
        delivery_days=10,
        terms="Cash on delivery",
        status=BidStatus.REJECTED
    ),
    Bid(
        supplier_id="1",
        items=[BidItem(name="Printers", quantity=5, unit_price=400.0)],
        total_price=2000.0,
        delivery_days=5,
        terms="Net 30 days",
        status=BidStatus.ACCEPTED
    ),
    Bid(
        supplier_id="2",
        items=[BidItem(name="Notebooks", quantity=100, unit_price=3.0)],
        total_price=300.0,
        delivery_days=3,
        terms="Net 15 days",
        status=BidStatus.PENDING
    ),
    Bid(
        supplier_id="3",
        items=[BidItem(name="Bricks", quantity=5000, unit_price=0.5)],
        total_price=2500.0,
        delivery_days=15,
        terms="Net 45 days",
        status=BidStatus.PENDING
    ),
    Bid(
        supplier_id="4",
        items=[BidItem(name="Wind Turbines", quantity=2, unit_price=50000.0)],
        total_price=100000.0,
        delivery_days=60,
        terms="25% upfront, balance in installments",
        status=BidStatus.PENDING
    ),
]

async def seed_database():
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongodb_url)
    db = client.procureai

    # Insert suppliers
    supplier_ids = {}
    for i, supplier in enumerate(mock_suppliers):
        result = await db.suppliers.insert_one(supplier.dict(by_alias=True))
        supplier_ids[str(i+1)] = str(result.inserted_id)

    # Update bids with actual supplier_ids
    for bid in mock_bids:
        bid.supplier_id = supplier_ids[bid.supplier_id]
        await db.bids.insert_one(bid.dict(by_alias=True))

    print("Seed data inserted successfully!")

if __name__ == "__main__":
    asyncio.run(seed_database())