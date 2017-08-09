from sys import argv
import sys
import json
import time

basics=["log", "cobblestone", "iron_ore", "MoveTo:", "Harvest:", "Craft:"]

def createItemList(): #Creates an array of arrays of items
    itemlist=[]
    with open("library", 'r') as handle:
        for line2 in handle:
            array =line2.split()
            if "Ingredientsfor" in array[0]:
                item=array[0].split("for")
                item2=item[1].split(":")
                item3=item2[0]
                array2=[]
                array2.append(item3)
                for i in range(1,len(array)): 
                    array2.append(array[i])   
                itemlist.append(array2)
    return itemlist

def writeOriginalPickaxetoTraces(): #Writes the original pickaxe traces to the traces file
    target=open("pickaxetraces.txt", "r")
    tracefile = open("traces.txt", "w")
    tracefile.truncate()
    for line in target.readlines():
        tracefile.write(line)
    tracefile.close()
    target.close()
    
    
def writetoTraces(line,ingredientlist,itemlist): #Given a list of ingredients, the list of traces, and an item, write the proper traces to the traces file
    target2 = open("traces.txt", "w")
    target2.truncate()
    array=[]
    if line not in basics:
        for i in range(0,len(ingredientlist)):
            if ingredientlist[i] in basics: #If it is a basic ingredient, write the ingredients to traces ("MoveTo: ___ Harvest: ____")
                templist=findCurrentList(ingredientlist[i],itemlist)
                for z in range(0,len(templist)):
                    array.append(templist[z])
            else:
                temparray=ingredientlist[i].split("###") #Else, write the traces to the traces.txt file
                array.append("Craft:")
                array.append(temparray[1])
        array.append("Craft:")
        array.append(line)    
    else:
        array=ingredientlist                  
    for i in range(0,len(array)-1,2):     
        if i!=(len(array)-2):
            target2.write(array[i] + " " + array[i+1] + "\n")
        else:
            target2.write(array[i] + array[i+1])
    target2.close()
    
def findCurrentList(item, itemlist): #Find the ingredient list for a certain item
    currentlist=[]
    for i in range(0,len(itemlist)):  
        if itemlist[i][0]==item:
            currentlist=itemlist[i][1:]
    return currentlist
            
def makeTrace(currentlist,itemlist): #Create the proper trace, replacing each ingredient with its recipe until only basic ingredients remain
    templist=[]
    for i in range(0,len(currentlist)):  
        if currentlist[i] not in basics and "###" not in currentlist[i]:
                newlist=findCurrentList(currentlist[i],itemlist)
                for z in range(0,len(newlist)): 
                    templist.append(newlist[z]) #fix this
                templist.append("Craft:")
                templist.append("###" + currentlist[i]) #Add ###Craft: Item to set apart that item from an item to be replaced
        else:
            templist.append(currentlist[i])   
    return templist
            
def checkAllBasics(currentlist): #Check if all ingredients in ingredients list are basic
    test=False
    for i in range(0,len(currentlist)): 
        if currentlist[i] not in basics and "###" not in currentlist[i]:
            test=True
            return True
        else:
            test=False   
    return test

def createPlan(target):
    itemlist=createItemList() #Create list of arrays of ingredients for all items
    targetlist=findCurrentList(target,itemlist) #Find ingredients for the target item in the itemlist
    while checkAllBasics(targetlist): #Check if all ingredients are basic, if not
        templist=makeTrace(targetlist,itemlist) #Iterate through all and replace items that aren't basic with their recipes
        targetlist=templist
    print targetlist
    return targetlist
    
def checkItemExists(line): #Check if the item is in the library
    target = open("library", "r")
    newitem="Ingredientsfor" + line + ":"
    if newitem not in target.read():
        print "Item does not exist"
        return False
    else:
        return True
    
def checkIngredientsExist(item): #Check if its ingredients are in the library
    itemlist=createItemList()
    newlist=[]
    for i in range(len(itemlist)):
        newlist.append(itemlist[i][0])
    currentlist=findCurrentList(item,itemlist)
    unidentifieditems=[]
    for i in range(len(currentlist)):
        if currentlist[i] not in newlist:
            if currentlist[i] not in basics:
                if currentlist[i] not in unidentifieditems:
                    unidentifieditems.append(currentlist[i])
    return unidentifieditems

def writeItemtoTraces(line): #Call several methods to convert the item to the correct traces
    itemlist=[]
    ingredients=createPlan(line)
    itemlist=createItemList()
    writetoTraces(line,ingredients,itemlist)


