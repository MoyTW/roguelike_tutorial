import libtcodpy as libtcod
import math
import textwrap

SCREEN_WIDTH = 80
SCREEN_HEIGHT = 50
LIMIT_FPS = 20

FOV_ALGO = 0
FOV_LIGHT_WALLS = True
TORCH_RADIUS = 10

BAR_WIDTH = 20
PANEL_HEIGHT = 7
PANEL_Y = SCREEN_HEIGHT - PANEL_HEIGHT

MSG_X = BAR_WIDTH + 2
MSG_WIDTH = SCREEN_WIDTH - BAR_WIDTH - 2
MSG_HEIGHT = PANEL_HEIGHT - 1

# ================================================== MAP SECTION =================================================
MAP_WIDTH = 80
MAP_HEIGHT = 43

ROOM_MAX_SIZE = 10
ROOM_MIN_SIZE = 6
MAX_ROOMS = 30

MAX_ROOM_MONSTERS = 3

color_dark_wall = libtcod.Color(0, 0, 100)
color_light_wall = libtcod.Color(130, 110, 50)
color_dark_ground = libtcod.Color(50, 50, 100)
color_light_ground = libtcod.Color(200, 180, 50)


class Tile(object):
    def __init__(self, blocked, block_sight=None):
        self.blocked = blocked
        self.explored = False

        # That's...basically shadowing. Reassignment! Hiss! Boo!
        if block_sight is None:
            block_sight = blocked
        self.block_sight = block_sight


class Rect(object):
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h

    def center(self):
        return (self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2

    def intersect(self, other):
        return self.x1 <= other.x2 and self.x2 >= other.x1 and self.y1 <= other.y2 and self.y2 >= other.y1


def is_blocked(x, y):
    if game_map[x][y].blocked:
        return True
    for o in objects:
        if o.blocks and o.x == x and o.y == y:
            return True
    return False


def create_room(room):
    # TODO: Fix this scoping issue
    global game_map
    for x in range(room.x1 + 1, room.x2):
        for y in range(room.y1 + 1, room.y2):
            game_map[x][y].blocked = False
            game_map[x][y].block_sight = False


def create_h_tunnel(x1, x2, y):
    # TODO: Scoping
    global game_map
    for x in range(min(x1, x2), max(x1, x2) + 1):
        game_map[x][y].blocked = False
        game_map[x][y].block_sight = False


def create_v_tunnel(y1, y2, x):
    # TODO: lol scope
    global game_map
    for y in range(min(y1, y2), max(y1, y2) + 1):
        game_map[x][y].blocked = False
        game_map[x][y].block_sight = False


def place_objects(room):
    num_monsters = libtcod.random_get_int(0, 0, MAX_ROOM_MONSTERS)

    for _ in range(num_monsters):
        x = libtcod.random_get_int(0, room.x1 + 1, room.x2 - 1)
        y = libtcod.random_get_int(0, room.y1 + 1, room.y2 - 1)

        if not is_blocked(x, y):
            if libtcod.random_get_int(0, 0, 100) < 80:
                fighter_component = Fighter(hp=10, defense=0, power=3, death_function=monster_death)
                ai_component = BasicMonster()

                monster = Object(x, y, 'o', 'orc', libtcod.desaturated_green, blocks=True, fighter=fighter_component,
                                 ai=ai_component)
            else:
                fighter_component = Fighter(hp=10, defense=0, power=3, death_function=monster_death)
                ai_component = BasicMonster()

                monster = Object(x, y, 'T', 'troll', libtcod.darker_green, blocks=True, fighter=fighter_component,
                                 ai=ai_component)

            objects.append(monster)


def render_bar(x, y, total_width, name, value, maximum, bar_color, back_color):
    bar_width = int(float(value) / maximum * total_width)

    # render background
    libtcod.console_set_default_background(panel, back_color)
    libtcod.console_rect(panel, x, y, total_width, 1, False, libtcod.BKGND_SCREEN)

    # render bar
    libtcod.console_set_default_background(panel, bar_color)
    if bar_width > 0:
        libtcod.console_rect(panel, x, y, bar_width, 1, False, libtcod.BKGND_SCREEN)

    # text
    libtcod.console_set_default_foreground(panel, libtcod.white)
    libtcod.console_print_ex(panel, x + total_width / 2, y, libtcod.BKGND_NONE, libtcod.CENTER,
                             name + ': ' + str(value) + '/' + str(maximum))


def make_game_map():
    # OH GOD! WHAT IS SCOPE EVEN
    global game_map

    game_map = [[Tile(True)
                 for _ in range(MAP_HEIGHT)]
                for _ in range(MAP_WIDTH)]

    rooms = []
    # You could just use the count of rooms here, couldn't you?
    num_rooms = 0

    for r in range(MAX_ROOMS):
        # Size of room
        w = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        h = libtcod.random_get_int(0, ROOM_MIN_SIZE, ROOM_MAX_SIZE)
        # Position of room
        x = libtcod.random_get_int(0, 0, MAP_WIDTH - w - 1)
        y = libtcod.random_get_int(0, 0, MAP_HEIGHT - h - 1)

        new_room = Rect(x, y, w, h)

        failed = False
        for other_room in rooms:
            if new_room.intersect(other_room):
                failed = True
                break

        if not failed:
            create_room(new_room)
            (new_x, new_y) = new_room.center()

            place_objects(new_room)

            if num_rooms == 0:
                player.x = new_x
                player.y = new_y
            else:
                # Connect to the last room in the room vector
                (prev_x, prev_y) = rooms[num_rooms - 1].center()

                if libtcod.random_get_int(0, 0, 1):
                    create_h_tunnel(prev_x, new_x, prev_y)
                    create_v_tunnel(prev_y, new_y, new_x)
                else:
                    create_v_tunnel(prev_y, new_y, new_x)
                    create_h_tunnel(prev_x, new_x, prev_y)

            rooms.append(new_room)
            num_rooms += 1


# Object is using 'con' as the buffer, which is unbound! Does that...work?
class Object(object):
    def __init__(self, x, y, char, name, color, blocks=False, fighter=None, ai=None):
        self.x = x
        self.y = y
        self.char = char
        self.name = name
        self.color = color
        self.blocks = blocks
        self.fighter = fighter

        if self.fighter:
            self.fighter.owner = self
        self.ai = ai

        if self.ai:
            self.ai.owner = self

    def move(self, dx, dy):
        # SCOPING DEAR OH GOD WHY FIX THIS AFTER THE TUTORIAL
        if not is_blocked(self.x + dx, self.y + dy):
            self.x += dx
            self.y += dy

    # TODO: Pull AI logic out of base Object class!
    # TODO: Take other instead of x/y!
    def move_towards(self, target_x, target_y):
        dx = target_x - self.x
        dy = target_y - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)

        dx = int(round(dx / distance))
        dy = int(round(dy / distance))
        self.move(dx, dy)

    def distance_to(self, other):
        dx = other.x - self.x
        dy = other.y - self.y
        return math.sqrt(dx ** 2 + dy ** 2)

    # TODO: Have draw take the buffer to draw to as a parameter!
    def draw(self):
        if libtcod.map_is_in_fov(fov_map, self.x, self.y):
            libtcod.console_set_default_foreground(con, self.color)
            libtcod.console_put_char(con, self.x, self.y, self.char, libtcod.BKGND_NONE)

    # TODO: Have clear take the buffer to draw to as a parameter!
    def clear(self):
        libtcod.console_put_char(con, self.x, self.y, ' ', libtcod.BKGND_NONE)

    def send_to_back(self):
        global objects
        objects.remove(self)
        objects.insert(0, self)


