import uuid
from datetime import datetime, date
from sqlalchemy import String, Text, Boolean, Date, DateTime, ForeignKey, UniqueConstraint, JSON, func
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

class User(Base):
    __tablename__='users'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    firebase_uid: Mapped[str|None] = mapped_column(String(180), unique=True, nullable=True)
    email: Mapped[str|None] = mapped_column(String(255), unique=True, nullable=True)
    phone: Mapped[str|None] = mapped_column(String(32), unique=True, nullable=True)
    password_hash: Mapped[str|None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Church(Base):
    __tablename__='churches'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160))
    country: Mapped[str] = mapped_column(String(80))
    city: Mapped[str|None] = mapped_column(String(120))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Member(Base):
    __tablename__='members'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID|None] = mapped_column(ForeignKey('users.id'), unique=True, nullable=True)
    church_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('churches.id'))
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str|None] = mapped_column(String(32), unique=True, nullable=True)
    email: Mapped[str|None] = mapped_column(String(255), unique=True, nullable=True)
    birth_date: Mapped[date|None] = mapped_column(Date, nullable=True)
    photo_url: Mapped[str|None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default='active')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Role(Base):
    __tablename__='roles'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(80), unique=True)

class UserRole(Base):
    __tablename__='user_roles'
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True)

class Group(Base):
    __tablename__='groups'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    church_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('churches.id'))
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str|None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class GroupMember(Base):
    __tablename__='group_members'
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('groups.id', ondelete='CASCADE'), primary_key=True)
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('members.id', ondelete='CASCADE'), primary_key=True)
    role_label: Mapped[str|None] = mapped_column(String(120), nullable=True)

class Position(Base):
    __tablename__='positions'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True)

class MemberPosition(Base):
    __tablename__='member_positions'
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('members.id', ondelete='CASCADE'), primary_key=True)
    position_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('positions.id', ondelete='CASCADE'), primary_key=True)
    church_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('churches.id'), primary_key=True)

class MediaPost(Base):
    __tablename__='media_posts'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    church_id: Mapped[uuid.UUID|None] = mapped_column(ForeignKey('churches.id'), nullable=True)
    author_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str|None] = mapped_column(Text, nullable=True)
    media_url: Mapped[str] = mapped_column(Text)
    thumbnail_url: Mapped[str|None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(40), default='general')
    status: Mapped[str] = mapped_column(String(30), default='draft')
    visibility: Mapped[str] = mapped_column(String(30), default='church')
    allow_sharing: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_comments: Mapped[bool] = mapped_column(Boolean, default=True)
    published_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)

class News(Base):
    __tablename__='news_posts'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    church_id: Mapped[uuid.UUID|None] = mapped_column(ForeignKey('churches.id'), nullable=True)
    author_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'))
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str|None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default='draft')
    visibility: Mapped[str] = mapped_column(String(30), default='church')
    published_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)

class Event(Base):
    __tablename__='events'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    church_id: Mapped[uuid.UUID|None] = mapped_column(ForeignKey('churches.id'), nullable=True)
    group_id: Mapped[uuid.UUID|None] = mapped_column(ForeignKey('groups.id'), nullable=True)
    author_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str|None] = mapped_column(Text, nullable=True)
    location: Mapped[str|None] = mapped_column(Text, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default='draft')
    visibility: Mapped[str] = mapped_column(String(30), default='church')

class Conversation(Base):
    __tablename__='conversations'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    type: Mapped[str] = mapped_column(String(20), default='private')
    title: Mapped[str|None] = mapped_column(String(200), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'))

class ConversationMember(Base):
    __tablename__='conversation_members'
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('conversations.id', ondelete='CASCADE'), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    muted: Mapped[bool] = mapped_column(Boolean, default=False)

class Message(Base):
    __tablename__='messages'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('conversations.id', ondelete='CASCADE'))
    sender_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'))
    message_type: Mapped[str] = mapped_column(String(30), default='text')
    body: Mapped[str|None] = mapped_column(Text, nullable=True)
    attachment_url: Mapped[str|None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)

class Notification(Base):
    __tablename__='notifications'
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    recipient_user_id: Mapped[uuid.UUID|None] = mapped_column(ForeignKey('users.id'), nullable=True)
    scope_type: Mapped[str] = mapped_column(String(30), default='user')
    scope_id: Mapped[uuid.UUID|None] = mapped_column(nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(60), default='general')
    data: Mapped[dict|None] = mapped_column(JSON, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class AuditLog(Base):
    __tablename__='audit_logs'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    actor_user_id: Mapped[uuid.UUID|None] = mapped_column(ForeignKey('users.id'), nullable=True)
    action: Mapped[str] = mapped_column(String(120))
    target_type: Mapped[str|None] = mapped_column(String(80), nullable=True)
    target_id: Mapped[str|None] = mapped_column(String(120), nullable=True)
    metadata_json: Mapped[dict|None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class AppSetting(Base):
    __tablename__='app_settings'
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default='')
