from pydantic import BaseModel
from typing import Optional, Dict, Any


class FNOLWorkItemCreate(BaseModel):
    subject: str
    body: str
    extracted_fields: Optional[Dict[str, Any]] = None

# Response schema for ORM model
class FNOLWorkItem(BaseModel):
    id: int
    subject: str
    body: str
    extracted_fields: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        orm_mode = True
        fields = {
            'subject': 'email_subject',
            'body': 'email_body',
        }

class FNOLWorkItemUpdate(BaseModel):
    extracted_fields: Optional[Dict[str, Any]] = None
    status: Optional[str] = None

class AttachmentCreate(BaseModel):
    workitem_id: int
    filename: str
    blob_url: str
    doc_type: Optional[str] = None
