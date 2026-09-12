from .domain.repository import UserRepository
from .domain.models import User
from .domain.lockout import AuthenticationFailureState
from uuid import UUID

class InMemoryUserRepository(UserRepository):
    def __init__(self): self._items={}
    def get_by_id(self,user_id): return self._items.get(user_id)
    def get_by_email(self,email): return next((u for u in self._items.values() if u.email_address==email),None)
    def exists_by_email(self,email): return self.get_by_email(email) is not None
    def save(self,user): self._items[user.id]=user

class InMemoryAuthenticationFailureRepository:
    def __init__(self): self._items={}
    def get(self,user_id:UUID): return self._items.get(user_id,AuthenticationFailureState(user_id))
    def save(self,state): self._items[state.user_id]=state
