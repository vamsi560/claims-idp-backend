
import models
import schemas
import database
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import func, case
from sqlalchemy.orm import Session
router = APIRouter()
# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Analytics Endpoints ---
@router.get("/analytics/claims-summary")
def claims_summary(db: Session = Depends(get_db)):
    # Claims by status
    status_counts = db.query(models.FNOLWorkItem.status, func.count(models.FNOLWorkItem.id)).group_by(models.FNOLWorkItem.status).all()
    # Claims by type (from attachments' doc_type)
    type_counts = db.query(models.Attachment.doc_type, func.count(models.Attachment.id)).group_by(models.Attachment.doc_type).all()
    # Average processing time (from created_at to now or to closed/approved)
    avg_processing_time = db.query(
        func.avg(
            case(
                (
                    models.FNOLWorkItem.status.in_(["approved", "closed", "completed"]),
                    func.extract('epoch', func.now() - models.FNOLWorkItem.created_at)
                ),
                else_=func.extract('epoch', func.now() - models.FNOLWorkItem.created_at)
            )
        )
    ).scalar()
    return {
        "claims_by_status": {status: count for status, count in status_counts},
        "claims_by_type": {doc_type or "Unknown": count for doc_type, count in type_counts},
        "average_processing_time_seconds": avg_processing_time or 0
    }

@router.get("/analytics/claims-trend")
def claims_trend(db: Session = Depends(get_db), days: int = 30):
    # Claims per day for the last N days
    from sqlalchemy import cast, Date
    import datetime
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    trend = db.query(
        cast(models.FNOLWorkItem.created_at, Date).label('date'),
        func.count(models.FNOLWorkItem.id)
    ).filter(models.FNOLWorkItem.created_at >= cutoff)
    trend = trend.group_by('date').order_by('date').all()
    return [{"date": str(date), "count": count} for date, count in trend]
import azure_blob
import llm_client
from typing import List
import mimetypes
from azure_doc_intel import extract_text_from_bytes


