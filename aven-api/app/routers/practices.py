import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import audit
from app.db import get_db
from app.deps import get_current_user, require_role
from app.models import Practice, Role, User
from app.schemas import PracticeIn, PracticeOut

router = APIRouter(prefix="/practices", tags=["practices"])


@router.get("", response_model=list[PracticeOut])
def list_practices(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Practice]:
    # No org filter needed here: the tenancy layer adds it to every query.
    return list(db.execute(select(Practice).order_by(Practice.name)).scalars())


@router.get("/{practice_id}", response_model=PracticeOut)
def get_practice(
    practice_id: uuid.UUID,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Practice:
    practice = db.execute(select(Practice).where(Practice.id == practice_id)).scalar_one_or_none()
    if practice is None:  # same answer whether it does not exist or belongs to another org
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Practice not found")
    return practice


@router.post("", response_model=PracticeOut, status_code=status.HTTP_201_CREATED)
def create_practice(
    body: PracticeIn,
    user: User = Depends(require_role(Role.manager)),
    db: Session = Depends(get_db),
) -> Practice:
    practice = Practice(id=uuid.uuid4(), org_id=user.org_id, name=body.name, specialty=body.specialty)
    db.add(practice)
    audit.record(db, user, "practice.created", "practice", practice.id)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "A practice with this name already exists") from None
    return practice
