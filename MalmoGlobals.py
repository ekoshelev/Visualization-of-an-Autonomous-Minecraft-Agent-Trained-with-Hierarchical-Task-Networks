import json


class Trace:
    """Class to represent a trace in plan traces"""

    def __init__(self, kind, item):
        self.kind = kind
        self.item = item
        self.amount = -1
        self.started = False

    def __str__(self):
        return "Trace: {} | {} | {} | {}".format(self.kind, self.item, self.amount, self.started)

    def set_amount(self, amount):
        self.amount = amount

    def set_started(self, started):
        self.started = started


def load_recipe():
    with open('recipes_custom.json') as recipe_file:
        data = json.load(recipe_file)
        return data


def load_traces():
    traces = []
    with open("traces.txt") as traces_file:
        content = traces_file.readlines()
        for t in content:
            tokens = t.split(":")
            kind = tokens[0].strip()
            item = tokens[1].strip()
            trace = Trace(kind, item)
            traces.append(trace)
        print traces
        return traces


current_block_to_hit = {'x': int(), 'y': int(), 'z': int(), 'valid': False}
extra_data = {'log_drop_count': 0, 'getting_drops': False, 'log_drop_tick': 0, 'prev_ax': None, 'prev_ay': None,
              'prev_az': None, 'prev_block_x': None, 'prev_block_y': None, 'prev_block_z': None, 'move_to_count': 0}
making_tools = {}  # to keep track of which tool the agent is making
craft_recipes = load_recipe()

target_items = [('iron_pickaxe', 1)]
target_traces = load_traces()
