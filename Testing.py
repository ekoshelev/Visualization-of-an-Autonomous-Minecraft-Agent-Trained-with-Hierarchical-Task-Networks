#Noah Reifsnyder
#Rachel Santangelo
#Read through the schemas to find indepth documentation. Describes all of
#the viable commands you can call that interact with the agent itself.


# ------------------------------------------------------------------------------------------------


# Copyright (c) 2016 Microsoft Corporation
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
# associated documentation files (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge, publish, distribute,
# sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or
# substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
# NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# ------------------------------------------------------------------------------------------------

import getXML#XML File, Easier to manage in seperate File
import MalmoPython
import os
import signal
import sys
import time
import json
import math
from datetime import datetime
from collections import namedtuple

f= open("log.txt","w",1)
contents=""

def myExit():
        global contents
        global f
        print "\nLogging Ended"
        contents+="End Log~"
        f.write(contents)
        f.close()

class block:
    def __init__(self, name, x, y, z):
        self.name=name
        self.loc=location(x,y,z)
    def __eq__(self, other):
        if isinstance(other,block):
            if (self.name==other.name and self.loc==other.loc):
                return True
        return False
    def __ne__(self, other):
        result = self.__eq__(other)
        return not result
    def __repr__(self):
        return ","+self.name+repr(self.loc)
class location:
    def __init__(self, x,y,z):
        self.x=x
        self.y=y
        self.z=z
    def __eq__(self, other):
        if isinstance(other,location):
            if(self.x==other.x and self.y==other.y and self.z==other.z):
                return True
        return False
    def __ne__(self, other):
        result = self.__eq__(other)
        return not result
    def __repr__(self):
        return "~x="+str(self.x)+" y="+str(self.y)+" z="+str(self.z)
class action:
    name=""
    Pas=location(0,0,0)
class item:
    def __init__(self, name, amt):
        self.name=name
        self.amt=amt
    def __eq__(self, other):
        if isinstance(other, item):
            return (self.name == other.name and self.amt==other.amt)
        return False
    def __ne__(self, other):
        result = self.__eq__(other)
        return not result
    def __repr__(self):
        return  self.name+"-"+str(self.amt)+" "

EntityInfo = namedtuple('EntityInfo', 'x, y, z, name, quantity, variation')
EntityInfo.__new__.__defaults__ = (0, 0, 0, "", 0)
inv =[]
grid=[]
Player=location(0,0,0)
def addLog(s,obs):
        global contents
        #str(grid) str(obs)
        contents+=(s+str(Player)+"~"+str(inv)+"\n") #ADD INVENTORY
        
def updateAction(action,obs):
        if(checkMove(action)):
                addLog("Move",obs)
                addLog(action.name,obs)

def checkMove(action):
    x=(Player.x-action.Pas.x)^2
    y=(Player.y-action.Pas.y)^2
    z=(Player.z-action.Pas.z)^2
    dist=math.sqrt(z+y+z)
    if(dist>5):
        return True
    return False

def checkInv(obs):
    global inv
    currInv=list(inv)
    currInvTemp=[]
    for i in currInv:
        currInvTemp.append(item(i.name,0))
    for x in xrange(0,39):
        number=0
        name="_"
        iKey = 'InventorySlot_'+str(x)+'_item'
        if iKey in obs:
            nKey = 'InventorySlot_'+str(x)+'_size'
            number = obs[nKey]
            name = obs[iKey]
        if (name=="_"):
            continue
        flag=0
        for i in xrange(0,len(currInvTemp)):
            if (currInvTemp[i].name==name):
                flag=1
                number+=currInvTemp[i].amt
                currInvTemp[i]=item(name,number)
                break
        if (flag==0):
                currInvTemp.append(item(name,number))
        ''' for j in currInvTemp:
        flag=0
        for i in xrange(0,len(currInv)):
            if(currInv[i].name==j.name):
                currInv[i]=j
                flag=1
        if(flag==0):
            currInv.append(j)'''
   
        #currInv+=str(i)+","+str(item)+","+str(number)+"\n"
    return currInvTemp

