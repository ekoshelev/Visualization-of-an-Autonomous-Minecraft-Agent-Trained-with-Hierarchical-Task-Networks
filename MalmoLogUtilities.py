from datetime import datetime
import time
import Testing


def get_time_second():
    dt = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S.%f')
    return dt


def hit_log(block_type, block, observations):
    s = 'Hit Log~ {}, x={} y={} z={}, {}'.format(block_type, block['x'], block['y'], block['z'], get_time_second())
    Testing.addLog(s, observations)


def position_log(positions, observations):
    s = 'Position Log~ x={} y={} z={}, {}'.format(positions['x'], positions['y'], positions['z'], get_time_second())
    Testing.addLog(s, observations)


def crafting_log(item, ingredients, observations):
    s = 'Crafting Log~ {} {}, {}'.format(item, ingredients, get_time_second())
    Testing.addLog(s, observations)


def move_to_log(block_positions, block_type, observations):
    s = 'MoveTo Log~ {} x={} y={} z={}, {}'.format(block_type, block_positions['x'], block_positions['y'],
                                                   block_positions['z'], get_time_second())
    Testing.addLog(s, observations)
