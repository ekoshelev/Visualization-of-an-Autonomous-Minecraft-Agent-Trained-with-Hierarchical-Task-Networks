import MalmoPython
import os
import sys
import time
import json
import math
import interactionXML as xml
import MalmoConstants as C
import MalmoGlobals as G
import MalmoMineUtilities as MMU
import MalmoCraftUtilities as MCU 
import MalmoTraceUtilities as MTU
import action

DEBUG_MODE = False

def rotateYaw(target):  #Rotates the agent to a specific angle
    for obs in agent_host.peekWorldState().observations:#Takes observations from environment to find current yaw
        msg = obs.text
        ob = json.loads(msg)
        yaw = (ob.get(u'Yaw'))
        while yaw%360<(target-4) or yaw%360>(target+4):
            for obs in agent_host.peekWorldState().observations:
                msg = obs.text
                ob = json.loads(msg)
                yaw = ob.get(u'Yaw')
            if yaw%360>target+4 or (yaw%360<90 and target>270):#Rotate left or right depending on which way is faster to reach target angle
                agent_host.sendCommand("turn -.2")
                time.sleep(.1)
                agent_host.sendCommand("turn 0")
            else:
                agent_host.sendCommand("turn .2") #check if right way
                time.sleep(.1)
                agent_host.sendCommand("turn 0")
                
def findYaw(x1,x2,y1,y2):  #Find the angle that the agent needs to turn to walk to the player
    dx=abs((x2-x1))
    dy=abs((y2-y1))
    if x2>x1 and y2>y1:
        yaw=270+math.degrees(math.atan(dy/dx))     
    elif(x2>x1 and y1>y2):
        yaw=270-math.degrees(math.atan(dy/dx))
    elif(x1>x2 and y1>y2):
        yaw=90+math.degrees(math.atan(dy/dx))
    elif(x1>x2 and y2>y1): 
        yaw=90-math.degrees(math.atan(dy/dx))
    elif (x1==x2 and y2>y1):
        yaw=180
    elif (x1==x2 and y1>y2):
        yaw=0
    elif (y1==y2 and x1>x2):
        yaw=90
    elif (y1==y2 and x2>x1):
        yaw=270
    else:
        yaw=0
    return yaw

def load_traces(): #We need this to refresh the traces every time the user requests a new item
    traces = []
    with open("traces.txt") as traces_file:
        content = traces_file.readlines()
        for t in content:
            tokens = t.split(":")
            kind = tokens[0].strip()
            item = tokens[1].strip()
            trace = G.Trace(kind, item)
            traces.append(trace)
        print traces
        return traces
    
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)  # flush print output immediately

# -- set up two agent hosts --
agent_host_user = MalmoPython.AgentHost()
agent_host = MalmoPython.AgentHost()

try:
    agent_host_user.parse( sys.argv )
except RuntimeError as e:
    print 'ERROR:',e
    print agent_host_user.getUsage()
    exit(1)
if agent_host_user.receivedArgument("help"):
    print agent_host_user.getUsage()
    exit(0)


# -- set up the mission --


my_mission = MalmoPython.MissionSpec(xml.xml,True)
my_mission.observeRecentCommands()

client_pool = MalmoPython.ClientPool()
client_pool.add( MalmoPython.ClientInfo('127.0.0.1',10000) )
client_pool.add( MalmoPython.ClientInfo('127.0.0.1',10001) )

my_mission_record = MalmoPython.MissionRecordSpec()

my_mission_record2 = MalmoPython.MissionRecordSpec()


xml.safeStartMission(agent_host_user, my_mission, client_pool, my_mission_record, 0, '' )
xml.safeStartMission(agent_host, my_mission, client_pool, my_mission_record2, 1, '' )
xml.safeWaitForStart([ agent_host_user, agent_host ])

endflag=0

