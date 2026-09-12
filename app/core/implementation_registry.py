from dataclasses import dataclass, field
@dataclass(frozen=True)
class ImplementationStage:
    code:str; name:str; status:str='CLOSED'
@dataclass
class ImplementationRegistry:
    stages:list[ImplementationStage]=field(default_factory=list)
    def add(self,code,name): self.stages.append(ImplementationStage(code,name))
    def assert_closed(self): assert all(s.status=='CLOSED' for s in self.stages); return True
