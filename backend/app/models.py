import uuid
from datetime import UTC, date, datetime
from typing import Any

from pydantic import EmailStr
from sqlalchemy import BigInteger, Column, Date, DateTime, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


# ==========================================
# 1. Institution
# ==========================================
class InstitutionBase(SQLModel):
    permanent_id: str = Field(unique=True, index=True, max_length=100)
    name: str = Field(max_length=255)
    region: str = Field(index=True, max_length=100)
    is_government: bool = Field(default=False)
    leased_private: bool = Field(default=False)
    programmes: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )
    contact_email: str | None = Field(default=None, max_length=255)


class Institution(InstitutionBase, table=True):
    __tablename__ = "institution"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)


# ==========================================
# 2. User
# ==========================================
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)
    role: str = Field(
        default="institution", max_length=50
    )  # institution | regional | bureau | auditor
    region: str | None = Field(default=None, max_length=50)
    institution_id: uuid.UUID | None = Field(default=None, foreign_key="institution.id")


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(SQLModel):
    email: EmailStr | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    is_superuser: bool | None = None
    full_name: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: str | None = Field(default=None, max_length=50)
    region: str | None = Field(default=None, max_length=50)
    institution_id: uuid.UUID | None = None


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class User(UserBase, table=True):
    __tablename__ = "user"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(default_factory=get_datetime_utc)


class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# ==========================================
# 3. Instrument
# ==========================================
class InstrumentBase(SQLModel):
    institution_id: uuid.UUID = Field(foreign_key="institution.id", index=True)
    region: str = Field(index=True, max_length=100)
    kind: str = Field(max_length=20)  # FDR | RTGS
    ref_no: str = Field(max_length=100)
    bank_code: str = Field(max_length=50)
    ifsc: str = Field(max_length=20)
    amount_paise: int = Field(sa_column=Column(BigInteger, nullable=False))
    issue_date: date = Field(sa_column=Column(Date, nullable=False))
    maturity_date: date = Field(sa_column=Column(Date, nullable=False))
    holders: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )
    lien_marked: bool = Field(default=False)
    is_duplicate_receipt: bool = Field(default=False)
    lifecycle: str = Field(
        default="pending", max_length=30
    )  # pending | active | matured | renewed | released
    replaces_id: uuid.UUID | None = Field(default=None, foreign_key="instrument.id")
    created_by: uuid.UUID | None = Field(default=None, foreign_key="user.id")


class Instrument(InstrumentBase, table=True):
    __tablename__ = "instrument"
    __table_args__ = (Index("instrument_ref_idx", "bank_code", "ref_no"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, default=get_datetime_utc
        ),
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, default=get_datetime_utc
        ),
    )


class InstrumentPublic(InstrumentBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    badge: str | None = None
    next_action_code: str | None = None
    next_action_label: str | None = None


class InstrumentsPublic(SQLModel):
    data: list[InstrumentPublic]
    count: int


class InstrumentSubmit(SQLModel):
    institution_id: uuid.UUID | None = None
    region: str | None = None
    kind: str = "FDR"
    ref_no: str
    bank_code: str
    ifsc: str
    amount_paise: int
    issue_date: date
    maturity_date: date
    holders: list[dict[str, Any]] = []
    lien_marked: bool = False
    is_duplicate_receipt: bool = False
    replaces_id: uuid.UUID | None = None
    document_ids: list[uuid.UUID] = []


# ==========================================
# 4. Document
# ==========================================
class DocumentBase(SQLModel):
    instrument_id: uuid.UUID = Field(foreign_key="instrument.id", index=True)
    kind: str = Field(
        max_length=50
    )  # fdr_scan | payment_proof | bank_letter | affidavit | certificate | indemnity | other
    version: int = Field(default=1)
    filename: str = Field(max_length=255)
    mime: str = Field(max_length=100)
    size_bytes: int = Field(sa_column=Column(BigInteger, nullable=False))
    sha256: str = Field(max_length=64, index=True)
    storage_key: str = Field(max_length=500)
    uploaded_by: uuid.UUID | None = Field(default=None, foreign_key="user.id")


class Document(DocumentBase, table=True):
    __tablename__ = "document"
    __table_args__ = (
        UniqueConstraint(
            "instrument_id",
            "kind",
            "version",
            name="uq_document_instrument_kind_version",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    uploaded_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, default=get_datetime_utc
        ),
    )


class DocumentPublic(DocumentBase):
    id: uuid.UUID
    uploaded_at: datetime
    is_signed_dsc: bool | None = None


class DocumentsPublic(SQLModel):
    data: list[DocumentPublic]
    count: int


# ==========================================
# 5. Confirmation
# ==========================================
class ConfirmationBase(SQLModel):
    instrument_id: uuid.UUID = Field(foreign_key="instrument.id", index=True)
    status: str = Field(
        default="requested", max_length=30
    )  # requested | confirmed | rejected | unavailable
    method: str = Field(max_length=30)  # signed_letter | callback | manual
    token_hash: str = Field(index=True, max_length=128)
    token_expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    token_used_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    fields: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    evidence_document_id: uuid.UUID | None = Field(
        default=None, foreign_key="document.id"
    )
    confirmed_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    expires_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    revoked: bool = Field(default=False)


class Confirmation(ConfirmationBase, table=True):
    __tablename__ = "confirmation"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    requested_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, default=get_datetime_utc
        ),
    )


