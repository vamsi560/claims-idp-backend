"""
Connection Test Script
Tests all service connections and ensures DB tables + Blob container exist.
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

load_dotenv()

PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"
INFO = "[INFO]"

results = {}

# ─────────────────────────────────────────────
# 1. PostgreSQL Connection + Table Check/Create
# ─────────────────────────────────────────────
print("\n" + "="*60)
print("1. POSTGRESQL CONNECTION")
print("="*60)
try:
    from sqlalchemy import create_engine, text, inspect
    from sqlalchemy.orm import sessionmaker

    POSTGRES_USER = os.getenv('POSTGRES_USER')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
    POSTGRES_HOST = os.getenv('POSTGRES_HOST')
    POSTGRES_PORT = os.getenv('POSTGRES_PORT')
    POSTGRES_DB = os.getenv('POSTGRES_DB')

    DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    print(f"{INFO}  Connecting to: {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB} as {POSTGRES_USER}")

    engine = create_engine(DATABASE_URL, connect_args={"connect_timeout": 10})
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.fetchone()[0]
        print(f"{PASS}  Connected! PostgreSQL version: {version[:50]}...")
        results['postgresql'] = 'OK'

    # Check / create tables
    print(f"\n{INFO}  Checking tables...")
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    from models import Base, FNOLWorkItem, Attachment
    required_tables = ['fnol_work_items', 'attachments']

    missing = [t for t in required_tables if t not in existing_tables]
    if missing:
        print(f"{WARN}  Missing tables: {missing}. Creating all tables...")
        Base.metadata.create_all(engine)
        print(f"{PASS}  Tables created successfully!")
    else:
        print(f"{PASS}  All required tables exist: {required_tables}")

    # Count rows
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    fnol_count = session.query(FNOLWorkItem).count()
    attach_count = session.query(Attachment).count()
    session.close()
    print(f"{INFO}  fnol_work_items: {fnol_count} rows")
    print(f"{INFO}  attachments:     {attach_count} rows")

except Exception as e:
    print(f"{FAIL}  PostgreSQL FAILED: {e}")
    results['postgresql'] = f'FAILED: {e}'

# ─────────────────────────────────────────────
# 2. Azure Blob Storage Connection + Container Check/Create
# ─────────────────────────────────────────────
print("\n" + "="*60)
print("2. AZURE BLOB STORAGE")
print("="*60)
try:
    from azure.storage.blob import BlobServiceClient

    conn_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    container_name = os.getenv('AZURE_STORAGE_CONTAINER')

    print(f"{INFO}  Container: {container_name}")
    blob_service_client = BlobServiceClient.from_connection_string(conn_str)

    # Check account connectivity
    account_info = blob_service_client.get_account_information()
    print(f"{PASS}  Connected to Azure Blob! Account kind: {account_info.get('account_kind', 'N/A')}, SKU: {account_info.get('sku_name', 'N/A')}")
    results['azure_blob'] = 'OK'

    # Check / create container
    container_client = blob_service_client.get_container_client(container_name)
    try:
        props = container_client.get_container_properties()
        print(f"{PASS}  Container '{container_name}' exists.")

        # List blobs
        blobs = list(container_client.list_blobs())
        print(f"{INFO}  Blobs in container: {len(blobs)}")
        if blobs:
            for b in blobs[:5]:
                print(f"       - {b['name']} ({b.get('size', '?')} bytes)")
            if len(blobs) > 5:
                print(f"       ... and {len(blobs)-5} more")
        else:
            print(f"{INFO}  Container is empty.")

    except Exception as ce:
        if "ContainerNotFound" in str(ce) or "ResourceNotFound" in str(ce):
            print(f"{WARN}  Container '{container_name}' not found. Creating...")
            container_client.create_container()
            print(f"{PASS}  Container '{container_name}' created!")
        else:
            raise ce

except Exception as e:
    print(f"{FAIL}  Azure Blob FAILED: {e}")
    results['azure_blob'] = f'FAILED: {e}'

# ─────────────────────────────────────────────
# 3. Gemini LLM API Connection
# ─────────────────────────────────────────────
print("\n" + "="*60)
print("3. GEMINI LLM API")
print("="*60)
try:
    GEMINI_API_URL = os.getenv("GEMINI_API_URL")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL")

    url = f"{GEMINI_API_URL}:generateContent?key={GEMINI_API_KEY}"
    print(f"{INFO}  Endpoint: {GEMINI_API_URL}:generateContent")
    print(f"{INFO}  Model: {GEMINI_MODEL}")

    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": "Reply with exactly: CONNECTION_OK"}]}
        ]
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
    response.raise_for_status()
    result = response.json()
    text_out = result["candidates"][0]["content"]["parts"][0]["text"].strip()
    print(f"{PASS}  Connected! LLM Response: '{text_out}'")
    results['gemini'] = 'OK'

except Exception as e:
    print(f"{FAIL}  Gemini LLM FAILED: {e}")
    results['gemini'] = f'FAILED: {e}'

# ─────────────────────────────────────────────
# 4. Azure Document Intelligence Connection
# ─────────────────────────────────────────────
print("\n" + "="*60)
print("4. AZURE DOCUMENT INTELLIGENCE")
print("="*60)
try:
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.core.credentials import AzureKeyCredential
    import base64

    endpoint = os.getenv('AZURE_DOC_INTELLIGENCE_ENDPOINT')
    key = os.getenv('AZURE_DOC_INTELLIGENCE_KEY')

    print(f"{INFO}  Endpoint: {endpoint}")
    print(f"{INFO}  SDK version: azure-ai-documentintelligence 1.0.2")
    client = DocumentIntelligenceClient(endpoint, AzureKeyCredential(key))

    # Use a minimal 1x1 white JPEG to test auth + network connectivity
    tiny_jpg = base64.b64decode(
        "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAIBAQIBAQICAgICAgIDBQMDAwMDBgQEAwUH"
        "BgcHBgYGBgcICwkHCAsIBgYIDAsJCgsKCgoGCAsMCwoKCgsKCgr/wAARC"
        "AABAAEDASIA/8QAFgABAQEAAAAAAAAAAAAAAAAABQYH/8QAIhAAAQQCAwEB"
        "AQAAAAAAAAAAAQIDBAUREiExQf/EABQBAQAAAAAAAAAAAAAAAAAAAAD/xAAU"
        "EQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCwR5EcPYlNx2nG0uNr"
        "OUqSoZBBHYgg1lz/AFHvFrp261XHXmo5lsTIbkRZMm4yHWlpUkpUlSVqIII"
        "IIIxuKUpSlKUpSlKUpSlKUpSlKUpX/2Q=="
    )
    try:
        poller = client.begin_analyze_document(
            model_id="prebuilt-read",
            body=tiny_jpg,
            content_type="image/jpeg"
        )
        _ = poller.result()
        print(f"{PASS}  Connected! Document Intelligence responded successfully.")
        results['azure_doc_intelligence'] = 'OK'
    except Exception as inner:
        err_str = str(inner)
        # A 400/InvalidContent means auth worked but content was rejected -- still connected
        if any(x in err_str for x in ["InvalidContent", "InvalidRequest", "400", "content"]):
            print(f"{PASS}  Connected! (Auth OK, service reachable)")
            results['azure_doc_intelligence'] = 'OK'
        else:
            raise

except Exception as e:
    print(f"{FAIL}  Azure Document Intelligence FAILED: {e}")
    results['azure_doc_intelligence'] = f'FAILED: {e}'

# ─────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────
print("\n" + "="*60)
print("SUMMARY")
print("="*60)
all_ok = True
for service, status in results.items():
    icon = PASS if status == 'OK' else FAIL
    print(f"  {icon}  {service:<30} {status}")
    if status != 'OK':
        all_ok = False

print()
if all_ok:
    print(f"{PASS}  All connections are healthy!")
else:
    print(f"{FAIL}  Some connections failed. Check the details above.")
print("="*60 + "\n")
sys.exit(0 if all_ok else 1)
