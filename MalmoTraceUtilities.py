import json
import math
import sys
import time
import MalmoConstants as C
import MalmoMineUtilities as MMU
import MalmoCraftUtilities as MCU
import MalmoLogUtilities as L


def process_trace(trace, agent_host, observations, ax, ay, az, a_yaw, a_pitch, grid3d, nearby_entities, line_of_sight,
                  current_block_to_hit, extra_data):
    if trace.kind == C.KIND_MOVE_TO:
        """Move to a resource"""
        res = MCU.trace_gather_basic_block(trace, agent_host, observations, trace.item, ax, ay, az, a_yaw, a_pitch, grid3d,
                                     nearby_entities, line_of_sight, current_block_to_hit, extra_data)

        if res == C.DONE:
            return True
        else:
            # not done yet -> false
            return False

    if trace.kind == C.KIND_HARVEST:
        """Harvest a resource"""
        # check if done already
        current_amt = MMU.inventory_amount(trace.item, observations)
        if current_amt > trace.amount:
            # done -> true
            return True

        MCU.trace_gather_basic_block(trace, agent_host, observations, trace.item, ax, ay, az, a_yaw, a_pitch, grid3d,
                                     nearby_entities, line_of_sight, current_block_to_hit, extra_data)

        return False

    if trace.kind == C.KIND_CRAFT:
        """Craft an item"""
        MCU.craft(agent_host, trace.item, observations)

        return True

    return False
