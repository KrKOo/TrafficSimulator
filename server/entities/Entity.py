import simpy
import itertools


class EntityBase:
    id_iter = itertools.count()

    def __init__(self):
        self.id = next(self.id_iter)


class SimulationEntity(EntityBase):
    def __init__(self, env: simpy.Environment):
        EntityBase.__init__(self)
        self.env = env
