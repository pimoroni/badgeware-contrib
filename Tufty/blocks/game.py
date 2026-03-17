"""
Game logic for Blocks and Pill Drop.

Blocks: SRS rotation, wall kicks, 7-bag, hold, ghost, back-to-back, combos.
Pill Drop: 3-colour viruses, 2-cell pills, match-4, chain gravity, level progression.
"""

import random


# ── Utilities ────────────────────────────────────────────────────────────────

def shuffle(lst):
    """Fisher-Yates shuffle (MicroPython has no random.shuffle)."""
    for i in range(len(lst) - 1, 0, -1):
        j = random.randint(0, i)
        lst[i], lst[j] = lst[j], lst[i]


# ── Tetromino Data (SRS) ────────────────────────────────────────────────────

PIECE_NAMES = ["I", "O", "T", "S", "Z", "J", "L"]

PIECES = {
    "I": [
        [(0, 0), (0, 1), (0, 2), (0, 3)],
        [(0, 2), (1, 2), (2, 2), (3, 2)],
        [(2, 0), (2, 1), (2, 2), (2, 3)],
        [(0, 1), (1, 1), (2, 1), (3, 1)],
    ],
    "O": [[(0, 0), (0, 1), (1, 0), (1, 1)]] * 4,
    "T": [
        [(0, 1), (1, 0), (1, 1), (1, 2)],
        [(0, 1), (1, 1), (1, 2), (2, 1)],
        [(1, 0), (1, 1), (1, 2), (2, 1)],
        [(0, 1), (1, 0), (1, 1), (2, 1)],
    ],
    "S": [
        [(0, 1), (0, 2), (1, 0), (1, 1)],
        [(0, 1), (1, 1), (1, 2), (2, 2)],
        [(1, 1), (1, 2), (2, 0), (2, 1)],
        [(0, 0), (1, 0), (1, 1), (2, 1)],
    ],
    "Z": [
        [(0, 0), (0, 1), (1, 1), (1, 2)],
        [(0, 2), (1, 1), (1, 2), (2, 1)],
        [(1, 0), (1, 1), (2, 1), (2, 2)],
        [(0, 1), (1, 0), (1, 1), (2, 0)],
    ],
    "J": [
        [(0, 0), (1, 0), (1, 1), (1, 2)],
        [(0, 1), (0, 2), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (1, 2), (2, 2)],
        [(0, 1), (1, 1), (2, 0), (2, 1)],
    ],
    "L": [
        [(0, 2), (1, 0), (1, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (2, 2)],
        [(1, 0), (1, 1), (1, 2), (2, 0)],
        [(0, 0), (0, 1), (1, 1), (2, 1)],
    ],
}

WALL_KICKS = {
    (0, 1): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
    (1, 0): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
    (1, 2): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
    (2, 1): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
    (2, 3): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],
    (3, 2): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
    (3, 0): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
    (0, 3): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],
}

I_WALL_KICKS = {
    (0, 1): [(0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)],
    (1, 0): [(0, 0), (2, 0), (-1, 0), (2, 1), (-1, -2)],
    (1, 2): [(0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1)],
    (2, 1): [(0, 0), (1, 0), (-2, 0), (1, -2), (-2, 1)],
    (2, 3): [(0, 0), (2, 0), (-1, 0), (2, 1), (-1, -2)],
    (3, 2): [(0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)],
    (3, 0): [(0, 0), (1, 0), (-2, 0), (1, -2), (-2, 1)],
    (0, 3): [(0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1)],
}

LINE_SCORES = {0: 0, 1: 100, 2: 300, 3: 500, 4: 800}

SPEEDS = [
    800, 720, 630, 550, 470, 380, 300, 220, 140, 100,
    83, 83, 83, 67, 67, 67, 50, 50, 50, 33,
]


# ── Board Dimensions ─────────────────────────────────────────────────────────

COLS = 10
ROWS = 20
HIDDEN = 2
TOTAL = ROWS + HIDDEN

DR_COLS = 8
DR_ROWS = 16
DR_HIDDEN = 1
DR_TOTAL = DR_ROWS + DR_HIDDEN


