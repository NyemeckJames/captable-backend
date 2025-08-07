from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, EmailStr
from app.infrastructure.api.auth.jwt_handler import authenticate_user, create_access_token
from app.infrastructure.config.settings import get_settings
from app.infrastructure.api.dependencies import get_audit_service
from app.application.services.audit_service import AuditService
from app.domain.entities.audit_event import AuditActionType, AuditEntityType

router = APIRouter(prefix="/api", tags=["Auth"])
settings = get_settings()

class LoginRequest(BaseModel):
    email: EmailStr = Field(..., example="admin@captable.com")
    password: str = Field(..., example="admin123")

class Token(BaseModel):
    access_token: str
    token_type: str
    user_info: dict





@router.post(
    "/token/",
    response_model=Token,
    summary="Authentification utilisateur",
    description="Retourne un token JWT d'accès après authentification de l'utilisateur (admin ou actionnaire).",
    tags=["Auth"],
    responses={
        200: {
            "description": "Token JWT retourné avec succès",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "user_info": {
                            "id": 1,
                            "username": "admin@captable.com",
                            "role": "admin",
                            "name": "Admin User"
                        }
                    }
                }
            }
        },
        401: {"description": "Identifiants incorrects ou non autorisé"},
        422: {"description": "Erreur de validation des données"}
    }
)
async def login_for_access_token(
    payload: LoginRequest,
    request: Request,
    audit_service: AuditService = Depends(get_audit_service)
):
    """
    Authenticates a user and returns a JWT access token.

    - **email**: User's email
    - **password**: User's password

    Use the returned token in the header: `Authorization: Bearer <token>` for protected endpoints.
    """
    user = await authenticate_user(payload.email, payload.password)
    print(f"Authenticated user: {user}")  # Debugging line to check user authentication
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )

    # Audit log
    try:
        ip_address = request.client.host if request.client else ""
        user_agent = request.headers.get("user-agent", "")
        await audit_service.log_event(
            action_type=AuditActionType.USER_LOGIN,
            user_id=user["id"],
            target_entity_type=AuditEntityType.USER,
            target_entity_id=user["id"],
            event_metadata={"email": user["username"]},
            ip_address=ip_address,
            user_agent=user_agent
        )
    except Exception as e:
        print(f"Audit log failed: {e}")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_info": {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "name": user["name"]
        }
    }
