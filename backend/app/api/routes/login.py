from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import SQLModel

from app import crud
from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
from app.core import security
from app.core.config import settings
from app.core.rate_limit import enforce_rate_limit, get_client_ip
from app.models import Message, NewPassword, Token, UserPublic, UserUpdate
from app.utils import (
    generate_password_reset_token,
    generate_reset_password_email,
    send_email,
    verify_password_reset_token,
)

router = APIRouter(tags=["login"])


@router.post("/login/access-token")
def login_access_token(
    session: SessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    request: Request,
) -> Token:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    client_ip = get_client_ip(request)
    limit_ip = 100 if settings.FASTAPI_ENV == "development" else 10
    limit_account = 50 if settings.FASTAPI_ENV == "development" else 5
    enforce_rate_limit(
        request,
        session,
        f"login:ip:{client_ip}",
        max_requests=limit_ip,
        window_seconds=60,
    )
    enforce_rate_limit(
        request,
        session,
        f"login:account:{form_data.username.lower()}",
        max_requests=limit_account,
        window_seconds=60,
    )

    user = crud.authenticate(
        session=session, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return Token(
        access_token=security.create_access_token(
            user.id, expires_delta=access_token_expires
        )
    )


@router.post("/login/test-token", response_model=UserPublic)
def test_token(current_user: CurrentUser) -> Any:
    """
    Test access token
    """
    return current_user


@router.post("/password-recovery/{email}")
def recover_password(email: str, session: SessionDep, request: Request) -> Message:
    """
    Password Recovery
    """
    client_ip = get_client_ip(request)
    limit_ip = 100 if settings.FASTAPI_ENV == "development" else 10
    limit_account = 50 if settings.FASTAPI_ENV == "development" else 5
    enforce_rate_limit(
        request,
        session,
        f"recover:ip:{client_ip}",
        max_requests=limit_ip,
        window_seconds=60,
    )
    enforce_rate_limit(
        request,
        session,
        f"recover:account:{email.lower()}",
        max_requests=limit_account,
        window_seconds=60,
    )

    user = crud.get_user_by_email(session=session, email=email)

    # Always return the same response to prevent email enumeration attacks
    # Only send email if user actually exists
    if user:
        password_reset_token = generate_password_reset_token(email=email)
        email_data = generate_reset_password_email(
            email_to=user.email, email=email, token=password_reset_token
        )
        send_email(
            email_to=user.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return Message(
        message="If that email is registered, we sent a password recovery link"
    )


@router.post("/reset-password/")
def reset_password(session: SessionDep, body: NewPassword, request: Request) -> Message:
    """
    Reset password
    """
    client_ip = get_client_ip(request)
    limit_ip = 100 if settings.FASTAPI_ENV == "development" else 10
    enforce_rate_limit(
        request,
        session,
        f"reset:ip:{client_ip}",
        max_requests=limit_ip,
        window_seconds=60,
    )

    email = verify_password_reset_token(token=body.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")
    user = crud.get_user_by_email(session=session, email=email)
    if not user:
        # Don't reveal that the user doesn't exist - use same error as invalid token
        raise HTTPException(status_code=400, detail="Invalid token")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    user_in_update = UserUpdate(password=body.new_password)
    crud.update_user(
        session=session,
        db_user=user,
        user_in=user_in_update,
    )
    return Message(message="Password updated successfully")


@router.post(
    "/password-recovery-html-content/{email}",
    dependencies=[Depends(get_current_active_superuser)],
    response_class=HTMLResponse,
)
def recover_password_html_content(email: str, session: SessionDep) -> Any:
    """
    HTML Content for Password Recovery
    """
    user = crud.get_user_by_email(session=session, email=email)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system.",
        )
    password_reset_token = generate_password_reset_token(email=email)
    email_data = generate_reset_password_email(
        email_to=user.email, email=email, token=password_reset_token
    )

    return HTMLResponse(
        content=email_data.html_content, headers={"subject:": email_data.subject}
    )


class DemoPersona(SQLModel):
    role: str
    name: str
    email: str
    badge: str
    color: str
    password: str


class DemoLoginRequest(SQLModel):
    email: str


@router.get("/login/demo-personas", response_model=list[DemoPersona])
def get_demo_personas() -> Any:
    """
    Returns pre-configured demo personas for evaluation.
    Only available in development / demo mode. Blocked outside development/demo.
    """
    if settings.FASTAPI_ENV not in ("development", "demo"):
        raise HTTPException(
            status_code=404, detail="Demo personas disabled outside development/demo"
        )

    return [
        DemoPersona(
            role="Institution",
            name="North Tech Inst.",
            email="inst.north1@example.com",
            badge="Maker",
            color="bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30",
            password=settings.FIRST_SUPERUSER_PASSWORD,
        ),
        DemoPersona(
            role="RO Maker",
            name="Officer North",
            email="officer.north@example.com",
            badge="Regional",
            color="bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/30",
            password=settings.FIRST_SUPERUSER_PASSWORD,
        ),
        DemoPersona(
            role="RO Checker",
            name="Checker North",
            email="checker.north@example.com",
            badge="Checker",
            color="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30",
            password=settings.FIRST_SUPERUSER_PASSWORD,
        ),
        DemoPersona(
            role="Bureau Head",
            name="Central Bureau",
            email="bureau@example.com",
            badge="Admin",
            color="bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30",
            password=settings.FIRST_SUPERUSER_PASSWORD,
        ),
        DemoPersona(
            role="Auditor",
            name="Reg. Auditor",
            email="auditor@example.com",
            badge="Read-Only",
            color="bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/30",
            password=settings.FIRST_SUPERUSER_PASSWORD,
        ),
    ]


@router.post("/login/demo", response_model=Token)
def demo_login(
    data: DemoLoginRequest,
    session: SessionDep,
) -> Token:
    """
    1-Click Demo Login for turnkey evaluation.
    Only available in development / demo mode. Blocked outside development/demo.
    """
    if settings.FASTAPI_ENV not in ("development", "demo"):
        raise HTTPException(
            status_code=404, detail="Demo login disabled outside development/demo"
        )
    user = crud.get_user_by_email(session=session, email=data.email)
    if not user:
        from app.core.db import init_db
        init_db(session)
        user = crud.get_user_by_email(session=session, email=data.email)
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="Invalid demo persona")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return Token(
        access_token=security.create_access_token(
            user.id, expires_delta=access_token_expires
        )
    )

