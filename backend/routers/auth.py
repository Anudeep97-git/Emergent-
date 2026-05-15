"""Auth router — login / logout / refresh / register. All routes nested under /api."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Request, Depends

from models.schemas import LoginRequest, LoginResponse, RegisterRequest, RefreshRequest
from services.auth_service import (
    hash_password, verify_password, create_access_token,
    create_refresh_token, decode_token, get_current_user,
)
from services.db import users
from services.audit import log

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, request: Request):
    user = await users.find_one({"email": req.email.lower()}, {"_id": 0})
    if not user or not verify_password(req.password, user["password_hash"]):
        await log(None, req.email, "/api/auth/login", "POST", 401,
                  request.client.host if request.client else "0.0.0.0", {})
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user["user_id"], user["email"], user["role"])
    refresh = create_refresh_token(user["user_id"], user["email"], user["role"])
    await users.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}},
    )
    await log(user["user_id"], user["email"], "/api/auth/login", "POST", 200,
              request.client.host if request.client else "0.0.0.0", {})
    return LoginResponse(
        token=token,
        refresh_token=refresh,
        role=user["role"],
        user_id=user["user_id"],
        is_existing_customer=bool(user.get("is_existing_customer", False)),
        email=user["email"],
        full_name=user.get("full_name"),
    )


@router.post("/register", response_model=LoginResponse)
async def register(req: RegisterRequest, request: Request):
    existing = await users.find_one({"email": req.email.lower()}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    user_id = str(uuid.uuid4())
    doc = {
        "user_id": user_id,
        "email": req.email.lower(),
        "password_hash": hash_password(req.password),
        "role": req.role,
        "full_name": req.full_name,
        "is_existing_customer": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_login": None,
    }
    await users.insert_one(doc)
    token = create_access_token(user_id, doc["email"], doc["role"])
    refresh = create_refresh_token(user_id, doc["email"], doc["role"])
    await log(user_id, doc["email"], "/api/auth/register", "POST", 200,
              request.client.host if request.client else "0.0.0.0", {})
    return LoginResponse(
        token=token, refresh_token=refresh, role=doc["role"],
        user_id=user_id, is_existing_customer=False,
        email=doc["email"], full_name=doc["full_name"],
    )


@router.post("/refresh")
async def refresh(req: RefreshRequest):
    payload = decode_token(req.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Not a refresh token")
    token = create_access_token(payload["user_id"], payload["email"], payload["role"])
    return {"token": token}


@router.post("/logout")
async def logout(user=Depends(get_current_user)):
    # stateless JWT: clients should discard the token; we just log it.
    await log(user["user_id"], user["email"], "/api/auth/logout", "POST", 200, "0.0.0.0", {})
    return {"status": "ok"}


@router.get("/me")
async def me(user=Depends(get_current_user)):
    u = await users.find_one({"user_id": user["user_id"]}, {"_id": 0, "password_hash": 0})
    return u or {}