# ==========================================
# 6. Obligation
# ==========================================
class ObligationBase(SQLModel):
    instrument_id: uuid.UUID = Field(foreign_key="instrument.id", index=True)
    kind: str = Field(
        max_length=50
    )  # confirmation_due | maturity | renewal_due | release_clearance
    due_date: date = Field(sa_column=Column(Date, nullable=False))
    status: str = Field(default="open", max_length=20)  # open | done | waived
    owner_role: str = Field(max_length=50)  # institution | regional | bureau


class Obligation(ObligationBase, table=True):
    __tablename__ = "obligation"
    __table_args__ = (
        UniqueConstraint(
            "instrument_id",
            "kind",
            "due_date",
            name="uq_obligation_instrument_kind_due_date",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)


# ==========================================
# 7. Notice
# ==========================================
class NoticeBase(SQLModel):
    instrument_id: uuid.UUID = Field(foreign_key="instrument.id", index=True)
    obligation_id: uuid.UUID = Field(foreign_key="obligation.id", index=True)
    step: str = Field(max_length=50)
    channel: str = Field(default="email", max_length=30)
    delivered: bool = Field(default=False)


class Notice(NoticeBase, table=True):
    __tablename__ = "notice"
    __table_args__ = (
        UniqueConstraint("obligation_id", "step", name="uq_notice_obligation_step"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    sent_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, default=get_datetime_utc
        ),
    )


# ==========================================
# 8. Case Note
# ==========================================
class CaseNoteBase(SQLModel):
    instrument_id: uuid.UUID = Field(foreign_key="instrument.id", index=True)
    author_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    body: str


class CaseNote(CaseNoteBase, table=True):
    __tablename__ = "case_note"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, default=get_datetime_utc
        ),
    )


# ==========================================
# 9. Flag Waiver
# ==========================================
class FlagWaiverBase(SQLModel):
    instrument_id: uuid.UUID = Field(foreign_key="instrument.id", index=True)
    code: str = Field(max_length=50)
    reason: str
    waived_by: uuid.UUID = Field(foreign_key="user.id")


class FlagWaiver(FlagWaiverBase, table=True):
    __tablename__ = "flag_waiver"
    __table_args__ = (
        UniqueConstraint(
            "instrument_id", "code", name="uq_flag_waiver_instrument_code"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, default=get_datetime_utc
        ),
    )


# ==========================================
# 10. Release Request
# ==========================================
class ReleaseRequestBase(SQLModel):
    instrument_id: uuid.UUID = Field(foreign_key="instrument.id", index=True)
    path: str = Field(max_length=50)  # term_completion | closure | merger | conversion
    checklist: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSONB, nullable=False, server_default="[]"),
    )
    status: str = Field(
        default="draft", max_length=30
    )  # draft | submitted | verified | approved | rejected | released
    requested_by: uuid.UUID = Field(foreign_key="user.id")
    verified_by: uuid.UUID | None = Field(default=None, foreign_key="user.id")
    approved_by: uuid.UUID | None = Field(default=None, foreign_key="user.id")
    receipt_token: str | None = Field(default=None, max_length=1000)


class ReleaseRequest(ReleaseRequestBase, table=True):
    __tablename__ = "release_request"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, default=get_datetime_utc
        ),
    )
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, default=get_datetime_utc
        ),
    )


# ==========================================
# 11. Audit Event & Checkpoint
# ==========================================
class AuditEvent(SQLModel, table=True):
    __tablename__ = "audit_event"

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    ts: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    actor_id: uuid.UUID | None = Field(default=None, index=True)
    action: str = Field(max_length=100)
    entity: str = Field(max_length=100)
    entity_id: str = Field(max_length=100)
    payload: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default="'{}'"),
    )
    prev_hash: str = Field(max_length=64)
    hash: str = Field(unique=True, index=True, max_length=64)


class AuditCheckpoint(SQLModel, table=True):
    __tablename__ = "audit_checkpoint"

    id: int | None = Field(
        default=None, sa_column=Column(BigInteger, primary_key=True, autoincrement=True)
    )
    up_to_id: int = Field(sa_column=Column(BigInteger, nullable=False))
    head_hash: str = Field(max_length=64)
    signature: str = Field(max_length=1000)
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, default=get_datetime_utc
        ),
    )


# ==========================================
# 12. Rate Limit & Generic Messages
# ==========================================
class RateLimitBucket(SQLModel, table=True):
    __tablename__ = "rate_limit_bucket"

    key: str = Field(primary_key=True, max_length=255)
    count: int = Field(default=1)
    reset_at: datetime = Field(sa_column_kwargs={"index": True})


class Message(SQLModel):
    message: str


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
