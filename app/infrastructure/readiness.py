from dataclasses import dataclass
@dataclass(frozen=True)
class Gate: name:str; passed:bool; evidence:str
class Readiness:
    def __init__(self): self.gates=[]
    def add(self,name,passed,evidence): self.gates.append(Gate(name,bool(passed),evidence))
    @property
    def passed(self): return bool(self.gates) and all(g.passed for g in self.gates)
    def require(self):
        if not self.passed: raise RuntimeError('production readiness gates are not all passed')
