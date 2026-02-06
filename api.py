
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

@router.post("/fnol/", response_model=schemas.FNOLWorkItemCreate)
def create_fnol(item: schemas.FNOLWorkItemCreate, db: Session = Depends(get_db)):
    db_item = models.FNOLWorkItem(
        email_subject=item.subject,
        email_body=item.body,
        extracted_fields=item.extracted_fields
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.get("/fnol/", response_model=List[schemas.FNOLWorkItemCreate])
def list_fnols(db: Session = Depends(get_db)):
    return db.query(models.FNOLWorkItem).all()

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
