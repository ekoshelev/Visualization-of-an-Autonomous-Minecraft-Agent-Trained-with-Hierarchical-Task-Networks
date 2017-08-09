# This is the XML File to build the world
# Read through the schemas to find indepth documentation
# Ask Ram about putting iron below a certain level to make a more interesting plan trace, see if it learns to go down that low
from random import randint
import MalmoConstants as C

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# To avoid overlap and infinite loops when creating minerals, keeps (iR^2)*iN+(cR^2)*cN < worldSize^2*stoneHeight, and under (worldSize/10)^2*stoneHeight for reality check (yes I know, math, but spacial awareness is important)
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

worldSize = 100
stoneHeight = 25
treeNumber = 50
ironNumber = 50
ironRadius = 2
ironDepth = stoneHeight
coalNumber = 50
coalRadius = 2
coalDepth = stoneHeight
observation_xz = C.OBSERVATION_RANGE
observation_min_y = C.OBSERVATION_RANGE_MIN_Y
observation_max_y = C.OBSERVATION_RANGE_MAX_Y
observation_grid_name = C.OBSERVATION_GRID_NAME
observationGrid = {
    "minX": -observation_xz,
    "maxX": observation_xz,
    "minY": observation_min_y,
    "maxY": observation_max_y,
    "minZ": -observation_xz,
    "maxZ": observation_xz,
    "name": observation_grid_name
}


def getPlacement():  # TO-DO MAKE RANDOM START WITHIN ZONE, NOT JUST MIDDLE
    return "<Placement x=\"" + str(worldSize / 2) + "\" y=\"" + str(stoneHeight + 5) + "\" z=\"" + str(
        worldSize / 2) + "\" yaw=\"90\"/>"


# TO-DO MAKE SO RESOURCES DON"T OVERLAP/GETLOST IN THEM SELVES
def getTree(x, z):
    return "<DrawCuboid type=\"log\" x1=\"" + x + "\" y1=\"" + str(
        stoneHeight + 5) + "\" z1=\"" + z + "\" x2=\"" + x + "\" y2=\"" + str(
        stoneHeight + 8) + "\" z2=\"" + z + "\"/>\n"


def getTrees():
    trees = ""
    for i in range(0, treeNumber):
        trees += getTree(str(randint(0, worldSize)), str(randint(0, worldSize)))
    return trees


def getIron(x, y, z):
    return "<DrawSphere type=\"iron_ore\" x=\"" + x + "\" y=\"" + y + "\" z=\"" + z + "\" radius=\"" + str(
        ironRadius) + "\" />\n"


def getIrons():
    irons = ""
    for i in range(0, ironNumber):
        irons += getIron(str(randint(0, worldSize)), str(randint(1, ironDepth - ironRadius)),
                         str(randint(0, worldSize)))
    return irons


def getCoal(x, y, z):
    return "<DrawSphere type=\"coal_ore\" x=\"" + x + "\" y=\"" + y + "\" z=\"" + z + "\" radius=\"" + str(
        coalRadius) + "\" />\n"


def getCoals():
    coals = ""
    for i in range(0, coalNumber):
        coals += getIron(str(randint(0, worldSize)), str(randint(1, coalDepth - coalRadius)),
                         str(randint(0, worldSize)))
    return coals


def getObservationGrid():
    grid = '''<Grid name="{}">
    <min x="{}" y="{}" z="{}"/>
    <max x="{}" y="{}" z="{}"/>
    </Grid>'''.format(observationGrid['name'], observationGrid['minX'], observationGrid['minY'],
                      observationGrid['minZ'], observationGrid['maxX'], observationGrid['maxY'],
                      observationGrid['maxZ'])
    return grid


def missionXML():
    return '''<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
    <Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <About>
        <Summary>Hello world!</Summary>
    </About>
    <ServerSection>
        <ServerInitialConditions>
            <Time>
                <StartTime>1000</StartTime>
                <AllowPassageOfTime>false</AllowPassageOfTime>
            </Time>
            <Weather>clear</Weather>
        </ServerInitialConditions>
        <ServerHandlers>
            <FlatWorldGenerator/>
            <DrawingDecorator>

                <DrawCuboid type="bedrock" x1="-1" y1="0" z1="-1" x2="''' + str(worldSize + 1) + '''" y2="''' + str(
                stoneHeight + 34) + '''" z2="''' + str(worldSize + 1) + '''"/>
                <DrawCuboid type="air"  x1="0" y1="1" z1="0" x2="''' + str(worldSize) + '''" y2="''' + str(
                stoneHeight + 34) + '''" z2="''' + str(worldSize) + '''"/>
            <DrawCuboid type="stone" x1="0" y1="1" z1="0" x2="''' + str(worldSize) + '''" y2="''' + str(
                stoneHeight) + '''" z2="''' + str(worldSize) + '''" />
            <DrawCuboid type="dirt" x1="0" y1="''' + str(stoneHeight + 1) + '''" z1="0" x2="''' + str(
                worldSize) + '''" y2="''' + str(stoneHeight + 3) + '''" z2="''' + str(worldSize) + '''" />
            <DrawCuboid type="grass" x1="0" y1="''' + str(stoneHeight + 4) + '''" z1="0" x2="''' + str(
                worldSize) + '''" y2="''' + str(stoneHeight + 4) + '''" z2="''' + str(worldSize) + '''" />

                ''' + getTrees() + '''
                ''' + getIrons() + '''
                ''' + getCoals() + '''

            </DrawingDecorator>
            <!--a server quit condition. Will end on time limit, or if an agent quits-->
            <ServerQuitWhenAnyAgentFinishes/>

        </ServerHandlers>
    </ServerSection>

    <AgentSection mode="Survival">
        <Name>Burton</Name>
        <AgentStart>
            ''' + getPlacement() + '''
            <Inventory>
                <!-- set the Inventory of an agent -->
            </Inventory>
        </AgentStart>
        <AgentHandlers>
            <ObservationFromChat />
            <ObservationFromFullStats/>
            <ObservationFromRecentCommands />
            <ObservationFromNearbyEntities>
                <Range name="nearby" xrange="10" yrange="10" zrange="10" update_frequency="1" />
            </ObservationFromNearbyEntities>
            <ObservationFromFullInventory/>
            <ObservationFromRay/>
            <ObservationFromGrid>
            ''' + getObservationGrid() + '''
            <Grid name="Blocks">
    	      <min x="-7" y="-7" z="-7"/>
              <max x="7" y="7" z="7"/>
            </Grid>
            </ObservationFromGrid>
            <ContinuousMovementCommands turnSpeedDegs="180">
                <ModifierList type="deny-list">
                    <command>strafe</command>
                </ModifierList>
            </ContinuousMovementCommands>
            <AbsoluteMovementCommands/>
            <DiscreteMovementCommands/>
            <SimpleCraftCommands/>
            <InventoryCommands/>
            <ChatCommands />
            <AgentQuitFromTimeUp>
            timeLimitMs="600000" 
            </AgentQuitFromTimeUp>
        </AgentHandlers>
    </AgentSection>

    </Mission>'''

