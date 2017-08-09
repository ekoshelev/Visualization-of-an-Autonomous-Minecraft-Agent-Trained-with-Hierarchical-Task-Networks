import json
import math
import sys

import time

import MalmoConstants as C
import MalmoLogUtilities as L

DEBUG_MODE = False


def send_command_to_agent(agent_host, cmd):
    agent_host.sendCommand(cmd);


def inventory_amount(target_item, obs):
    count = 0
    for i in xrange(0, 39):
        key = 'InventorySlot_' + str(i) + '_item'
        if key in obs:
            item = obs[key]
            if item == target_item:
                count += int(obs[u'InventorySlot_' + str(i) + '_size'])

    return count


def distance2d(ax, ay, bx, by):
    return math.sqrt(((ax - bx) ** 2) + ((ay - by) ** 2))


def distance3d(ax, ay, az, bx, by, bz):
    return math.sqrt(((ax - bx) ** 2) + ((ay - by) ** 2) + ((az - bz) ** 2))


def get_yaw_to_block(ax, ay, az, a_yaw, targetx, targety, targetz):
    dx = int(targetx) + C.BLOCK_CENTER_DELTA - ax
    dz = int(targetz) + C.BLOCK_CENTER_DELTA - az
    target_yaw = (math.atan2(dz, dx) * 180.0 / math.pi) - 90
    difference = target_yaw - a_yaw
    while difference < -180:
        difference += 360

    while difference > 180:
        difference -= 360

    # normalize
    difference /= 180.0

    return difference


def get_pitch_to_block(ax, ay, az, targetx, targety, targetz):
    block_center_delta = C.BLOCK_CENTER_DELTA
    head_height = C.HEAD_HEIGHT

    hx = ax
    hy = ay + head_height
    hz = az
    # round down to get the correct coordinates of the block
    bx = int(targetx) + block_center_delta
    by = int(targety) + block_center_delta
    bz = int(targetz) + block_center_delta

    straight_dist = distance3d(hx, hy, hz, bx, by, bz)
    y_diff = (hy - by)
    sin = y_diff / straight_dist
    return math.asin(sin) * 180 / math.pi


def stop_all_motions(agent_host):
    send_command_to_agent(agent_host, "move 0")
    send_command_to_agent(agent_host, "attack 0")
    send_command_to_agent(agent_host, "turn 0")
    send_command_to_agent(agent_host, "pitch 0")


def init_grid3d(obs_range):
    grid3d = []
    asize = 2 * obs_range + 1
    for i in range(asize):
        grid3d.append([])
        for _ in range(asize):
            grid3d[i].append([])

    return grid3d


def raw_gridobs_to_3d_gridobs(grid3d, raw_grid_obs, obs_range):
    asize = 2 * obs_range + 1

    for idx, el in enumerate(raw_grid_obs):
        index = idx % (asize * asize)
        grid3d[index / asize][index % asize].append(el)


def get_observations_from_raw_observations(message):
    observations = json.loads(message)  # and parse the JSON
    ax = observations.get(u'XPos')
    az = observations.get(u'ZPos')
    ay = observations.get(u'YPos')
    a_yaw = observations.get(u'Yaw')
    a_pitch = observations.get(u'Pitch')
    nearby_entities = observations.get(u'nearby')
    raw_grid_observations = observations.get(C.OBSERVATION_GRID_NAME)

    line_of_sight = None
    # if line_of_sight is none -> either looking at the sky or the object is too far away
    if u'LineOfSight' in observations:
        line_of_sight = observations[u'LineOfSight']

    return observations, ax, az, ay, a_yaw, a_pitch, nearby_entities, raw_grid_observations, line_of_sight



# Get Yaw Delta to get from Source to Target, assuming the same Y
def get_yaw_delta_to_target(target_x, target_z, source_x, source_z, source_yaw):
    dx = target_x - source_x
    dz = target_z - source_z
    target_yaw = (math.atan2(dz, dx) * 180.0 / math.pi) - 90
    difference = target_yaw - source_yaw
    while difference < -180:
        difference += 360

    while difference > 180:
        difference -= 360

    # normalize
    difference /= 180.0

    return difference


