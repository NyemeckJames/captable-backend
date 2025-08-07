from sqlalchemy import Column, String, Integer, Numeric, Date, DateTime, Text, ForeignKey, Boolean, Enum as SqlEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from .connection import Base


class UserModel(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # "admin", "shareholder"
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship to shareholder profile (only for shareholders)
    shareholder_profile = relationship("ShareholderProfileModel", back_populates="user", uselist=False)


class ShareholderProfileModel(Base):
    __tablename__ = "shareholder_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    address = Column(Text)
    phone = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("UserModel", back_populates="shareholder_profile")
    issuances = relationship("ShareIssuanceModel", back_populates="shareholder_profile")


class CompanyModel(Base):
    __tablename__ = "companies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    authorized_shares = Column(Integer, nullable=False)
    issued_shares = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relation avec ShareClassModel
    share_classes = relationship("ShareClassModel", back_populates="company")


class ShareClassModel(Base):
    __tablename__ = "share_classes"
    
    id = Column(String(50), primary_key=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    rights = Column(Text)  # JSON string for rights
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relation avec CompanyModel
    company = relationship("CompanyModel", back_populates="share_classes")

class ShareIssuanceModel(Base):
    __tablename__ = "share_issuances"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shareholder_profile_id = Column(UUID(as_uuid=True), ForeignKey("shareholder_profiles.id"), nullable=False)
    share_class_id = Column(String(50), nullable=False)
    quantity = Column(Integer, nullable=False)
    price_per_share = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="EUR")
    issue_date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    shareholder_profile = relationship("ShareholderProfileModel", back_populates="issuances")
    certificate = relationship("ShareCertificateModel", back_populates="issuance", uselist=False)


class ShareCertificateModel(Base):
    __tablename__ = "share_certificates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    share_issuance_id = Column(UUID(as_uuid=True), ForeignKey("share_issuances.id"), nullable=False, unique=True)
    watermark = Column(Text)
    storage_path = Column(String(500))
    generation_date = Column(DateTime(timezone=True), server_default=func.now())
    
    issuance = relationship("ShareIssuanceModel", back_populates="certificate")

class AuditEventModel(Base):
    __tablename__ = "audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_type = Column(String(50), nullable=False)  # e.g., "user_login", "share_issuance_created"
    user_id = Column(UUID(as_uuid=True), nullable=False)
    target_entity_type = Column(String(50), nullable=False)  # e.g., "User", "ShareIssuance"
    target_entity_id = Column(UUID(as_uuid=True), nullable=False)
    event_metadata = Column(Text)  # JSON string (was 'metadata')
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
