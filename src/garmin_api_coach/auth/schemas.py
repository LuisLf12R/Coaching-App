from pydantic import BaseModel


class AuthenticatedCoach(BaseModel):
    coach_id: str
    email: str
    display_name: str
    auth_provider: str
