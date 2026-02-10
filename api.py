
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import models
import schemas
import database
import azure_blob
import llm_client
from typing import List

router = APIRouter()

# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/fnol/", response_model=schemas.FNOLWorkItem)
def create_fnol(item: schemas.FNOLWorkItemCreate, db: Session = Depends(get_db)):
    # Deduplication: check for existing message_id if provided
    if item.message_id:
        existing_item = db.query(models.FNOLWorkItem).filter(models.FNOLWorkItem.message_id == item.message_id).first()
        if existing_item:
            return existing_item

    # Always extract fields unless explicitly provided
    if item.extracted_fields is not None:
        extracted_fields = item.extracted_fields
    else:
        extracted_fields = llm_client.extract_fields_from_email(
            item.subject,
            item.body,
            item.attachment_text
        )
    db_item = models.FNOLWorkItem(
        message_id=item.message_id,
        email_subject=item.subject,
        email_body=item.body,
        extracted_fields=extracted_fields
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    # Save attachments from email payload if present
    attachments = []
    if hasattr(item, 'attachments') and item.attachments:
        for att in item.attachments:
            # att should be a dict with at least filename and content (base64 or bytes)
            filename = att.get('filename') or att.get('name')
            content = att.get('contentBytes') or att.get('content')
            doc_type = att.get('doc_type') or att.get('contentType')
            if filename and content:
                import base64
                file_bytes = base64.b64decode(content)
                blob_url = azure_blob.upload_attachment(filename, file_bytes)
                attachment = models.Attachment(
                    workitem_id=db_item.id,
                    filename=filename,
                    blob_url=blob_url,
                    doc_type=doc_type
                )
                db.add(attachment)
                db.commit()
                db.refresh(attachment)
                attachments.append(attachment)
    # Fetch all attachments for this work item
    all_attachments = db.query(models.Attachment).filter(models.Attachment.workitem_id == db_item.id).all()
    # Convert attachments to Pydantic models
    attachments_out = [
        schemas.AttachmentOut(
            id=a.id,
            filename=a.filename,
            blob_url=a.blob_url,
            doc_type=a.doc_type
        ) for a in all_attachments
    ]
    return schemas.FNOLWorkItem(
        id=db_item.id,
        message_id=db_item.message_id,
        subject=db_item.email_subject,
        body=db_item.email_body,
        extracted_fields=db_item.extracted_fields,
        status=db_item.status,
        created_at=db_item.created_at,
        attachments=attachments_out
    )

@router.get("/fnol/", response_model=List[schemas.FNOLWorkItem])
def list_fnols(db: Session = Depends(get_db)):
    items = db.query(models.FNOLWorkItem).all()
    for item in items:
        attachments = db.query(models.Attachment).filter(models.Attachment.workitem_id == item.id).all()
        item.attachments = attachments
    return items

@router.post("/attachments/")
def upload_attachment(workitem_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    blob_url = azure_blob.upload_attachment(file.filename, file.file)
    attachment = models.Attachment(
        workitem_id=workitem_id,
        filename=file.filename,
        blob_url=blob_url
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return {"url": blob_url}


# Update FNOL work item
@router.put("/fnol/{fnol_id}/", response_model=schemas.FNOLWorkItemCreate)
def update_fnol(fnol_id: int, item: schemas.FNOLWorkItemUpdate, db: Session = Depends(get_db)):
    db_item = db.query(models.FNOLWorkItem).filter(models.FNOLWorkItem.id == fnol_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="FNOL work item not found")
    if item.extracted_fields is not None:
        db_item.extracted_fields = item.extracted_fields
    if item.status is not None:
        db_item.status = item.status
    db.commit()
    db.refresh(db_item)
    return db_item
