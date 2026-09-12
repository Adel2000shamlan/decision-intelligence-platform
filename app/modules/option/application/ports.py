from abc import ABC, abstractmethod
from uuid import UUID
from app.modules.option.domain.models import Option
class OptionApplicationPort(ABC):
    @abstractmethod
    def get_option(self,option_id:UUID)->Option: ...
