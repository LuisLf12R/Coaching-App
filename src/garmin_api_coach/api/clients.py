from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from garmin_api_coach.api.coaches import get_or_create_coach
from garmin_api_coach.api.schemas import ClientCreate, ClientRead
from garmin_api_coach.auth.dependencies import get_current_coach
from garmin_api_coach.auth.schemas import AuthenticatedCoach
from garmin_api_coach.db.models import Client
from garmin_api_coach.db.session import get_db_session

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientRead])
def list_clients(
    current_coach: AuthenticatedCoach = Depends(get_current_coach),
    db: Session = Depends(get_db_session),
) -> list[Client]:
    coach = get_or_create_coach(db, current_coach)
    return list(db.scalars(select(Client).where(Client.coach_id == coach.id).order_by(Client.created_at)))


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientCreate,
    current_coach: AuthenticatedCoach = Depends(get_current_coach),
    db: Session = Depends(get_db_session),
) -> Client:
    coach = get_or_create_coach(db, current_coach)
    client = Client(
        coach_id=coach.id,
        display_name=payload.display_name,
        sport_focus=payload.sport_focus,
        goals=payload.goals,
        injury_notes=payload.injury_notes,
        training_constraints=payload.training_constraints,
        coach_notes=payload.coach_notes,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client