def observeWorld(): #Code for the agent to take commands in the chat
    while agent_host.peekWorldState().is_mission_running: 
        for obs in agent_host.peekWorldState().observations:
            msg = obs.text
            ob = json.loads(msg)
            chat = ob.get(u'Chat', "")            
            for command in chat:
                parts = command.split("> ") #Observe the chat
                if "Sudo make" in parts[1]:
                    if "stone_pickaxe" in parts[1]:
                        action.writeOriginalPickaxetoTraces()
                        makeItem("stone_pickaxe")
                    else: #Make an item other than the pickaxe
                        newparts=parts[1].split()
                        item=newparts[3]                     
                        itemExists=action.checkItemExists(item) #Check if it is in the library, return boolean
                        if itemExists:
                            checkUnknownIngredients=action.checkIngredientsExist(item)
                            if len(checkUnknownIngredients)==0:
                                action.writeItemtoTraces(item)
                                makeItem(item)
                            else:
                                agent_host.sendCommand("chat I do not recognize these items: " + ' '.join(checkUnknownIngredients))
                                time.sleep(1)
                        else:
                            agent_host.sendCommand("chat I do not recognize this item.")
                            time.sleep(1)      
                if parts[1]=="Print coordinates": #Print the agent and user's coordinates, for testing purposes
                    for obs in agent_host_user.peekWorldState().observations:
                        msg = obs.text
                        ob = json.loads(msg)
                        chat = ob.get(u'Chat', "")
                        ux = ob.get(u'XPos')
                        uz = ob.get(u'ZPos')
                    sys.stdout.write("x: " + '{0:.0f}'.format(ux) + "\n")
                    sys.stdout.write("z: " + '{0:.0f}'.format(uz) + "\n")            
                    for obs in agent_host_user.peekWorldState().observations:
                        msg = obs.text
                        ob = json.loads(msg)
                        ux = ob.get(u'XPos')
                        uz = ob.get(u'ZPos')
                        sys.stdout.write("user x: " + '{0:.0f}'.format(ux) +  "user z: " + '{0:.0f}'.format(uz) + "\n")
                    for obs in agent_host.peekWorldState().observations:
                        msg = obs.text
                        ob = json.loads(msg)
                        sx = ob.get(u'XPos')
                        sz = ob.get(u'ZPos')
                        sys.stdout.write("sudo x: " + '{0:.0f}'.format(sx) + "sudo z: " + '{0:.0f}'.format(sz) + "\n")
                    print findYaw(sx,ux,sz,uz)
                if parts[1]=="Sudo find me": #The agent navigates to the user
                    startrun=False
                    while startrun==False:
                        for obs in agent_host_user.peekWorldState().observations:
                            msg = obs.text
                            ob = json.loads(msg)
                            ux = ob.get(u'XPos')
                            uz = ob.get(u'ZPos')
                        for obs in agent_host.peekWorldState().observations:
                            msg = obs.text
                            ob = json.loads(msg)
                            sx = ob.get(u'XPos')
                            sz = ob.get(u'ZPos')
                        rotateYaw(findYaw(sx,ux,sz,uz))
                        agent_host.sendCommand("move 1")
                        time.sleep(.5)
                        agent_host.sendCommand("move 0")
                        if abs(sx-ux)<5 and abs(sz-uz)<5:
                            agent_host.sendCommand("move 0")
                            agent_host.sendCommand("turn 0")
                            agent_host.sendCommand("discardCurrentItem")
                            startrun=True        
                if "To make" in parts[1]: #Allows the user to put in new recipes      
                    line=parts[1]
                    words=line.split()
                    if words[0]=="To" and words[1]=="make":
                        item=words[2]
                        ingredients=words[4:]
                        target = open("library", "a+")
                        if action.checkItemExists(item)!=True:
                            newingredients= "\nIngredientsfor" + item +": " + ' '.join(ingredients)
                            print newingredients
                            target.write(newingredients)
                            agent_host.sendCommand("chat Added to library!") 
                            time.sleep(1)
                            target.close()
                        else:
                            with open("library", 'r') as handle:
                                for line2 in handle:
                                    array =line2.split()
                                    if array[0]==("Ingredientsfor" + item + ":"):
                                        typethis= ','.join(array[1:])
                                        agent_host.sendCommand("chat This item already exists, here are the ingredients: " + typethis)
                                        time.sleep(1)

