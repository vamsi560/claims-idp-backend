from pydantic import BaseModel
import datetime
from typing import Optional, Dict, Any


# Request schema for creating FNOL work item
from typing import List
from pydantic import Field

class FNOLWorkItemCreate(BaseModel):
    message_id: Optional[str] = None
    subject: str
    body: str
    attachment_text: Optional[List[str]] = None
    extracted_fields: Optional[Dict[str, Any]] = None
    attachments: Optional[List[Dict[str, Any]]] = None

# Response schema for ORM model

class AttachmentOut(BaseModel):
    id: int
    filename: str
    blob_url: str
    doc_type: Optional[str] = None

    class Config:
        from_attributes = True

class FNOLWorkItem(BaseModel):
    id: int
    message_id: Optional[str] = None
    tag: Optional[str] = None
    subject: str = Field(..., alias="email_subject")
    body: str = Field(..., alias="email_body")
    extracted_fields: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    created_at: Optional[datetime.datetime] = None
    attachments: Optional[list[AttachmentOut]] = []

    class Config:
        from_attributes = True
        validate_by_name = True

class FNOLWorkItemUpdate(BaseModel):
    extracted_fields: Optional[Dict[str, Any]] = None
    status: Optional[str] = None

class AttachmentCreate(BaseModel):
    workitem_id: int
    filename: str
    blob_url: str
    doc_type: Optional[str] = None
