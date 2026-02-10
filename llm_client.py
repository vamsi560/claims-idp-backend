
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
</FIELDS>

If a field is not present, use null or an empty string/list as appropriate. Only use the information in the provided text.

Email Subject: {email_subject}
Email Body: {email_body}
Attachment Text: {attachment_text if attachment_text else ''}
Return only the JSON object.
'''

    # Call Gemini LLM API
    headers = {
        "Content-Type": "application/json",
    }
    url = f"{GEMINI_API_URL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "model": GEMINI_MODEL,
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ]
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
        response.raise_for_status()
        result = response.json()
        # Gemini returns the text in a nested structure; extract JSON from the response
        text = result["candidates"][0]["content"]["parts"][0]["text"]
        # Remove Markdown code block if present
        if text.strip().startswith('```'):
            text = text.strip()
            # Remove the first line (```json or ```) and the last line (```)
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
        # Fallback: return error info for debugging
        return {"error": str(e), "llm_response": result if 'result' in locals() else None}
