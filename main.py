import uuid
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from passlib.context import CryptContext
from config import settings
from db import Base, engine, get_db
from models import *
from schemas import *
from auth import *
from storage import safe_key, presigned_put, presigned_get, delete as r2_delete

app = FastAPI(
    title=settings.app_name,
    version='1.0.0',
    docs_url='/docs' if settings.environment != 'production' else '/docs'
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in settings.cors_origins.split(',')],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

@app.on_event('startup')
def startup():
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        names = ['member', 'registration_agent', 'group_leader', 'church_leader', 'regional_admin', 'national_admin', 'super_admin']
        existing = {r.name for r in db.query(Role).all()}
        for n in names:
            if n not in existing:
                db.add(Role(name=n))
        db.commit()

@app.get('/health')
def health():
    return {'service': 'ELIM API', 'status': 'ok', 'version': '1.0.0'}

@app.get('/api/v1/storage/upload-url')
def storage_upload_url(filename: str, content_type: str, prefix: str = 'media', user=Depends(current_user)):
    key = safe_key(prefix, filename)
    return {'key': key, 'upload_url': presigned_put(key, content_type), 'expires_in': settings.r2_presign_expiry_seconds, 'public_url': (settings.r2_public_base_url.rstrip('/') + '/' + key) if settings.r2_public_base_url else None}

@app.get('/api/v1/storage/download-url')
def storage_download_url(key: str = Query(...), user=Depends(current_user)):
    return {'key': key, 'url': presigned_get(key), 'expires_in': settings.r2_presign_expiry_seconds}

@app.delete('/api/v1/storage/object')
def storage_delete(key: str = Query(...), user=Depends(require_roles('super_admin', 'national_admin')), db: Session = Depends(get_db)):
    r2_delete(key)
    db.add(AuditLog(actor_user_id=user.id, action='delete_storage_object', target_type='storage', target_id=key))
    db.commit()
    return {'deleted': True, 'key': key}

@app.get('/api/v1/config/public')
def public_config(db: Session = Depends(get_db)):
    rows = db.query(AppSetting).all()
    return {r.key: r.value for r in rows}

@app.put('/api/v1/admin/config')
def update_config(data: dict, user=Depends(require_roles('super_admin')), db: Session = Depends(get_db)):
    allowed = {'app_name', 'slogan', 'logo_url', 'favicon_url', 'welcome_image_url', 'primary_color', 'secondary_color', 'default_language', 'country', 'support_phone', 'support_email'}
    for key, value in data.items():
        if key not in allowed:
            continue
        row = db.query(AppSetting).filter_by(key=key).first()
        if not row:
            row = AppSetting(key=key, value=str(value))
            db.add(row)
        else:
            row.value = str(value)
    db.add(AuditLog(actor_user_id=user.id, action='update_app_config', target_type='settings'))
    db.commit()
    return {'ok': True}

@app.post('/api/v1/auth/firebase')
def firebase_login(data: FirebaseLogin, db: Session = Depends(get_db)):
    claims = verify_firebase_token(data.id_token)
    uid = claims['uid']
    user = db.query(User).filter_by(firebase_uid=uid).first()
    if not user:
        user = User(firebase_uid=uid, email=claims.get('email'), phone=claims.get('phone'))
        db.add(user)
        db.flush()
        role = db.query(Role).filter_by(name='member').first()
        db.add(UserRole(user_id=user.id, role_id=role.id))
        db.commit()
        db.refresh(user)
    return {'access_token': make_token(user.id), 'token_type': 'bearer', 'user_id': str(user.id), 'roles': roles_for(user, db)}

@app.post('/api/v1/auth/admin')
def admin_login(data: AdminLogin, db: Session = Depends(get_db)):
    if not settings.admin_email or data.email.lower() != settings.admin_email.lower() or not settings.admin_password or data.password != settings.admin_password:
        raise HTTPException(401, 'Identifiants administrateur invalides')
    user = db.query(User).filter_by(email=data.email.lower()).first()
    if not user:
        user = User(email=data.email.lower())
        db.add(user)
        db.flush()
        role = db.query(Role).filter_by(name='super_admin').first()
        db.add(UserRole(user_id=user.id, role_id=role.id))
        db.commit()
        db.refresh(user)
    return {'access_token': make_token(user.id), 'token_type': 'bearer', 'user_id': str(user.id), 'roles': roles_for(user, db)}

