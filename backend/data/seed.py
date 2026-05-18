import asyncio
import os

from dotenv import load_dotenv
from models import Bid, BidItem, BidStatus, Supplier
from motor.motor_asyncio import AsyncIOMotorClient

# Mock suppliers data – Greek public sector context
mock_suppliers = [
    Supplier(
        name="Πληροφορική Α.Ε.",
        category="Εξοπλισμός IT",
        contact="info@pliroforiki.gr",
        rating=4.5,
    ),
    Supplier(
        name="Γραφική Ύλη Παπαδόπουλος",
        category="Γραφική Ύλη & Αναλώσιμα",
        contact="sales@papadopoulos-yli.gr",
        rating=4.2,
    ),
    Supplier(
        name="Τεχνοδομή Κατασκευαστική Ε.Π.Ε.",
        category="Κατασκευές & Συντήρηση",
        contact="info@technodomi.gr",
        rating=4.0,
    ),
    Supplier(
        name="Ενεργειακές Λύσεις Α.Ε.",
        category="Ενεργειακός Εξοπλισμός",
        contact="support@energeiakes.gr",
        rating=4.8,
    ),
    Supplier(
        name="Ιατρική Εφοδιαστική Ε.Π.Ε.",
        category="Ιατρικά Υλικά & Εξοπλισμός",
        contact="orders@iatriki-efod.gr",
        rating=4.3,
    ),
    Supplier(
        name="Αυτοκινητοβιομηχανία Ελλάς Α.Ε.",
        category="Οχήματα & Ανταλλακτικά",
        contact="fleet@autohellas.gr",
        rating=3.9,
    ),
    Supplier(
        name="Τροφοδοσία Δημοσίου Α.Ε.",
        category="Τρόφιμα & Ποτά",
        contact="orders@trofodosia.gr",
        rating=4.1,
    ),
    Supplier(
        name="Ασφάλεια & Τεχνολογία Α.Ε.",
        category="Συστήματα Ασφαλείας",
        contact="security@asf-tech.gr",
        rating=4.6,
    ),
    Supplier(
        name="Καθαριότητα & Υγιεινή Ε.Π.Ε.",
        category="Είδη Καθαρισμού",
        contact="info@kathariotita.gr",
        rating=4.4,
    ),
    Supplier(
        name="Μεταφορικό Δίκτυο Α.Ε.",
        category="Υπηρεσίες Μεταφορών",
        contact="logistics@diktyo-met.gr",
        rating=4.7,
    ),
    Supplier(
        name="Εκπαιδευτικά Συστήματα Ε.Π.Ε.",
        category="Εκπαιδευτικό Υλικό",
        contact="edu@ekpaid-syst.gr",
        rating=4.2,
    ),
    Supplier(
        name="Ένδυση Επαγγελματική Α.Ε.",
        category="Στολές & Ένδυση",
        contact="sales@endysi-epag.gr",
        rating=3.8,
    ),
]