# Check if there's a drop to collect
def has_drop(agent_host, block_type, nearby_entities, source_x, source_z, source_yaw, extra_data):
    # check if there's any floating cube -> get it
    for entity in nearby_entities:
        # a drop
        if entity.get(u'name') == block_type:
            yaw_delta = get_yaw_delta_to_target(entity[u'x'], entity[u'z'], source_x, source_z, source_yaw)
            send_command_to_agent(agent_host, "turn " + str(yaw_delta))
            send_command_to_agent(agent_host, "move " + str(1.0 - abs(yaw_delta)))
            return True

    return False


# Check if there's a drop to collect
def has_drop_counted(agent_host, block_type, nearby_entities, source_x, source_z, source_yaw, extra_data):
    # check if there's any floating cube -> get it
    # also if there's a drop floating for a long time over LOG_DROP_TICKS_LIMIT -> go get it
    counter = 0
    for entity in nearby_entities:
        # a drop
        if entity.get(u'name') == block_type:
            counter += 1

        if entity.get(u'name') == block_type and extra_data['getting_drops'] is True:
            # stop all other actions
            stop_all_motions(agent_host)
            # go towards the drop
            yaw_delta = get_yaw_delta_to_target(entity[u'x'], entity[u'z'], source_x, source_z, source_yaw)
            send_command_to_agent(agent_host, "turn " + str(yaw_delta))
            send_command_to_agent(agent_host, "move " + str(1.0 - abs(yaw_delta)))
            return True

    if counter == 0:  # no more drops
        extra_data['getting_drops'] = False
        extra_data['log_drop_tick'] = 0

    if counter > 0:
        extra_data['log_drop_tick'] += 1

    if counter >= C.DROPS_LIMIT or extra_data['log_drop_tick'] > C.LOG_DROP_TICKS_LIMIT:
        extra_data['getting_drops'] = True

    return False


# Check if the current tree has more blocks to harvest (aka, above and below blocks)
def has_block_below_or_above_precise(agent_host, block_type, ax, ay, az, a_pitch, observation_range,
                                     observation_range_y,
                                     current_block_to_hit, grid3d):
    bx = int(current_block_to_hit['x'])
    by = int(current_block_to_hit['y'])
    bz = int(current_block_to_hit['z'])

    # Check if agent is right by the block, if not return False
    if round(abs(bx - ax)) > 2 or round(abs(bz - az)) > 2:
        return False

    # stop moving or turning or attacking
    stop_all_motions(agent_host)

    target_pitch = get_pitch_to_block(ax, ay, az, bx, by, bz)

    pitch_delta = abs((target_pitch - a_pitch) / 180.0)

    if target_pitch == a_pitch:
        C.print_debug(DEBUG_MODE, "WEIRD SITUATION IN PITCHING PRECISE")
        return False

    C.print_debug(DEBUG_MODE, "PITCH DELTA " + str(pitch_delta))

    if abs(pitch_delta) < C.PITCH_DELTA:
        return False

    if target_pitch > a_pitch:
        send_command_to_agent(agent_host, "pitch " + str(pitch_delta * C.PITCH_FRACTION))
    else:
        send_command_to_agent(agent_host, "pitch -" + str(pitch_delta * C.PITCH_FRACTION))

    return True


# Check if ray is pointing at a nearby block
def has_block_nearby_and_in_ray(agent_host, target_block_type, ax, az, ay, line_of_sight, current_block_to_hit):
    if line_of_sight is not None:
        hit_type = line_of_sight[u'hitType']
        block_type = line_of_sight[u'type']
        # safeguard against hitting grass
        if block_type == u'grass' and hit_type == u'block':
            # stop attacking if grass
            send_command_to_agent(agent_host, 'attack 0')
            return False

        if hit_type == u'block' or hit_type == u'entity' and block_type == (u'' + target_block_type) \
                and (u'prop_type' not in line_of_sight) and line_of_sight[u'inRange'] is True:  # block
            # is it nearby?
            bx = line_of_sight[u'x']
            bz = line_of_sight[u'z']
            by = line_of_sight[u'y']

            delta_x = abs(int(int(bx) - int(ax)))
            delta_z = abs(int(int(bz) - int(az)))

            if delta_x <= 1 and delta_z <= 1:
                current_block_to_hit['x'] = line_of_sight[u'x']
                current_block_to_hit['z'] = line_of_sight[u'z']
                current_block_to_hit['y'] = line_of_sight[u'y']
                current_block_to_hit['valid'] = True
                # stop and start hitting
                stop_all_motions(agent_host)
                send_command_to_agent(agent_host, 'attack 1')
                return True

        else:
            # stop attacking
            send_command_to_agent(agent_host, 'attack 0')
            return False
    else:
        send_command_to_agent(agent_host, 'attack 0')
        return False


