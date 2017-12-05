
class Task(object):
    def __init__(self, map, target, dest):
        self.map = map
        self.target = target
        self.dest = dest


class Dig(Task):
    def __init__(self, map, target, dest):
        Task.__init__(self, map, target, dest)


class Cut(Task):
    def __init__(self, map, target, dest):
        Task.__init__(self, map, target, dest)


class Carry(Task):
    def __init__(self, map, target, dest, item_to_find):
        Task.__init__(self, map, target, dest)
        self.item_to_find = item_to_find


class Build(Task):
    def __init__(self, map, target, dest):
        Task.__init__(self, map, target, dest)
