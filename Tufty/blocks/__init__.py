"""
Tetris & Dr. Mario for Tufty 2350 / Badgeware

Controls:
  A = Move left          C = Move right
  UP = Rotate            DOWN = Soft drop
  B = Hard drop / Start  A+B = Pause
  A+C = Hold piece (Tetris only)

Title: A/C to pick game, B to start.
Pause menu: Theme, Stats, Quit.
Theme is random each launch — change it in the pause menu.
"""

APP_DIR = "/system/apps/blocks"

import os
import sys
import random

os.chdir(APP_DIR)
sys.path.insert(0, APP_DIR)

# Set HIRES before importing draw (it reads screen dimensions at module level)
badge.mode(HIRES)

from game import Tetris, DrMario, GS
from stats import Stats
from themes import get_theme, get_theme_names, THEME_LIST
from draw import (
    draw_tetris_board, draw_tetris_piece, draw_tetris_line_anim,
    draw_tetris_panels, draw_dr_board, draw_dr_pill, draw_dr_line_anim,
    draw_dr_panels, draw_title, draw_bg, draw_pause, draw_themes,
    draw_stats, draw_gameover, draw_popup, draw_level_clear, stc,
    PAUSE_ITEMS, T_BX, T_BY, T_BW, T_BH, D_BX, D_BY, D_BW, D_BH,
    DR_BG,
)


# ── Initialisation ───────────────────────────────────────────────────────────

stats = Stats()
stats.load()

# Random theme each launch
tn = THEME_LIST[random.randint(0, len(THEME_LIST) - 1)]
theme = get_theme(tn)

tetris = Tetris(stats)
dr = DrMario(stats)

game_sel = 0       # 0 = Tetris, 1 = Dr. Mario
game = tetris       # currently active game
is_dr = False
pause_sel = 0
theme_sel = 0
theme_names = get_theme_names()


def reload_theme():
    global theme, tn
    tn = stats.theme_name
    theme = get_theme(tn)


def set_game(idx):
    global game, is_dr, game_sel
    game_sel = idx
    if idx == 0:
        game = tetris
        is_dr = False
    else:
        game = dr
        is_dr = True


# ── Input ────────────────────────────────────────────────────────────────────

def handle_play():
    """Handle input during gameplay for both games."""
    ap = badge.pressed(BUTTON_A)
    bp = badge.pressed(BUTTON_B)
    cp = badge.pressed(BUTTON_C)
    ah = badge.held(BUTTON_A)
    ch = badge.held(BUTTON_C)

    # A+B = Pause
    if ah and bp:
        game.state = GS.MENU
        return

    # A+C = Hold (Tetris only)
    if not is_dr and ((ah and cp) or (ch and ap)):
        tetris.hold()
        return

    if badge.pressed(BUTTON_UP):
        game.rotate(1)
    elif bp:
        game.hard_drop()
    else:
        game.soft_drop_active = badge.held(BUTTON_DOWN)
        if ap:
            game.move(-1, 0)
            game.last_move_lr = badge.ticks
        if cp:
            game.move(1, 0)
            game.last_move_lr = badge.ticks

        # DAS auto-repeat
        now = badge.ticks
        if ah and not ch:
            el = now - game.last_move_lr
            if el > game.das_delay:
                if (el - game.das_delay) % game.arr_delay < badge.ticks_delta:
                    game.move(-1, 0)
        if ch and not ah:
            el = now - game.last_move_lr
            if el > game.das_delay:
                if (el - game.das_delay) % game.arr_delay < badge.ticks_delta:
                    game.move(1, 0)

    game.gravity_tick()
    if not is_dr:
        tetris.update_danger()


# ── Main loop ────────────────────────────────────────────────────────────────

