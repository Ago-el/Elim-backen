import uuid
from datetime import date, datetime
from pydantic import BaseModel, EmailStr, Field

class FirebaseLogin(BaseModel): id_token: str
class AdminLogin(BaseModel): email: EmailStr; password: str
class ChurchIn(BaseModel): name: str=Field(min_length=2,max_length=160); country: str; city: str|None=None
class MemberIn(BaseModel): church_id: uuid.UUID; first_name: str; last_name: str; phone: str|None=None; email: EmailStr|None=None; birth_date: date|None=None; photo_url: str|None=None
class GroupIn(BaseModel): church_id: uuid.UUID; name: str; description: str|None=None
class PositionIn(BaseModel): name: str
class MediaIn(BaseModel): church_id: uuid.UUID|None=None; title: str; description: str|None=None; media_url: str; thumbnail_url: str|None=None; category: str='sermon'; visibility: str='church'
class NewsIn(BaseModel): church_id: uuid.UUID|None=None; title: str; content: str; image_url: str|None=None; visibility: str='church'
class EventIn(BaseModel): church_id: uuid.UUID|None=None; group_id: uuid.UUID|None=None; title: str; description: str|None=None; location: str|None=None; starts_at: datetime; ends_at: datetime|None=None; visibility: str='church'
class Moderate(BaseModel): status: str
class ConversationIn(BaseModel): user_ids: list[uuid.UUID]; type: str='private'; title: str|None=None
class MessageIn(BaseModel): message_type: str='text'; body: str|None=None; attachment_url: str|None=None
class NotificationIn(BaseModel): recipient_user_id: uuid.UUID|None=None; scope_type: str='user'; scope_id: uuid.UUID|None=None; title: str; body: str; kind: str='general'; data: dict|None=None