# Check if a nearby block is a block_type, 3D case
def has_block_in_range_3d(agent_host, block_type, ax, az, ay, a_yaw, observation_range_xz, observation_range_y,
                          current_block_to_hit, grid3d, observations, extra_data):
    smallest_dist = sys.maxint

    # tx, tz, ty is the coordinates of the closest block with respect to the observation grid
    # so they are not the same as the coordinates with respect to the world
    tx = None
    tz = None
    ty = None

    # observation_range_y is the range of y in the observation grid
    # we're assuming observation grid has y starting at 0 (the ground level)
    y_level = observation_range_y
    # Assumption: agent is in a flat world so its Y is also at AGENT_Y, which is currently defined to be at 0
    # NB: is it wrong?

    delta_ax_from_center = 0
    delta_ay_from_center = 0
    delta_az_from_center = 0

    if ax - int(ax) > C.BLOCK_CENTER_DELTA:
        delta_ax_from_center = 1

    if az - int(az) > C.BLOCK_CENTER_DELTA:
        delta_az_from_center = 1

    if ay - int(ay) > C.BLOCK_CENTER_DELTA:
        delta_ay_from_center = 1

    for i in range(2 * observation_range_xz + 1):
        for j in range(2 * observation_range_xz + 1):
            for k in range(y_level + 1):
                if grid3d[i][j][k] == block_type:
                    distance = distance3d(j, k, i,
                                          observation_range_xz + delta_ax_from_center,
                                          C.AGENT_DEFAULT_EYE_LEVEL + delta_ay_from_center,
                                          observation_range_xz + delta_az_from_center)
                    if distance < smallest_dist:
                        smallest_dist = distance
                        tx = j
                        tz = i
                        ty = k

    if tx is not None and tz is not None and ty is not None:
        targetx = int(ax) + tx - observation_range_xz + C.BLOCK_CENTER_DELTA
        targetz = int(az) + tz - observation_range_xz + C.BLOCK_CENTER_DELTA
        targety = int(ay) + ty + C.BLOCK_CENTER_DELTA
        delta_x = abs(int(int(targetx) - int(ax)))
        delta_z = abs(int(int(targetz) - int(az)))

        C.print_debug(DEBUG_MODE, 'Found a {} at: x {} y {} z {}'.format(block_type, targetx, targety, targetz))
        C.print_debug(DEBUG_MODE, 'Agent at: x {} y {} z {}'.format(ax, ay, az))

        current_block_to_hit['x'] = targetx
        current_block_to_hit['z'] = targetz
        current_block_to_hit['y'] = targety

        # Log out position of the new target block of it's a new target block
        block_center_coors = {'x': targetx, 'y': targety, 'z': targetz}

        if extra_data['prev_block_x'] != block_center_coors['x'] \
                or extra_data['prev_block_y'] != block_center_coors['y'] \
                or extra_data['prev_block_z'] != block_center_coors['z']:

            # there's a bug where if a x or y is close to a nearest integer in range of C.XZ_SIGMA
            # -> the target x or z change while it's actually the same and the change is only 1
            # check for that case
            if (extra_data['prev_block_x'] is not None and abs(
                        extra_data['prev_block_x'] - block_center_coors['x']) == 1 and abs(
                    int(round(ax)) - ax) < C.XZ_SIGMA) or (extra_data['prev_block_z'] is not None and abs(
                    extra_data['prev_block_z'] - block_center_coors['z']) == 1 and abs(
                    int(round(az)) - az) < C.XZ_SIGMA) or (
                            extra_data['prev_block_x'] is None and 0 < abs(int(round(ax)) - ax) < C.XZ_SIGMA) or (
                            extra_data['prev_block_z'] is None and 0 < abs(int(round(az)) - az) < C.XZ_SIGMA):

                # print 'PLEASE DISCARD: subtle bug'
                None
            else:
                L.move_to_log(block_center_coors, block_type, observations)

                # Update the prev positions of the agent
                extra_data['prev_block_x'] = block_center_coors['x']
                extra_data['prev_block_y'] = block_center_coors['y']
                extra_data['prev_block_z'] = block_center_coors['z']

        # If not, turn and go to the target
        # aim to the CORE of the block
        yaw_difference = get_yaw_to_block(ax, ay, az, a_yaw, targetx, targety, targetz)

        # If block is right by to the agent, check difference and don't move
        C.print_debug(DEBUG_MODE, "Yaw delta: {}".format(abs(yaw_difference)))
        C.print_debug(DEBUG_MODE, 'Deltas: x {} z {}'.format(delta_x, delta_z))

        if delta_x <= 1 and delta_z <= 1:
            if abs(yaw_difference) < C.YAW_DELTA:
                return False
            else:
                stop_all_motions(agent_host)
                send_command_to_agent(agent_host, "turn " + str(yaw_difference))
        else:
            stop_all_motions(agent_host)
            send_command_to_agent(agent_host, "turn " + str(yaw_difference))

            # if close to the target, should move more slowly -> easier to lock on target
            if (delta_x + delta_z) <= C.MOVE_SPEED_FRACTION_LIMIT:
                send_command_to_agent(agent_host, "move " + str((1.0 - abs(yaw_difference)) * C.MOVE_SPEED_FRACTION))
            else:
                send_command_to_agent(agent_host, "move " + str(1.0 - abs(yaw_difference)))

            # Log out position of the agent if position changes
            truncated_positions = {'x': int(ax), 'y': int(ay), 'z': int(az)}
            if extra_data['prev_ax'] != truncated_positions['x'] or extra_data['prev_ay'] != truncated_positions['y'] \
                    or extra_data['prev_az'] != truncated_positions['z']:
                L.position_log(truncated_positions, observations)
            # Update the prev positions of the agent
            extra_data['prev_ax'] = truncated_positions['x']
            extra_data['prev_ay'] = truncated_positions['y']
            extra_data['prev_az'] = truncated_positions['z']

        return True
    else:
        return False


