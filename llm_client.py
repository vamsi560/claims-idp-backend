
import os
import requests
import json
from dotenv import load_dotenv


load_dotenv()

GEMINI_API_URL = os.getenv("GEMINI_API_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")


def extract_fields_from_email(email_subject, email_body, attachment_text=None):
    """
    Calls the LLM to extract all required FNOL fields from the provided email subject, body, and attachment text.
    Returns a nested dict matching the required schema.
    """
    # Combine all text sources for extraction
    combined_text = email_subject + "\n" + email_body
    if attachment_text:
        if isinstance(attachment_text, list):
            combined_text += "\n" + "\n".join(attachment_text)
        else:
            combined_text += "\n" + str(attachment_text)

    # --- LLM PROMPT TEMPLATE ---
    prompt = f'''
You are an expert insurance claims assistant. Extract the following fields and subfields from the provided email subject, body, and attachment text. Return the result as a JSON object matching this structure:

<FIELDS>
summary: str
intent: dict (with keys: intent_type: str, confidence_score: float)
reported_by_and_main_contact_are_same: bool
claim_type: dict (category: str, sub_category: str)
reporting_contact: dict (name: str, relationship_to_insured: str, phone: str, email: str, preferred_contact_method: str)
best_contact: dict (contact_type: str, name: str, phone: str, email: str)
reply_to_emails: List[str]
insured: dict (full_name: str, insured_type: str, phone: str, email: str, address_line1: str, city: str, state: str, postal_code: str)
claimants: List[dict (name: str, claimant_type: str, injury_type: str, phone: str, email: str)]
claimants_count: int
injured_person_contact: dict (name: str, injury_severity: str, medical_treatment_received: bool, hospital_name: str)
plaintiff: str
policy: dict (policy_number: str, policy_type: str, line_of_business: str, effective_date: str, expiration_date: str, insurer_name: str, policy_status: str)
loss: dict (loss_date: str, loss_time: str, loss_type: str, cause_of_loss: str, description: str, reported_date: str, location_address_line1: str, location_city: str, location_state: str, location_postal_code: str)
matter: str
acknowledgment: dict (recipient_name: str, recipient_role: str, delivery_method: str, acknowledgment_sent: bool)
lawsuit_or_complaint_received: bool
_field_metadata: dict mapping each extracted field or dotted path (e.g. "summary", "policy.policy_number", "policy.policy_type", "loss.loss_date", "loss.cause_of_loss", "loss.description", "insured.full_name", "claim_type.category", etc.) to an object with:
  "confidence": float (between 0.0 and 1.0),
  "source": str (specific document or section, e.g. "Email Subject", "Email Body", "Attachment: Police Report", "Attachment: Claim Form")
</FIELDS>

If a field is not present, use null or an empty string/list as appropriate. Only use the information in the provided text.

Email Subject: {email_subject}
Email Body: {email_body}
Attachment Text: {attachment_text if attachment_text else ''}
Return only the JSON object.
'''

    # Call LLM API (Azure OpenAI or Gemini)
    try:
        text = _call_llm(prompt)
        # Remove Markdown code block if present
        text = text.strip()
        if text.startswith('```'):
            lines = text.splitlines()
            if lines[0].startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].startswith('```'):
                lines = lines[:-1]
            text = '\n'.join(lines)
        # Try to parse the JSON object from the LLM response
        extracted = json.loads(text)
        return extracted
    except Exception as e:
        # Fallback: return sanitized error info for debugging
        return {"error": f"Field extraction failed: {type(e).__name__} - {str(e)}"}


def _call_azure_openai(prompt: str, max_retries: int = 3) -> str:
    """
    Calls Azure OpenAI endpoint (supporting /openai/responses preview and standard endpoints)
    with automatic exponential backoff retry.
    """
    import time
    url = os.getenv("AZURE_OPENAI_ENDPOINT") or "https://code-suggestion-ai-model.openai.azure.com/openai/responses?api-version=2025-04-01-preview"
    key = os.getenv("AZURE_OPENAI_KEY", "")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5.4-mini")

    headers = {
        "api-key": key,
        "Content-Type": "application/json"
    }
    payload = {
        "model": deployment,
        "input": prompt
    }

    last_error_msg = ""
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            if response.status_code in (429, 500, 502, 503, 504):
                last_error_msg = f"HTTP {response.status_code} from Azure OpenAI"
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                    continue

            response.raise_for_status()
            result = response.json()
            # Azure /openai/responses format
            if "output" in result and result["output"]:
                content = result["output"][0].get("content", [])
                if content and "text" in content[0]:
                    return content[0]["text"]
            # Fallback for standard /chat/completions format
            if "choices" in result and result["choices"]:
                return result["choices"][0]["message"]["content"]
            raise ValueError(f"Unexpected response structure from Azure OpenAI: {result}")
        except requests.exceptions.RequestException as req_err:
            status_code = getattr(getattr(req_err, "response", None), "status_code", None)
            last_error_msg = f"Request error (HTTP {status_code})" if status_code else "Connection error to Azure OpenAI"
            if attempt < max_retries and (status_code in (429, 500, 502, 503, 504) or status_code is None):
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(last_error_msg)

    raise RuntimeError(last_error_msg or "Azure OpenAI request failed after retries")


