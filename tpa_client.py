import os
import uuid
import random
import requests
from dotenv import load_dotenv

load_dotenv()

TPA_API_URL = os.getenv("TPA_API_URL")
TPA_API_KEY = os.getenv("TPA_API_KEY")
TPA_WEBHOOK_SECRET = os.getenv("TPA_WEBHOOK_SECRET")

# Mock response statuses cycled through to simulate realistic TPA behaviour
_MOCK_STATUSES = ["received", "acknowledged", "under_review", "assigned"]


def _mock_push_response(fnol_id: int, provider_code: str = "MOCK") -> dict:
    """
    Simulate a TPA acknowledgement response without making a real HTTP call.
    Returns a dict that mirrors what a real TPA API would return.
    """
    ref_id = f"{provider_code}-{fnol_id:06d}-{uuid.uuid4().hex[:6].upper()}"
    return {
        "tpa_reference_id": ref_id,
        "status": "received",
        "message": f"[MOCK] Claim {fnol_id} received by {provider_code}. Reference: {ref_id}",
        "mock": True,
    }


def push_claim_to_tpa(fnol_id: int, extracted_fields: dict, attachments: list,
                       provider=None) -> dict:
    """
    Push a new FNOL claim to the TPA system.

    If the provider is flagged as mock (is_mock=True) OR TPA_API_URL is not set,
    returns a simulated response without making any HTTP call.

    Args:
        fnol_id:          Internal FNOL work item ID.
        extracted_fields: LLM-extracted JSON fields dict.
        attachments:      List of Attachment ORM objects.
        provider:         TPAProvider ORM object (optional). Used to determine
                          mock vs live mode and to pick the right API URL/code.

    Returns:
        dict with at minimum: { "tpa_reference_id": "...", "status": "..." }
    """
    provider_code = provider.code if provider else "TPA"
    is_mock = True  # default to mock

    if provider:
        is_mock = provider.is_mock
        api_url = provider.api_url if not provider.is_mock else None
    else:
        api_url = TPA_API_URL
        is_mock = not bool(TPA_API_URL)

    # --- MOCK MODE ---
    if is_mock or not api_url:
        print(f"[TPA MOCK] Simulating push for FNOL {fnol_id} to provider '{provider_code}'")
        return _mock_push_response(fnol_id, provider_code)

    # --- LIVE MODE ---
    payload = {
        "source_claim_id": str(fnol_id),
        "claim_type": extracted_fields.get("claim_type", {}),
        "insured": extracted_fields.get("insured", {}),
        "loss": extracted_fields.get("loss", {}),
        "policy": extracted_fields.get("policy", {}),
        "claimants": extracted_fields.get("claimants", []),
        "reporting_contact": extracted_fields.get("reporting_contact", {}),
        "injured_person_contact": extracted_fields.get("injured_person_contact", {}),
        "summary": extracted_fields.get("summary", ""),
        "intent": extracted_fields.get("intent", {}),
        "attachments": [
            {
                "filename": a.filename,
                "url": a.blob_url,
                "doc_type": a.doc_type,
                "mime_type": getattr(a, "mime_type", None),
            }
            for a in attachments
        ],
    }
    api_key = TPA_API_KEY or ""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Source-System": "claims-idp-backend",
    }
    response = requests.post(f"{api_url}/claims", json=payload, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def simulate_status_update(tpa_reference_id: str) -> dict:
    """
    Simulate a TPA status progression for a mock claim.
    Returns a webhook-style payload that the /tpa/webhook/ endpoint would receive.
    """
    status = random.choice(["acknowledged", "under_review", "assigned", "approved", "closed"])
    return {
        "tpa_reference_id": tpa_reference_id,
        "source_claim_id": tpa_reference_id.split("-")[1].lstrip("0") if "-" in tpa_reference_id else "0",
        "status": status,
        "notes": f"[MOCK] Automated status update: claim moved to '{status}'",
        "mock": True,
    }


def validate_webhook_secret(secret_header: str) -> bool:
    """
    Validate the shared secret sent by the TPA in the X-TPA-Secret header.
    Returns True if valid, or if no secret is configured (dev/mock mode).
    """
    if not TPA_WEBHOOK_SECRET:
        return True  # No secret configured — allow all (mock/dev mode)
    return secret_header == TPA_WEBHOOK_SECRET
