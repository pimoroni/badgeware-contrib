import random

# Behaviours for NPCs. Not used in this version.


class Behaviour:
    def __init__(self):
        self.entity = None

    def set_behaviour_target(self, entity):
        self.entity = entity

    def behaviour_update(self):
        pass


class DVDBehaviour(Behaviour):
    def __init__(self):
        super().__init__()

    def behaviour_update(self):
        self.entity.check_movement(1)

        while (not self.entity.can_walk_x or not self.entity.can_walk_y):
            self.entity.turn(random.randint(-5, 5))
            self.entity.check_movement(1)

        self.entity.walk(1)


class SpotTurnBehaviour(Behaviour):
    def __init__(self):
        super().__init__()

    def behaviour_update(self):
        self.entity.turn(1)


class FreezeBehaviour(Behaviour):
    def __init__(self):
        super().__init__()

    def behaviour_update(self):
        pass
