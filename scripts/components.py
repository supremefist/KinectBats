
class Component(object):
    def __init__(self, name, type_id, amount=1, group_id=-1, volume=10000000.0):
        self.name = name
        self.type_id = type_id
        self.amount = amount
        self.group_id = group_id
        self.volume = volume
        
        self.components = {}
        self.reprocessing = {}
        
    def __str__(self):
        return "Component (id=" + str(self.type_id) + ", " + self.name + ", group_id=" + str(self.group_id) + ")"
