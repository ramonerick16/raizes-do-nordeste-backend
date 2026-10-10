import os, base64, hashlib, hmac, secrets
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.domain.models import Usuario

def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260000)
    return "pbkdf2_sha256$260000$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()

def check_password(password, stored):
    try:
        _, n, salt, digest = stored.split("$")
        chk = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt), int(n))
        return hmac.compare_digest(chk, base64.b64decode(digest))
    except (ValueError, TypeError): return False

def issue_token(user):
    secret = os.getenv("JWT_SECRET", "CHAVE-APENAS-DESENVOLVIMENTO-ALTERE")
    return jwt.encode({"sub":str(user.id),"exp":datetime.now(timezone.utc)+timedelta(minutes=int(os.getenv("TOKEN_MINUTES", "120")))}, secret, algorithm="HS256")

bearer = HTTPBearer(auto_error=False)
def current_user(credentials: HTTPAuthorizationCredentials | None=Depends(bearer), db:Session=Depends(get_db)):
    if credentials is None:
        raise HTTPException(401, detail="Token de autenticação necessário", headers={"WWW-Authenticate":"Bearer"})
    try:
        payload=jwt.decode(credentials.credentials,os.getenv("JWT_SECRET", "CHAVE-APENAS-DESENVOLVIMENTO-ALTERE"),algorithms=["HS256"])
        user=db.get(Usuario,int(payload["sub"]))
        if not user: raise ValueError()
        return user
    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise HTTPException(401,detail="Token inválido ou expirado")

def allowed(*roles):
    def check(user:Usuario=Depends(current_user)):
        if user.perfil not in roles: raise HTTPException(403,detail="Operação não permitida para este perfil")
        return user
    return check
