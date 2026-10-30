# Copyright (c) 2026 Chris Parrish
# SPDX-License-Identifier: MIT
import gc
import math
import random
import time

VERSION = '1.1'
APP_DIR = '/system/apps/halloween'
ANIMATION_STEP_MS = 40
FRAME_MS = ANIMATION_STEP_MS
RANDOM_BOO_MIN_MS = 45000
RANDOM_BOO_MAX_MS = 150000
BOO_DURATION_MS = 2400
CHARACTERS = ('ghost', 'bats', 'spider', 'pumpkin', 'skull')
MESSAGE_COUNT = 8
SPRITE_COUNTS = (10, 10, 10, 30, 10)
SCARE_FRAMES = BOO_DURATION_MS // ANIMATION_STEP_MS
NORMAL_FRAMES = 6400 // ANIMATION_STEP_MS

badge.caselights(0)
badge.mode(HIRES | VSYNC)
screen.alpha = 255
display.backlight(.7)
badge.default_clear = None


# BEGIN ARTWORK INDEX
ASSETS = {'night': (0, 20627, 320, 240), 'background': (20627, 32575, 320, 240), 'face-0': (53202, 6957, 98, 61), 'face-1': (60159, 7024, 98, 61), 'face-2': (67183, 7029, 98, 61), 'face-3': (74212, 7060, 98, 61), 'face-4': (81272, 7085, 98, 61), 'face-5': (88357, 7102, 98, 61), 'face-6': (95459, 7127, 98, 61), 'face-7': (102586, 7160, 98, 61), 'ghost-0': (109746, 2851, 38, 47), 'ghost-1': (112597, 2899, 38, 47), 'ghost-2': (115496, 2851, 38, 47), 'message-0': (118347, 8113, 296, 28), 'message-1': (126460, 7752, 296, 28), 'message-2': (134212, 8365, 296, 28), 'message-3': (142577, 7858, 296, 28), 'message-4': (150435, 9067, 296, 28), 'message-5': (159502, 8208, 296, 28), 'message-6': (167710, 8517, 296, 28), 'message-7': (176227, 9216, 296, 28), 'controls': (185443, 5433, 320, 21), 'controls-paused': (190876, 5040, 320, 21), 'boo-word': (195916, 3739, 92, 31), 'scare-ghost-0': (199655, 5459, 82, 99), 'scare-bats-0': (205114, 2835, 64, 38), 'scare-spider-0': (207949, 7294, 88, 72), 'scare-skull-0': (215243, 4955, 70, 83), 'scare-ghost-1': (220198, 6151, 82, 99), 'scare-bats-1': (226349, 2383, 64, 38), 'scare-spider-1': (228732, 6829, 88, 72), 'scare-skull-1': (235561, 4948, 70, 83), 'scare-ghost-2': (240509, 6315, 82, 99), 'scare-bats-2': (246824, 2249, 64, 38), 'scare-spider-2': (249073, 6351, 88, 72), 'scare-skull-2': (255424, 4947, 70, 83), 'scare-ghost-3': (260371, 6315, 82, 99), 'scare-bats-3': (266686, 2249, 64, 38), 'scare-spider-3': (268935, 6206, 88, 72), 'scare-skull-3': (275141, 4947, 70, 83), 'scare-ghost-4': (280088, 6151, 82, 99), 'scare-bats-4': (286239, 2383, 64, 38), 'scare-spider-4': (288622, 6629, 88, 72), 'scare-skull-4': (295251, 4948, 70, 83), 'scare-ghost-5': (300199, 5459, 82, 99), 'scare-bats-5': (305658, 2835, 64, 38), 'scare-spider-5': (308493, 7054, 88, 72), 'scare-skull-5': (315547, 4955, 70, 83), 'scare-ghost-6': (320502, 6183, 82, 99), 'scare-bats-6': (326685, 2694, 64, 38), 'scare-spider-6': (329379, 7989, 88, 72), 'scare-skull-6': (337368, 4915, 70, 83), 'scare-ghost-7': (342283, 6221, 82, 99), 'scare-bats-7': (348504, 2931, 64, 38), 'scare-spider-7': (351435, 7872, 88, 72), 'scare-skull-7': (359307, 4862, 70, 83), 'scare-ghost-8': (364169, 6283, 82, 99), 'scare-bats-8': (370452, 2931, 64, 38), 'scare-spider-8': (373383, 7982, 88, 72), 'scare-skull-8': (381365, 4862, 70, 83), 'scare-ghost-9': (386227, 6183, 82, 99), 'scare-bats-9': (392410, 2694, 64, 38), 'scare-spider-9': (395104, 7969, 88, 72), 'scare-skull-9': (403073, 4915, 70, 83), 'scare-pumpkin-0': (407988, 16155, 136, 123), 'scare-pumpkin-1': (424143, 17161, 136, 123), 'scare-pumpkin-2': (441304, 17278, 136, 123), 'scare-pumpkin-3': (458582, 17300, 136, 123), 'scare-pumpkin-4': (475882, 17486, 136, 123), 'scare-pumpkin-5': (493368, 17577, 136, 123), 'scare-pumpkin-6': (510945, 17559, 136, 123), 'scare-pumpkin-7': (528504, 17665, 136, 123), 'scare-pumpkin-8': (546169, 17665, 136, 123), 'scare-pumpkin-9': (563834, 17559, 136, 123), 'scare-pumpkin-10': (581393, 17577, 136, 123), 'scare-pumpkin-11': (598970, 17486, 136, 123), 'scare-pumpkin-12': (616456, 17300, 136, 123), 'scare-pumpkin-13': (633756, 17278, 136, 123), 'scare-pumpkin-14': (651034, 17161, 136, 123), 'scare-pumpkin-15': (668195, 16155, 136, 123), 'scare-pumpkin-16': (684350, 17188, 136, 123), 'scare-pumpkin-17': (701538, 17163, 136, 123), 'scare-pumpkin-18': (718701, 17182, 136, 123), 'scare-pumpkin-19': (735883, 17272, 136, 123), 'scare-pumpkin-20': (753155, 17235, 136, 123), 'scare-pumpkin-21': (770390, 17322, 136, 123), 'scare-pumpkin-22': (787712, 17288, 136, 123), 'scare-pumpkin-23': (805000, 17288, 136, 123), 'scare-pumpkin-24': (822288, 17322, 136, 123), 'scare-pumpkin-25': (839610, 17235, 136, 123), 'scare-pumpkin-26': (856845, 17272, 136, 123), 'scare-pumpkin-27': (874117, 17182, 136, 123), 'scare-pumpkin-28': (891299, 17163, 136, 123), 'scare-pumpkin-29': (908462, 17188, 136, 123)}
# END ARTWORK INDEX