@router.post("/fnol/", response_model=schemas.FNOLWorkItem)
def create_fnol(item: schemas.FNOLWorkItemCreate, db: Session = Depends(get_db)):
    print(f"\n=== create_fnol called with message_id: {item.message_id} ===")
    
    # Deduplication: check for existing message_id if provided
    if item.message_id:
        existing_item = db.query(models.FNOLWorkItem).filter(models.FNOLWorkItem.message_id == item.message_id).first()
        if existing_item:
            print(f"Found existing item with id: {existing_item.id}, returning cached result")
            all_attachments = db.query(models.Attachment).filter(models.Attachment.workitem_id == existing_item.id).all()
            attachments_out = [
                schemas.AttachmentOut(
                    id=a.id,
                    filename=a.filename,
                    blob_url=a.blob_url,
                    doc_type=a.doc_type
                ) for a in all_attachments
            ]
            return schemas.FNOLWorkItem(
                id=existing_item.id,
                message_id=existing_item.message_id,
                email_subject=existing_item.email_subject,
                email_body=existing_item.email_body,
                extracted_fields=existing_item.extracted_fields,
                status=existing_item.status,
                attachments=attachments_out
            )
    else:
        print("WARNING: No message_id provided - deduplication will not work!")

    # Step 1: Extract text from all attachments
    import base64
    extracted_texts = []
    attachment_data = []
    seen_filenames = set()
    
    if hasattr(item, 'attachments') and item.attachments:
        for att in item.attachments:
            filename = att.get('filename') or att.get('name')
            content = att.get('contentBytes') or att.get('content')
            
            # Skip duplicate filenames in the input
            if filename in seen_filenames:
                print(f"Skipping duplicate attachment in input: {filename}")
                continue
            
            print(f"Processing attachment: filename={filename}, content_present={bool(content)}")
            if filename and content:
                seen_filenames.add(filename)
                file_bytes = base64.b64decode(content)
                mime_type, _ = mimetypes.guess_type(filename)
                extracted_text = None
                print(f"Guessed MIME type for {filename}: {mime_type}")
                if mime_type in ['image/png', 'image/jpeg', 'image/jpg', 'application/pdf']:
                    print("entered into mime type processing")
                    try:
                        extracted_text = extract_text_from_bytes(file_bytes, mime_type)
                    except Exception as e:
                        print(f"Error extracting text from {filename}: {e}")
                        extracted_text = None
                
                if extracted_text:
                    extracted_texts.append(extracted_text)
                
                attachment_data.append({
                    'filename': filename,
                    'file_bytes': file_bytes,
                    'mime_type': mime_type,
                    'extracted_text': extracted_text
                })
    # print("attachment_data:", attachment_data)

    # Step 2: Pass extracted text to LLM for field extraction
    combined_attachment_text = '\n\n'.join(extracted_texts) if extracted_texts else ''
    # print("Combined attachment text:", combined_attachment_text)
    if item.extracted_fields is not None:
        extracted_fields = item.extracted_fields
    else:
        extracted_fields = llm_client.extract_fields_from_email(
            item.subject,
            item.body,
            combined_attachment_text
        )
    
    # Step 3: Create FNOL work item
    db_item = models.FNOLWorkItem(
        message_id=item.message_id,
        email_subject=item.subject,
        email_body=item.body,
        extracted_fields=extracted_fields,
        tag=extracted_fields['claim_type']['category'] if 'claim_type' in extracted_fields else None
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    # Step 4: Store attachments in DB
    print(f"Storing {len(attachment_data)} attachments for workitem_id={db_item.id}")
    attachments_added = 0
    for att_data in attachment_data:
        filename = att_data['filename']
        print(f"Checking if attachment '{filename}' already exists for workitem {db_item.id}")
        existing_attachment = db.query(models.Attachment).filter_by(workitem_id=db_item.id, filename=filename).first()
        if existing_attachment:
            print(f"Attachment '{filename}' already exists with id={existing_attachment.id}, skipping")
            continue
        
        fname_lower = filename.lower()
        text_for_detection = (att_data['extracted_text'] or '') + ' ' + fname_lower
        from llm_client import guess_doc_type
        try:
            doc_type = guess_doc_type(text_for_detection)
            print(f"LLM guessed document type for '{filename}': {doc_type}")
        except Exception as e:
            print(f"Guessing based on the keywords in the document '{filename}': {e}")
            
            if 'claim' in text_for_detection:
                doc_type = 'Claim Form'
            elif 'police' in text_for_detection:
                doc_type = 'Police Report'
            elif 'loss' in text_for_detection:
                doc_type = 'Proof of Loss'
            elif 'invoice' in text_for_detection:
                doc_type = 'Invoice'
            elif 'declaration' in text_for_detection:
                doc_type = 'Declaration'
            elif 'photo' in text_for_detection or 'image' in text_for_detection:
                doc_type = 'Photo'
            elif 'id' in text_for_detection or 'identity' in text_for_detection:
                doc_type = 'ID Document'
            else:
                doc_type = 'Other Document'
        
        print(f"Uploading attachment '{filename}' to blob storage")
        blob_url = azure_blob.upload_attachment(filename, att_data['file_bytes'])
        print(f"Creating attachment record for '{filename}' with doc_type='{doc_type}'")
        attachment = models.Attachment(
            workitem_id=db_item.id,
            filename=filename,
            blob_url=blob_url,
            doc_type=doc_type
        )
        db.add(attachment)
        attachments_added += 1
        print(f"Added attachment '{filename}' to session (total added: {attachments_added})")
    
    print(f"Committing {attachments_added} attachments to database")
    try:
        db.commit()
        print("Attachments committed successfully")
    except Exception as e:
        print(f"ERROR committing attachments: {e}")
        db.rollback()
        raise
    
    # Fetch all attachments for response
    all_attachments = db.query(models.Attachment).filter(models.Attachment.workitem_id == db_item.id).all()
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
        email_subject=db_item.email_subject,
        email_body=db_item.email_body,
        extracted_fields=db_item.extracted_fields,
        status=db_item.status,
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
def upload_attachments(workitem_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
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