def gather(agent_host, block_type, ax, ay, az, a_yaw, a_pitch, grid3d, nearby_entities,
           line_of_sight, current_block_to_hit, extra_data, observations):
    if has_drop_counted(agent_host, block_type, nearby_entities, ax, az, a_yaw, extra_data):
        # set current_block_to_hit invalid
        current_block_to_hit['valid'] = False
        C.print_debug(DEBUG_MODE, 'Getting {} Drop...'.format(block_type))
        # go to next tick
        return True

    if has_block_in_range_3d(agent_host, block_type, ax, az, ay, a_yaw, C.OBSERVATION_RANGE, C.OBSERVATION_RANGE_MAX_Y,
                             current_block_to_hit, grid3d, observations, extra_data):
        C.print_debug(DEBUG_MODE,
                      'Turning to a nearby {} block at {} {} {}'.format(block_type, current_block_to_hit['x'],
                                                                        current_block_to_hit['y'],
                                                                        current_block_to_hit['z']))
        return True

    if has_block_below_or_above_precise(agent_host, block_type, ax, ay, az, a_pitch, C.OBSERVATION_RANGE,
                                        C.OBSERVATION_RANGE_MAX_Y, current_block_to_hit, grid3d):
        C.print_debug(DEBUG_MODE, 'Pitching to a {} block below or above'.format(block_type))
        return True

    if has_block_nearby_and_in_ray(agent_host, block_type, ax, az, ay, line_of_sight, current_block_to_hit):
        # log this action
        L.hit_log(block_type, current_block_to_hit, observations)
        C.print_debug(DEBUG_MODE,
                      'Hitting a {} block in front at {} {} {}'.format(block_type, current_block_to_hit['x'],
                                                                       current_block_to_hit['y'],
                                                                       current_block_to_hit['z']))
        return True

    if has_drop(agent_host, block_type, nearby_entities, ax, az, a_yaw, extra_data):
        C.print_debug(DEBUG_MODE, 'Getting the leftover {} drop...'.format(block_type))
        return True

    C.print_debug(DEBUG_MODE, "Nothing to do from MMU.gather ...")

    return False


