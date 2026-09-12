class DecisionRepository:
    def __init__(self): self.items={}
    def save(self,item): self.items[item['id']]=item; return item
    def get(self,item_id): return self.items.get(str(item_id))
    def list(self): return list(self.items.values())
