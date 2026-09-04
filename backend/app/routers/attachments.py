"""Evidence files attached to a case (and optionally a single message)."""

from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas, storage
from ..audit import record
from ..config import settings
from ..database import get_db
from ..security import current_user

router = APIRouter(tags=["attachments"])


def _out(a: models.Attachment) -> schemas.AttachmentOut:
    data = schemas.AttachmentOut.model_validate(a).model_dump()
    data["uploaded_by"] = a.uploaded_by.username if a.uploaded_by else None
    return schemas.AttachmentOut(**data)


@router.get("/api/cases/{case_id}/attachments", response_model=list[schemas.AttachmentOut])
def list_attachments(case_id: int, db: Session = Depends(get_db)):
    if db.get(models.Case, case_id) is None:
        raise HTTPException(status_code=404, detail="Case not found")
    rows = db.scalars(
        select(models.Attachment)
        .where(models.Attachment.case_id == case_id)
        .order_by(models.Attachment.created_at.desc())
    ).all()
    return [_out(a) for a in rows]


@router.post(
    "/api/cases/{case_id}/attachments",
    response_model=schemas.AttachmentOut,
    status_code=201,
)
async def upload_attachment(
    case_id: int,
    request: Request,
    file: UploadFile,
    tlp: str = Form(default="AMBER"),
    interaction_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
    user: models.User | None = Depends(current_user),
):
    if db.get(models.Case, case_id) is None:
        raise HTTPException(status_code=404, detail="Case not found")

    data = await file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"file exceeds {settings.max_upload_mb} MB")
    if not data:
        raise HTTPException(status_code=422, detail="empty file")
    if interaction_id is not None:
        it = db.get(models.Interaction, interaction_id)
        if it is None or it.case_id != case_id:
            raise HTTPException(status_code=404, detail="interaction_id not on this case")

    key, digest, size = storage.save(data)
    att = models.Attachment(
        case_id=case_id,
        interaction_id=interaction_id,
        filename=file.filename or "file",
        content_type=file.content_type or "application/octet-stream",
        size=size,
        sha256=digest,
        tlp=tlp,
        storage_key=key,
        uploaded_by_id=user.id if user else None,
    )
    db.add(att)
    record(
        db, request, action="update", entity_type="case", entity_id=case_id,
        summary=f"attached {att.filename}",
    )
    db.commit()
    db.refresh(att)
    return _out(att)


@router.get("/api/attachments/{att_id}")
def download_attachment(att_id: int, db: Session = Depends(get_db)):
    att = db.get(models.Attachment, att_id)
    if att is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    try:
        data = storage.load(att.storage_key)
    except FileNotFoundError:
        raise HTTPException(status_code=410, detail="file is gone from storage")
    return Response(
        content=data,
        media_type=att.content_type,
        headers={"Content-Disposition": f'attachment; filename="{att.filename}"'},
    )


@router.delete("/api/attachments/{att_id}", status_code=204)
def delete_attachment(att_id: int, request: Request, db: Session = Depends(get_db)):
    att = db.get(models.Attachment, att_id)
    if att is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    storage.delete(att.storage_key)
    record(
        db, request, action="update", entity_type="case", entity_id=att.case_id,
        summary=f"removed attachment {att.filename}",
    )
    db.delete(att)
    db.commit()
