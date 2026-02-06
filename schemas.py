from pydantic import BaseModel
from typing import Optional, Dict, Any


class FNOLWorkItemCreate(BaseModel):
    subject: str
    body: str
    extracted_fields: Optional[Dict[str, Any]] = None

# Response schema for ORM model
from pydantic import Field

class FNOLWorkItem(BaseModel):
    id: int
    subject: str = Field(..., alias="email_subject")
    body: str = Field(..., alias="email_body")
    extracted_fields: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    created_at: Optional[datetime.datetime] = None

    class Config:
        orm_mode = True
        allow_population_by_field_name = True

class FNOLWorkItemUpdate(BaseModel):
    extracted_fields: Optional[Dict[str, Any]] = None
    status: Optional[str] = None

class AttachmentCreate(BaseModel):
    workitem_id: int
    filename: str
    blob_url: str
    doc_type: Optional[str] = None
