
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import models
import schemas
import database
import azure_blob
import llm_client
from typing import List
import mimetypes
from azure_doc_intel import extract_text_from_bytes

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

    attachments = []
    if hasattr(item, 'attachments') and item.attachments:
        for att in item.attachments:
            filename = att.get('filename') or att.get('name')
            content = att.get('contentBytes') or att.get('content')
            doc_type = att.get('doc_type') or att.get('contentType')
            if filename and content:
                import base64
                file_bytes = base64.b64decode(content)
                mime_type, _ = mimetypes.guess_type(filename)
                # If image, use Azure Document Intelligence OCR for text extraction
                extracted_text = None
                if mime_type in ['image/png', 'image/jpeg', 'image/jpg']:
                    try:
                        extracted_text = extract_text_from_bytes(file_bytes, mime_type)
                    except Exception as e:
                        extracted_text = None
                # Document type detection using filename and OCR text
                fname_lower = filename.lower() if filename else ''
                text_for_detection = (extracted_text or '') + ' ' + fname_lower
                if 'claim' in text_for_detection:
                    doc_type = 'Claim Form'
                elif 'police' in text_for_detection:
                    doc_type = 'Police Report'
                elif 'loss' in text_for_detection:
                    doc_type = 'Proof of Loss'
                elif 'invoice' in text_for_detection:
                    doc_type = 'Invoice'
                elif 'photo' in text_for_detection or 'image' in text_for_detection:
                    doc_type = 'Photo'
                elif 'id' in text_for_detection or 'identity' in text_for_detection:
                    doc_type = 'ID Document'
                elif not doc_type:
                    doc_type = 'Other Document'
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
    # Save attachments from email payload if present
    attachments = []
    if hasattr(item, 'attachments') and item.attachments:
        for att in item.attachments:
            filename = att.get('filename') or att.get('name')
            content = att.get('contentBytes') or att.get('content')
            doc_type = att.get('doc_type') or att.get('contentType')
            if filename and content:
                # Deduplication: check if attachment already exists for this workitem and filename
                existing_attachment = db.query(models.Attachment).filter_by(workitem_id=db_item.id, filename=filename).first()
                if existing_attachment:
                    attachments.append(existing_attachment)
                    continue
                import base64
                file_bytes = base64.b64decode(content)
                mime_type, _ = mimetypes.guess_type(filename)
                # If image, use Azure Document Intelligence OCR for text extraction
                extracted_text = None
                if mime_type in ['image/png', 'image/jpeg', 'image/jpg']:
                    try:
                        extracted_text = extract_text_from_bytes(file_bytes, mime_type)
                    except Exception as e:
                        extracted_text = None
                # Document type detection using filename and OCR text
                fname_lower = filename.lower() if filename else ''
                text_for_detection = (extracted_text or '') + ' ' + fname_lower
                if 'claim' in text_for_detection:
                    doc_type = 'Claim Form'
                elif 'police' in text_for_detection:
                    doc_type = 'Police Report'
                elif 'loss' in text_for_detection:
                    doc_type = 'Proof of Loss'
                elif 'invoice' in text_for_detection:
                    doc_type = 'Invoice'
                elif 'photo' in text_for_detection or 'image' in text_for_detection:
                    doc_type = 'Photo'
                elif 'id' in text_for_detection or 'identity' in text_for_detection:
                    doc_type = 'ID Document'
                elif not doc_type:
                    doc_type = 'Other Document'
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

@router.get("/fnol/{id}/", response_model=schemas.FNOLWorkItem)
def get_fnol(id : int, db: Session = Depends(get_db)):

    item = db.query(models.FNOLWorkItem).filter(models.FNOLWorkItem.id == id).first()
    attachment = db.query(models.Attachment).filter(models.Attachment.workitem_id == item.id).first()
    item.attachments = [attachment] if attachment else []
    if not item:
        raise HTTPException(status_code=404, detail="FNOL work item not found")
    return item

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
