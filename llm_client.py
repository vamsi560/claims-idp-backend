# Placeholder for Gemini LLM integration
# Implement the call to Gemini API to extract FNOL fields from email content


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

matter: str
lawsuit_or_complaint_received: bool
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

    # TODO: Replace the following with a real LLM call using the above prompt and combined_text
    # For now, return a sample output for UI development
    return {
        "summary": "Rear-end collision reported by insured.",
        "intent": {"intent_type": "FNOL", "confidence_score": 0.98},
        "reported_by_and_main_contact_are_same": True,
        "claim_type": {"category": "Auto", "sub_category": "Collision"},
        "reporting_contact": {
            "name": "John Doe",
            "relationship_to_insured": "Self",
            "phone": "555-1234",
            "email": "john.doe@email.com",
            "preferred_contact_method": "Email"
        },
        "best_contact": {
            "contact_type": "Insured",
            "name": "John Doe",
            "phone": "555-1234",
            "email": "john.doe@email.com"
        },
        "reply_to_emails": ["reply@email.com"],
        "insured": {
            "full_name": "John Doe",
            "insured_type": "Individual",
            "phone": "555-1234",
            "email": "john.doe@email.com",
            "address_line1": "123 Main St",
            "city": "Springfield",
            "state": "IL",
            "postal_code": "62701"
        },
        "claimants": [
            {"name": "Jane Smith", "claimant_type": "Individual", "injury_type": "Physical", "phone": "555-5678", "email": "jane.smith@email.com"}
        ],
        "claimants_count": 1,
        "injured_person_contact": {
            "name": "Jane Smith",
            "injury_severity": "Minor",
            "medical_treatment_received": False,
            "hospital_name": ""
        },
        "plaintiff": None,
        "policy": {
            "policy_number": "A1234567",
            "policy_type": "Auto",
            "line_of_business": "Personal Auto",
            "effective_date": "2024-01-01",
            "expiration_date": "2025-01-01",
            "insurer_name": "Acme Insurance",
            "policy_status": "Active"
        },
        "loss": {
            "loss_date": "2025-12-15",
            "loss_time": "14:30",
            "loss_type": "Accident",
            "cause_of_loss": "Rear-end collision",
            "description": "Insured was rear-ended at a stoplight.",
            "reported_date": "2025-12-16",
            "location_address_line1": "5th & Main St",
            "location_city": "Springfield",
            "location_state": "IL",
            "location_postal_code": "62701"
        },
        "matter": None,
        "acknowledgment": {
            "recipient_name": "John Doe",
            "recipient_role": "Insured",
            "delivery_method": "Email",
            "acknowledgment_sent": True
        },
        "lawsuit_or_complaint_received": False
    }
