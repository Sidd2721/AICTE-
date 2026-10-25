import hashlib
import uuid
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.core.audit import audit
from app.domain.vault import (
    detect_dsc,
    read_from_vault,
    sniff_magic_bytes,
    store_in_vault,
)
from app.models import Document, DocumentPublic, Institution, Instrument

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentPublic)
async def upload_document(
    session: SessionDep,
    current_user: CurrentUser,
    file: UploadFile = File(...),
    kind: str = Form("fdr_scan"),
    instrument_id: uuid.UUID | None = Form(None),
) -> Any:
    data = await file.read()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    try:
        mime = sniff_magic_bytes(data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    sha = hashlib.sha256(data).hexdigest()
    has_dsc = detect_dsc(data, mime)
    storage_key = uuid.uuid4().hex
    store_in_vault(storage_key, data)

    # Determine instrument_id if not explicitly provided
    inst: Instrument | None = None
    if instrument_id:
        inst = session.get(Instrument, instrument_id)
        if not inst:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Instrument {instrument_id} not found",
            )
    else:
        # Determine institution for the user
        inst_id = current_user.institution_id
        if not inst_id:
            institution = session.exec(select(Institution)).first()
            if not institution:
                institution = Institution(
                    permanent_id=f"1-{uuid.uuid4().hex[:8].upper()}",
                    name="Default Institution",
                    region="North",
                    is_government=False,
                    leased_private=False,
                )

                session.add(institution)
                session.commit()
                session.refresh(institution)
            inst_id = institution.id

        institution_obj = session.get(Institution, inst_id)
        region = institution_obj.region if institution_obj else "North"

        # Create provisional instrument
        inst = Instrument(
            institution_id=inst_id,
            region=region,
            kind="FDR",
            ref_no=f"PROV-{uuid.uuid4().hex[:8].upper()}",
            bank_code="PROV",
            ifsc="PROV0001234",
            amount_paise=10000000,
            issue_date=date.today(),
            maturity_date=date.today() + timedelta(days=3650),
            lifecycle="pending",
            created_by=current_user.id,
        )
        session.add(inst)
        session.commit()
        session.refresh(inst)

    # Calculate version
    existing_count = len(
        session.exec(
            select(Document).where(
                Document.instrument_id == inst.id,
                Document.kind == kind,
            )
        ).all()
    )
    version = existing_count + 1

    doc = Document(
        instrument_id=inst.id,
        kind=kind,
        version=version,
        filename=file.filename or f"{kind}_{version}.bin",
        mime=mime,
        size_bytes=len(data),
        sha256=sha,
        storage_key=storage_key,
        uploaded_by=current_user.id,
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)

    audit(
        session=session,
        actor_id=current_user.id,
        action="document_uploaded",
        entity="document",
        entity_id=str(doc.id),
        payload={
            "document_id": str(doc.id),
            "instrument_id": str(inst.id),
            "kind": kind,
            "version": version,
            "sha256": sha,
            "size_bytes": len(data),
            "is_signed_dsc": has_dsc,
        },
    )

    return DocumentPublic(
        id=doc.id,
        instrument_id=doc.instrument_id,
        kind=doc.kind,
        version=doc.version,
        filename=doc.filename,
        mime=doc.mime,
        size_bytes=doc.size_bytes,
        sha256=doc.sha256,
        storage_key=doc.storage_key,
        uploaded_by=doc.uploaded_by,
        uploaded_at=doc.uploaded_at,
        is_signed_dsc=has_dsc,
    )


@router.get("/{document_id}")
def download_document(
    document_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    doc = session.get(Document, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Check permission
    inst = session.get(Instrument, doc.instrument_id)
    if not current_user.is_superuser and current_user.role not in (
        "bureau",
        "auditor",
        "regional",
    ):
        if (
            current_user.institution_id
            and inst
            and inst.institution_id != current_user.institution_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not permitted to access this document",
            )

    try:
        content = read_from_vault(doc.storage_key)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vault file not found on disk",
        ) from e

    return Response(
        content=content,
        media_type=doc.mime,
        headers={"Content-Disposition": f'inline; filename="{doc.filename}"'},
    )