@app.get('/api/v1/me')
def me(user=Depends(current_user), db: Session = Depends(get_db)):
    return {'id': str(user.id), 'email': user.email, 'phone': user.phone, 'roles': roles_for(user, db)}

@app.get('/api/v1/roles')
def roles(user=Depends(require_roles('super_admin', 'national_admin')), db: Session = Depends(get_db)):
    return [{'id': str(r.id), 'name': r.name} for r in db.query(Role).order_by(Role.name).all()]

@app.get('/api/v1/churches')
def churches(db: Session = Depends(get_db)):
    return [{'id': str(c.id), 'name': c.name, 'country': c.country, 'city': c.city, 'active': c.active} for c in db.query(Church).filter_by(active=True).order_by(Church.name).all()]

@app.post('/api/v1/churches')
def create_church(data: ChurchIn, user=Depends(require_roles('super_admin', 'national_admin')), db: Session = Depends(get_db)):
    c = Church(**data.model_dump())
    db.add(c)
    db.add(AuditLog(actor_user_id=user.id, action='create_church', target_type='church'))
    db.commit()
    db.refresh(c)
    return {'id': str(c.id), 'name': c.name, 'country': c.country, 'city': c.city}

@app.get('/api/v1/members')
def members(q: str = '', church_id: uuid.UUID | None = None, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(Member, Church.name.label('church_name'), Church.country.label('country')).join(Church, Church.id == Member.church_id)
    if q:
        query = query.filter((Member.first_name.ilike(f'%{q}%')) | (Member.last_name.ilike(f'%{q}%')) | (Member.phone.ilike(f'%{q}%')))
    if church_id:
        query = query.filter(Member.church_id == church_id)
    rows = query.limit(min(limit, 500)).all()
    return [{'id': str(m.id), 'first_name': m.first_name, 'last_name': m.last_name, 'phone': m.phone, 'email': m.email, 'church_id': str(m.church_id), 'church_name': cn, 'country': country} for m, cn, country in rows]

@app.post('/api/v1/members')
def create_member(data: MemberIn, user=Depends(require_roles('super_admin', 'national_admin', 'regional_admin', 'church_leader', 'registration_agent')), db: Session = Depends(get_db)):
    if db.query(Member).filter((Member.phone == data.phone) & (Member.phone.is_not(None))).first():
        raise HTTPException(409, 'Un membre avec ce téléphone existe déjà')
    m = Member(**data.model_dump())
    db.add(m)
    db.add(AuditLog(actor_user_id=user.id, action='create_member', target_type='member'))
    db.commit()
    db.refresh(m)
    return {'id': str(m.id), 'status': m.status}

@app.post('/api/v1/groups')
def create_group(data: GroupIn, user=Depends(require_roles('super_admin', 'national_admin', 'regional_admin', 'church_leader', 'group_leader')), db: Session = Depends(get_db)):
    g = Group(**data.model_dump())
    db.add(g)
    db.add(AuditLog(actor_user_id=user.id, action='create_group', target_type='group'))
    db.commit()
    db.refresh(g)
    return {'id': str(g.id), 'name': g.name}

@app.get('/api/v1/groups')
def list_groups(church_id: uuid.UUID | None = None, db: Session = Depends(get_db)):
    q = db.query(Group).filter_by(active=True)
    if church_id:
        q = q.filter_by(church_id=church_id)
    return [{'id': str(g.id), 'church_id': str(g.church_id), 'name': g.name, 'description': g.description} for g in q.all()]

@app.post('/api/v1/media')
def create_media(data: MediaIn, user=Depends(current_user), db: Session = Depends(get_db)):
    m = MediaPost(author_user_id=user.id, **data.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    return {'id': str(m.id), 'status': m.status}

@app.get('/api/v1/media')
def list_media(status: str = 'published', church_id: uuid.UUID | None = None, db: Session = Depends(get_db)):
    q = db.query(MediaPost).filter(MediaPost.status == status)
    if church_id:
        q = q.filter(MediaPost.church_id == church_id)
    return [{'id': str(x.id), 'title': x.title, 'media_url': x.media_url, 'category': x.category, 'status': x.status, 'church_id': str(x.church_id) if x.church_id else None} for x in q.order_by(MediaPost.published_at.desc().nullslast()).limit(200).all()]

@app.post('/api/v1/media/{item_id}/moderate')
def moderate_media(item_id: uuid.UUID, data: Moderate, user=Depends(require_roles('super_admin', 'national_admin', 'regional_admin', 'church_leader')), db: Session = Depends(get_db)):
    m = db.get(MediaPost, item_id)
    if not m:
        raise HTTPException(404, 'Média introuvable')
    m.status = data.status
    if data.status == 'published':
        m.published_at = datetime.now(timezone.utc)
    db.add(AuditLog(actor_user_id=user.id, action='moderate_media', target_type='media', target_id=str(item_id)))
    db.commit()
    return {'status': m.status}

@app.post('/api/v1/news')
def create_news(data: NewsIn, user=Depends(current_user), db: Session = Depends(get_db)):
    n = News(author_user_id=user.id, **data.model_dump())
    db.add(n)
    db.commit()
    db.refresh(n)
    return {'id': str(n.id), 'status': n.status}

@app.get('/api/v1/news')
def list_news(church_id: uuid.UUID | None = None, db: Session = Depends(get_db)):
    q = db.query(News).filter(News.status == 'published')
    if church_id:
        q = q.filter(News.church_id == church_id)
    return [{'id': str(n.id), 'title': n.title, 'content': n.content, 'image_url': n.image_url, 'church_id': str(n.church_id) if n.church_id else None} for n in q.order_by(News.published_at.desc().nullslast()).limit(100).all()]

@app.post('/api/v1/news/{item_id}/moderate')
def moderate_news(item_id: uuid.UUID, data: Moderate, user=Depends(require_roles('super_admin', 'national_admin', 'regional_admin', 'church_leader')), db: Session = Depends(get_db)):
    n = db.get(News, item_id)
    if not n:
        raise HTTPException(404, 'Actualité introuvable')
    n.status = data.status
    if data.status == 'published':
        n.published_at = datetime.now(timezone.utc)
    db.add(AuditLog(actor_user_id=user.id, action='moderate_news', target_type='news', target_id=str(item_id)))
    db.commit()
    return {'status': n.status}

@app.post('/api/v1/events')
def create_event(data: EventIn, user=Depends(current_user), db: Session = Depends(get_db)):
    e = Event(author_user_id=user.id, **data.model_dump())
    db.add(e)
    db.commit()
    db.refresh(e)
    return {'id': str(e.id), 'status': e.status}

@app.get('/api/v1/events')
def list_events(church_id: uuid.UUID | None = None, db: Session = Depends(get_db)):
    q = db.query(Event).filter(Event.status == 'published')
    if church_id:
        q = q.filter(Event.church_id == church_id)
    return [{'id': str(e.id), 'title': e.title, 'description': e.description, 'location': e.location, 'starts_at': e.starts_at, 'ends_at': e.ends_at, 'church_id': str(e.church_id) if e.church_id else None} for e in q.order_by(Event.starts_at).limit(100).all()]

@app.post('/api/v1/events/{item_id}/moderate')
def moderate_event(item_id: uuid.UUID, data: Moderate, user=Depends(require_roles('super_admin', 'national_admin', 'regional_admin', 'church_leader')), db: Session = Depends(get_db)):
    e = db.get(Event, item_id)
    if not e:
        raise HTTPException(404, 'Événement introuvable')
    e.status = data.status
    db.add(AuditLog(actor_user_id=user.id, action='moderate_event', target_type='event', target_id=str(item_id)))
    db.commit()
    return {'status': e.status}

@app.post('/api/v1/conversations')
def create_conversation(data: ConversationIn, user=Depends(current_user), db: Session = Depends(get_db)):
    ids = set(data.user_ids) | {user.id}
    c = Conversation(type=data.type, title=data.title, created_by=user.id)
    db.add(c)
    db.flush()
    for uid in ids:
        db.add(ConversationMember(conversation_id=c.id, user_id=uid))
    db.commit()
    return {'id': str(c.id)}

@app.get('/api/v1/conversations')
def conversations(user=Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(Conversation).join(ConversationMember, Conversation.id == ConversationMember.conversation_id).filter(ConversationMember.user_id == user.id).all()
    return [{'id': str(c.id), 'type': c.type, 'title': c.title} for c in rows]

@app.post('/api/v1/conversations/{cid}/messages')
def send_message(cid: uuid.UUID, data: MessageIn, user=Depends(current_user), db: Session = Depends(get_db)):
    if not db.query(ConversationMember).filter_by(conversation_id=cid, user_id=user.id).first():
        raise HTTPException(403, 'Vous n’êtes pas membre de cette conversation')
    m = Message(conversation_id=cid, sender_user_id=user.id, **data.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    return {'id': str(m.id), 'created_at': m.created_at}

@app.get('/api/v1/conversations/{cid}/messages')
def messages(cid: uuid.UUID, user=Depends(current_user), db: Session = Depends(get_db)):
    if not db.query(ConversationMember).filter_by(conversation_id=cid, user_id=user.id).first():
        raise HTTPException(403, 'Accès refusé')
    return [{'id': str(m.id), 'sender_user_id': str(m.sender_user_id), 'message_type': m.message_type, 'body': m.body, 'attachment_url': m.attachment_url, 'created_at': m.created_at} for m in db.query(Message).filter_by(conversation_id=cid, deleted_at=None).order_by(Message.created_at).limit(500).all()]

@app.post('/api/v1/admin/notifications')
def admin_notification(data: NotificationIn, user=Depends(require_roles('super_admin', 'national_admin', 'regional_admin', 'church_leader')), db: Session = Depends(get_db)):
    targets = []
    if data.recipient_user_id:
        targets = [data.recipient_user_id]
    elif data.scope_type == 'all':
        targets = [x.id for x in db.query(User).filter_by(active=True).all()]
    elif data.scope_type == 'church':
        targets = [x.user_id for x in db.query(Member).filter(Member.church_id == data.scope_id, Member.user_id.is_not(None)).all()]
    elif data.scope_type == 'group':
        members = db.query(GroupMember).filter_by(group_id=data.scope_id).all()
        mids = [x.member_id for x in members]
        targets = [x.user_id for x in db.query(Member).filter(Member.id.in_(mids), Member.user_id.is_not(None)).all()]
    else:
        raise HTTPException(400, 'scope_type invalide')
    for uid in targets:
        db.add(Notification(recipient_user_id=uid, scope_type=data.scope_type, scope_id=data.scope_id, title=data.title, body=data.body, kind=data.kind, data=data.data))
    db.add(AuditLog(actor_user_id=user.id, action='send_notification', target_type='notification', metadata_json={'count': len(targets)}))
    db.commit()
    return {'sent': len(targets)}

@app.get('/api/v1/notifications')
def notifications(user=Depends(current_user), db: Session = Depends(get_db)):
    return [{'id': str(n.id), 'title': n.title, 'body': n.body, 'kind': n.kind, 'data': n.data} for n in db.query(Notification).filter_by(recipient_user_id=user.id, active=True).order_by(Notification.id.desc()).limit(100).all()]

@app.get('/api/v1/admin/audit')
def audit(user=Depends(require_roles('super_admin', 'national_admin')), db: Session = Depends(get_db)):
    return [{'id': x.id, 'actor_user_id': str(x.actor_user_id) if x.actor_user_id else None, 'action': x.action, 'target_type': x.target_type, 'target_id': x.target_id, 'created_at': x.created_at} for x in db.query(AuditLog).order_by(AuditLog.id.desc()).limit(500).all()]

class WSManager:
    def __init__(self):
        self.connections = {}
    async def connect(self, uid, ws):
        await ws.accept()
        self.connections.setdefault(uid, []).append(ws)
    def disconnect(self, uid, ws):
        self.connections.get(uid, []).remove(ws)
    async def send(self, uid, data):
        for ws in list(self.connections.get(uid, [])):
            try:
                await ws.send_json(data)
            except:
                pass

manager = WSManager()

@app.websocket('/ws/{user_id}')
async def websocket_endpoint(ws: WebSocket, user_id: uuid.UUID, token: str):
    data = verify_token(token)
    if data.get('sub') != str(user_id):
        await ws.close(code=1008)
        return
    await manager.connect(user_id, ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id, ws)
