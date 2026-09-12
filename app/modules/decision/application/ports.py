class DecisionUnitOfWork:
    def __init__(self,repository,factory,policy,commit=lambda:None): self.repository=repository; self.factory=factory; self.policy=policy; self.commit=commit
