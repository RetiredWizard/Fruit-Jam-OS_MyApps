import board
import supervisor
import displayio
import adafruit_imageload
from displayio import Palette
from adafruit_display_text import label
import terminalio
#from adafruit_pybadger import PyBadger
import time

import select
from sys import stdin

try:
    from pydos_ui import Pydos_ui
    Pydos_display = ('display' in dir(Pydos_ui))
    sba = Pydos_ui.serial_bytes_available
except:
    Pydos_display = False
    sba = lambda : supervisor.runtime.serial_bytes_available

try:
    from pydos_ui import input
except:
    pass

def snek(envVars):
    global sprite, ORIGINAL_MAP, CURRENT_MAP, ENTITY_SPRITES
    global ENTITY_SPRITES_DICT, INVENTORY, PLAYER_LOC, sprite_group
    global CAMERA_VIEW, MAP_HEIGHT, MAP_WIDTH
    global group, NEED_TO_SPAWN_BOOTS, SPAWN_LOC
    global MAP_DOOR_COUNT
    global LAST_BOOT_MOVE_DICT
    global CUR_MAP_INDEX
    global CAMERA_OFFSET_X
    global CAMERA_OFFSET_Y

    try:
        type(envVars)
    except:
        envVars = {}
        
    if '_display' in envVars.keys():
        display = envVars['_display']
    elif Pydos_display:
        display = Pydos_ui.display
    elif 'display' in dir(supervisor.runtime) and supervisor.runtime.display is not None:
        display = supervisor.runtime.display
    elif 'DISPLAY' in dir(board):
        display = board.DISPLAY
    else:
        try:
            import matrix
            display = matrix.envVars['_display']
        except:
            try:
                import framebufferio
                import dotclockframebuffer
            except:
                try:
                    import adafruit_ili9341
                except:
                    import framebufferio
                    import picodvi

            displayio.release_displays()

            if 'TFT_PINS' in dir(board):
                sWdth = getenv('CIRCUITPY_DISPLAY_WIDTH')
                if sWdth == None:
                    if board.board_id == "makerfabs_tft7":
                        sWdth = input("What is the resolution Width of the touch screen? (1024/800/...): ")
                    else:
                        sWdth = board.TFT_TIMINGS['width']
                    if 'updateTOML' in dir(Pydos_ui):
                        Pydos_ui.updateTOML("CIRCUITPY_DISPLAY_WIDTH",str(sWdth))

                if sWdth == 1024 and "TFT_TIMINGS1024" in dir(board):
                    disp_bus=dotclockframebuffer.DotClockFramebuffer(**board.TFT_PINS,**board.TFT_TIMINGS1024)
                else:
                    disp_bus=dotclockframebuffer.DotClockFramebuffer(**board.TFT_PINS,**board.TFT_TIMINGS)
                display=framebufferio.FramebufferDisplay(disp_bus)

            else:
                try:
                    type(adafruit_ili9341)
                    if 'SPI' in dir(board):
                        spi = board.SPI()
                    else:
                        spi = busio.SPI(clock=board.SCK,MOSI=board.MOSI,MISO=board.MISO)
                    disp_bus=displayio.FourWire(spi,command=board.D10,chip_select=board.D9, \
                        reset=board.D6)
                    display=adafruit_ili9341.ILI9341(disp_bus,width=320,height=240)
                except:
                    # DVI Sock
                    fb = picodvi.Framebuffer(320,240,clk_dp=board.GP14, clk_dn=board.GP15, \
                        red_dp=board.GP12, red_dn=board.GP13,green_dp=board.GP18, \
                        green_dn=board.GP19,blue_dp=board.GP16, blue_dn=board.GP17,color_depth=8)
                    display=framebufferio.FramebufferDisplay(fb)


    # Direction constants for comparison
    UP = 0
    DOWN = 1
    RIGHT = 2
    LEFT = 3

    MOVING_DIRECTION = -1

    HIDE_SPLASH_TIME = -1


    LAST_BOOT_MOVE_DICT = {}


    # how long to wait between rendering frames
    FPS_DELAY = 1/60

    # how many tiles can fit on thes screen. Tiles are 16x16
    SCREEN_HEIGHT_TILES = 8
    SCREEN_WIDTH_TILES = 10

    MAP_LIST = [
        "map.csv"
    ]

    CUR_MAP_INDEX = 0

    MAP_HEIGHT = 0
    MAP_WIDTH = 0


    # hold the map state as it came out of the csv. Only holds non-entities.
    ORIGINAL_MAP = {}

    # hold the current map state if/when it changes. Only holds non-entities.
    CURRENT_MAP = {}

    # dictionary with tuple keys that map to tile type values
    # e.x. {(0,0): "left_wall", (1,1): "floor"}
    CAMERA_VIEW = {}

    # how far offset the camera is from the CURRENT_MAP
    # used to determine where things are at in the camera view vs. the MAP
    CAMERA_OFFSET_X = 0
    CAMERA_OFFSET_Y = 0

    # list of sprite objects, one for each entity
    ENTITY_SPRITES = []

    # Dictionary with touple keys that map to lists of entity objects.
    # Each one has the index of the sprite in the ENTITY_SPRITES list
    # and the tile type string
    ENTITY_SPRITES_DICT = {}

    # list of entities that need to be on the screen currently based on the camera view
    NEED_TO_DRAW_ENTITIES = []

    # hold the location of the player in tile coordinates
    PLAYER_LOC = (0,0)

    # hold the location of the spawn point for current map
    SPAWN_LOC = (0,0)

    INVENTORY = []

    MAP_DOOR_COUNT = 0

    NEED_TO_SPAWN_BOOTS = []

    # return from CURRENT_MAP the tile name of the tile of the given coords
    def get_tile(coords):
        return CURRENT_MAP[coords[0], coords[1]]

    # return from TILES dict the tile object with stats and behavior for the tile at the given coords.
    def get_tile_obj(coords):
        return TILES[CURRENT_MAP[coords[0], coords[1]]]

    # check the can_walk property of the tile at the given coordinates
    def is_tile_moveable(tile_coords):
        return TILES[CURRENT_MAP[tile_coords[0], tile_coords[1]]]['can_walk']

    def take_item(to_coords, from_coords, entity_obj):
        print(entity_obj)
        INVENTORY.append(entity_obj["map_tile_name"])
        ENTITY_SPRITES_DICT[to_coords].remove(entity_obj)
        if len(ENTITY_SPRITES_DICT[to_coords]) == 0:
            del ENTITY_SPRITES_DICT[to_coords]

        if (-1,-1) in ENTITY_SPRITES_DICT:
            ENTITY_SPRITES_DICT[-1,-1].append(entity_obj)
        else:
            ENTITY_SPRITES_DICT[-1,-1] = [entity_obj]

        return True;

    def door_walk(to_coords, from_coords, entity_obj):
        global PLAYER_LOC, ENTITY_SPRITES, ENTITY_SPRITES_DICT
        global MAP_DOOR_COUNT, CUR_MAP_INDEX

        #print("moving player")
        #print(SPAWN_LOC)
        PLAYER_LOC = to_coords
        draw_player()
        time.sleep(0.3)

        #print("changing to closed door")
        ENTITY_SPRITES_DICT[to_coords][0]['map_tile_name'] = "green_door_closed"

        entity_sprite = displayio.TileGrid(sprite_sheet, pixel_shader=palette,
                                            width = 1,
                                            height = 1,
                                            tile_width = 16,
                                            tile_height = 16,
                                            default_tile = TILES["green_door_closed"]['sprite_index'])
        sprite_group.remove(ENTITY_SPRITES[entity_obj["entity_sprite_index"]])
        sprite_group.insert(entity_obj["entity_sprite_index"], entity_sprite)
        ENTITY_SPRITES[entity_obj["entity_sprite_index"]] = entity_sprite


        PLAYER_LOC = SPAWN_LOC
        draw_player()

        MAP_DOOR_COUNT -= 1

        if MAP_DOOR_COUNT == 0:
            # you win
            text_area.text = "You Win\n =D"
            text_area.y = int(128/2 - 30)
            group.append(splash)
            time.sleep(2)
            group.remove(splash)
            CUR_MAP_INDEX += 1
            if CUR_MAP_INDEX >= len(MAP_LIST):
                CUR_MAP_INDEX = 0
            load_map(MAP_LIST[CUR_MAP_INDEX])

        return False

    def heart_walk(to_coords, from_coords, entity_obj):
        global PLAYER_LOC, CUR_MAP_INDEX
        print("inside heart_walk")
        print("%s -> %s" % (from_coords, to_coords))

        # you win
        text_area.text = "You Win\n =D"
        text_area.y = int(128/2 - 30)
        group.append(splash)
        time.sleep(2)
        group.remove(splash)
        CUR_MAP_INDEX += 1
        if CUR_MAP_INDEX >= len(MAP_LIST):
            CUR_MAP_INDEX = 0
        load_map(MAP_LIST[CUR_MAP_INDEX])


    def move_boots(now):
        global LAST_BOOT_MOVE_DICT

        #ignore_locs = {}
        new_last_moved_times = {}
        #print("inside move_boots()")
        for loc in ENTITY_SPRITES_DICT.keys():
            for entity_obj in ENTITY_SPRITES_DICT[loc]:
                if "boot" in entity_obj['map_tile_name']:
                    if LAST_BOOT_MOVE_DICT[entity_obj["map_tile_name"]] + TILES[entity_obj["map_tile_name"]]['delay'] <= now:
                    #if loc not in ignore_locs:
                        if "movement" in TILES[entity_obj["map_tile_name"]].keys():
                        #print("possible loc %s" % (loc[0] + 1))
                            if loc[0] + TILES[entity_obj["map_tile_name"]]['movement'] >= MAP_WIDTH:
                                new_loc = 0
                            elif loc[0] + TILES[entity_obj["map_tile_name"]]['movement'] < 0:
                                new_loc = MAP_WIDTH-1
                            else:
                                new_loc = loc[0] + TILES[entity_obj["map_tile_name"]]['movement']
                        else:
                            if loc[0] + 1 < MAP_WIDTH:
                                new_loc = loc[0] + 1
                            else:
                                new_loc = 0
                        #print("moving boot %s -> %s" % (loc, (new_loc, loc[1])))
                        #if (new_loc, loc[1]) in ignore_locs:
                        #    ignore_locs[(new_loc, loc[1])] += 1
                        #else:
                        #    ignore_locs[(new_loc, loc[1])] = 1
                        remove_entity(entity_obj, loc)
                        add_entity(entity_obj, (new_loc, loc[1]))
    #                    future_spawn_obj = {
    #                        "entity_obj": entity_obj,
    #                        "loc": (new_loc, loc[1]),
    #                        "time": now
    #                    }
    #                   NEED_TO_SPAWN_BOOTS.append(future_spawn_obj)
                        #    "time": now + 0.25
                    #else:
                        #ignore_locs[loc] -= 1
                        #print("ignoring boot, new count: %s" % ignore_locs[loc])
                        #if ignore_locs[loc] == 0:
                            #del ignore_locs[loc]

                        new_last_moved_times[entity_obj["map_tile_name"]] = now
        for tile_name in new_last_moved_times.keys():
            LAST_BOOT_MOVE_DICT[tile_name] = new_last_moved_times[tile_name]
    def check_future_spawns(now):
        for future_spawn_obj in NEED_TO_SPAWN_BOOTS:
            if now >= future_spawn_obj['time']:
                add_entity(future_spawn_obj['entity_obj'], future_spawn_obj['loc'])
                NEED_TO_SPAWN_BOOTS.remove(future_spawn_obj)

    def check_collide():
        if PLAYER_LOC in ENTITY_SPRITES_DICT.keys():
            #print(ENTITY_SPRITES_DICT[PLAYER_LOC])
            sprites_at_loc = ENTITY_SPRITES_DICT[PLAYER_LOC]
            for sprite in sprites_at_loc:
                if "boot" in sprite['map_tile_name']:
                    time.sleep(0.5)
                    text_area.text = "Game Over\nSnek has been\nstep on"
                    text_area.y = int(128/2 - 30)
                    group.append(splash)
                    time.sleep(2)
                    group.remove(splash)
                    load_map(MAP_LIST[CUR_MAP_INDEX])

    def add_entity(entity_obj, to_loc):
        global ENTITY_SPRITES_DICT
        # check if there are etity(s) at the tile we are trying to push to.
        if to_loc in ENTITY_SPRITES_DICT:
            # append the thing we are pushing to the the list at the new coordinates in the dictionary
            ENTITY_SPRITES_DICT[to_loc].append(entity_obj)
        else:
            # create a list with the thing we are pushing and store it in the dictionary
            ENTITY_SPRITES_DICT[to_loc] = [entity_obj]


    def remove_entity(entity_obj, from_loc):
        global ENTITY_SPRITES_DICT
        # remove the thing we are pushing from it's old location
        ENTITY_SPRITES_DICT[from_loc].remove(entity_obj)

        # if there are no entities left in the old location
        if len(ENTITY_SPRITES_DICT[from_loc]) == 0:
            # delete the empty lyst
            del ENTITY_SPRITES_DICT[from_loc]


    # main dictionary that maps tile type strings to objects.
    # each one stores the sprite_sheet index and any necessary
    # behavioral stats like can_walk or before_move
    TILES = {
        # empty strings default to floor and no walk.
        "": {
            "sprite_index": 52,
            "can_walk": False
        },
        "empty": {
            "sprite_index": 52,
            "can_walk": False
        },
        "sidewalk": {
            "sprite_index": 19,
            "can_walk": True
        },
        "boot": {
            "sprite_index": 21,
            "can_walk": True,
            "entity":True,
            "delay": 1.2
        },
        "boot_flip_flop": {
            "sprite_index": 22,
            "can_walk": True,
            "entity":True,
            "delay": 1.5
        },
        "boot_converse": {
            "sprite_index": 23,
            "can_walk": True,
            "entity":True,
            "movement": -1,
            "delay": 0.9
        },
        "paper_box": {
            "sprite_index": 24,
            "can_walk": False,
            "entity": True,
        },
        "vendor": {
            "sprite_index": 8,
            "can_walk": False,
            "entity": True,
        },
        "transit_kiosk": {
            "sprite_index": 0,
            "can_walk": False,
            "entity": True,
        },
        "vendor_umbrella": {
            "sprite_index": 2,
            "can_walk": False,
            "entity": False,
        },
        "heart": {
            "sprite_index": 50,
            "can_walk": True,
            "entity": True,
            "before_move": heart_walk
        },
        "player": {
            "sprite_index": 48,
            "entity": True,
        },
        "grey_right_wall": {
            "sprite_index": 47,
            "can_walk": False,
        },
        "grey_front_wall": {
            "sprite_index": 46,
            "can_walk": False,
        },
        "grey_left_wall": {
            "sprite_index": 45,
            "can_walk": False,
        },
        "grey_right_top_edge": {
            "sprite_index": 41,
            "can_walk": False,
        },
        "grey_front_top_edge": {
            "sprite_index": 40,
            "can_walk": False,
        },
        "grey_left_top_edge": {
            "sprite_index": 39,
            "can_walk": False,
        },

        "grey_right_roof": {
            "sprite_index": 35,
            "can_walk": False,
        },
        "grey_front_roof": {
            "sprite_index": 34,
            "can_walk": False,
        },
        "grey_left_roof": {
            "sprite_index": 33,
            "can_walk": False,
        },

        "brick_right_wall": {
            "sprite_index": 44,
            "can_walk": False,
        },
        "brick_front_wall": {
            "sprite_index": 43,
            "can_walk": False,
        },
        "brick_left_wall": {
            "sprite_index": 42,
            "can_walk": False,
        },

        "brick_right_top_edge": {
            "sprite_index": 38,
            "can_walk": False,
        },
        "brick_front_top_edge": {
            "sprite_index": 37,
            "can_walk": False,
        },
        "brick_left_top_edge": {
            "sprite_index": 36,
            "can_walk": False,
        },

        "brick_right_roof": {
            "sprite_index": 32,
            "can_walk": False,
        },
        "brick_front_roof": {
            "sprite_index": 31,
            "can_walk": False,
        },
        "brick_left_roof": {
            "sprite_index": 30,
            "can_walk": False,
        },
        "green_door_closed": {
            "sprite_index": 29,
            "can_walk": False,
            "entity": True,
        },
        "green_door_open": {
            "sprite_index": 28,
            "entity": True,
            "before_move": door_walk
        }

    }


    for tile_name in TILES.keys():
        if "boot" in tile_name:
            LAST_BOOT_MOVE_DICT[tile_name] = 0

    # Badger object for easy button handling
    #badger = PyBadger()

    # display object variable
    #display = board.DISPLAY

    # Load the sprite sheet (bitmap)
    sprite_sheet, palette = adafruit_imageload.load("no_step_snek_sprite_sheet.bmp",
                                                    bitmap=displayio.Bitmap,
                                                    palette=displayio.Palette)

    # make bright pink be transparent so entities can be drawn on top of map tiles
    palette.make_transparent(0)

    # Create the castle TileGrid
    castle = displayio.TileGrid(sprite_sheet, pixel_shader=palette,
                                width = 10,
                                height = 8,
                                tile_width = 16,
                                tile_height = 16)



    # Create a Group to hold the castle and add it
    castle_group = displayio.Group()
    castle_group.append(castle)

    sprite_group = displayio.Group()

    # Create a Group to hold the sprite and castle
    group = displayio.Group(scale=3)

    # Add the sprite and castle to the group
    group.append(castle_group)



    # Make the display context
    splash = displayio.Group()

    # Draw a green background
    color_bitmap = displayio.Bitmap(160, 128, 1)
    color_palette = displayio.Palette(1)
    color_palette[0] = 0x000077

    bg_sprite = displayio.TileGrid(color_bitmap,
                                pixel_shader=color_palette,
                                x=0, y=0)

    splash.append(bg_sprite)

    # Draw a smaller inner rectangle
    inner_bitmap = displayio.Bitmap(160-30, 128-30, 1)
    inner_palette = displayio.Palette(1)
    inner_palette[0] = 0xAA0088 # Purple
    inner_sprite = displayio.TileGrid(inner_bitmap,
                                    pixel_shader=inner_palette,
                                    x=15, y=15)
    splash.append(inner_sprite)

    # Draw a label
    text_group = displayio.Group(scale=1, x=24, y=24)

    text = "Game Over"
    text_area = label.Label(terminalio.FONT, text=" "*64, color=0xFFFF00)
    text_area.text = text
    text_group.append(text_area) # Subgroup for text scaling
    splash.append(text_group)

    sprite = None

    #group.append(splash)

    def load_map(file_name):
        global sprite, ORIGINAL_MAP, CURRENT_MAP, ENTITY_SPRITES
        global ENTITY_SPRITES_DICT, INVENTORY, PLAYER_LOC, sprite_group
        global CAMERA_VIEW, MAP_HEIGHT, MAP_WIDTH
        global group, NEED_TO_SPAWN_BOOTS, SPAWN_LOC
        global MAP_DOOR_COUNT


        for cur_s in ENTITY_SPRITES:
            sprite_group.remove(cur_s)
        try:
            sprite_group.remove(sprite)
        except:
            pass

        ORIGINAL_MAP = {}
        CURRENT_MAP = {}
        ENTITY_SPRITES = []
        ENTITY_SPRITES_DICT = {}
        NEED_TO_SPAWN_BOOTS = []
        NEED_TO_SPAWN_BOOTS = []
        CAMERA_VIEW = {}
        INVENTORY = []
        MAP_DOOR_COUNT = 0

        # Open and read raw string from the map csv file
        f = open(file_name, 'r')
        map_csv_str = f.read()
        f.close()

        # split the raw string into lines
        map_csv_lines = map_csv_str.replace("\r", "").split("\n")

        # if the last row is empty then remove it
        if len(map_csv_lines[-1]) == 0:
            del map_csv_lines[-1]

        # set the WIDTH and HEIGHT variables.
        # this assumes the map is rectangular.
        MAP_HEIGHT = len(map_csv_lines)
        MAP_WIDTH = len(map_csv_lines[0].split(","))

        #print(TILES.keys())
        #print(map_csv_lines)
        print('\nLoading Map',end="")

        # loop over each line storing index in y variable
        kount = 0
        for y, line in enumerate(map_csv_lines):
            # ignore empty line
            if line != "":
                # loop over each tile type separated by commas, storing index in x variable
                for x, tile_name in enumerate(line.split(",")):
                    #print("%s '%s'" % (len(tile_name), str(tile_name)))
                    kount += 1
                    if kount%20 == 0:
                        print(".",end="")

                    # if the tile exists in our main dictionary
                    if tile_name in TILES.keys():

                        # if the tile is an entity
                        if 'entity' in TILES[tile_name].keys() and TILES[tile_name]['entity']:
                            if tile_name == "chip":
                                MAP_CHIP_COUNT += 1
                            # set the map tiles to floor
                            ORIGINAL_MAP[x,y] = "sidewalk"
                            CURRENT_MAP[x,y] = "sidewalk"

                            # if it's the player
                            if tile_name == "player":
                                # Create the sprite TileGrid
                                sprite = displayio.TileGrid(sprite_sheet, pixel_shader=palette,
                                    width = 1,
                                    height = 1,
                                    tile_width = 16,
                                    tile_height = 16,
                                    default_tile = TILES[tile_name]['sprite_index'])

                                # set the position of sprite on screen
                                sprite.x = x*16
                                sprite.y = y*16

                                # set position in x,y tile coords for reference later
                                PLAYER_LOC = (x,y)
                                SPAWN_LOC = (x,y)

                                # add sprite to the group
                                sprite_group.append(sprite)
                            else: # not the player

                                if tile_name.endswith("door_open"):
                                    MAP_DOOR_COUNT += 1
                                # Create the sprite TileGrid
                                entity_srite = displayio.TileGrid(sprite_sheet, pixel_shader=palette,
                                            width = 1,
                                            height = 1,
                                            tile_width = 16,
                                            tile_height = 16,
                                            default_tile = TILES[tile_name]['sprite_index'])
                                # set the position of sprite on screen
                                # default to offscreen
                                entity_srite.x = -16
                                entity_srite.y = -16

                                # add the sprite object to ENTITY_SPRITES list
                                ENTITY_SPRITES.append(entity_srite)
                                #print("setting entity_sprites_dict[%s,%s]" % (x,y))

                                # create an entity obj
                                entity_obj = {
                                    "entity_sprite_index": len(ENTITY_SPRITES) - 1,
                                    "map_tile_name": tile_name
                                }

                                # if there are no entities at this location yet
                                if (x,y) not in ENTITY_SPRITES_DICT:
                                    # create a list and add it to the dictionary at the x,y location
                                    ENTITY_SPRITES_DICT[x, y] = [entity_obj]
                                else:
                                    # append the entity to the existing list in the dictionary
                                    ENTITY_SPRITES_DICT[x, y].append(entity_obj)

                        else: # tile is not entity
                            # set the tile_name into MAP dictionaries
                            ORIGINAL_MAP[x, y] = tile_name
                            CURRENT_MAP[x, y] = tile_name

                    else: # tile type wasn't found in dict
                        print("tile: %s not found in TILES dict" % tile_name)
        print()

        # add all entity sprites to the group
        for entity in ENTITY_SPRITES:
            sprite_group.append(entity)

    # Add the Group to the Display

    load_map(MAP_LIST[CUR_MAP_INDEX])
    group.append(sprite_group)

    display.root_group=group
    # variables to store previous value of button state
    prev_up = False
    prev_down = False
    prev_left = False
    prev_right = False

    prev_b = False
    prev_a = False
    prev_start = False
    prev_select = False

    # helper function returns true if player is allowed to move given direction
    # based on can_walk property of the tiles next to the player
    def can_player_move(direction):
        if direction == UP:
            if PLAYER_LOC[1] - 1 < 0:
                return False
            tile_above_coords = (PLAYER_LOC[0], PLAYER_LOC[1] - 1)
            result = TILES[CURRENT_MAP[tile_above_coords[0], tile_above_coords[1]]]['can_walk']
            if not result:
                return result


            if tile_above_coords in ENTITY_SPRITES_DICT.keys():
                for entity in ENTITY_SPRITES_DICT[tile_above_coords]:
                    if "can_walk" in TILES[entity['map_tile_name']]:
                        if TILES[entity['map_tile_name']]["can_walk"] == False:
                            return False
            return result

        if direction == DOWN:
            print("%s - %s" % (PLAYER_LOC[1] + 1, MAP_HEIGHT-1))
            if PLAYER_LOC[1] + 1 > MAP_HEIGHT-1:
                return False
            tile_below_coords = (PLAYER_LOC[0], PLAYER_LOC[1] + 1)
            result =  TILES[CURRENT_MAP[tile_below_coords[0], tile_below_coords[1]]]['can_walk']
            if not result:
                return result

            if tile_below_coords in ENTITY_SPRITES_DICT.keys():
                for entity in ENTITY_SPRITES_DICT[tile_below_coords]:
                    if "can_walk" in TILES[entity['map_tile_name']]:
                        if TILES[entity['map_tile_name']]["can_walk"] == False:
                            return False
            return result

        if direction == LEFT:
            if PLAYER_LOC[0]-1 < 0:
                return False
            tile_left_of_coords = (PLAYER_LOC[0]-1, PLAYER_LOC[1])
            result = TILES[CURRENT_MAP[tile_left_of_coords[0], tile_left_of_coords[1]]]['can_walk']
            if not result:
                return result

            if tile_left_of_coords in ENTITY_SPRITES_DICT.keys():
                for entity in ENTITY_SPRITES_DICT[tile_left_of_coords]:
                    if "can_walk" in TILES[entity['map_tile_name']]:
                        if TILES[entity['map_tile_name']]["can_walk"] == False:
                            return False
            return result
        if direction == RIGHT:
            if PLAYER_LOC[0]+1 > MAP_WIDTH -1:
                return False
            tile_right_of_coords = (PLAYER_LOC[0] + 1, PLAYER_LOC[1])
            result = TILES[CURRENT_MAP[tile_right_of_coords[0], tile_right_of_coords[1]]]['can_walk']

            if not result:
                return result

            if tile_right_of_coords in ENTITY_SPRITES_DICT.keys():
                for entity in ENTITY_SPRITES_DICT[tile_right_of_coords]:
                    if "can_walk" in TILES[entity['map_tile_name']]:
                        if TILES[entity['map_tile_name']]["can_walk"] == False:
                            return False
            return result

    # set the appropriate tiles into the CAMERA_VIEW dictionary
    # based on given starting coords and size
    def set_camera_view(startX, startY, width, height):
        global CAMERA_OFFSET_X
        global CAMERA_OFFSET_Y
        # set the offset variables for use in other parts of the code
        CAMERA_OFFSET_X = startX
        CAMERA_OFFSET_Y = startY

        # loop over the rows and indexes in the desired size section
        for y_index, y in enumerate(range(startY, startY+height)):
            # loop over columns and indexes in the desired size section
            for x_index, x in enumerate(range(startX, startX+width)):
                #print("setting camera_view[%s,%s]" % (x_index,y_index))
                try:
                    # set the tile at the current coordinate of the MAP into the CAMERA_VIEW
                    CAMERA_VIEW[x_index,y_index] = CURRENT_MAP[x,y]
                except KeyError:
                    # if coordinate is out of bounds set it to empty by default
                    CAMERA_VIEW[x_index,y_index] = "empty"


    def move_player(x_offset, y_offset):
        global PLAYER_LOC
        # variable to store if player is allowed to move
        can_move = False

        # coordinates the player is moving to
        moving_to_coords = (PLAYER_LOC[0] + x_offset, PLAYER_LOC[1] + y_offset)

        # tile name of the spot player is moving to
        moving_to_tile_name = CURRENT_MAP[moving_to_coords[0], moving_to_coords[1]]
        #print("moving to %s checking before_move" % moving_to_tile_name )
        # if there are entity(s) at spot the player is moving to
        if moving_to_coords in ENTITY_SPRITES_DICT:
            #print("found entity(s) where we are moving to")

            # loop over all entities at the location player is moving to
            for entity_obj in ENTITY_SPRITES_DICT[moving_to_coords]:
                #print("checking entity %s" % entity_obj["map_tile_name"])

                # if the entity has a before_move behavior function
                if "before_move" in TILES[entity_obj["map_tile_name"]].keys():
                    #print("calling before_move %s, %s, %s" % (moving_to_coords,PLAYER_LOC,entity_obj))

                    # call the before_move behavior function act upon it's result
                    if TILES[entity_obj["map_tile_name"]]['before_move'](moving_to_coords,PLAYER_LOC,entity_obj):
                        # all the movement if it returned true
                        can_move = True
                    #else:
                        # pass and don't allow movement if it returned false
                        #pass
                else: # entity does not have a before_move function
                    # allow movement
                    can_move = True

        else: # no entities at the location player is moving to
            # check if the tile has a before_move behavior function
            if "before_move" in TILES[moving_to_tile_name].keys():
                if TILES[moving_to_tile_name]['before_move'](moving_to_coords,PLAYER_LOC, moving_to_tile_name):
                    # allow the movement if it returned true
                    can_move = True
                #else:
                    # break and don't allow movement if it returned false
                    #pass
            else:
                can_move = True
        # if player is allowed to move
        if can_move:
            #print("Player is allowed to move, changing coords")
            # set the player loc variable to the new coords
            PLAYER_LOC = moving_to_coords
        #else:
            #print("Player is not allowed to move")

    def draw_player():
        #print("inside draw player")
        player_screen_x = PLAYER_LOC[0] - CAMERA_OFFSET_X
        player_screen_y = PLAYER_LOC[1] - CAMERA_OFFSET_Y
        #print("setting player loc %s, %s" % (player_screen_x, player_screen_y))
        sprite.x = player_screen_x*16
        sprite.y = player_screen_y*16

    # draw the current CAMERA_VIEW dictionary and the ENTITY_SPRITES_DICT
    def draw_camera_view():
        # list that will hold all entities that have been drawn based on their MAP location
        # any entities not in this list should get moved off the screen
        drew_entities = []
        #print(CAMERA_VIEW)

        # loop over y tile coordinates
        for y in range(0, SCREEN_HEIGHT_TILES):
            # loop over x tile coordinates
            for x in range(0, SCREEN_WIDTH_TILES):
                # tile name at this location
                tile_name = CAMERA_VIEW[x,y]

                # if tile exists in the main dictionary
                if tile_name in TILES.keys():
                    # if there are entity(s) at this location
                    if (x + CAMERA_OFFSET_X, y + CAMERA_OFFSET_Y) in ENTITY_SPRITES_DICT:
                        # default background for entities is floor
                        #castle[x, y] = TILES["sidewalk"]['sprite_index']
                        castle[x, y] = TILES[ORIGINAL_MAP[x + CAMERA_OFFSET_X,y+ CAMERA_OFFSET_Y]]['sprite_index']
                        # if it's not the player
                        if tile_name != "player":
                            # loop over all entities at this location
                            for entity_obj_at_tile in ENTITY_SPRITES_DICT[x + CAMERA_OFFSET_X, y + CAMERA_OFFSET_Y]:
                                # set appropriate x,y screen coordinates based on tile coordinates
                                ENTITY_SPRITES[int(entity_obj_at_tile["entity_sprite_index"])].x = x * 16
                                ENTITY_SPRITES[int(entity_obj_at_tile["entity_sprite_index"])].y = y * 16

                                # add the index of the entity sprite to the drew_entities list so we know not to hide it later.
                                drew_entities.append(entity_obj_at_tile["entity_sprite_index"])

                    else: # no entities at this location
                        # set the sprite index of this tile into the CASTLE dictionary
                        #print(TILES[tile_name]['sprite_index'])
                        castle[x, y] = TILES[tile_name]['sprite_index']

                else: # tile type not found in main dictionary
                    # default to floor tile
                    castle[x, y] = TILES["sidewalk"]['sprite_index']

                # if the player is at this x,y tile coordinate accounting for camera offset
                if PLAYER_LOC == ((x + CAMERA_OFFSET_X, y + CAMERA_OFFSET_Y)):
                    # set player sprite screen coordinates
                    sprite.x = x*16
                    sprite.y = y*16

        # loop over all entity sprites
        for index in range(0, len(ENTITY_SPRITES)):
            # if the sprite wasn't drawn then it's outside the camera view
            if index not in drew_entities:
                # hide the sprite by moving it off screen
                ENTITY_SPRITES[index].x = int(-16)
                ENTITY_SPRITES[index].y = int(-16)

    # variable to store timestamp of last drawn frame
    last_update_time = 0

    # variables to store movement offset values
    x_offset = 0
    y_offset = 0

    # main loop
    cur_up = False
    cur_down = False
    cur_right = False
    cur_left = False
    cur_a = False
    cur_b = False
    cur_start = False
    cur_select = False

    try:
        while True:
            # auto dim the screen
            #badger.auto_dim_display(delay=10, check_buttons=True)

            # set the current button values into variables
            #cur_up = badger.button.up
            #cur_down = badger.button.down
            #cur_right = badger.button.right
            #cur_left = badger.button.left

            #cur_a = badger.button.a
            #cur_b = badger.button.b
            #cur_start = badger.button.start
            #cur_select = badger.button.select

            if sba():
                key = stdin.read(1)
            else:
                key = ""

            if key == '\x1b':
                arrow = stdin.read(2)[1]
                if arrow == 'A':
                    prev_up = True
                elif arrow == 'B':
                    prev_down = True
                elif arrow == 'C':
                    prev_right = True
                elif arrow == 'D':
                    prev_left = True
            elif key.upper() == 'A':
                prev_a = True
            elif key.upper() == 'B':
                prev_b = True
            elif key.upper() == 'S':
                prev_start = True
            elif key.upper() == 'Q':
                display.root_group=displayio.CIRCUITPYTHON_TERMINAL
                break

            # check for start button press / release
            if not cur_start and prev_start:
                text_area.text = "Press B\nto Restart"
                text_area.y = int(128/2 - 30)
                group.append(splash)
                HIDE_SPLASH_TIME = now + 3

            if not cur_b and prev_b:
                if HIDE_SPLASH_TIME > now:
                    if text_area.text == "Press B\nto Restart":
                        HIDE_SPLASH_TIME = -1
                        group.remove(splash)
                        load_map(MAP_LIST[CUR_MAP_INDEX])

            # check for up button press / release
            if not cur_up and prev_up:
                if can_player_move(UP):
                    x_offset = 0
                    y_offset = - 1

            # check for down button press / release
            if not cur_down and prev_down:
                if can_player_move(DOWN):
                    x_offset = 0
                    y_offset = 1

            # check for right button press / release
            if not cur_right and prev_right:
                if can_player_move(RIGHT):
                    x_offset = 1
                    y_offset = 0

            # check for left button press / release
            if not cur_left and prev_left:
                if can_player_move(LEFT):
                    x_offset = -1
                    y_offset = 0

            # if any offset is not zero then we need to process player movement
            if x_offset != 0 or y_offset != 0:
                move_player(x_offset, y_offset)

            # reset movement offset variables
            y_offset = 0
            x_offset = 0

            # set previos button values for next iteration
            prev_up = cur_up
            prev_down = cur_down
            prev_right = cur_right
            prev_left = cur_left

            prev_select = cur_select
            prev_start = cur_start
            prev_a = cur_a
            prev_b = cur_b

            # current time
            now = time.monotonic()

            # if it has been long enough based on FPS delay
            if now >= last_update_time + FPS_DELAY:

                move_boots(now)
                #check_future_spawns(now)


                set_camera_view(
                    max(min(PLAYER_LOC[0]-4,MAP_WIDTH-SCREEN_WIDTH_TILES),0),
                    max(min(PLAYER_LOC[1]-3,MAP_HEIGHT-SCREEN_HEIGHT_TILES),0),
                    10,
                    8
                )

                # draw the camera
                draw_camera_view()

                # check for collisions after drawing so player can see the collision
                check_collide()

                # store the last update time
                last_update_time = now

                if HIDE_SPLASH_TIME != -1:
                    if HIDE_SPLASH_TIME < now:
                        group.remove(splash)
                        HIDE_SPLASH_TIME = -1

            else:
                # draw the camera
                draw_camera_view()

    except KeyboardInterrupt:
        display.root_group=displayio.CIRCUITPYTHON_TERMINAL


try:
    type(envVars)
except:
    envVars = {}

snek(envVars)

del sprite, ORIGINAL_MAP, CURRENT_MAP, ENTITY_SPRITES
del ENTITY_SPRITES_DICT, INVENTORY, PLAYER_LOC, sprite_group
del CAMERA_VIEW, MAP_HEIGHT, MAP_WIDTH
del group, NEED_TO_SPAWN_BOOTS, SPAWN_LOC
del MAP_DOOR_COUNT
del LAST_BOOT_MOVE_DICT
del CUR_MAP_INDEX
del CAMERA_OFFSET_X
del CAMERA_OFFSET_Y

supervisor.reload()