def makeItem(item): #Code to make a specific item
    startrun=False
    endflag=0
    G.target_traces=load_traces() #Reload the traces.txt file
    tracess=G.target_traces
    while agent_host.peekWorldState().is_mission_running: 
        world_state = agent_host.getWorldState()     
        for error in world_state.errors:
            print "Error:", error.text
    
        if world_state.number_of_observations_since_last_state > 0:  # Have any observations come in?
            msg = world_state.observations[-1].text  # Yes, so get the text
            # get observations from raw observations
            observations, ax, az, ay, a_yaw, a_pitch, nearby_entities, raw_grid_observations, line_of_sight = \
            MMU.get_observations_from_raw_observations(msg)
            # safeguard against glitches
            if raw_grid_observations is None or observations is None or nearby_entities is None:
                # get next tick
                continue
    
            grid3d = MMU.init_grid3d(C.OBSERVATION_RANGE)
            MMU.raw_gridobs_to_3d_gridobs(grid3d, observations.get(C.OBSERVATION_GRID_NAME), C.OBSERVATION_RANGE)
            
            # if all requirements traces are made -> stop all motions
            if len(tracess) == 0:
                MMU.stop_all_motions(agent_host)
                if endflag < 5:
                    endflag += 1
                else:
                    for obs in agent_host.peekWorldState().observations:
                        msg = obs.text
                        ob = json.loads(msg)
                        pitch = ob.get(u'Pitch')
                    while pitch<-1 or pitch>1: #Adjust the agent so it is looking forward
                        for obs in agent_host.peekWorldState().observations:
                            msg = obs.text
                            ob = json.loads(msg)
                            pitch = ob.get(u'Pitch')
                        if pitch<0:
                            agent_host.sendCommand("pitch .1")
                            time.sleep(.05)
                            agent_host.sendCommand("pitch 0")
                        if pitch>0:
                            agent_host.sendCommand("pitch -.1")
                            time.sleep(.05)
                            agent_host.sendCommand("pitch 0")
                    while startrun==False: #Navigate back to user
                        for obs in agent_host_user.peekWorldState().observations:
                            msg = obs.text
                            ob = json.loads(msg)
                            ux = ob.get(u'XPos')
                            uz = ob.get(u'ZPos')
                        for obs in agent_host.peekWorldState().observations:
                            msg = obs.text
                            ob = json.loads(msg)
                            sx = ob.get(u'XPos')
                            sz = ob.get(u'ZPos')
                        rotateYaw(findYaw(sx,ux,sz,uz))
                        agent_host.sendCommand("move 1")
                        time.sleep(.5)
                        agent_host.sendCommand("move 0")
                        if abs(sx-ux)<5 and abs(sz-uz)<5:
                            agent_host.sendCommand("move 0")
                            agent_host.sendCommand("turn 0")
                            if item!="stone_pickaxe":
                                for obs in agent_host.peekWorldState().observations:
                                    msg = obs.text
                                    MCU.printInventory(observations)
                                    if 'InventorySlot_0_item' not in observations or observations['InventorySlot_0_item'] != item:
                                        MCU.select_item(agent_host, observations, item)
                                        agent_host.sendCommand("discardCurrentItem") #Select item and discard it
                                        time.sleep(1)
                                    if 'InventorySlot_0_item' not in observations or observations['InventorySlot_0_item'] != 'stone_pickaxe':
                                        MCU.select_item(agent_host, observations, 'stone_pickaxe') #Reequip stone pickaxe
                            startrun=True      
                            endflag=0
                            observeWorld() #Agent waits for more commands
            else:
                trace = G.target_traces[0]
                print trace
                C.print_debug(DEBUG_MODE, "Trace: {}, item: {}".format(trace.kind, trace.item))
    
                # set some init data in this trace to detect if the trace has been completed later on
                if not trace.started:
                    if trace.kind == C.KIND_HARVEST or trace.kind == C.KIND_MOVE_TO:
                        current_amt = MMU.inventory_amount(trace.item, observations)
                        print current_amt
                        trace.set_amount(current_amt)
    
                    trace.set_started(True)
                done = MTU.process_trace(trace, agent_host, observations, ax, ay, az, a_yaw, a_pitch, grid3d,
                                        nearby_entities,
                                         line_of_sight, G.current_block_to_hit, G.extra_data)
                if done:
                    # remove current trace from the list (always the first)
                    del G.target_traces[0]
                   
            time.sleep(0.1)
           
while agent_host.peekWorldState().is_mission_running: 
    observeWorld() #Agent waits for commands