# Check if a nearby block is a block_type, 3D case
def trace_has_block_in_range_3d(agent_host, block_type, ax, az, ay, a_yaw, observation_range_xz, observation_range_y,
                                current_block_to_hit, grid3d, observations, extra_data):
    smallest_dist = sys.maxint

    # tx, tz, ty is the coordinates of the closest block with respect to the observation grid
    # so they are not the same as the coordinates with respect to the world
    tx = None
    tz = None
    ty = None

    # observation_range_y is the range of y in the observation grid
    # we're assuming observation grid has y starting at 0 (the ground level)
    y_level = observation_range_y
    # Assumption: agent is in a flat world so its Y is also at AGENT_Y, which is currently defined to be at 0
    # NB: is it wrong?

    delta_ax_from_center = 0
    delta_ay_from_center = 0
    delta_az_from_center = 0

    if ax - int(ax) > C.BLOCK_CENTER_DELTA:
        delta_ax_from_center = 1

    if az - int(az) > C.BLOCK_CENTER_DELTA:
        delta_az_from_center = 1

    if ay - int(ay) > C.BLOCK_CENTER_DELTA:
        delta_ay_from_center = 1

    for i in range(2 * observation_range_xz + 1):
        for j in range(2 * observation_range_xz + 1):
            for k in range(y_level + 1):
                if grid3d[i][j][k] == block_type:
                    distance = distance3d(j, k, i,
                                          observation_range_xz + delta_ax_from_center,
                                          C.AGENT_DEFAULT_EYE_LEVEL + delta_ay_from_center,
                                          observation_range_xz + delta_az_from_center)
                    if distance < smallest_dist:
                        smallest_dist = distance
                        tx = j
                        tz = i
                        ty = k

    if tx is not None and tz is not None and ty is not None:
        targetx = int(ax) + tx - observation_range_xz + C.BLOCK_CENTER_DELTA
        targetz = int(az) + tz - observation_range_xz + C.BLOCK_CENTER_DELTA
        targety = int(ay) + ty + C.BLOCK_CENTER_DELTA
        delta_x = abs(int(int(targetx) - int(ax)))
        delta_z = abs(int(int(targetz) - int(az)))

        C.print_debug(DEBUG_MODE, 'Found a {} at: x {} y {} z {}'.format(block_type, targetx, targety, targetz))
        C.print_debug(DEBUG_MODE, 'Agent at: x {} y {} z {}'.format(ax, ay, az))

        current_block_to_hit['x'] = targetx
        current_block_to_hit['z'] = targetz
        current_block_to_hit['y'] = targety

        # Log out position of the new target block of it's a new target block
        block_center_coors = {'x': targetx, 'y': targety, 'z': targetz}

        if extra_data['prev_block_x'] != block_center_coors['x'] \
                or extra_data['prev_block_y'] != block_center_coors['y'] \
                or extra_data['prev_block_z'] != block_center_coors['z']:

            # there's a bug where if a x or y is close to a nearest integer in range of C.XZ_SIGMA
            # -> the target x or z change while it's actually the same and the change is only 1
            # check for that case
            if (extra_data['prev_block_x'] is not None and abs(
                        extra_data['prev_block_x'] - block_center_coors['x']) == 1 and abs(
                    int(round(ax)) - ax) < C.XZ_SIGMA) or (extra_data['prev_block_z'] is not None and abs(
                    extra_data['prev_block_z'] - block_center_coors['z']) == 1 and abs(
                    int(round(az)) - az) < C.XZ_SIGMA) or (
                            extra_data['prev_block_x'] is None and 0 < abs(int(round(ax)) - ax) < C.XZ_SIGMA) or (
                            extra_data['prev_block_z'] is None and 0 < abs(int(round(az)) - az) < C.XZ_SIGMA):

                # print 'PLEASE DISCARD: subtle bug'
                None
            else:
                L.move_to_log(block_center_coors, block_type, observations)

                # Update the prev positions of the agent
                extra_data['prev_block_x'] = block_center_coors['x']
                extra_data['prev_block_y'] = block_center_coors['y']
                extra_data['prev_block_z'] = block_center_coors['z']

        # If not, turn and go to the target
        # aim to the CORE of the block
        yaw_difference = get_yaw_to_block(ax, ay, az, a_yaw, targetx, targety, targetz)

        # If block is right by to the agent, check difference and don't move
        C.print_debug(DEBUG_MODE, "Yaw delta: {}".format(abs(yaw_difference)))
        C.print_debug(DEBUG_MODE, 'Deltas: x {} z {}'.format(delta_x, delta_z))

        if delta_x <= 1 and delta_z <= 1:
            if abs(yaw_difference) < C.YAW_DELTA:
                return C.DONE
            else:
                stop_all_motions(agent_host)
                send_command_to_agent(agent_host, "turn " + str(yaw_difference))
        else:
            stop_all_motions(agent_host)
            send_command_to_agent(agent_host, "turn " + str(yaw_difference))

            # if close to the target, should move more slowly -> easier to lock on target
            if (delta_x + delta_z) <= C.MOVE_SPEED_FRACTION_LIMIT:
                send_command_to_agent(agent_host, "move " + str((1.0 - abs(yaw_difference)) * C.MOVE_SPEED_FRACTION))
            else:
                send_command_to_agent(agent_host, "move " + str(1.0 - abs(yaw_difference)))

            # Log out position of the agent if position changes
            truncated_positions = {'x': int(ax), 'y': int(ay), 'z': int(az)}
            if extra_data['prev_ax'] != truncated_positions['x'] or extra_data['prev_ay'] != truncated_positions['y'] \
                    or extra_data['prev_az'] != truncated_positions['z']:
                L.position_log(truncated_positions, observations)
            # Update the prev positions of the agent
            extra_data['prev_ax'] = truncated_positions['x']
            extra_data['prev_ay'] = truncated_positions['y']
            extra_data['prev_az'] = truncated_positions['z']

        return C.WORKING
    else:
        return C.YIELD


