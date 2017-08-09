# Utility file for all thing crafting in Malmo
import random
import time

import MalmoConstants as C
import MalmoGlobals as G
import MalmoMineUtilities as MMU
import MalmoLogUtilities as L

DEBUG_MODE = False


def send_command_to_agent(agent_host, cmd):
    agent_host.sendCommand(cmd)


def craft(agent_host, item, observations):
    """
    Craft an item from available recipes
    :param agent_host: the agent_host object connected to the current client
    :param item: item to craft
    :param observations: observations to pass to the logging function
    :return:
    """

    # need to sleep to stop from crafting the same item multiple times
    send_command_to_agent(agent_host, 'attack 0')
    send_command_to_agent(agent_host, 'move 0')
    send_command_to_agent(agent_host, 'turn 0')
    send_command_to_agent(agent_host, 'pitch 0')
    time.sleep(0.1)
    send_command_to_agent(agent_host, 'craft {}'.format(item))
    # Log out crafting action
    ingredients = G.craft_recipes[item]['ingredients']
    L.crafting_log(item, ingredients, observations)
    # need to sleep to stop from crafting the same item multiple times
    time.sleep(0.5)


def randomize_recipe(target):
    # first, randomize the recipe of this target
    randomize_recipe_helper(target)

    # then randmize the recipe of all the sub targets (necessary ingredients of this target)
    recipe = G.craft_recipes[target]
    ingredients = recipe['ingredients']
    # ingredients must be a list (because target's recipe has been randomized)
    for pair in ingredients:
        sub_target = pair[0]
        if sub_target not in C.BASIC_INGREDIENTS:
            # not basic -> need to randomize
            randomize_recipe(pair[0])


def randomize_recipe_helper(target):
    """
    Randomize the recipe with the target as the goal. Affects G.craft_recipes.
    :param target: target name of the item
    """

    recipe = G.craft_recipes[target]
    ingredients = recipe['ingredients']
    if type(ingredients) is dict:  # not yet randomized before -> turn into an array
        tmp = []
        ingredients_keys = ingredients.keys()
        for key in ingredients_keys:
            tmp.append((key, ingredients[key]))

        G.craft_recipes[target]['ingredients'] = tmp

    ingredients_list = G.craft_recipes[target]['ingredients']
    if type(ingredients_list) is list:  # list -> randomized before
        random.shuffle(ingredients_list)
        G.craft_recipes[target]['ingredients'] = ingredients_list
    else:
        print 'randomize_recipe weird'


def lookup_recipe(target):
    if target.startswith('stone') and target not in G.craft_recipes:
        target = target.replace('stone', 'cobblestone')

    return G.craft_recipes[target]


# Make a specific item. Traverse the requirement graph in random order.
def make(agent_host, target_item, observations, ax, ay, az, a_yaw, a_pitch, grid3d, nearby_entities, line_of_sight,
         current_block_to_hit, extra_data):
    # is it a basic item?
    if target_item in C.BASIC_INGREDIENTS:
        if gather_basic_block(agent_host, target_item, ax, ay, az, a_yaw, a_pitch, grid3d, nearby_entities,
                              line_of_sight,
                              current_block_to_hit, extra_data):
            return True

    # not basic -> look into recipes
    recipe = lookup_recipe(target_item)
    ingredients = recipe['ingredients']
    # NB: assuming that target's recipe has been randomized by calling randomize_recipe
    # thus, ingredients will be a list of tuple, instead of a dict
    lack_materials = 0

    for pair in ingredients:
        # assume not having enough material at first
        ingredient = pair[0]
        amt_required = pair[1]

        # NB: a hack to change oak_wood to log instead due to recipe conflict
        # if ingredient == 'oak_wood':
        #     ingredient = 'log'

        amt_current = MMU.inventory_amount(ingredient, observations)

        if amt_current < amt_required:
            lack_materials += 1
            # is it basic ingredient, if yes, go gather
            if ingredient in C.BASIC_INGREDIENTS:
                if gather_basic_block(agent_host, observations, ingredient, ax, ay, az, a_yaw, a_pitch, grid3d,
                                      nearby_entities, line_of_sight, current_block_to_hit, extra_data):
                    return True
                else:
                    C.print_debug(DEBUG_MODE, 'Must do sth else. Gather doesnt work')
                    return False

            # if not, call recursively
            else:
                return make(agent_host, ingredient, observations, ax, ay, az, a_yaw, a_pitch, grid3d,
                            nearby_entities, line_of_sight, current_block_to_hit, extra_data)
        else:
            C.print_debug(DEBUG_MODE,
                          'Requirement {} for {} is good with {}'.format(ingredient, target_item, amt_current))

    if lack_materials == 0:
        craft(agent_host, target_item, observations)
        return True


