from random import randint
import MalmoConstants as C
import MalmoGlobals as G
import MalmoPython
import time
import sys
import os 
#Code to initialize the agent and the environment
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
def getEnd():
    return "x=\"" + str(worldSize / 2) + "\" y=\"" + str(stoneHeight + 5) + "\" z=\"" + str(
        worldSize / 2) + "\""
        
def getPlacement():  # TO-DO MAKE RANDOM START WITHIN ZONE, NOT JUST MIDDLE
    return "<Placement x=\"" + str(worldSize / 2) + "\" y=\"" + str(stoneHeight + 5) + "\" z=\"" + str(
        worldSize / 2) + "\" yaw=\"90\"/>"

def getPlacement2():  # TO-DO MAKE RANDOM START WITHIN ZONE, NOT JUST MIDDLE
    return "<Placement x=\"" + str(worldSize / 2.5) + "\" y=\"" + str(stoneHeight + 5) + "\" z=\"" + str(
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

# TO-DO MAKE SO RESOURCES DON"T OVERLAP/GETLOST IN THEM SELVES
def getCobbleStone(x, z):
    return "<DrawCuboid type=\"cobblestone\" x1=\"" + x + "\" y1=\"" + str(
        stoneHeight + 5) + "\" z1=\"" + z + "\" x2=\"" + x + "\" y2=\"" + str(
        stoneHeight + 8) + "\" z2=\"" + z + "\"/>\n"


def getCobbleStones():
    trees = ""
    for i in range(0, treeNumber):
        trees += getCobbleStone(str(randint(0, worldSize)), str(randint(0, worldSize)))
    return trees

def getIronTree(x, z):
    return "<DrawCuboid type=\"iron_ore\" x1=\"" + x + "\" y1=\"" + str(
        stoneHeight + 5) + "\" z1=\"" + z + "\" x2=\"" + x + "\" y2=\"" + str(
        stoneHeight + 8) + "\" z2=\"" + z + "\"/>\n"


def getIronTrees():
    trees = ""
    for i in range(0, treeNumber):
        trees += getIronTree(str(randint(0, worldSize)), str(randint(0, worldSize)))
    return trees

def getIron(x, y, z):
    return "<DrawSphere type=\"iron_ore\" x=\"" + x + "\" y=\"" + y + "\" z=\"" + z + "\" radius=\"" + str(
        ironRadius) + "\" />\n"


def getIrons():
    irons = ""
    for i in range(0, ironNumber):
        irons += getIron(str(randint(0, worldSize)), str(randint(stoneHeight + 5, stoneHeight + 8 - ironRadius)),
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

def safeStartMission(agent_host, my_mission, my_client_pool, my_mission_record, role, expId):
    used_attempts = 0
    max_attempts = 5
    print "Calling startMission for role", role
    while True:
        try:
            # Attempt start:
            agent_host.startMission(my_mission, my_client_pool, my_mission_record, role, expId)
            break
        except MalmoPython.MissionException as e:
            errorCode = e.details.errorCode
            if errorCode == MalmoPython.MissionErrorCode.MISSION_SERVER_WARMING_UP:
                print "Server not quite ready yet - waiting..."
                time.sleep(2)
            elif errorCode == MalmoPython.MissionErrorCode.MISSION_INSUFFICIENT_CLIENTS_AVAILABLE:
                print "Not enough available Minecraft instances running."
                used_attempts += 1
                if used_attempts < max_attempts:
                    print "Will wait in case they are starting up.", max_attempts - used_attempts, "attempts left."
                    time.sleep(2)
            elif errorCode == MalmoPython.MissionErrorCode.MISSION_SERVER_NOT_FOUND:
                print "Server not found - has the mission with role 0 been started yet?"
                used_attempts += 1
                if used_attempts < max_attempts:
                    print "Will wait and retry.", max_attempts - used_attempts, "attempts left."
                    time.sleep(2)
            else:
                print "Other error:", e.message
                print "Waiting will not help here - bailing immediately."
                exit(1)
        if used_attempts == max_attempts:
            print "All chances used up - bailing now."
            exit(1)
    print "startMission called okay."

def safeWaitForStart(agent_hosts):
    print "Waiting for the mission to start",
    start_flags = [False for a in agent_hosts]
    start_time = time.time()
    time_out = 120  # Allow a two minute timeout.
    while not all(start_flags) and time.time() - start_time < time_out:
        states = [a.peekWorldState() for a in agent_hosts]
        start_flags = [w.has_mission_begun for w in states]
        errors = [e for w in states for e in w.errors]
        if len(errors) > 0:
            print "Errors waiting for mission start:"
            for e in errors:
                print e.text
            print "Bailing now."
            exit(1)
        time.sleep(0.1)
        print ".",
    if time.time() - start_time >= time_out:
        print "Timed out while waiting for mission to start - bailing."
        exit(1)
    print
    print "Mission has started."


# -- set up the mission --
xml = '''<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
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
            <FlatWorldGenerator forceReset="1"/>
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
                ''' + getCobbleStones() + '''
                ''' + getIronTrees() + '''
                ''' + getCoals() + '''

            </DrawingDecorator>
        </ServerHandlers>
    </ServerSection>


    <AgentSection mode="Survival">
        <Name>User</Name>
        <AgentStart>
            ''' + getPlacement() + '''
        </AgentStart>
        <AgentHandlers>
            <ChatCommands />
            <ContinuousMovementCommands turnSpeedDegs="180">
                <ModifierList type="deny-list">
                    <command>strafe</command>
                </ModifierList>
            </ContinuousMovementCommands>
            <ObservationFromFullStats/>
            <ObservationFromChat />
            <AbsoluteMovementCommands />
            <DiscreteMovementCommands />
        </AgentHandlers>
    </AgentSection>

    <AgentSection mode="Survival">
        <Name>Sudo</Name>
        <AgentStart>
            ''' + getPlacement2() + '''
            <Inventory>
                <!-- set the Inventory of an agent -->
            </Inventory>
        </AgentStart>
        <AgentHandlers>
            <ObservationFromDistance>
                <Marker name="End" ''' + getEnd() + '''/>
                <Marker name="Zero" x="0" y="0" z="0"/>
            </ObservationFromDistance>
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
            <SimpleCraftCommands/>
            <InventoryCommands/>
            <ChatCommands />
        </AgentHandlers>
    </AgentSection>

    </Mission>'''