# Check if there's a drop to collect
def trace_has_drop(agent_host, block_type, nearby_entities, source_x, source_z, source_yaw, extra_data):
    # check if there's any floating cube -> get it
    for entity in nearby_entities:
        # a drop
        if entity.get(u'name') == block_type:
            yaw_delta = get_yaw_delta_to_target(entity[u'x'], entity[u'z'], source_x, source_z, source_yaw)
            send_command_to_agent(agent_host, "turn " + str(yaw_delta))
            send_command_to_agent(agent_host, "move " + str(1.0 - abs(yaw_delta)))
            return C.WORKING

    return C.YIELD


# Check if there's a drop to collect
def trace_has_drop_counted(agent_host, block_type, nearby_entities, source_x, source_z, source_yaw, extra_data):
    # check if there's any floating cube -> get it
    # also if there's a drop floating for a long time over LOG_DROP_TICKS_LIMIT -> go get it
    counter = 0
    for entity in nearby_entities:
        # a drop
        if entity.get(u'name') == block_type:
            counter += 1

        if entity.get(u'name') == block_type and extra_data['getting_drops'] is True:
            # stop all other actions
            stop_all_motions(agent_host)
            # go towards the drop
            yaw_delta = get_yaw_delta_to_target(entity[u'x'], entity[u'z'], source_x, source_z, source_yaw)
            send_command_to_agent(agent_host, "turn " + str(yaw_delta))
            send_command_to_agent(agent_host, "move " + str(1.0 - abs(yaw_delta)))
            return C.WORKING

    if counter == 0:  # no more drops
        extra_data['getting_drops'] = False
        extra_data['log_drop_tick'] = 0

    if counter > 0:
        extra_data['log_drop_tick'] += 1

    if counter >= C.DROPS_LIMIT or extra_data['log_drop_tick'] > C.LOG_DROP_TICKS_LIMIT:
        extra_data['getting_drops'] = True

    return C.YIELD


# Check if ray is pointing at a nearby block
def trace_has_block_nearby_and_in_ray(agent_host, target_block_type, ax, az, ay, line_of_sight, current_block_to_hit):
    if line_of_sight is not None:
        hit_type = line_of_sight[u'hitType']
        block_type = line_of_sight[u'type']
        # safeguard against hitting grass
        if block_type == u'grass' and hit_type == u'block':
            # stop attacking if grass
            send_command_to_agent(agent_host, 'attack 0')
            return C.YIELD

        if hit_type == u'block' or hit_type == u'entity' and block_type == (u'' + target_block_type) \
                and (u'prop_type' not in line_of_sight) and line_of_sight[u'inRange'] is True:  # block
            # is it nearby?
            bx = line_of_sight[u'x']
            bz = line_of_sight[u'z']
            by = line_of_sight[u'y']

            delta_x = abs(int(int(bx) - int(ax)))
            delta_z = abs(int(int(bz) - int(az)))

            if delta_x <= 1 and delta_z <= 1:
                current_block_to_hit['x'] = line_of_sight[u'x']
                current_block_to_hit['z'] = line_of_sight[u'z']
                current_block_to_hit['y'] = line_of_sight[u'y']
                current_block_to_hit['valid'] = True
                # stop and start hitting
                stop_all_motions(agent_host)
                send_command_to_agent(agent_host, 'attack 1')
                return C.WORKING

        else:
            # stop attacking
            send_command_to_agent(agent_host, 'attack 0')
            return C.YIELD
    else:
        send_command_to_agent(agent_host, 'attack 0')
        return C.YIELD