def gravity_ms(level):
    """Gravity delay in ms for a given Blocks level."""
    return SPEEDS[level] if level < len(SPEEDS) else 33


# ── Bag Randomiser ───────────────────────────────────────────────────────────

class Bag:
    """7-bag piece randomiser. Each bag contains one of each piece."""

    def __init__(self):
        self._bag = []

    def next(self):
        if not self._bag:
            self._bag = list(PIECE_NAMES)
            shuffle(self._bag)
        return self._bag.pop()


# ── Game States ──────────────────────────────────────────────────────────────

class GS:
    TITLE = 0
    PLAYING = 1
    GAME_OVER = 2
    LINE_CLEAR = 3
    COUNTDOWN = 4
    TOP_OUT = 5
    MENU = 6
    STATS_VIEW = 7
    THEME_SELECT = 8
    LEVEL_CLEAR = 9


# ── Animations ───────────────────────────────────────────────────────────────

class LineClearAnim:
    def __init__(self, rows):
        self.rows = rows
        self.start = badge.ticks
        self.duration = 300

    def progress(self):
        return min(1.0, (badge.ticks - self.start) / self.duration)

    def done(self):
        return self.progress() >= 1.0


class TopOutAnim:
    def __init__(self, total_rows=TOTAL):
        self.start = badge.ticks
        self.duration = 1500
        self._total = total_rows

    def progress(self):
        return min(1.0, (badge.ticks - self.start) / self.duration)

    def gray_row(self):
        return int(self.progress() * self._total)

    def done(self):
        return self.progress() >= 1.0


# ── Blocks ───────────────────────────────────────────────────────────────────