class Fighter(object):
    def __init__(self, hp, defense, power, death_function=None):
        self.max_hp = hp
        self.hp = hp
        self.defense = defense
        self.power = power
        self.death_function = death_function

    def attack(self, target):
        damage = self.power - target.fighter.defense
        if damage > 0:
            message(self.owner.name.capitalize() + ' attacks ' + target.name + ' for ' + str(damage), libtcod.yellow)
            target.fighter.take_damage(damage)
        else:
            message(self.owner.name.capitalize() + ' attacks ' + target.name + ' but it does no damage', libtcod.green)

    def take_damage(self, damage):
        if damage > 0:
            self.hp -= damage

        if self.hp == 0:
            function = self.death_function
            if function is not None:
                function(self.owner)


class BasicMonster(object):
    def take_turn(self):
        monster = self.owner
        if libtcod.map_is_in_fov(fov_map, monster.x, monster.y):
            if monster.distance_to(player) >= 2:
                monster.move_towards(player.x, player.y)
            elif player.fighter.hp > 0:
                monster.fighter.attack(player)


def player_move_or_attack(dx, dy):
    global fov_recompute

    x = player.x + dx
    y = player.y + dy

    target = None
    for obj in objects:
        if obj.fighter and obj.x == x and obj.y == y:
            target = obj
            break

    if target is not None:
        player.fighter.attack(target)
    else:
        player.move(dx, dy)
        fov_recompute = True


# uuuugh scoping
def handle_keys():
    # TODO: scope
    global fov_recompute

    key = libtcod.console_wait_for_keypress(True)
    if key.vk == libtcod.KEY_ENTER and key.lalt:
        libtcod.console_set_fullscreen(not libtcod.console_is_fullscreen())
    elif key.vk == libtcod.KEY_ESCAPE:
        return 'exit'

    if game_state == 'playing':
        if libtcod.console_is_key_pressed(libtcod.KEY_UP):
            player_move_or_attack(0, -1)
        elif libtcod.console_is_key_pressed(libtcod.KEY_DOWN):
            player_move_or_attack(0, 1)
        elif libtcod.console_is_key_pressed(libtcod.KEY_LEFT):
            player_move_or_attack(-1, 0)
        elif libtcod.console_is_key_pressed(libtcod.KEY_RIGHT):
            player_move_or_attack(1, 0)
        else:
            return 'didnt-take-turn'  # TODO: Enum