# Check if the current tree has more blocks to harvest (aka, above and below blocks)
def trace_has_block_below_or_above_precise(agent_host, block_type, ax, ay, az, a_pitch, observation_range,
                                           observation_range_y,
                                           current_block_to_hit, grid3d):
    bx = int(current_block_to_hit['x'])
    by = int(current_block_to_hit['y'])
    bz = int(current_block_to_hit['z'])

    # Check if agent is right by the block, if not return False
    if round(abs(bx - ax)) > 2 or round(abs(bz - az)) > 2:
        return C.YIELD

    # stop moving or turning or attacking
    stop_all_motions(agent_host)

    target_pitch = get_pitch_to_block(ax, ay, az, bx, by, bz)

    pitch_delta = abs((target_pitch - a_pitch) / 180.0)

    if target_pitch == a_pitch:
        C.print_debug(DEBUG_MODE, "WEIRD SITUATION IN PITCHING PRECISE")
        return C.YIELD

    C.print_debug(DEBUG_MODE, "PITCH DELTA " + str(pitch_delta))

    if abs(pitch_delta) < C.PITCH_DELTA:
        return C.DONE

    if target_pitch > a_pitch:
        send_command_to_agent(agent_host, "pitch " + str(pitch_delta * C.PITCH_FRACTION))
    else:
        send_command_to_agent(agent_host, "pitch -" + str(pitch_delta * C.PITCH_FRACTION))

    return C.WORKING


def trace_move_to(agent_host, block_type, ax, ay, az, a_yaw, a_pitch, grid3d, nearby_entities,
                  line_of_sight, current_block_to_hit, extra_data, observations):
    res = trace_has_block_in_range_3d(agent_host, block_type, ax, az, ay, a_yaw, C.OBSERVATION_RANGE,
                                      C.OBSERVATION_RANGE_MAX_Y,
                                      current_block_to_hit, grid3d, observations, extra_data)
    if res == C.WORKING:
        return res

    # if here, the previous res must have yielded -> check pitch
    res = trace_has_block_below_or_above_precise(agent_host, block_type, ax, ay, az, a_pitch, C.OBSERVATION_RANGE,
                                                 C.OBSERVATION_RANGE_MAX_Y, current_block_to_hit, grid3d)
    return res


def trace_harvest(agent_host, block_type, ax, ay, az, a_yaw, a_pitch, grid3d, nearby_entities,
                  line_of_sight, current_block_to_hit, extra_data, observations):
    res = has_drop_counted(agent_host, block_type, nearby_entities, ax, az, a_yaw, extra_data)
    if res == C.WORKING:
        # set current_block_to_hit invalid
        current_block_to_hit['valid'] = False
        C.print_debug(DEBUG_MODE, 'Getting {} Drop...'.format(block_type))
        # go to next tick
        return res

    res = has_block_nearby_and_in_ray(agent_host, block_type, ax, az, ay, line_of_sight, current_block_to_hit)
    if res == C.WORKING:
        C.print_debug(DEBUG_MODE,
                      'Hitting a {} block in front at {} {} {}'.format(block_type, current_block_to_hit['x'],
                                                                       current_block_to_hit['y'],
                                                                       current_block_to_hit['z']))
        return res

    res = has_drop(agent_host, block_type, nearby_entities, ax, az, a_yaw, extra_data)
    if res == C.WORKING:
        C.print_debug(DEBUG_MODE, 'Getting the leftover {} drop...'.format(block_type))
        return res

    return res


def trace_gather(trace, agent_host, block_type, ax, ay, az, a_yaw, a_pitch, grid3d, nearby_entities,
                 line_of_sight, current_block_to_hit, extra_data, observations):
    if trace.kind == C.KIND_MOVE_TO:
        return trace_move_to(agent_host, block_type, ax, ay, az, a_yaw, a_pitch, grid3d, nearby_entities,
                             line_of_sight, current_block_to_hit, extra_data, observations)

    elif trace.kind == C.KIND_HARVEST:
        return trace_harvest(agent_host, block_type, ax, ay, az, a_yaw, a_pitch, grid3d, nearby_entities,
                             line_of_sight, current_block_to_hit, extra_data, observations)