def select_item(agent_host, obs, target_item):
    for i in xrange(0, 39):
        key = 'InventorySlot_' + str(i) + '_item'
        if key in obs:
            item = obs[key]
            if item == target_item:
                send_command_to_agent(agent_host, "swapInventoryItems 0 " + str(i))
                return True
    return False


def printInventory(obs):
    for i in xrange(0, 39):
        key = 'InventorySlot_' + str(i) + '_item'
        var_key = 'InventorySlot_' + str(i) + '_variant'
        col_key = 'InventorySlot_' + str(i) + '_colour'
        if key in obs:
            item = obs[key]
            print str(i) + " ------ " + item,
        else:
            print str(i) + " -- ",
        if var_key in obs:
            print obs[var_key],
        if col_key in obs:
            print obs[col_key],
        print


def gather_basic_block(agent_host, observations, block_type, ax, ay, az, a_yaw, a_pitch, grid3d, nearby_entities,
                       line_of_sight, current_block_to_hit, extra_data):
    # mining logs
    if block_type == 'log':
        return MMU.gather(agent_host, block_type, ax, ay, az, a_yaw, a_pitch, grid3d, nearby_entities,
                          line_of_sight, current_block_to_hit, extra_data, observations)
    
    if block_type == 'User':
        return MMU.gather(trace, agent_host, block_type, ax, ay, az, a_yaw, a_pitch, grid3d, nearby_entities,
                          line_of_sight, current_block_to_hit, extra_data, observations)
    # mining cobblestone
    if block_type == 'cobblestone':
        # require a pickaxe...
        required = 'wooden_pickaxe'
        if MMU.inventory_amount(required, observations) > 0:
            # made the recipe -> switch of making tool flag
            G.making_tools[required] = False
            # if not currently holding a pickaxe and have a pickaxe -> select it
            if 'InventorySlot_0_item' not in observations or observations['InventorySlot_0_item'] != required:
                select_item(agent_host, observations, required)
                # sleep to give time to select item
                # time.sleep(0.5)

            # mine cobblestone
            return MMU.gather(agent_host, block_type, ax, ay, az, a_yaw, a_pitch, grid3d, nearby_entities,
                              line_of_sight, current_block_to_hit, extra_data, observations)

        else:
            # make the require tool
            # if first time making this tool -> randomize the recipe
            if required not in G.making_tools or G.making_tools[required] is False:
                randomize_recipe(required)
                # need to keep track of making this tool in order to randomize the recipe only once
                G.making_tools[required] = True

            return make(agent_host, required, observations, ax, ay, az, a_yaw, a_pitch, grid3d, nearby_entities,
                        line_of_sight, current_block_to_hit, extra_data)

    # mining iron
    if block_type == 'iron_ore':
        # require a stone pickaxe...
        required = 'stone_pickaxe'
        if MMU.inventory_amount(required, observations) > 0:
            # made the recipe -> switch off making tool flag
            G.making_tools[required] = False
            # if not currently holding a pickaxe and have a pickaxe -> select it
            if 'InventorySlot_0_item' not in observations or observations['InventorySlot_0_item'] != required:
                select_item(agent_host, observations, required)
                # sleep to give time to select item
                # time.sleep(0.5)

            # mine cobblestone
            return MMU.gather(agent_host, block_type, ax, ay, az, a_yaw, a_pitch, grid3d, nearby_entities,
                              line_of_sight, current_block_to_hit, extra_data, observations)

        else:
            # make the required tool
            # if first time making this tool -> randomize the recipe
            if required not in G.making_tools or G.making_tools[required] is False:
                randomize_recipe(required)
                # need to keep track of making this tool in order to randomize the recipe only once
                G.making_tools[required] = True
            return make(agent_host, required, observations, ax, ay, az, a_yaw, a_pitch, grid3d, nearby_entities,
                        line_of_sight, current_block_to_hit, extra_data)