def player_death(_):
    global game_state
    message('You died!', libtcod.red)
    game_state = 'dead'  # TODO: Enum

    player.char = '%'
    player.color = libtcod.dark_red


def monster_death(monster):
    message(monster.name.capitalize() + ' is dead!', libtcod.red)
    monster.char = '%'
    monster.color = libtcod.dark_red
    monster.blocks = False
    monster.fighter = None
    monster.ai = None
    monster.name = 'Remains of ' + monster.name
    monster.send_to_back()


def render_all():
    # TODO: scope
    global fov_recompute

    for o in objects:
        if o != player:
            o.draw()
    player.draw()

    if fov_recompute:
        fov_recompute = False
        libtcod.map_compute_fov(fov_map, player.x, player.y, TORCH_RADIUS, FOV_LIGHT_WALLS, FOV_ALGO)

    # Underscore because shadowing
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            visible = libtcod.map_is_in_fov(fov_map, x, y)
            wall = game_map[x][y].block_sight
            if not visible:
                if game_map[x][y].explored:
                    if wall:
                        libtcod.console_set_char_background(con, x, y, color_dark_wall, libtcod.BKGND_SET)
                    else:
                        libtcod.console_set_char_background(con, x, y, color_dark_ground, libtcod.BKGND_SET)
            else:
                if wall:
                    libtcod.console_set_char_background(con, x, y, color_light_wall, libtcod.BKGND_SET)
                else:
                    libtcod.console_set_char_background(con, x, y, color_light_ground, libtcod.BKGND_SET)
                game_map[x][y].explored = True

    libtcod.console_blit(con, 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, 0, 0, 0)

    # Rendering GUI
    libtcod.console_set_default_background(panel, libtcod.black)
    libtcod.console_clear(panel)

    y = 1
    for (line, color) in game_msgs:
        libtcod.console_set_default_foreground(panel, color)
        libtcod.console_print_ex(panel, MSG_X, y, libtcod.BKGND_NONE, libtcod.LEFT, line)
        y += 1

    render_bar(1, 1, BAR_WIDTH, 'HP', player.fighter.hp, player.fighter.max_hp, libtcod.light_red, libtcod.darker_red)
    libtcod.console_blit(panel, 0, 0, SCREEN_WIDTH, PANEL_HEIGHT, 0, 0, PANEL_Y)


def message(new_msg, color=libtcod.white):
    new_msg_lines = textwrap.wrap(new_msg, MSG_WIDTH)

    for line in new_msg_lines:
        if len(game_msgs) == MSG_HEIGHT:
            del game_msgs[0]

        game_msgs.append((line, color))


def clear_objects():
    for o in objects:
        o.clear()

# =================================================== MAIN LOOP ==================================================

# Set font
libtcod.console_set_custom_font('arial10x10.png', libtcod.FONT_TYPE_GREYSCALE | libtcod.FONT_LAYOUT_TCOD)

# Initialize windows/buffers
libtcod.console_init_root(SCREEN_WIDTH, SCREEN_HEIGHT, 'tutorial roguelike! whooo!', False)
con = libtcod.console_new(MAP_WIDTH, MAP_HEIGHT)
panel = libtcod.console_new(SCREEN_WIDTH, PANEL_HEIGHT)

# I don't want this to be real-time, so this line effectively does nothing!
libtcod.sys_set_fps(LIMIT_FPS)

# Initialize Object objects
# TODO: Rename Object lol
player_fighter = Fighter(hp=30, defense=2, power=5, death_function=player_death)
player = Object(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, '@', 'player', libtcod.white, blocks=True, fighter=player_fighter)
objects = [player]

# Init before main loop
make_game_map()

game_state = 'playing'  # TODO: Enum?
player_action = None

fov_recompute = True
fov_map = libtcod.map_new(MAP_WIDTH, MAP_HEIGHT)
for g_y in range(MAP_HEIGHT):
    for g_x in range(MAP_WIDTH):
        libtcod.map_set_properties(fov_map, g_x, g_y, not game_map[g_x][g_y].block_sight,
                                   not game_map[g_x][g_y].blocked)

game_msgs = []
message('Initial Message')

# Main loop (what is exit fn?)
while not libtcod.console_is_window_closed():
    print('turn!')
    libtcod.console_set_default_foreground(0, libtcod.white)

    render_all()
    libtcod.console_flush()
    clear_objects()

    player_action = handle_keys()
    if player_action == 'exit':
        break

    if game_state == 'playing' and player_action != 'didnt-take-turn':
        for o in objects:
            if o.ai:
                o.ai.take_turn()
