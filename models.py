from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
import datetime

Base = declarative_base()

class FNOLWorkItem(Base):
    __tablename__ = 'fnol_work_items'
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String, nullable=True, index=True, unique=False)  # Set unique=True if always available
    email_subject = Column(String, nullable=False)
    email_body = Column(Text, nullable=False)
    extracted_fields = Column(JSONB)
    status = Column(String, default='pending')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Attachment(Base):
    __tablename__ = 'attachments'
    id = Column(Integer, primary_key=True, index=True)
    workitem_id = Column(Integer)
    filename = Column(String)
    blob_url = Column(String)
    doc_type = Column(String)