# Mock bids data – Greek public sector context
mock_bids = [
    Bid(
        supplier_id="1",
        items=[
            BidItem(name="Φορητός Η/Υ", quantity=10, unit_price=1100.0),
            BidItem(name="Οθόνη 27''", quantity=10, unit_price=280.0),
        ],
        total_price=13800.0,
        delivery_days=7,
        terms="Πληρωμή 30 ημέρες",
        status=BidStatus.PENDING,
    ),
    Bid(
        supplier_id="2",
        items=[BidItem(name="Καρέκλα γραφείου εργονομική", quantity=50, unit_price=140.0)],
        total_price=7000.0,
        delivery_days=14,
        terms="Πληρωμή 60 ημέρες",
        status=BidStatus.ACCEPTED,
    ),
    Bid(
        supplier_id="3",
        items=[
            BidItem(name="Τσιμέντο (σάκος)", quantity=100, unit_price=9.0),
            BidItem(name="Χαλυβδίνες δοκοί", quantity=20, unit_price=450.0),
        ],
        total_price=9900.0,
        delivery_days=21,
        terms="Αντικαταβολή",
        status=BidStatus.PENDING,
    ),
    Bid(
        supplier_id="4",
        items=[BidItem(name="Φωτοβολταϊκά πάνελ", quantity=100, unit_price=180.0)],
        total_price=18000.0,
        delivery_days=30,
        terms="Προκαταβολή 50%, υπόλοιπο κατά την παράδοση",
        status=BidStatus.PENDING,
    ),
    Bid(
        supplier_id="5",
        items=[BidItem(name="Χειρουργικά γάντια (κιβώτιο)", quantity=1000, unit_price=0.45)],
        total_price=450.0,
        delivery_days=3,
        terms="Πληρωμή 15 ημέρες",
        status=BidStatus.ACCEPTED,
    ),
    Bid(
        supplier_id="6",
        items=[BidItem(name="Ελαστικά οχημάτων", quantity=200, unit_price=75.0)],
        total_price=15000.0,
        delivery_days=10,
        terms="Πληρωμή 30 ημέρες",
        status=BidStatus.REJECTED,
    ),
    Bid(
        supplier_id="7",
        items=[BidItem(name="Καφές φίλτρου (κιλό)", quantity=500, unit_price=4.50)],
        total_price=2250.0,
        delivery_days=5,
        terms="Αντικαταβολή",
        status=BidStatus.PENDING,
    ),
    Bid(
        supplier_id="8",
        items=[
            BidItem(name="Κάμερα ασφαλείας IP", quantity=20, unit_price=230.0),
            BidItem(name="Σύστημα συναγερμού", quantity=5, unit_price=900.0),
        ],
        total_price=9100.0,
        delivery_days=14,
        terms="Πληρωμή 45 ημέρες",
        status=BidStatus.PENDING,
    ),
    Bid(
        supplier_id="9",
        items=[BidItem(name="Αποσμητικό δαπέδων (λίτρα)", quantity=1000, unit_price=1.80)],
        total_price=1800.0,
        delivery_days=7,
        terms="Πληρωμή 30 ημέρες",
        status=BidStatus.ACCEPTED,
    ),
    Bid(
        supplier_id="10",
        items=[BidItem(name="Μεταφορικά κιβώτια (τεμάχιο)", quantity=50, unit_price=280.0)],
        total_price=14000.0,
        delivery_days=20,
        terms="Προκαταβολή 50%",
        status=BidStatus.PENDING,
    ),
    Bid(
        supplier_id="11",
        items=[BidItem(name="Εγχειρίδια εκπαίδευσης", quantity=200, unit_price=45.0)],
        total_price=9000.0,
        delivery_days=14,
        terms="Πληρωμή 60 ημέρες",
        status=BidStatus.PENDING,
    ),
    Bid(
        supplier_id="12",
        items=[BidItem(name="Φόρμες υπηρεσίας", quantity=500, unit_price=9.0)],
        total_price=4500.0,
        delivery_days=10,
        terms="Αντικαταβολή",
        status=BidStatus.REJECTED,
    ),
    Bid(
        supplier_id="1",
        items=[BidItem(name="Εκτυπωτής laser", quantity=5, unit_price=380.0)],
        total_price=1900.0,
        delivery_days=5,
        terms="Πληρωμή 30 ημέρες",
        status=BidStatus.ACCEPTED,
    ),
    Bid(
        supplier_id="2",
        items=[BidItem(name="Μπλοκ σημειώσεων Α4", quantity=100, unit_price=2.50)],
        total_price=250.0,
        delivery_days=3,
        terms="Πληρωμή 15 ημέρες",
        status=BidStatus.PENDING,
    ),
    Bid(
        supplier_id="3",
        items=[BidItem(name="Τούβλα (παλέτα)", quantity=5000, unit_price=0.45)],
        total_price=2250.0,
        delivery_days=15,
        terms="Πληρωμή 45 ημέρες",
        status=BidStatus.PENDING,
    ),
    Bid(
        supplier_id="4",
        items=[BidItem(name="Ανεμογεννήτρια", quantity=2, unit_price=45000.0)],
        total_price=90000.0,
        delivery_days=60,
        terms="Προκαταβολή 25%, υπόλοιπο σε δόσεις",
        status=BidStatus.PENDING,
    ),
]


async def seed_database():
    load_dotenv()
    mongodb_url = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongodb_url)
    db = client.procureai

    # Insert suppliers
    supplier_ids = {}
    for i, supplier in enumerate(mock_suppliers):
        result = await db.suppliers.insert_one(supplier.dict(by_alias=True))
        supplier_ids[str(i + 1)] = str(result.inserted_id)

    # Update bids with actual supplier_ids
    for bid in mock_bids:
        bid.supplier_id = supplier_ids[bid.supplier_id]
        await db.bids.insert_one(bid.dict(by_alias=True))

    print("Seed data inserted successfully!")


if __name__ == "__main__":
    asyncio.run(seed_database())
