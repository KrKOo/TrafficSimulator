import simpy
import itertools


class WithId(type):
    def __init__(cls, name, bases, attrs):
        super().__init__(name, bases, attrs)
        cls._ids = itertools.count(1)


class EntityBase:
    def __init__(self):
        pass


class SimulationEntity(EntityBase):
    def __init__(self, env: simpy.Environment):
        EntityBase.__init__(self)
        self.env = env