def update():
    global pause_sel, theme_sel, game_sel

    # ── State machine ──

    if game.state == GS.TITLE:
        if badge.pressed(BUTTON_A):
            set_game((game_sel - 1) % 2)
        if badge.pressed(BUTTON_C):
            set_game((game_sel + 1) % 2)
        if badge.pressed(BUTTON_B):
            if is_dr:
                dr.start()
            else:
                tetris.start()

    elif game.state == GS.PLAYING:
        handle_play()

    elif game.state == GS.COUNTDOWN:
        if game.countdown_num() == 0:
            if badge.ticks - game.countdown_start > 2100:
                game.begin_play()

    elif game.state == GS.LINE_CLEAR:
        if game.line_anim and game.line_anim.done():
            game.finish_clear()

    elif game.state == GS.TOP_OUT:
        if game.topout_anim and game.topout_anim.done():
            game.state = GS.GAME_OVER

    elif game.state == GS.LEVEL_CLEAR:
        if badge.pressed(BUTTON_B):
            dr.new_level()
            dr.begin_play()

    elif game.state == GS.MENU:
        if badge.pressed(BUTTON_UP):
            pause_sel = (pause_sel - 1) % len(PAUSE_ITEMS)
        if badge.pressed(BUTTON_DOWN):
            pause_sel = (pause_sel + 1) % len(PAUSE_ITEMS)
        if badge.pressed(BUTTON_B):
            item = PAUSE_ITEMS[pause_sel]
            if item == "Resume":
                game.state = GS.PLAYING
                game.last_gravity = badge.ticks
            elif item == "Theme":
                theme_sel = theme_names.index(tn) if tn in theme_names else 0
                game.state = GS.THEME_SELECT
            elif item == "Stats":
                game.state = GS.STATS_VIEW
            elif item == "Quit":
                if is_dr:
                    stats.end_dr(dr.score, dr.level)
                else:
                    stats.end_tetris(tetris.score, tetris.lines)
                game.state = GS.TITLE
        if badge.pressed(BUTTON_A):
            game.state = GS.PLAYING
            game.last_gravity = badge.ticks

    elif game.state == GS.THEME_SELECT:
        if badge.pressed(BUTTON_UP):
            theme_sel = (theme_sel - 1) % len(theme_names)
            stats.theme_name = theme_names[theme_sel]
            reload_theme()
        if badge.pressed(BUTTON_DOWN):
            theme_sel = (theme_sel + 1) % len(theme_names)
            stats.theme_name = theme_names[theme_sel]
            reload_theme()
        if badge.pressed(BUTTON_B):
            stats.save()
            game.state = GS.MENU
        if badge.pressed(BUTTON_A):
            game.state = GS.MENU

    elif game.state == GS.STATS_VIEW:
        if badge.pressed(BUTTON_A):
            game.state = GS.MENU

    elif game.state == GS.GAME_OVER:
        if badge.pressed(BUTTON_B):
            if is_dr:
                dr.start()
            else:
                tetris.start()
        if badge.pressed(BUTTON_A):
            game.state = GS.TITLE

    # ── Render ──

    if game.state == GS.TITLE:
        draw_title(theme, tn, game_sel, stats)
        return

    if game.state == GS.THEME_SELECT:
        draw_themes(theme_names, theme_sel, theme, tn)
        return

    if game.state == GS.STATS_VIEW:
        draw_stats(stats, theme, tn)
        return

    # Gameplay screens — Dr. Mario uses fixed bg, Tetris uses theme
    if is_dr:
        screen.pen = DR_BG
        screen.clear()
        draw_dr_board(dr)
        if game.state == GS.LINE_CLEAR:
            draw_dr_line_anim(dr)
        elif game.state in (GS.PLAYING, GS.MENU, GS.COUNTDOWN):
            draw_dr_pill(dr)
        draw_dr_panels(dr)
        draw_popup(dr, D_BX, D_BY, D_BW, D_BH)
    else:
        screen.pen = theme["bg"]
        screen.clear()
        draw_bg(tn, theme)
        draw_tetris_board(tetris, theme)
        if game.state == GS.LINE_CLEAR:
            draw_tetris_line_anim(tetris, theme)
        elif game.state in (GS.PLAYING, GS.MENU, GS.COUNTDOWN):
            draw_tetris_piece(tetris, theme)
        draw_tetris_panels(tetris, theme)
        draw_popup(tetris, T_BX, T_BY, T_BW, T_BH)

    # Overlays
    if game.state == GS.COUNTDOWN:
        bx = D_BX if is_dr else T_BX
        bw = D_BW if is_dr else T_BW
        by = D_BY if is_dr else T_BY
        bh = D_BH if is_dr else T_BH
        num = game.countdown_num()
        if num > 0:
            screen.pen = color.rgb(0, 0, 0, 140)
            screen.shape(shape.rectangle(bx, by, bw, bh))
            stc(str(num), by + bh // 2 - 10, True, theme)
    elif game.state == GS.MENU:
        draw_pause(theme, pause_sel)
    elif game.state in (GS.GAME_OVER, GS.TOP_OUT):
        draw_gameover(game, stats, is_dr)
    elif game.state == GS.LEVEL_CLEAR:
        draw_level_clear(dr)


def on_exit():
    # Only save stats if mid-game (not already saved by game over)
    if game.state in (GS.PLAYING, GS.COUNTDOWN, GS.LINE_CLEAR, GS.MENU,
                       GS.THEME_SELECT, GS.STATS_VIEW):
        if is_dr:
            stats.end_dr(dr.score, dr.level)
        else:
            stats.end_tetris(tetris.score, tetris.lines)
    stats.save()


run(update)