def trace_gather_basic_block(trace, agent_host, observations, block_type, ax, ay, az, a_yaw, a_pitch, grid3d, nearby_entities,
                             line_of_sight, current_block_to_hit, extra_data):
    # mining logs
    if block_type == 'log':
        return MMU.trace_gather(trace, agent_host, block_type, ax, ay, az, a_yaw, a_pitch, grid3d, nearby_entities,
                          line_of_sight, current_block_to_hit, extra_data, observations)
    if block_type == 'User':
        return MMU.trace_gather(trace, agent_host, block_type, ax, ay, az, a_yaw, a_pitch, grid3d, nearby_entities,
                          line_of_sight, current_block_to_hit, extra_data, observations)
    # mining cobblestone
    if block_type == 'cobblestone':
        # require a pickaxe...
        required = 'wooden_pickaxe'
        if MMU.inventory_amount(required, observations) > 0:
            # made the recipe -> switch of making tool flag
            G.making_tools[required] = False
            # if not currently holding a pickaxe and have a pickaxe -> select it
            if 'InventorySlot_0_item' not in observations or observations['InventorySlot_0_item'] != required:
                select_item(agent_host, observations, required)
                # sleep to give time to select item
                # time.sleep(0.5)

            # mine cobblestone
            return MMU.trace_gather(trace, agent_host, block_type, ax, ay, az, a_yaw, a_pitch, grid3d, nearby_entities,
                              line_of_sight, current_block_to_hit, extra_data, observations)

        else:
            # make the require tool
            # if first time making this tool -> randomize the recipe
            if required not in G.making_tools or G.making_tools[required] is False:
                randomize_recipe(required)
                # need to keep track of making this tool in order to randomize the recipe only once
                G.making_tools[required] = True

            return make(agent_host, required, observations, ax, ay, az, a_yaw, a_pitch, grid3d, nearby_entities,
                        line_of_sight, current_block_to_hit, extra_data)

    # mining iron
    if block_type == 'iron_ore':
        # require a stone pickaxe...
        required = 'stone_pickaxe'
        if MMU.inventory_amount(required, observations) > 0:
            # made the recipe -> switch off making tool flag
            G.making_tools[required] = False
            # if not currently holding a pickaxe and have a pickaxe -> select it
            if 'InventorySlot_0_item' not in observations or observations['InventorySlot_0_item'] != required:
                select_item(agent_host, observations, required)
                # sleep to give time to select item
                # time.sleep(0.5)

            # mine cobblestone
            return MMU.trace_gather(trace, agent_host, block_type, ax, ay, az, a_yaw, a_pitch, grid3d, nearby_entities,
                              line_of_sight, current_block_to_hit, extra_data, observations)

        else:
            # make the required tool
            # if first time making this tool -> randomize the recipe
            if required not in G.making_tools or G.making_tools[required] is False:
                randomize_recipe(required)
                # need to keep track of making this tool in order to randomize the recipe only once
                G.making_tools[required] = True
            return make(agent_host, required, observations, ax, ay, az, a_yaw, a_pitch, grid3d, nearby_entities,
                        line_of_sight, current_block_to_hit, extra_data)
