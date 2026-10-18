"""
Seed script — creates the tpa_providers table and inserts 5 dummy TPA providers.
Safe to run multiple times (uses INSERT ... ON CONFLICT DO NOTHING).
"""
from database import engine, SessionLocal
from models import Base, TPAProvider
from sqlalchemy import text

# Step 1: Create tpa_providers table + add tpa_provider_id column to fnol_work_items
print("Running DB migrations...")
with engine.connect() as conn:
    # Create tpa_providers table if not exists
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS tpa_providers (
            id SERIAL PRIMARY KEY,
            name VARCHAR NOT NULL,
            code VARCHAR UNIQUE NOT NULL,
            contact_email VARCHAR,
            contact_phone VARCHAR,
            api_url VARCHAR,
            specialties VARCHAR,
            is_active BOOLEAN DEFAULT TRUE,
            is_mock BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))
    print("  [OK] tpa_providers table")

    # Add tpa_provider_id FK column to fnol_work_items if not exists
    conn.execute(text("""
        ALTER TABLE fnol_work_items
        ADD COLUMN IF NOT EXISTS tpa_provider_id INTEGER
        REFERENCES tpa_providers(id) ON DELETE SET NULL
    """))
    print("  [OK] fnol_work_items.tpa_provider_id column")

    conn.commit()

# Step 2: Seed 5 dummy TPA providers
DUMMY_TPAS = [
    {
        "name": "Sedgwick Claims Management Services",
        "code": "SEDGWICK",
        "contact_email": "claims@sedgwick-mock.com",
        "contact_phone": "+1-800-221-5473",
        "api_url": None,
        "specialties": "Auto, Property, Workers Compensation, Liability",
        "is_active": True,
        "is_mock": True,
    },
    {
        "name": "Gallagher Bassett Services",
        "code": "GALLAGHER",
        "contact_email": "fnol@gallagher-mock.com",
        "contact_phone": "+1-800-445-2677",
        "api_url": None,
        "specialties": "Property, Casualty, Marine, Aviation",
        "is_active": True,
        "is_mock": True,
    },
    {
        "name": "Crawford & Company",
        "code": "CRAWFORD",
        "contact_email": "intake@crawford-mock.com",
        "contact_phone": "+1-800-241-2541",
        "api_url": None,
        "specialties": "Auto, Property, Catastrophe, Liability",
        "is_active": True,
        "is_mock": True,
    },
    {
        "name": "Broadspire Services",
        "code": "BROADSPIRE",
        "contact_email": "claims@broadspire-mock.com",
        "contact_phone": "+1-888-446-7746",
        "api_url": None,
        "specialties": "Workers Compensation, Auto, Liability",
        "is_active": True,
        "is_mock": True,
    },
    {
        "name": "CorVel Corporation",
        "code": "CORVEL",
        "contact_email": "fnol@corvel-mock.com",
        "contact_phone": "+1-888-726-7835",
        "api_url": None,
        "specialties": "Workers Compensation, Auto, Health",
        "is_active": True,
        "is_mock": True,
    },
]

db = SessionLocal()
inserted = 0
skipped = 0
try:
    for tpa_data in DUMMY_TPAS:
        existing = db.query(TPAProvider).filter(TPAProvider.code == tpa_data["code"]).first()
        if existing:
            print(f"  [SKIP] {tpa_data['code']} already exists (id={existing.id})")
            skipped += 1
        else:
            tpa = TPAProvider(**tpa_data)
            db.add(tpa)
            inserted += 1
            print(f"  [ADD]  {tpa_data['code']} — {tpa_data['name']}")
    db.commit()
finally:
    db.close()

print(f"\nDone. Inserted: {inserted}, Skipped: {skipped}")
print("Dummy TPA providers are ready.")