def _call_gemini(prompt: str, max_retries: int = 3) -> str:
    """
    Helper function to send a prompt to the Gemini API with:
    1. Secure authentication via 'x-goog-api-key' header (preventing key leakage in URLs/errors).
    2. Exponential backoff retry logic for transient errors (503, 500, 502, 429).
    3. Masked error reporting.
    """
    import time
    api_url = os.getenv("GEMINI_API_URL") or "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash"
    api_key = os.getenv("GEMINI_API_KEY", "")
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # Strip query parameters (?key=...) from GEMINI_API_URL to prevent key leakage in URLs/logs
    base_url = api_url.split("?")[0].rstrip("/")
    if not base_url.endswith(":generateContent"):
        url = f"{base_url}:generateContent"
    else:
        url = base_url

    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }
    payload = {
        "model": model,
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ]
    }

    last_error_msg = ""
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            if response.status_code in (429, 500, 502, 503, 504):
                last_error_msg = f"HTTP {response.status_code} from Gemini service"
                if attempt < max_retries:
                    sleep_secs = 2 ** attempt
                    time.sleep(sleep_secs)
                    continue

            response.raise_for_status()
            result = response.json()
            return result["candidates"][0]["content"]["parts"][0]["text"]
        except requests.exceptions.RequestException as req_err:
            status_code = getattr(getattr(req_err, "response", None), "status_code", None)
            last_error_msg = f"Request error (HTTP {status_code})" if status_code else "Connection error to Gemini service"
            if attempt < max_retries and (status_code in (429, 500, 502, 503, 504) or status_code is None):
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(last_error_msg)
        except (KeyError, IndexError) as parse_err:
            raise ValueError(f"Unexpected response structure from Gemini API: {parse_err}")

    raise RuntimeError(last_error_msg or "Gemini API request failed after retries")


def _call_llm(prompt: str) -> str:
    """
    Routes prompt to configured LLM provider:
    Defaults to Azure OpenAI if AZURE_OPENAI_KEY is provided or LLM_PROVIDER is set to azure_openai.
    """
    provider = (os.getenv("LLM_PROVIDER") or "").strip().lower()
    if provider == "gemini":
        return _call_gemini(prompt)
    if provider == "azure_openai" or os.getenv("AZURE_OPENAI_KEY"):
        return _call_azure_openai(prompt)
    return _call_gemini(prompt)



def guess_doc_type(data: str):
    prompt = f"""
    You are a document classification assistant.

    Your task is to determine the document type based only on the provided text content.

    Classify the document into one of the following categories only:

    - Claim Form
    - Police Report
    - Proof of Loss
    - Invoice
    - Declaration
    - Photo
    - ID Document
    - Other Document

    Classification Rules:
    - Claim Form → Contains insurance claim details, claim number, policy number, claimant information, incident description.
    - Police Report → Contains police department references, officer names, badge numbers, case/report numbers, incident reports.
    - Proof of Loss → Contains statements of loss, damage valuation, sworn loss statements, insurance loss summaries.
    - Invoice → Contains billing details, invoice number, line items, totals, payment terms.
    - Declaration → Contains formal statements affirming truth, signatures under penalty, sworn declarations.
    - Photo → Mentions image/photo metadata or indicates the content is a photograph.
    - ID Document → Contains identity details such as name, date of birth, ID number, license/passport details.

    If none clearly apply, return: Other Document.

    Instructions:
    - Base your answer strictly on the text content.
    - Do not guess beyond the provided text.
    - Return only the document type label.
    - Do not provide explanations.

    Input Text:
    \"\"\"
    {data}
    \"\"\"

    Output:
    """

    try:
        doc_type = _call_llm(prompt).strip()
        return doc_type
    except Exception as e:
        return "Other Document"