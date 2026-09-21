from .domain.repository import UserRepository


class DelegatingUserRepository(UserRepository):
    def __init__(self, backend):
        self.backend = backend

    def configure(self, backend):
        self.backend = backend

    def get_by_id(self, user_id):
        return self.backend.get_by_id(user_id)

    def get_by_email(self, email):
        return self.backend.get_by_email(email)

    def exists_by_email(self, email):
        return self.backend.exists_by_email(email)

    def save(self, user):
        return self.backend.save(user)