class Blocks:
    """Classic falling blocks with SRS, hold, ghost, back-to-back, combos."""

    def __init__(self, stats):
        self.stats = stats
        self.reset()

    def reset(self):
        self.board = [[None] * COLS for _ in range(TOTAL)]
        self.bag = Bag()
        self.score = 0
        self.lines = 0
        self.level = 0
        self.state = GS.TITLE

        self.piece = None
        self.piece_rot = 0
        self.piece_x = 0
        self.piece_y = 0
        self.hold_piece = None
        self.hold_used = False
        self.next_queue = [self.bag.next() for _ in range(3)]

        self.last_gravity = 0
        self.last_move_lr = 0
        self.das_delay = 133
        self.arr_delay = 40
        self.soft_drop_active = False

        self.line_anim = None
        self.topout_anim = None
        self.lock_timer = 0
        self.lock_delay = 500
        self.on_ground = False
        self.countdown_start = 0

        self.danger = False
        self.b2b = 0
        self.combo = 0
        self.popup = None

    def start(self):
        self.reset()
        self.state = GS.COUNTDOWN
        self.countdown_start = badge.ticks
        self.stats.start_game()

    def begin_play(self):
        self.state = GS.PLAYING
        self.spawn()
        self.last_gravity = badge.ticks

    def countdown_num(self):
        el = badge.ticks - self.countdown_start
        if el < 600:
            return 3
        if el < 1200:
            return 2
        if el < 1800:
            return 1
        return 0

    def cells(self, p, r):
        return PIECES[p][r % 4]

    def collides(self, p, r, px, py):
        for dr, dc in self.cells(p, r):
            row, col = py + dr, px + dc
            if col < 0 or col >= COLS or row >= TOTAL:
                return True
            if row >= 0 and self.board[row][col] is not None:
                return True
        return False

    def spawn(self):
        self.piece = self.next_queue.pop(0)
        self.next_queue.append(self.bag.next())
        self.piece_rot = 0
        self.piece_x = 3
        self.piece_y = 0
        self.hold_used = False
        self.on_ground = False
        self.lock_timer = 0
        if self.collides(self.piece, self.piece_rot, self.piece_x, self.piece_y):
            self.topout_anim = TopOutAnim()
            self.state = GS.TOP_OUT
            self.stats.end_blocks(self.score, self.lines)

    def rotate(self, d):
        old = self.piece_rot
        new = (old + d) % 4
        kicks = I_WALL_KICKS if self.piece == "I" else WALL_KICKS
        key = (old, new)
        if key not in kicks:
            return False
        for dx, dy in kicks[key]:
            if not self.collides(self.piece, new, self.piece_x + dx, self.piece_y - dy):
                self.piece_x += dx
                self.piece_y -= dy
                self.piece_rot = new
                if self.on_ground:
                    self.lock_timer = badge.ticks
                return True
        return False

    def move(self, dx, dy):
        if not self.collides(self.piece, self.piece_rot, self.piece_x + dx, self.piece_y + dy):
            self.piece_x += dx
            self.piece_y += dy
            if dx != 0 and self.on_ground:
                self.lock_timer = badge.ticks
            return True
        return False

    def hard_drop(self):
        n = 0
        while not self.collides(self.piece, self.piece_rot, self.piece_x, self.piece_y + 1):
            self.piece_y += 1
            n += 1
        self.score += n * 2
        self.lock()

    def ghost_y(self):
        gy = self.piece_y
        while not self.collides(self.piece, self.piece_rot, self.piece_x, gy + 1):
            gy += 1
        return gy

    def hold(self):
        if self.hold_used:
            return
        self.hold_used = True
        if self.hold_piece is None:
            self.hold_piece = self.piece
            self.spawn()
        else:
            self.piece, self.hold_piece = self.hold_piece, self.piece
            self.piece_rot = 0
            self.piece_x = 3
            self.piece_y = 0
            self.on_ground = False
            self.lock_timer = 0

    def lock(self):
        for dr, dc in self.cells(self.piece, self.piece_rot):
            r, c = self.piece_y + dr, self.piece_x + dc
            if 0 <= r < TOTAL and 0 <= c < COLS:
                self.board[r][c] = self.piece

        full = [r for r in range(TOTAL)
                if all(cell is not None for cell in self.board[r])]

        if full:
            n = len(full)
            sc = LINE_SCORES.get(n, 800) * (self.level + 1)

            # Back-to-back Blocks bonus
            if n == 4:
                self.b2b += 1
                if self.b2b > 1:
                    sc = int(sc * 1.5)
                self.stats.session_b2b = max(self.stats.session_b2b, self.b2b)
            else:
                self.b2b = 0

            self.combo += 1
            self.stats.session_combo = max(self.stats.session_combo, self.combo)
            self.score += sc

            # Score popup
            names = {1: "SINGLE", 2: "DOUBLE", 3: "TRIPLE", 4: "QUAD!"}
            txt = names.get(n, "")
            if n == 4 and self.b2b > 1:
                txt = "B2B QUAD!"
            if txt:
                self.popup = (txt, badge.ticks)

            self.line_anim = LineClearAnim(full)
            self.state = GS.LINE_CLEAR
        else:
            self.combo = 0
            self.spawn()

    def finish_clear(self):
        rows = self.line_anim.rows
        n = len(rows)
        for r in sorted(rows, reverse=True):
            del self.board[r]
        for _ in range(n):
            self.board.insert(0, [None] * COLS)
        self.lines += n
        self.level = self.lines // 10
        self.line_anim = None
        self.state = GS.PLAYING
        self.spawn()
        return rows

    def update_danger(self):
        self.danger = any(
            self.board[r][c] is not None
            for r in range(HIDDEN, HIDDEN + 4)
            for c in range(COLS)
        )

    def gravity_tick(self):
        now = badge.ticks
        delay = gravity_ms(self.level)
        if self.soft_drop_active:
            delay = max(delay // 10, 20)
        if now - self.last_gravity >= delay:
            self.last_gravity = now
            if not self.move(0, 1):
                if not self.on_ground:
                    self.on_ground = True
                    self.lock_timer = now
                elif now - self.lock_timer >= self.lock_delay:
                    self.lock()
            else:
                self.on_ground = False
                if self.soft_drop_active:
                    self.score += 1

    def current_speed(self):
        return gravity_ms(self.level)

    def popup_active(self):
        if self.popup and badge.ticks - self.popup[1] < 800:
            return True
        self.popup = None
        return False


# ── Pill Drop ────────────────────────────────────────────────────────────────

class PillDrop:
    """
    Pill Drop: clear viruses by matching 4+ of the same colour.

    Board cells:
      None    = empty
      0, 1, 2 = pill halves (colour index)
      10, 11, 12 = viruses (colour index = cell % 10)
    """

    def __init__(self, stats):
        self.stats = stats
        self.reset()

    def reset(self):
        self.board = [[None] * DR_COLS for _ in range(DR_TOTAL)]
        self.score = 0
        self.level = 0
        self.viruses = 0
        self.state = GS.TITLE

        self.pill_a = 0
        self.pill_b = 0
        self.pill_rot = 0
        self.pill_x = 0
        self.pill_y = 0
        self.next_a = 0
        self.next_b = 0

        self.last_gravity = 0
        self.last_move_lr = 0
        self.das_delay = 133
        self.arr_delay = 40
        self.soft_drop_active = False

        self.line_anim = None
        self.topout_anim = None
        self.countdown_start = 0
        self.popup = None

        self._gen_next()

    def _gen_next(self):
        self.next_a = random.randint(0, 2)
        self.next_b = random.randint(0, 2)

    def start(self, level=0):
        self.reset()
        self.level = level
        self._place_viruses()
        self.state = GS.COUNTDOWN
        self.countdown_start = badge.ticks
        self.stats.start_game()

    def _place_viruses(self):
        """Place viruses randomly, avoiding prematch 3-in-a-row."""
        # Clear board for new level
        self.board = [[None] * DR_COLS for _ in range(DR_TOTAL)]
        count = min(4 + self.level * 4, 64)
        self.viruses = 0
        attempts = 0
        while self.viruses < count and attempts < 300:
            r = random.randint(DR_TOTAL - DR_ROWS + 4, DR_TOTAL - 1)
            c = random.randint(0, DR_COLS - 1)
            if self.board[r][c] is not None:
                attempts += 1
                continue
            v = random.randint(0, 2)

            # Check no 3-in-a-row would form
            ok = True
            # Horizontal
            h = 0
            for dc in range(-2, 1):
                cc = c + dc
                if 0 <= cc < DR_COLS and self.board[r][cc] is not None:
                    if self.board[r][cc] % 10 == v:
                        h += 1
                    else:
                        h = 0
                else:
                    h = 0
            if h >= 2:
                ok = False
            # Vertical
            vv = 0
            for dr in range(-2, 1):
                rr = r + dr
                if 0 <= rr < DR_TOTAL and self.board[rr][c] is not None:
                    if self.board[rr][c] % 10 == v:
                        vv += 1
                    else:
                        vv = 0
                else:
                    vv = 0
            if vv >= 2:
                ok = False

            if ok:
                self.board[r][c] = 10 + v
                self.viruses += 1
            attempts += 1

    def begin_play(self):
        self.state = GS.PLAYING
        self._spawn_pill()
        self.last_gravity = badge.ticks

    def new_level(self):
        """Set up a new level with fresh viruses."""
        self._place_viruses()

    def countdown_num(self):
        el = badge.ticks - self.countdown_start
        if el < 600:
            return 3
        if el < 1200:
            return 2
        if el < 1800:
            return 1
        return 0

    def _spawn_pill(self):
        self.pill_a = self.next_a
        self.pill_b = self.next_b
        self._gen_next()
        self.pill_rot = 0
        self.pill_x = DR_COLS // 2 - 1
        self.pill_y = 0
        if self._collides(self.pill_x, self.pill_y, self.pill_rot):
            self.topout_anim = TopOutAnim(DR_TOTAL)
            self.state = GS.TOP_OUT
            self.stats.end_pd(self.score, self.level)

    def pill_cells(self, px, py, rot):
        """Return ((r1, c1), (r2, c2)) for the two pill halves."""
        if rot == 0:
            return ((py, px), (py, px + 1))
        if rot == 1:
            return ((py, px), (py + 1, px))
        if rot == 2:
            return ((py, px + 1), (py, px))
        return ((py + 1, px), (py, px))

    def _collides(self, px, py, rot):
        for r, c in self.pill_cells(px, py, rot):
            if c < 0 or c >= DR_COLS or r >= DR_TOTAL:
                return True
            if r >= 0 and self.board[r][c] is not None:
                return True
        return False

    def rotate(self, d):
        new = (self.pill_rot + d) % 4
        # Try straight, then kick right, then kick left
        for dx in [0, 1, -1]:
            if not self._collides(self.pill_x + dx, self.pill_y, new):
                self.pill_x += dx
                self.pill_rot = new
                return True
        return False

    def move(self, dx, dy):
        if not self._collides(self.pill_x + dx, self.pill_y + dy, self.pill_rot):
            self.pill_x += dx
            self.pill_y += dy
            return True
        return False

    def hard_drop(self):
        while not self._collides(self.pill_x, self.pill_y + 1, self.pill_rot):
            self.pill_y += 1
            self.score += 1
        self._lock_pill()

    def _lock_pill(self):
        cells = self.pill_cells(self.pill_x, self.pill_y, self.pill_rot)
        colors = [self.pill_a, self.pill_b]
        for i, (r, c) in enumerate(cells):
            if 0 <= r < DR_TOTAL and 0 <= c < DR_COLS:
                self.board[r][c] = colors[i]
        self._check_matches()

    def _check_matches(self):
        """Find and clear all match-4+ groups."""
        to_clear = set()

        # Horizontal matches
        for r in range(DR_TOTAL):
            run = 1
            start = 0
            for c in range(1, DR_COLS):
                prev = self.board[r][c - 1]
                curr = self.board[r][c]
                if prev is not None and curr is not None and prev % 10 == curr % 10:
                    run += 1
                else:
                    if run >= 4:
                        for cc in range(start, start + run):
                            to_clear.add((r, cc))
                    run = 1
                    start = c
            if run >= 4:
                for cc in range(start, start + run):
                    to_clear.add((r, cc))

        # Vertical matches
        for c in range(DR_COLS):
            run = 1
            start = 0
            for r in range(1, DR_TOTAL):
                prev = self.board[r - 1][c]
                curr = self.board[r][c]
                if prev is not None and curr is not None and prev % 10 == curr % 10:
                    run += 1
                else:
                    if run >= 4:
                        for rr in range(start, start + run):
                            to_clear.add((rr, c))
                    run = 1
                    start = r
            if run >= 4:
                for rr in range(start, start + run):
                    to_clear.add((rr, c))

        if to_clear:
            v_cleared = sum(
                1 for r, c in to_clear
                if self.board[r][c] is not None and self.board[r][c] >= 10
            )
            self.viruses = max(0, self.viruses - v_cleared)
            self.score += v_cleared * 100 * (self.level + 1)

            rows_affected = set()
            for r, c in to_clear:
                self.board[r][c] = None
                rows_affected.add(r)

            self.line_anim = LineClearAnim(sorted(rows_affected))
            self.state = GS.LINE_CLEAR
        else:
            if self.viruses <= 0:
                self.level += 1
                self.popup = ("LEVEL CLEAR!", badge.ticks)
                self.state = GS.LEVEL_CLEAR
            else:
                self.state = GS.PLAYING
                self._spawn_pill()

    def finish_clear(self):
        """After clear animation: apply gravity, re-check for chains."""
        self.line_anim = None

        # Drop floating pill halves (not viruses)
        changed = True
        while changed:
            changed = False
            for c in range(DR_COLS):
                for r in range(DR_TOTAL - 2, -1, -1):
                    cell = self.board[r][c]
                    if cell is not None and cell < 10:  # pill, not virus
                        if r + 1 < DR_TOTAL and self.board[r + 1][c] is None:
                            self.board[r + 1][c] = cell
                            self.board[r][c] = None
                            changed = True

        # Re-check for chain matches.
        # _check_matches always sets state: LINE_CLEAR, LEVEL_CLEAR, or PLAYING.
        self._check_matches()

    def gravity_tick(self):
        now = badge.ticks
        delay = max(100, 600 - self.level * 40)
        if self.soft_drop_active:
            delay = max(delay // 8, 20)
        if now - self.last_gravity >= delay:
            self.last_gravity = now
            if not self.move(0, 1):
                self._lock_pill()

    def popup_active(self):
        if self.popup and badge.ticks - self.popup[1] < 1000:
            return True
        self.popup = None
        return False
