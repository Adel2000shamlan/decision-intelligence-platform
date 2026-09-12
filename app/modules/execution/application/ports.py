class ExecutionUnitOfWork:
 def __init__(self,repository,factory=None,policy=None,commit=lambda:None): self.repository=repository; self.factory=factory; self.policy=policy; self.commit=commit
