from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4
@dataclass
class Store:
    data:dict[str,dict[str,Any]]=field(default_factory=dict)
    def add(self, kind,obj):
        self.data.setdefault(kind,{})[str(obj['id'])]=obj; return obj
    def list(self,kind): return list(self.data.get(kind,{}).values())
    def get(self,kind,id): return self.data.get(kind,{}).get(str(id))
store=Store()