def asset(name):
    offset, length, width, height = ASSETS[name]
    artwork.seek(offset)
    data = artwork.read(length)
    if len(data) != length:
        raise ValueError('Incomplete art.bin')
    sprite = image.load(data)
    if (sprite.width, sprite.height) != (width, height):
        raise ValueError('Artwork size mismatch')
    return sprite


# The Christmas badge also uses one blob with an offset/length artwork index.
# Keep PNG payloads here so Tufty's full colour and alpha edges stay intact.
with open(APP_DIR + '/art.bin', 'rb') as artwork:
    background = asset('background')
    night = asset('night')
    faces = tuple(asset('face-' + str(i)) for i in range(8))
    ghosts = tuple(asset('ghost-' + str(i)) for i in range(3))
    messages = tuple(asset('message-' + str(i)) for i in range(MESSAGE_COUNT))
    controls = (asset('controls'), asset('controls-paused'))
    scares = tuple(tuple(asset('scare-' + name + '-' + str(i))
                         for i in range(SPRITE_COUNTS[kind]))
                   for kind, name in enumerate(CHARACTERS))
    boo_word = asset('boo-word')
del artwork
ORIGIN = vec2(0, 0)
FACE_POS = vec2(111, 104)
MESSAGE_POS = vec2(12, 187)
CONTROLS_POS = vec2(0, 219)
WORD_POS = vec2(12, 54)
RAIL_DARK = color.rgb(53, 39, 61)
RAIL_LIT = color.rgb(89, 64, 91)
THREAD = color.rgb(137, 116, 143)
# Cached poses and coordinates keep the animation loop free of vector creation.
MOTION = tuple((int(7 * math.sin(i * math.pi * 2 / NORMAL_FRAMES)),
                int(5 * math.sin(i * math.pi * 4 / NORMAL_FRAMES)))
               for i in range(NORMAL_FRAMES))