def checkChangedInv(obs):
        global inv
        global grid
        newInv=checkInv(obs)
        if(newInv != inv ):
                st = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S.%f')
                for i in xrange(0,len(inv)):
                        x = inv[i]
                        y = newInv[i]
                        if(x != y ):
                                addLog("Inventory Log~ "+repr(x)+repr(y)+","+st, obs)
                if (len(newInv)>len(inv)):
                        for i in xrange(len(inv), len(newInv)):
                                x=newInv[i]
                                y=item(newInv[i].name,0)
                                addLog("Inventory Log~ "+repr(y)+repr(x)+","+st, obs)

                inv=newInv
                return True
        return False

def checkAction(obs):
        checkChangedBlocks(obs)
        checkChangedInv(obs)
rPlayer=location(0,0,0)
lastLook=location(0,0,0)
last2Look=location(0,0,0)
last3Look=location(0,0,0)
def checkChangedBlocks(obs):
    global grid
    global Player
    global rPlayer
    global lastLook
    global last2Look
    global last3Look
    if 'Blocks' in obs:
        st = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S.%f')
        dLoc=checkChangedPos(obs)
        newGrid=obs['Blocks']
        try:
                LOS=obs['LineOfSight']
                rlooking=location((LOS.get('x')),(LOS.get('y')),(LOS.get('z')))
                looking=location(int(rlooking.x),int(rlooking.y),int(rlooking.z))
                if rlooking.x==int(rlooking.x)*1.0:
                         if rPlayer.x>looking.x:
                                 looking.x-=1
                if rlooking.y==int(rlooking.y)*1.0:
                        if rPlayer.y>=looking.y or rPlayer.y+1>= looking.y:
                                looking.y-=1
                if rlooking.z==int(rlooking.z)*1.0:
                        if rPlayer.z>looking.z:
                                looking.z-=1
        except:
                looking=(1000,1000,1000)
       
        gridSize=len(newGrid)
        dim=int(round(math.pow(gridSize,1./3.)))
	for y in xrange(0,dim):
                for z in xrange(0,dim):	
            	        for x in xrange(0,dim):
				index=x+(z*dim)+(y*dim*dim)
                                b=getLoc(x,y,z,dim)
				index2=(x+dLoc.x)+((z+dLoc.z)*dim)+((y+dLoc.y)*dim*dim)
                                try:
                                        if  newGrid[index]!=grid[index] and newGrid[index]=="air" and (b==lastLook or b==last2Look or b==last3Look) and dLoc==location(0,0,0):
                                                #if((b==looking or b==lastLook) and newGrid[index2]=="air"):
                                                addLog("Block Log~ "+grid[index]+" "+newGrid[index2]+","+st,obs)
				except:
					pass
        grid=newGrid
        last3Look=last2Look
        last2Look=lastLook
        lastLook=looking
def parseGrid(grid):
   
    newGrid=[]
    for y in xrange(0,dim):
        for z in xrange(0,dim):
            for x in xrange(0,dim):
                index=x+(z*dim)+(y*dim*dim)
                newGrid.append(makeName(x,y,z,grid[index],dim))
    return newGrid
def getLoc(x,y,z,dim):
        global Player
        middle=int(math.ceil(dim/2.))
        x=Player.x+x-middle+1
        y=Player.y+y-middle+1
        z=Player.z+z-middle+1
        return location(x,y,z)
def checkChangedPos(obs):
        global rPlayer
        global Player
        if "nearby" in obs:
                tPlayer=location(0,0,0)
                tPlayer.x=int(obs['XPos'])
                tPlayer.y=int(obs['YPos'])
                tPlayer.z=int(obs['ZPos'])
                rPlayer.x=obs['XPos']
                rPlayer.y=obs['YPos']
                rPlayer.z=obs['ZPos']
                if(tPlayer!=Player):
                        loc=location(Player.x-tPlayer.x, Player.y-tPlayer.y, Player.z-tPlayer.z)
                        Player=tPlayer
                        return loc
        return location(0,0,0)














#Enter some hard coded commands in here


# Loop until mission ends:

#Role here denotes which client is doing which code. Set role with command line
#argument when starting program.
    #This is the constant running code.
def get(read):
    msg=""
    while msg=="" :
        try:
    	    tmp=os.read(read,1)
    	    while tmp!="\n" and tmp!="":
                msg+=tmp
        	tmp=os.read(read, 1)
        except:
            msg=""
    return msg

def done(write):
    os.write(write, "d")

def run(agent_host, read, write):
	while True:
                msg=get(read)
		ob=json.loads(msg)
		checkAction(ob)
		done(write)
                lastmsg=msg
                


