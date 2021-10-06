import math, sys
import json
from lux import constants
from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES, Resource
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate
from lux.game_objects import Unit

DIRECTIONS = Constants.DIRECTIONS
game_state = None

logfile = 'logfile'
open(logfile, 'w')

unit_to_tiles_one = {}
unit_to_tiles_two = {}



def find_path(current, goal, map, opponent):
    
    # add other units pos
    # add overrides for friendly cities
    # can swap places with other units
    unwalkable = []
    override = []

    for city in list(opponent.cities.values()):
        for tiles in city.citytiles:
            unwalkable.append(map.get_cell_by_pos(tiles.pos))
        
    vals_to_check = [(1,0),(0,1),(-1,0),(0,-1)]

    best_cell = map.get_cell(current.pos.x , current.pos.y ) 
    for loc_x,loc_y in vals_to_check:
        cell = map.get_cell(current.pos.x + loc_x, current.pos.y + loc_y) 
        if cell in unwalkable: continue;
        if cell.pos.distance_to(goal.pos) <= best_cell.pos.distance_to(goal.pos):
            best_cell = cell

    return current.pos.direction_to(best_cell.pos)

    



def get_closest_resource(resource_tiles,unit,player):
    '''Get the closest resource tile to unit'''
    closest_dist = math.inf
    closest_resource_tile = None
    for resource_tile in resource_tiles:
        dist = resource_tile.pos.distance_to(unit.pos)
        if dist < closest_dist:
            closest_dist = dist
            closest_resource_tile = resource_tile

    return closest_resource_tile

def get_closest_city(unit, player):
    '''Get closes city tile to unit'''
    closest_dist = math.inf
    closest_city_tile = None
    for k, city in player.cities.items():
        for city_tile in city.citytiles:
            dist = city_tile.pos.distance_to(unit.pos)
            if dist < closest_dist:
                closest_dist = dist
                closest_city_tile = city_tile
    return closest_city_tile


def get_unit_with_id(ID, units):
    for unit in units:
        if ID == unit.id:
            return unit                        



def get_new_tile(units_to_tiles, key, player, resources):


    def sort_resources(resource):
        closest = list(player.cities.values())[0].citytiles[0]
        for cities in list(player.cities.values()):
            for tiles in cities.citytiles:
                if tiles.pos.distance_to(resource.pos) < closest.pos.distance_to(resource.pos):
                    closest = tiles

        return closest.pos.distance_to(resource.pos)



    duplicate = units_to_tiles.copy()
    duplicate.pop(key)
    type = 2
    if (not player.researched_uranium()):
        type = 1
        if (not player.researched_coal()):
            type = 0
        
    with open(logfile, "a") as f:
            f.write(f"{key} finding new resource\n")

    resources[type] = sorted(resources[type],key=sort_resources)

    
    for resource_cell in resources[type]:
        if resource_cell not in duplicate.values():
            if resource_cell.resource.type == Constants.RESOURCE_TYPES.WOOD:
                if resource_cell.resource.amount > 500:
                    return key, resource_cell
            else:
                return key, resource_cell
            

    return key, None


def get_lowest_city(player):
    lowest = list(player.cities.values())[0]
    
    for city in list(player.cities.values()):
        if city.fuel < lowest.fuel:
            lowest = city
    
    return city


def apply_unit_actions(units_to_tiles, player, opponent, resources, actions, game_map):
    '''take all agent states and evaluate them and apply corisponding actions'''
    new_pairs = {}


    for key, val in units_to_tiles.items():
        unit = get_unit_with_id(key, player.units)

        if unit.cooldown < 1:
            with open(logfile, "a") as f:
                f.write(f"updaing {key} \n")

            if unit.get_cargo_space_left() > 5:
                # if unit can mine more
                if val.resource.type == Constants.RESOURCE_TYPES.WOOD:
                    if not game_map.get_cell_by_pos(val.pos).has_resource():
                        # if wood resource has reources
                        unit_id, resource_tile = get_new_tile(units_to_tiles, key, player,resources)
                        
                        if (resource_tile != None):
                            # if compatable resrouce is found create action
                            new_pairs[unit_id] = resource_tile
                            actions.append(unit.move(find_path(game_map.get_cell_by_pos(unit.pos), resource_tile, game_map, opponent)))
                            
                        else:
                            with open(logfile, "a") as f:
                                f.write(f"{key} has no resources to collect \n")

                    else:
                        actions.append(unit.move(find_path(game_map.get_cell_by_pos(unit.pos), val, game_map, opponent)))
                        with open(logfile, "a") as f:
                            f.write(f"{key} is moving twoards or is at a wood resource that is > than 150 {game_map.get_cell_by_pos(val.pos).has_resource()} \n")
                
                else:
                    with open(logfile, "a") as f:
                        f.write(f"{key} is collecting something besides wood \n")

            else:
                with open(logfile, "a") as f:
                    f.write(f"moving {key} twoards city \n")
                actions.append(unit.move(find_path(game_map.get_cell_by_pos(unit.pos), get_lowest_city(player).citytiles[0], game_map, opponent)))
                

    units_to_tiles =  units_to_tiles | new_pairs # merge dicts and override values



def agent(observation, configuration):
    global game_state

    ### Do not edit ###
    if observation["step"] == 0:
        game_state = Game()
        game_state._initialize(observation["updates"])
        game_state._update(observation["updates"][2:])
        game_state.id = observation.player
    else:
        game_state._update(observation["updates"])
    
    actions = []

    ### AI Code goes down here! ### 


    player = game_state.players[observation.player]
    opponent = game_state.players[(observation.player + 1) % 2]
    width, height = game_state.map.width, game_state.map.height

    
    resources : list[list] = []

    wood_tiles: list[Cell] = []
    coal_tiles: list[Cell] = []
    uranium_tiles: list[Cell] = []

    resources.append(wood_tiles)
    resources.append(coal_tiles)
    resources.append(uranium_tiles)

    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell(x, y)
            if cell.has_resource():
                if cell.resource.type == Constants.RESOURCE_TYPES.WOOD:
                    wood_tiles.append(cell)
                elif cell.resource.type == Constants.RESOURCE_TYPES.COAL:
                    coal_tiles.append(cell)
                else:
                    uranium_tiles.append(cell)


    
    
    if player.team == 1:

        if len(player.units) > 0:
            if len(unit_to_tiles_one) == 0:

                with open(logfile, "a") as f:
                    f.write(f"Adding first unit\n")

                closest_resource_tile = get_closest_resource(wood_tiles,player.units[0],player)
                unit_to_tiles_one[player.units[0].id] = closest_resource_tile
            
            apply_unit_actions(unit_to_tiles_one, player,opponent,resources, actions, game_state.map)
    
    else:
        if len(player.units) > 0:
            if len(unit_to_tiles_two) == 0:

                with open(logfile, "a") as f:
                    f.write(f"Adding first unit\n")

                closest_resource_tile = get_closest_resource(wood_tiles,player.units[0],player)
                unit_to_tiles_two[player.units[0].id] = closest_resource_tile
            
            apply_unit_actions(unit_to_tiles_two, player,opponent, resources, actions, game_state.map)




    # you can add debug annotations using the functions in the annotate object
    # actions.append(annotate.circle(0, 0))


    return actions