FLICKER = tuple(max(0, min(7, int(4 + 2 * math.sin(i * .568) +
                               math.sin(i * 1.544)))) for i in range(NORMAL_FRAMES))
NORMAL_DRAWS = tuple((ghosts[(i//10) % 3], vec2(36+MOTION[i][0], 90+MOTION[i][1]),
                      ghosts[(i//10+1) % 3],
                      vec2(248+MOTION[(i+54) % NORMAL_FRAMES][0],
                           111+MOTION[(i+54) % NORMAL_FRAMES][1]))
                     for i in range(NORMAL_FRAMES))
OFF_LIGHTS = (0, 0, 0, 0)
SCARE_LIGHTS = tuple((.45*(SCARE_FRAMES-i)/SCARE_FRAMES,
                      .45*.78*(SCARE_FRAMES-i)/SCARE_FRAMES,
                      .45*.9*(SCARE_FRAMES-i)/SCARE_FRAMES,
                      .45*.68*(SCARE_FRAMES-i)/SCARE_FRAMES)
                     for i in range(SCARE_FRAMES))


def make_plans(kind):
    plans = []
    for i in range(SCARE_FRAMES):
        t = i / (SCARE_FRAMES-1)
        wave = math.sin(t * math.pi)
        alpha = max(0, min(255, int(min(i, SCARE_FRAMES-1-i)*ANIMATION_STEP_MS*255/320)))
        thread = None
        if kind == 1:
            sprites = tuple(((i + round(j*2.5)) % SPRITE_COUNTS[kind],
                             rect(int(-90 + t*440 + j*55),
                                  int(91 + j*18 + 12*math.sin(t*math.pi*4+j)),
                                  64, 38)) for j in range(3))
        else:
            if kind == 0:
                w, h = int(82*(.65+.6*wave)), int(99*(.65+.6*wave))
                x = int(160-w/2+9*math.sin(t*math.pi*4))
                y = int(114-h/2+4*math.sin(t*math.pi*6))
            elif kind == 2:
                w, h = 88, 72
                x = int(116+14*math.sin(t*math.pi*3))
                y = int(52+38*wave+5*math.sin(t*math.pi*6)*wave)
                thread = (x+44, 51, 1, max(1, y+25-51))
            elif kind == 3:
                w, h = 136, 123
                x = 93 + round(2*math.sin(i*math.pi/15))
                y = 60 - round(2*math.sin(i*math.pi/15)**2)
            else:
                w, h = 70, 83
                x = int(220-60*wave)
                y = int(98-32*wave)
            sprites = ((i % SPRITE_COUNTS[kind], rect(x, y, w, h)),)
        plans.append((alpha, sprites, thread))
    return tuple(plans)


PLANS = tuple(make_plans(i) for i in range(len(CHARACTERS)))
message_index = 0
paused = False
animation_ms = 0
last_tick = time.ticks_ms()
boo_until = None
boo_kind = -1
manual_kind = -1
brightness_step = 7
last_light_index = -1
last_scene = -1
fence_length = max(0, min(85, int(badge.battery_level() * 85 / 100)))
next_battery_check = time.ticks_add(last_tick, 30000)


def random_delay():
    # 30 bits cover the full interval; 16 bits would truncate the upper end.
    return RANDOM_BOO_MIN_MS + random.getrandbits(30) % (
        RANDOM_BOO_MAX_MS - RANDOM_BOO_MIN_MS + 1)


random_remaining = random_delay()
gc.collect()


def update():
    global message_index, paused, animation_ms, last_tick, boo_until, boo_kind
    global brightness_step, last_light_index, random_remaining, last_scene
    global fence_length, next_battery_check, manual_kind
    now = time.ticks_ms()
    remaining = FRAME_MS - time.ticks_diff(now, last_tick)
    if remaining > 0:
        time.sleep_ms(remaining)
        now = time.ticks_ms()
    elapsed = time.ticks_diff(now, last_tick)
    last_tick = now
    pressed = badge.pressed()
    if BUTTON_C in pressed:
        paused = not paused
    if not paused:
        animation_ms = (animation_ms + elapsed) % 6400
        random_remaining -= elapsed
    if BUTTON_B in pressed:
        message_index = (message_index + 1) % len(messages)
    if BUTTON_UP in pressed:
        brightness_step = min(10, brightness_step + 1)
        display.backlight(brightness_step / 10)
    if BUTTON_DOWN in pressed:
        brightness_step = max(1, brightness_step - 1)
        display.backlight(brightness_step / 10)
    if time.ticks_diff(now, next_battery_check) >= 0:
        fence_length = max(0, min(85, int(badge.battery_level() * 85 / 100)))
        next_battery_check = time.ticks_add(now, 30000)

    if boo_until is not None and time.ticks_diff(boo_until, now) <= 0:
        boo_until = None
    boo_active = boo_until is not None
    manual = BUTTON_A in pressed
    if manual or (not paused and random_remaining <= 0 and not boo_active):
        if manual:
            manual_kind = (manual_kind + 1) % len(CHARACTERS)
            boo_kind = manual_kind
        else:
            # Automatic scares stay random and avoid the previous character.
            if boo_kind < 0:
                boo_kind = random.getrandbits(8) % len(CHARACTERS)
            else:
                boo_kind = ((boo_kind + 1 + random.getrandbits(8) % 4)
                            % len(CHARACTERS))
        boo_until = time.ticks_add(now, BOO_DURATION_MS)
        boo_active = True
        random_remaining = BOO_DURATION_MS + random_delay()
    phase = animation_ms // ANIMATION_STEP_MS
    scare_frame = 0
    if boo_active:
        left = time.ticks_diff(boo_until, now)
        scare_frame = min(SCARE_FRAMES-1, (BOO_DURATION_MS-left)//ANIMATION_STEP_MS)
        light_index = scare_frame
    else:
        light_index = -1
    if light_index != last_light_index:
        badge.caselights(*(OFF_LIGHTS if light_index < 0 else SCARE_LIGHTS[light_index]))
        last_light_index = light_index
    # A small integer replaces a fresh scene-key tuple on every update.
    scene = ((scare_frame if boo_active else phase) |
             ((boo_kind+1 if boo_active else 0) << 8) |
             (message_index << 11) | (paused << 14) | (fence_length << 15))
    if scene == last_scene:
        return False
    last_scene = scene
    screen.alpha = 255
    screen.blit(night if boo_active else background, ORIGIN)
    # The existing fence rail carries the charge level, without a label or icon.
    screen.pen = RAIL_DARK
    screen.rectangle(0, 163, 85, 2)
    if fence_length:
        screen.pen = RAIL_LIT
        screen.rectangle(0, 163, fence_length, 2)
    if boo_active:
        alpha, sprites, thread = PLANS[boo_kind][scare_frame]
        # New Badgeware blends using destination alpha, including PNG edges.
        screen.alpha = alpha
        try:
            if thread and alpha:
                screen.pen = THREAD
                screen.rectangle(*thread)
            for frame, bounds in sprites:
                screen.blit(scares[boo_kind][frame], bounds)
            screen.blit(boo_word, WORD_POS)
        finally:
            screen.alpha = 255
    else:
        screen.blit(faces[FLICKER[phase]], FACE_POS)
        first, first_pos, second, second_pos = NORMAL_DRAWS[phase]
        screen.blit(first, first_pos)
        screen.blit(second, second_pos)
    screen.blit(messages[message_index], MESSAGE_POS)
    screen.blit(controls[1 if paused else 0], CONTROLS_POS)
    return True


def on_exit():
    screen.alpha = 255
    badge.caselights(0)
    badge.default_clear = color.black


def main():
    try:
        while True:
            badge.poll()
            if update():
                display.update()
    finally:
        on_exit()


main()
