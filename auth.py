import json, uuid
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Header
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from config import settings
from db import get_db
from models import User, UserRole, Role

pwd = CryptContext(schemes=['bcrypt'], deprecated='auto')

def make_token(user_id: uuid.UUID):
    exp = datetime.now(timezone.utc)+timedelta(minutes=settings.jwt_exp_minutes)
    return jwt.encode({'sub':str(user_id),'exp':exp}, settings.jwt_secret, algorithm='HS256')

def verify_token(token: str):
    try: return jwt.decode(token, settings.jwt_secret, algorithms=['HS256'])
    except JWTError: raise HTTPException(401,'Jeton invalide ou expiré')

def current_user(authorization: str|None=Header(None), db: Session=Depends(get_db)):
    if not authorization or not authorization.startswith('Bearer '): raise HTTPException(401,'Authentification requise')
    data=verify_token(authorization[7:]); user=db.get(User,uuid.UUID(data['sub']))
    if not user or not user.active: raise HTTPException(401,'Compte inactif ou introuvable')
    return user

def roles_for(user, db):
    return [r.name for r in db.query(Role).join(UserRole,Role.id==UserRole.role_id).filter(UserRole.user_id==user.id).all()]

def require_roles(*allowed):
    def dep(user=Depends(current_user), db: Session=Depends(get_db)):
        roles=roles_for(user,db)
        if not any(r in allowed for r in roles): raise HTTPException(403,'Permission insuffisante')
        return user
    return dep

def verify_firebase_token(id_token: str):
    if not settings.firebase_credentials_json: raise HTTPException(503,'Firebase Admin non configuré')
    import firebase_admin
    from firebase_admin import auth, credentials
    if not firebase_admin._apps:
        cred=credentials.Certificate(json.loads(settings.firebase_credentials_json))
        firebase_admin.initialize_app(cred)
    try: return auth.verify_id_token(id_token)
    except Exception: raise HTTPException(401,'Jeton Firebase invalide')
