def send_command_to_agent(agent_host, cmd):
    agent_host.sendCommand(cmd)


# print only if debug_mode is true
def print_debug(debug_mode, str):
    if debug_mode:
        print str


OBSERVATION_GRID_NAME = u'cube5x5x5'
OBSERVATION_RANGE = 50
OBSERVATION_RANGE_MAX_Y = 10
OBSERVATION_RANGE_MIN_Y = 0
OBSERVATION_DEFAULT_AGENT_Y = 0
AGENT_DEFAULT_EYE_LEVEL = 1
# Log drop
LOG_DROP_TICKS_LIMIT = 50
# Limit of drops around to go collect drops
DROPS_LIMIT = 1
MOVE_SPEED_FRACTION = 0.6
MOVE_SPEED_FRACTION_LIMIT = 6
PITCH_SPEED = 0.1
PITCH_FRACTION = 0.8
PITCH_DELTA = 0.1
# yaw delta to stop turning to target a block
YAW_DELTA = 0.01
MOVE_SPEED = 0.8
AGENT_Y = 0  # assume to be at 0
# To find pitch constants
BLOCK_CENTER_DELTA = 0.5
HEAD_HEIGHT = 1.62

# MOVE_TO logging
MOVE_TO_COUNT_THRESHOLD = 1
XZ_SIGMA = 0.1

### Gatherable ingredients
basic_ingredients = ['log', 'stone', 'cobblestone', 'oak_wood', 'iron_ore', 'User']
BASIC_INGREDIENTS = set(basic_ingredients)

# Trace constants
KIND_MOVE_TO = "MoveTo"
KIND_CRAFT = "Craft"
KIND_HARVEST = "Harvest"

DONE = "DONE"
ERROR = "ERROR"
YIELD = "YIELD"
WORKING = "WORKING"
