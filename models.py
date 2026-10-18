from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy import UniqueConstraint, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
import datetime

Base = declarative_base()


class TPAProvider(Base):
    __tablename__ = 'tpa_providers'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)                    # Full company name
    code = Column(String, unique=True, nullable=False)       # Short code e.g. "SEDGWICK"
    contact_email = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)
    api_url = Column(String, nullable=True)                  # Real API URL — null means mock mode
    specialties = Column(String, nullable=True)              # e.g. "Auto, Property, Liability"
    is_active = Column(Boolean, default=True)
    is_mock = Column(Boolean, default=True)                  # True = simulated, False = live TPA
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    claims = relationship('FNOLWorkItem', back_populates='tpa_provider')


class FNOLWorkItem(Base):
    __tablename__ = 'fnol_work_items'
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String, nullable=True, index=True, unique=False)
    email_subject = Column(String, nullable=False)
    email_body = Column(Text, nullable=False)
    extracted_fields = Column(JSONB)
    status = Column(String, default='pending')
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    attachments = relationship('Attachment', back_populates='workitem', cascade='all, delete-orphan')
    tag = Column(Text)
    # TPA integration fields
    tpa_reference_id = Column(String, nullable=True, index=True)   # Reference ID returned by TPA
    tpa_status = Column(String, nullable=True)                      # TPA's own status label
    tpa_pushed_at = Column(DateTime, nullable=True)                 # When we last pushed to TPA
    tpa_last_updated = Column(DateTime, nullable=True)              # When TPA last updated us
    tpa_provider_id = Column(Integer, ForeignKey('tpa_providers.id', ondelete='SET NULL'), nullable=True, index=True)
    tpa_provider = relationship('TPAProvider', back_populates='claims')


class Attachment(Base):
    __tablename__ = 'attachments'
    id = Column(Integer, primary_key=True, index=True)
    workitem_id = Column(Integer, ForeignKey('fnol_work_items.id', ondelete='CASCADE'), nullable=False, index=True)
    filename = Column(String)
    blob_url = Column(String)
    doc_type = Column(String)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)
    uploader = Column(String, nullable=True)
    file_size = Column(BigInteger, nullable=True)
    mime_type = Column(String, nullable=True)
    workitem = relationship('FNOLWorkItem', back_populates='attachments')
    __table_args__ = (UniqueConstraint('workitem_id', 'filename', name='uix_workitem_filename'),)
