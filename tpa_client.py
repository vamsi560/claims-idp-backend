import os
import requests
from dotenv import load_dotenv

load_dotenv()

TPA_API_URL = os.getenv("TPA_API_URL")
TPA_API_KEY = os.getenv("TPA_API_KEY")
TPA_WEBHOOK_SECRET = os.getenv("TPA_WEBHOOK_SECRET")


def push_claim_to_tpa(fnol_id: int, extracted_fields: dict, attachments: list) -> dict:
    """
    Push a new FNOL claim outbound to the TPA system.

    Args:
        fnol_id:          The internal FNOL work item ID.
        extracted_fields: The LLM-extracted JSON fields dict.
        attachments:      List of Attachment ORM objects.

    Returns:
        TPA response dict, expected to contain at minimum:
        { "tpa_reference_id": "...", "status": "received" }

    Raises:
        requests.HTTPError if TPA returns a non-2xx response.
    """
    if not TPA_API_URL or not TPA_API_KEY:
        raise ValueError("TPA_API_URL and TPA_API_KEY must be set in environment variables.")

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

    headers = {
        "Authorization": f"Bearer {TPA_API_KEY}",
        "Content-Type": "application/json",
        "X-Source-System": "claims-idp-backend",
    }

    response = requests.post(
        f"{TPA_API_URL}/claims",
        json=payload,
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def validate_webhook_secret(secret_header: str) -> bool:
    """
    Validate the shared secret sent by the TPA in the X-TPA-Secret header.
    Returns True if valid, False otherwise.
    """
    if not TPA_WEBHOOK_SECRET:
        # If no secret is configured, skip validation (not recommended for production)
        return True
    return secret_header == TPA_WEBHOOK_SECRET
