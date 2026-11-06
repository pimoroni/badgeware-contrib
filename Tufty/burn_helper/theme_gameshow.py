# "Running Man" theme: the 1987 deadly game show, broadcast live from the Zone.
#   sleep  -> runner passed out on the concrete, show is OFF AIR
#   idle   -> runner limbering up while the show is on STANDBY
#   walk   -> jogging into the Zone, LIVE
#   run    -> running flat out with a hockey-masked stalker on his heels
#   sprint -> sprinting through explosions, searchlights sweeping, ratings maxed
# Hearts are the 5-hour budget, the WEEK bar is the 7-day budget.
#
# One-shot activity animations (Status.act; only the demos send them for now), each played
# once over the jog or run: edit = counterattack on a stalker, read = searchlight sweep,
# shell = barrel blast, web = drone cam, spawn = a tag-team runner, fail = zapped ("ZAP!"),
# done = applause, prompt = the host's next round, arrive = new contestant, refill =
# commercial break while the collar recharges.
#
# The weekly reset is the SEASON finale, and gets louder as it nears (S.week_stage): a pink RESET
# clock alternating with the game clock under 6 h; the caption, a pulsing strip and faster
# searchlights under 1 h; the host cutting in at every whole minute of the last 10; a studio
# "ON AIR IN" board for the last minute; flashing numbers for the last 10 s; and a NEW SEASON
# title card with confetti when it arrives. The full-screen parts wait while a session is waiting
# for you or an activity plays.
#
# When the connection is lost (scene.lost_stage) the show goes to NO SIGNAL: the runner stands by,
# the collar goes grey and the caption says how long and why; after a minute, the colour bars and
# PLEASE STAND BY, with a lower third saying how long and why, and the caption taking turns between
# the usage as of the last data and what to try. When it comes back: WE'RE BACK!
#
# The weekly pace (S.pace_*): a tick on the collar's weekly strip where an even pace would leave it,
# and now and then, while agents work, the caption says the season ends early at this pace.

import math
import figure as F
import gfx
import scene as S

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 214, 0)
PINK = (255, 46, 140)
CYAN = (40, 228, 255)
RED = (230, 30, 40)
NIGHT = (34, 8, 52)

RUNNER = {
    F.OUT: (16, 8, 20), F.SKIN: (236, 176, 128), F.SKIN_D: (190, 130, 90),
    F.HAIR: (60, 36, 24), F.TOP: (255, 212, 0), F.TOP_D: (196, 150, 0),
    F.BOT: (255, 212, 0), F.BOT_D: (196, 150, 0), F.SHOE: (40, 40, 48),
    F.EYE: (16, 8, 20), F.WHITE: (255, 255, 255),
}

STALKER = {
    F.OUT: (10, 10, 20), F.SKIN: (230, 170, 130), F.SKIN_D: (180, 120, 90),
    F.HAIR: (40, 30, 30), F.TOP: (36, 80, 190), F.TOP_D: (24, 52, 130),
    F.BOT: (34, 34, 46), F.BOT_D: (22, 22, 30), F.SHOE: (20, 20, 30),
    F.EYE: (10, 10, 20), F.ACC1: (92, 100, 120), F.ACC2: (255, 40, 40),
    F.ACC3: (150, 100, 56), F.ACC4: (236, 240, 248), F.WHITE: (255, 255, 255),
}


def _stick(g, j, pose):  # noqa: ARG001
    hx, hy = j["hand_f"]
    fx, fy = j["fwd"]
    ux, uy = j["up"]
    ex = hx + fx * 4 - ux * 8
    ey = hy + fy * 4 - uy * 8
    g.seg(hx - fx, hy - fy, ex, ey, 1, F.ACC3)
    g.seg(ex, ey, ex + fx * 4, ey + fy * 4, 2, F.ACC3)
    # jersey stripe
    nx, ny = j["neck"]
    hpx, hpy = j["hip"]
    g.seg(nx * 0.5 + hpx * 0.5 - fx * 2, ny * 0.5 + hpy * 0.5 - fy * 2,
          nx * 0.5 + hpx * 0.5 + fx * 2, ny * 0.5 + hpy * 0.5 + fy * 2, 1, F.ACC4)


RUNNER_SPEC = F.Spec(torso_w=5, arm_w=2, leg_w=2, hair="short", forearms=F.TOP, uppers=F.TOP)
STALKER_SPEC = F.Spec(torso_w=6, arm_w=2, leg_w=3, hair="none", hat="helmet",
                      forearms=F.TOP, extra=_stick)

# ---------------------------------------------------------------- activity animations
ACTIONS = {"edit": 1800, "read": 1800, "shell": 1600, "web": 1800, "spawn": 2000, "fail": 1400,
           "done": 1800, "prompt": 1800, "arrive": 2200, "refill": 2400}
GOLD = (255, 200, 40)
SKYBLUE = (86, 180, 233)        # Okabe-Ito sky blue: success accents
VERMILLION = (213, 94, 0)       # Okabe-Ito vermillion: failure accents
VERMILLION_L = (245, 160, 90)
BROWN = (130, 82, 40)
BROWN_D = (86, 52, 24)

# a subagent runner: same build, cyan suit so it reads as a second player
BUDDY = dict(RUNNER)
BUDDY.update({F.TOP: (40, 200, 230), F.TOP_D: (20, 140, 170), F.BOT: (40, 200, 230), F.BOT_D: (20, 140, 170),
              F.HAIR: (200, 120, 40)})
# the runner lit up by a zap: suit and skin flash pale
ZAPPED = dict(RUNNER)
ZAPPED.update({F.TOP: (255, 250, 210), F.TOP_D: (230, 220, 160), F.BOT: (255, 250, 210), F.BOT_D: (230, 220, 160),
               F.SKIN: (255, 255, 255), F.SKIN_D: (220, 220, 230), F.HAIR: (255, 255, 255), F.OUT: (120, 40, 0)})
HOST = {
    F.OUT: (16, 8, 20), F.SKIN: (236, 180, 140), F.SKIN_D: (190, 136, 100),
    F.HAIR: (70, 44, 28), F.TOP: (200, 30, 120), F.TOP_D: (140, 20, 84),
    F.BOT: (40, 30, 60), F.BOT_D: (26, 20, 40), F.SHOE: (20, 20, 24),
    F.EYE: (16, 8, 20), F.ACC1: (200, 200, 210), F.ACC2: (60, 60, 70), F.WHITE: (255, 255, 255),
}


def _mic(g, j, pose):
    if pose.prop != "mic":
        return
    hx, hy = j["hand_f"]
    ux, uy = j["up"]
    g.seg(hx, hy, hx + ux * 3, hy + uy * 3, 1, F.ACC2)
    g.disc(hx + ux * 4, hy + uy * 4, 1, F.ACC1)
    # bow tie
    nx, ny = j["neck"]
    g.set(nx, ny + 1, F.WHITE)


HOST_SPEC = F.Spec(torso_w=6, arm_w=2, leg_w=2, hair="short", forearms=F.TOP, uppers=F.TOP,
                   shins=F.BOT, extra=_mic)

DRONE = ("RR.......RR",
         "KKKK...KKKK",
         ".K.......K.",
         ".KKKKKKKKK.",
         "..KGGGGGK..",
         "...KLLLK...",
         "....KKK....")

CAPTIONS = {
    "edit": ("STALKER ATTACKS!", "COUNTERATTACK!"),
    "read": ("SEARCHLIGHTS ON!", "HIDING IN THE ZONE..."),
    "shell": ("PYRO IN THE ZONE!", "KA-BOOM!"),
    "web": ("DRONE CAM: LIVE FEED", "DRONE CAM: LIVE FEED"),
    "spawn": ("A NEW RUNNER ENTERS!", "SUBAGENT ON THE RUN"),
    "fail": ("ZAP! A TOOL FAILED", "ZAP! A TOOL FAILED"),
    "done": ("APPLAUSE! TURN DONE", "APPLAUSE! TURN DONE"),
    "prompt": ("THE HOST HAS A NEW RULE", "NEXT ROUND!"),
    "arrive": ("PLEASE WELCOME...", "A NEW CONTESTANT!"),
    "refill": ("WE'LL BE RIGHT BACK", "COLLAR RECHARGED!"),
}
# the weekly pace's captions (S.pace_caption), two lines in turn: the week is the season
PACE = {"watch": ("AT THIS PACE THE SEASON", "ENDS EARLY: ~%(at)s"),
        "warn": ("SEASON OVER ~%(at)s", "%(early)s BEFORE THE NEW SEASON"),
        "eased": ("PACE EASED: FULL SEASON", "NO EARLY FINALE NOW"),
        "room": ("%(left)d%% OF THE SEASON LEFT", "NEW SEASON IN %(cd)s")}


# the test card for the connection-lost page: the seven bars, and the short reversed row under them
BARS = ((192, 192, 192), (192, 192, 0), (0, 192, 192), (0, 192, 0), (192, 0, 192), (192, 0, 0), (0, 0, 192))
BARS_LOW = ((0, 0, 192), (16, 16, 20), (192, 0, 192), (16, 16, 20), (0, 192, 192), (16, 16, 20), (192, 192, 192))


def week_digits(us, places):
    """The weekly countdown as big digits: "41.380" (places 3), "6.12" (places 2), "9:20" over a minute."""
    s = us if us > 0 else 0
    sec = s // 1000000
    if sec >= 60:
        return "%d:%02d" % (sec // 60, sec % 60)
    if places <= 0:
        return "%d" % sec
    frac = (s % 1000000) * (10 ** places) // 1000000
    return "%d.%s" % (sec, ("0" * places + str(frac))[-places:])


def ease(p):
    p = max(0.0, min(1.0, p))
    return p * p * (3 - 2 * p)


def seg(p, a, b):
    """0..1 progress of p within [a, b]."""
    return max(0.0, min(1.0, (p - a) / (b - a)))


class Theme(S.Theme):
    name = "gameshow"
    label = "RUNNING MAN"
    ACTIONS = ACTIONS

    def __init__(self):
        S.Theme.__init__(self)
        self.refill_from = 0
        self.last_hearts = None
        self.ws = None          # the weekly reset's stage this frame (S.week_stage)
        self.lost = None        # the connection-lost stage this frame (S.lost_stage)
        self.pace_kind = None   # the weekly pace's caption is showing: its kind (S.pace_caption)

    def build(self):
        rp = gfx.palette(RUNNER)
        sp = gfx.palette(STALKER)

        def run_img(pose):
            return gfx.to_image(F.render(RUNNER_SPEC, pose), rp)

        self.sleep = run_img(F.lying(af=(70, 30), ab=(100, 10)))
        self.flex = [run_img(F.stand(af=(40, 120), ab=(-30, 120))), run_img(F.stand(af=(20, 140), ab=(-20, 140), hip=(0, 1)))]
        self.jog = [gfx.to_image(g, rp) for g in F.cycle(RUNNER_SPEC, "jog", 8)]
        self.run = [gfx.to_image(g, rp) for g in F.cycle(RUNNER_SPEC, "run", 8)]
        self.sprint = [gfx.to_image(g, rp) for g in F.cycle(RUNNER_SPEC, "sprint", 8, mouth=True)]
        self.stalker = [gfx.to_image(g, sp) for g in F.cycle(STALKER_SPEC, "run", 8)]
        self.clock = gfx.clock_icon(YELLOW, BLACK)
        self.far = self._skyline()
        self.mid = self._fence()
        self.ground = self._ground()
        self._build_actions()

    def _build_actions(self):
        """Poses and props for the activity animations, built once."""
        rp = gfx.palette(RUNNER)
        sp = gfx.palette(STALKER)

        def r(pose, pal=rp, spec=RUNNER_SPEC):
            return gfx.to_image(F.render(spec, pose), pal)

        self.duck = r(F.Pose(lean=38, hip=(0, 4), lf=(84, 96), lb=(20, 130), af=(120, 120), ab=(60, 120)))
        self.kick = r(F.Pose(lean=-28, hip=(0, -1), lf=(100, 4), lb=(-12, 6), af=(40, 70), ab=(-60, 80), mouth=True))
        self.punch = r(F.Pose(lean=12, lf=(36, 30), lb=(-34, 12), af=(92, 0), ab=(-20, 110), mouth=True))
        self.crouch = r(F.Pose(lean=10, hip=(0, 5), lf=(82, 84), lb=(70, 120), af=(70, 70), ab=(40, 90)))
        self.leap = r(F.Pose(lean=18, lf=(84, 100), lb=(-40, 70), af=(130, 30), ab=(-70, 40), mouth=True))
        self.cheer = [r(F.Pose(lf=(8, 2), lb=(-8, 2), af=(140, 0), ab=(-140, 0), mouth=True)),
                      r(F.Pose(hip=(0, -2), lf=(14, 10), lb=(-14, 10), af=(125, 15), ab=(-125, -15), mouth=True))]
        self.pose_in = r(F.Pose(lf=(10, 2), lb=(-10, 2), af=(160, 20), ab=(-40, 120)))     # one fist up
        zp = gfx.palette(ZAPPED)
        jolt = F.Pose(hip=(0, -2), lf=(34, 0), lb=(-34, 0), af=(140, -30), ab=(-140, 30), eye=False, mouth=True)
        self.jolt = [r(jolt), r(jolt, zp)]
        bp = gfx.palette(BUDDY)
        self.buddy = [gfx.to_image(g, bp) for g in F.cycle(RUNNER_SPEC, "run", 8)]
        self.five = r(F.Pose(lean=4, lf=(30, 30), lb=(-30, 20), af=(150, 10), ab=(-30, 60)))
        self.buddy_five = r(F.Pose(lean=4, lf=(30, 30), lb=(-30, 20), af=(150, 10), ab=(-30, 60)), bp)
        # stalker: closing in, the swing, knocked flat
        self.s_swing = r(F.Pose(lean=30, lf=(30, 20), lb=(-30, 10), af=(150, 20), ab=(-20, 60)), sp, STALKER_SPEC)
        self.s_follow = r(F.Pose(lean=50, lf=(40, 30), lb=(-40, 10), af=(60, 0), ab=(-40, 50)), sp, STALKER_SPEC)
        self.s_down = r(F.lying(af=(60, 30), ab=(120, 10)), sp, STALKER_SPEC)
        hp = gfx.palette(HOST)
        self.host = [gfx.to_image(F.render(HOST_SPEC, F.Pose(lf=(6, 2), lb=(-6, 2), af=(40, 120), ab=(-20, 30),
                                                             prop="mic", mouth=m)), hp) for m in (False, True)]
        self.drone = gfx.sprite(DRONE, {"R": (200, 200, 220), "K": (60, 64, 80), "G": (150, 156, 176),
                                        "L": (40, 228, 255)})

    def start_action(self, key, t0, st):
        S.Theme.start_action(self, key, t0, st)
        if key == "refill":
            # the collar is already full by now: light it up from what was shown before
            self.refill_from = self.last_hearts if self.last_hearts is not None and self.last_hearts < 20 else 0

    def _skyline(self):
        img = image(160, 44)
        x = -10
        i = 0
        while x < 170:
            w = 14 + (i * 7) % 12
            h = 16 + (i * 13) % 26
            img.pen = gfx.rgb((52, 30, 84) if i % 2 else (44, 24, 72))
            img.rectangle(x, 44 - h, w, h)
            # broken roofline
            img.pen = gfx.rgb(NIGHT)
            img.triangle(x + w - 6, 44 - h, x + w, 44 - h, x + w, 44 - h + 6)
            img.pen = gfx.rgb((255, 190, 60))
            for k in range(3):
                wx = x + 3 + (k * 5 + i * 3) % max(4, w - 4)
                wy = 44 - h + 4 + (k * 7 + i) % max(4, h - 8)
                img.rectangle(wx, wy, 1, 2)
            x += w + 2
            i += 1
        return S.Layer(img, 46, 0.2)

    def _fence(self):
        img = image(160, 22)
        img.pen = color.rgb(150, 160, 180, 90)
        for x in range(-22, 182, 4):
            img.line(x, 2, x + 18, 21)
            img.line(x + 18, 2, x, 21)
        img.pen = gfx.rgb((90, 96, 110))
        for x in range(0, 160, 32):
            img.rectangle(x, 0, 2, 22)
        img.rectangle(0, 1, 160, 1)
        img.pen = gfx.rgb(YELLOW)
        img.rectangle(56, 8, 18, 7)
        img.pen = gfx.rgb(BLACK)
        img.rectangle(58, 10, 14, 1)
        img.rectangle(58, 12, 10, 1)
        return S.Layer(img, 68, 0.6)

    def _ground(self):
        img = image(160, 18)
        img.pen = gfx.rgb((70, 66, 80))
        img.rectangle(0, 0, 160, 18)
        img.pen = gfx.rgb((96, 92, 106))
        img.rectangle(0, 0, 160, 2)
        img.pen = gfx.rgb(YELLOW)
        for x in range(0, 160, 20):
            img.rectangle(x, 11, 10, 2)
        img.pen = gfx.rgb((44, 40, 52))
        for x in range(7, 160, 37):
            img.line(x, 3, x + 4, 7)
            img.line(x + 4, 7, x + 2, 10)
        return S.Layer(img, 90, 1.0)

    # ------------------------------------------------------------ render
    def render(self, st, t):
        lv = st.level
        p = self.acting(t)
        ws = self.ws = S.week_stage(st)
        self.lost = S.lost_stage(st, t)
        if self.lost == "lost":
            self.lost_page(st, t)
            return
        fast = ws in ("hour", "ten", "minute", "ten_s")     # the searchlights sweep faster, at every level
        gfx.box(0, 22, 160, 30, (14, 2, 26))
        gfx.box(0, 52, 160, 38, NIGHT)
        if p is not None and self.action == "read":
            self.lock_on(t, p)
        elif lv >= S.RUN or fast:
            self.searchlights(t * 2.2 if fast else t)
        self.far.draw(self.scroll)
        self.mid.draw(self.scroll)
        self.ground.draw(self.scroll)
        self.drums(t)
        if lv == S.SLEEP:
            screen.pen = color.rgb(0, 0, 0, 120)
            screen.rectangle(0, 22, 160, 86)
        if p is None:
            self.draw_runner(st, t)
        else:
            getattr(self, "act_" + self.action)(st, t, p)
        if lv == S.SPRINT:
            self.explosions(t)
        if st.waiting:
            self.vote(st, t)
        gfx.scanlines(22, 108, 34)
        self.viewfinder(lv, t)
        if p is not None:
            over = getattr(self, "over_" + self.action, None)
            if over:
                over(st, t, p)
        if ws is not None:
            self.week_overlay(st, t, ws, p is not None)
        saved = st.hearts
        saved_week = st.week
        zp = S.week_zero_progress(st) if ws == "zero" else None
        if p is not None and self.action == "refill":
            # the collar lights fill back up from what was shown before
            st.hearts = min(20, self.refill_from + int(seg(p, 0.15, 0.8) * (21 - self.refill_from)))
        elif zp is not None:
            # the new season: the collar and the weekly strip fill back up
            k = seg(zp, 0.2, 0.8)
            base = self.last_hearts if self.last_hearts is not None else 0
            if st.hearts is not None:
                st.hearts = min(20, base + int(k * (21 - base)))
            wk = st.week if st.week is not None else 0.0
            st.week = wk + (1.0 - wk) * k
        else:
            self.last_hearts = st.hearts
        self.draw_hud(st, t)
        st.hearts = saved
        st.week = saved_week
        self.draw_caption(st, t)

    def searchlights(self, t):
        for k, base in enumerate((30, 126)):
            a = math.sin(t / 900.0 + k * 2.1) * 0.6
            tipx = base + math.sin(a) * 80
            screen.pen = color.rgb(200, 230, 255, 40)
            screen.triangle(base - 2, 90, base + 2, 90, tipx + 12, 22)
            screen.triangle(base - 2, 90, tipx - 12, 22, tipx + 12, 22)

    def drums(self, t):
        period = 150
        for k in range(2):
            wx = k * period + 40
            x = int((wx - self.scroll) % (period * 2)) - 30
            if -12 < x < 170:
                gfx.box(x, 80, 9, 12, (110, 40, 30))
                gfx.box(x, 83, 9, 1, (60, 20, 16))
                gfx.box(x, 88, 9, 1, (60, 20, 16))
                for i in range(5):
                    p = ((t / 380.0) + i / 5.0) % 1.0
                    fx = x + 4 + math.sin(t / 90.0 + i * 1.7) * 2
                    fy = 79 - p * 12
                    r = 2.6 * (1 - p) + 0.5
                    screen.pen = color.rgb(255, int(220 - 160 * p), 40, int(255 * (1 - p)))
                    screen.shape(shape.circle(fx, fy, r))

    def draw_runner(self, st, t):
        lv = st.level
        foot = 104
        x = 66
        flip = False
        if lv == S.SLEEP:
            img = self.sleep
            x = 52
        elif lv == S.IDLE:
            img = self.flex[(t // 600) % 2]
            flip = (t // 4000) % 2 == 1
        elif lv == S.WALK:
            img = self.frame(self.jog, t, 11)
        elif lv == S.RUN:
            img = self.frame(self.run, t, 14)
        else:
            img = self.frame(self.sprint, t, 17)
            x = 74
        if lv >= S.RUN:
            gap = 34 + math.sin(t / 700.0) * 8 + (10 if lv == S.SPRINT else 0)
            simg = self.frame(self.stalker, t + 120, 13)
            gfx.blit(simg, x - gap - 20, foot - 27 * 2, 2)
        y = foot - 27 * 2
        if lv == S.SLEEP:
            y = foot - 26 * 2 + 4
        gfx.blit(img, x, y, 2, flip)
        if lv == S.SLEEP:
            gfx.zzz(x + 10, y + 26, t, (255, 230, 120), font.sins)

    def explosions(self, t):
        for k in range(2):
            period = 1400 + k * 500
            p = ((t + k * 700) % period) / float(period)
            if p > 0.6:
                continue
            q = p / 0.6
            ex = 18 + k * 34 + (t // period) % 3 * 6
            ey = 86 - k * 8
            r = 3 + q * 12
            screen.pen = color.rgb(255, int(150 - q * 100), 20, int(255 * (1 - q * q)))
            screen.shape(shape.circle(ex, ey, r))
            screen.pen = color.rgb(255, 230, 90, int(255 * (1 - q)))
            screen.shape(shape.circle(ex, ey, r * 0.6))
            screen.pen = color.rgb(255, 255, 230, int(255 * (1 - q)))
            screen.shape(shape.circle(ex, ey, r * 0.25))
            for i in range(6):
                a = i * 1.047 + k
                screen.pen = color.rgb(255, 220, 120, int(255 * (1 - q)))
                screen.rectangle(int(ex + math.cos(a) * r * 1.3), int(ey + math.sin(a) * r * 0.9), 1, 1)

    def vote(self, st, t):  # noqa: ARG002
        if (t // 400) % 2 == 0:
            screen.pen = color.rgb(255, 40, 140, 170)
            screen.rectangle(0, 22, 160, 2)
            screen.rectangle(0, 106, 160, 2)
            screen.rectangle(0, 22, 2, 86)
            screen.rectangle(158, 22, 2, 86)
        gfx.bubble(98, 46, "YOUR MOVE!", BLACK, YELLOW, font.sins)

    def viewfinder(self, lv, t):  # noqa: ARG002
        c = color.rgb(255, 255, 255, 150)
        screen.pen = c
        for (x, y, dx, dy) in ((4, 26, 1, 1), (155, 26, -1, 1), (4, 103, 1, -1), (155, 103, -1, -1)):
            screen.rectangle(min(x, x + dx * 7), y, 8, 1)
            screen.rectangle(x, min(y, y + dy * 5), 1, 6)

    def draw_hud(self, st, t):
        gfx.box(0, 0, 160, 22, (10, 0, 18))
        gfx.box(0, 21, 160, 1, PINK)
        gfx.text("RUNNING MAN", 2, -2, YELLOW, font.sins, shadow=RED)
        ws = self.ws
        lv = st.level
        if not st.online:
            self.rtext("NO SIGNAL", (150, 150, 160))
        elif lv == S.SLEEP:
            self.rtext("OFF AIR", (150, 150, 160))
        elif lv == S.IDLE:
            self.rtext("STANDBY", CYAN)
        else:
            x = self.rtext("LIVE", WHITE)
            if S.blink(t, 500):
                screen.pen = gfx.rgb(RED)
                screen.shape(shape.circle(x - 5, 5, 3))
        self.draw_collar(st, t, 2, 10)
        # the show's game clock: time until the collar recharges (5-hour reset, or the week's)
        gfx.box(94, 9, 64, 11, BLACK)
        gfx.box(94, 9, 64, 1, PINK)
        cd = S.cd_life(st)
        w = gfx.width(cd, font.sins)
        gfx.text(cd, 156 - w, 7, gfx.countdown_color(S.life_left(st), YELLOW, (255, 150, 40), RED), font.sins)
        screen.blit(self.clock, vec2(int(156 - w - 8), 12))
        if ws == "six":
            if (t // 2200) % 2 == 1:
                self.season_clock(st)           # the weekly clock takes turns with the game clock
        elif ws == "hour" and st.mode != "week":
            # the weekly strip pulses, and the logo gives way to SEASON FINALE every other turn
            gfx.box(6, 19, 76, 3, PINK if (t // 220) % 2 == 0 else WHITE)
            gfx.meter(6, 20, 76, 1, st.week, CYAN, (30, 30, 60))
            if (t // 1200) % 2 == 1:
                gfx.box(0, 0, 90, 10, (10, 0, 18))
                gfx.text("SEASON FINALE", 2, -2, PINK, font.sins, shadow=YELLOW)
        elif ws in ("ten", "minute", "ten_s"):
            self.season_clock(st)
            if st.mode != "week":
                gfx.box(6, 19, 76, 3, PINK if (t // 160) % 2 == 0 else WHITE)
                gfx.meter(6, 20, 76, 1, st.week, CYAN, (30, 30, 60))
        S.draw_accounts(st, t, self.lost is not None)     # a row for each other Claude account

    def season_clock(self, st):
        """The weekly countdown in the corner clock's place, in pink."""
        gfx.box(88, 9, 70, 11, PINK)
        gfx.box(88, 9, 70, 1, WHITE)
        us = st.left7
        cd = week_digits(us, 2) if us < 10000000 else gfx.countdown(us)     # hundredths in the last 10 s
        gfx.text(gfx.fit("RESET " + cd, 68, font.sins), 90, 7, BLACK, font.sins)

    def draw_collar(self, st, t, x, y):
        """The runner's explosive collar: 10 lights = the 5-hour budget.

        Green = charge left, amber = half a light, dark red = spent. Under two
        lights the rest flash red. The strip under the band is the weekly budget. In "week" mode
        the lights are the week, the ones likely spent by the reset go dark now and then, and there
        is no strip.
        """
        stale = self.lost is not None       # the connection is lost: the last known charge, in grey
        units = st.hearts if stale else S.icon_units(st, st.hearts, t)
        gfx.box(x, y + 1, 84, 7, (58, 62, 74))
        gfx.box(x, y + 1, 84, 1, (110, 116, 132))
        gfx.box(x, y, 4, 9, (120, 126, 142))
        gfx.box(x + 80, y, 4, 9, (120, 126, 142))
        low = units is not None and units <= 4 and not stale
        flash = low and S.blink(t, 250)
        for i in range(10):
            cx = x + 8 + i * 7
            if units is None:
                c = (40, 40, 48)
            elif stale:
                left = units - i * 2
                c = (170, 170, 180) if left >= 2 else ((110, 110, 120) if left == 1 else (40, 40, 48))
            else:
                left = units - i * 2
                if left >= 2:
                    c = (255, 50, 40) if flash else (70, 255, 140)
                elif left == 1:
                    c = (255, 50, 40) if flash else (255, 170, 0)
                else:
                    c = (72, 12, 16)
            gfx.box(cx - 2, y + 2, 5, 5, c)
            if units is not None and units - i * 2 >= 1 and not flash:
                gfx.box(cx - 1, y + 3, 1, 1, (255, 255, 255))
        # weekly budget: a thin charge strip under the collar, with the pace tick
        if st.mode != "week":
            gfx.meter(x + 4, y + 10, 76, 1, st.week, (150, 150, 160) if stale else CYAN, (30, 30, 60))
            S.pace_tick(st, x + 4, y + 10, 76, 1)

    def rtext(self, s, c):
        x = 158 - gfx.width(s, font.sins)
        gfx.text(s, x, -2, c, font.sins)
        return x

    def draw_caption(self, st, t):
        if st.online and st.waiting:
            S.draw_waiting_bar(st, t)     # who is waiting, one name at a time
            return
        msg = self.caption(st, t)
        bar = YELLOW
        if self.pace_kind:
            bar = {"warn": S.PACE_INK[2], "eased": S.BACK, "room": S.BACK}.get(self.pace_kind, bar)
        if self.lost is not None and msg.startswith("CONNECTION LOST"):
            bar = S.LOST
        elif S.back_online(st, t):
            msg, bar = "WE'RE BACK! LIVE AGAIN", S.BACK
        gfx.box(0, 108, 160, 12, bar)
        gfx.box(0, 108, 4, 12, PINK)
        gfx.ctext(gfx.fit(msg, 150, font.sins), 82, 107, BLACK, font.sins)

    def caption(self, st, t):
        self.pace_kind = None
        if not st.online:
            return S.lost_caption(st, t) if self.lost else (st.net or "PLEASE STAND BY...")
        p = self.acting(t)
        ws = self.ws
        if ws == "zero":
            return "NEW SEASON! GAME RESET"
        if ws in ("hour", "ten", "minute", "ten_s") and p is None:
            us = st.left7
            if ws == "ten_s":
                return "RESETTING IN %s" % week_digits(us, 1)
            if ws == "minute":
                return "ON AIR IN %s" % week_digits(us, 0)
            return "THE GAME RESETS IN " + gfx.countdown(us)
        if p is not None:
            a, b = CAPTIONS[self.action]
            return a if p < 0.45 else b
        pc = S.pace_caption(st, t, PACE)
        if pc:
            msg, self.pace_kind = pc
            return msg
        if st.hearts is not None and st.hearts <= 4 and (t // 3000) % 2:
            return "COLLAR LOW! RECHARGE " + gfx.countdown(S.life_left(st))
        tc = S.tier_caption(st, t, "ULTRA RATINGS: HYPERSPACE!")
        if tc:
            return tc
        lv = st.level
        n = max(1, st.agents)
        if lv == S.SLEEP:
            return "OFF AIR - RUNNER ASLEEP"
        if lv == S.IDLE:
            return "STAND BY FOR THE NEXT RUN"
        if lv == S.WALK:
            return "RUNNER IN THE ZONE: %d AGENT%s" % (n, "" if n == 1 else "S")
        if lv == S.RUN:
            return "STALKER RELEASED! %d AGENTS" % n
        return "MAXIMUM RATINGS!" if (t // 3000) % 2 == 0 else "%d AGENTS, %d TOOLS/MIN" % (n, st.tpm)

    def gait_img(self, st, t):
        lv = st.level
        if lv == S.RUN:
            return self.frame(self.run, t, 14)
        if lv == S.SPRINT:
            return self.frame(self.sprint, t, 17)
        return self.frame(self.jog, t, 11)

    def put(self, img, x, foot=104, flip=False, h=27, lift=0):
        gfx.blit(img, x, foot - h * 2 - lift, 2, flip)

    # ------------------------------------------------------------ the connection lost
    def lost_page(self, st, t):
        """A minute without data: the colour bars and PLEASE STAND BY, a lower third with how long and
        why, and the caption taking turns between the usage as of the last data and what to try."""
        top = 22
        for i, c in enumerate(BARS):
            x0, x1 = i * 160 // 7, (i + 1) * 160 // 7
            gfx.box(x0, top, x1 - x0, 46, c)
            gfx.box(x0, top + 46, x1 - x0, 6, BARS_LOW[i])
        k = (t % 5000) / 5000.0             # a soft dark band rolls down the picture, like a lost hold
        screen.pen = color.rgb(0, 0, 0, 80)
        screen.rectangle(0, int(top + k * 58) - 4, 160, 7)
        gfx.box(12, 31, 136, 27, BLACK)
        gfx.box(12, 31, 136, 1, WHITE)
        gfx.box(12, 57, 136, 1, WHITE)
        gfx.ctext("PLEASE STAND BY", 80, 31, WHITE, font.sins)
        gfx.ctext("TECHNICAL DIFFICULTIES", 80, 43, YELLOW, font.sins)
        # the lower third
        gfx.box(0, 74, 160, 34, (14, 4, 28))
        gfx.box(0, 74, 160, 2, PINK)
        gfx.box(0, 76, 4, 32, S.LOST)
        gfx.text("SIGNAL LOST " + S.lost_for(S.lost_ms(st, t) or 0), 8, 76, S.LOST, font.sins)
        gfx.text(gfx.fit(S.lost_reason(st), 148, font.sins), 8, 88, WHITE, font.sins)
        gfx.scanlines(22, 108, 34)
        self.draw_hud(st, t)
        tip = (t // 3000) % 2 == 1
        gfx.box(0, 108, 160, 12, YELLOW)
        gfx.box(0, 108, 4, 12, PINK)
        msg = S.lost_advice(st) if tip else S.last_usage(st)
        gfx.ctext(gfx.fit(msg, 150, font.sins), 82, 107, BLACK, font.sins)

    # ------------------------------------------------------------ the weekly reset
    def week_overlay(self, st, t, ws, acting):
        """What the weekly reset puts on the screen. The full-screen parts wait while a session is
        waiting for you or an activity plays; the HUD and caption parts (draw_hud, caption) do not."""
        if ws == "zero":
            self.new_season(st, t)
        elif not S.week_takes_screen(st, acting):
            return
        elif ws == "ten":
            if S.week_interstitial(st):
                self.pulse_frame(t)
                self.host_card(st.left7, t)
        elif ws == "minute":
            self.board(st.left7, t, False)
        elif ws == "ten_s":
            self.board(st.left7, t, True)

    def pulse_frame(self, t):
        if (t // 200) % 2 == 0:
            screen.pen = color.rgb(255, 46, 140, 190)
            screen.rectangle(0, 22, 160, 2)
            screen.rectangle(0, 106, 160, 2)
            screen.rectangle(0, 22, 2, 86)
            screen.rectangle(158, 22, 2, 86)

    def host_card(self, left, t):
        bx, top = 108, 44
        gfx.box(bx - 2, top - 2, 52, 62, PINK)
        gfx.box(bx, top, 48, 58, (30, 10, 50))
        for i in range(6):
            gfx.box(bx + 3 + i * 8, top + 2, 3, 2, YELLOW if (i + t // 150) % 2 else (120, 90, 20))
        gfx.blit(self.host[1 if (t // 140) % 2 == 0 else 0], bx - 4, top - 6, 2)
        gfx.bubble(bx + 18, top - 1, "NEW SEASON IN %s!" % week_digits(left, 0), BLACK, WHITE, font.sins)

    def board(self, left, t, flash):
        """The studio countdown board: fills the scene area."""
        top, bot = 22, 108
        edge = PINK if (t // 160) % 2 == 0 else YELLOW
        gfx.box(0, top, 160, bot - top, (14, 4, 28))
        gfx.box(0, top, 160, 3, edge)
        gfx.box(0, bot - 3, 160, 3, edge)
        gfx.box(0, top, 3, bot - top, edge)
        gfx.box(157, top, 3, bot - top, edge)
        # the audience sign, flashing
        w = int(gfx.width("APPLAUSE", font.sins)) + 10
        sx = 80 - w // 2
        gfx.box(sx - 1, top + 5, w + 2, 13, SKYBLUE)
        gfx.box(sx, top + 6, w, 11, BLACK)
        gfx.text("APPLAUSE", sx + 5, top + 4, GOLD if (t // 200) % 2 == 0 else (120, 96, 30), font.sins)
        gfx.ctext("NEW SEASON IN" if flash else "ON AIR IN", 80, top + 23, YELLOW, font.sins)
        if flash:
            col = WHITE if (t // 125) % 2 == 0 else YELLOW
        else:
            col = YELLOW if (t // 400) % 2 == 0 else WHITE
        gfx.ctext(week_digits(left, 2 if flash else 3), 80, top + 36, col, font.futile, shadow=PINK)
        gfx.ctext("SECONDS", 80, top + 68, WHITE, font.sins)
        if flash and left % 1000000 > 850000:         # a white flash as each second turns over
            screen.pen = color.rgb(255, 255, 255, 215)
            screen.rectangle(0, top, 160, bot - top)

    def new_season(self, st, t):
        """The reset itself: confetti and a NEW SEASON title card."""
        p = S.week_zero_progress(st)
        if p is None:
            return
        top, bot = 22, 108
        cols = (YELLOW, PINK, CYAN, WHITE, GOLD)
        for i in range(36):
            x = (i * 7919) % 160 + math.sin(p * 14 + i) * 3
            y = top + ((p * 1.6 + i / 36.0) % 1.0) * (bot - top)
            gfx.box(x, y, 2, 2, cols[i % 5])
        cx = int(-120 + ease(seg(p, 0.0, 0.2)) * 200)       # the title card slides in and settles
        gfx.box(cx - 62, 44, 124, 30, PINK)
        gfx.box(cx - 60, 46, 120, 26, BLACK)
        gfx.ctext("NEW", cx, 47, YELLOW, font.sins)
        gfx.ctext("SEASON", cx, 59, WHITE if (t // 180) % 2 == 0 else YELLOW, font.sins)
        if p > 0.45:
            gfx.bubble(80, 40, "WELCOME BACK, RUNNER!", BLACK, WHITE, font.sins)

    # ------------------------------------------------------------ edit: a fight
    def act_edit(self, st, t, p):
        x = 66
        if p < 0.3:                        # stalker charges in from the left, stick raised
            q = ease(seg(p, 0.0, 0.3))
            sx = -50 + q * 76
            self.put(self.frame(self.stalker, t, 16), sx)
            self.put(self.gait_img(st, t), x, flip=p > 0.18)       # the runner hears him and turns
        elif p < 0.5:                      # the swing: runner ducks under it
            self.put(self.s_swing if p < 0.4 else self.s_follow, 12)
            self.put(self.duck, x, flip=True, lift=-6)
            self.whoosh(86, 58, t)
        elif p < 0.75:                     # counter: a high kick, then a punch
            self.put(self.s_follow, 22 - (p - 0.5) * 30)
            self.put(self.kick if p < 0.63 else self.punch, x - 10, flip=True)
            self.pow(54, 52 if p < 0.63 else 60, "POW!" if p < 0.63 else "WHAM!")
        else:                              # stalker flat on the concrete, runner turns and goes
            self.put(self.s_down, 2 - (p - 0.75) * 60, h=24, lift=-6)
            self.put(self.gait_img(st, t), x, flip=p < 0.85)
            for i in range(3):             # dazed stars
                a = t / 160.0 + i * 2.1
                gfx.box(18 + math.cos(a) * 7 - (p - 0.75) * 60, 80 + math.sin(a) * 2, 1, 1, GOLD)

    def whoosh(self, x, y, t):  # noqa: ARG002
        # the stick's swing, an arc passing just over his head
        screen.pen = color.rgb(255, 255, 255, 190)
        for i in range(9):
            a = 3.6 + i * 0.22
            screen.rectangle(int(x + math.cos(a) * 22), int(y + math.sin(a) * 10), 2, 1)

    def pow(self, x, y, word):
        # a starburst with a word: theme yellow, not a good/bad colour
        screen.pen = gfx.rgb(YELLOW)
        for i in range(8):
            a = i * 0.785
            screen.line(int(x), int(y), int(x + math.cos(a) * 9), int(y + math.sin(a) * 7))
        w = int(gfx.width(word, font.sins))
        gfx.box(x - w // 2 - 2, y - 13, w + 4, 10, YELLOW)
        gfx.text(word, x - w // 2, y - 15, BLACK, font.sins)

    # ------------------------------------------------------------ read: searchlights find him
    def lock_on(self, t, p):
        target = 94
        for k, base in enumerate((30, 126)):
            free = base + math.sin(math.sin(t / 900.0 + k * 2.1) * 0.6) * 80
            q = ease(seg(p, 0.1, 0.45)) * (1 - ease(seg(p, 0.82, 1.0)))
            tipx = free + (target - free) * q
            screen.pen = color.rgb(220, 240, 255, 40 + int(40 * q))
            screen.triangle(base - 2, 90, base + 2, 90, tipx + 12, 22)
            screen.triangle(base - 2, 90, tipx - 12, 22, tipx + 12, 22)

    def act_read(self, st, t, p):
        x = 66
        cx = 160 - ease(seg(p, 0.0, 0.3)) * 66          # a crate scrolls in, then he stops behind it
        if p >= 0.82:
            cx = 94 - ease(seg(p, 0.82, 1.0)) * 90
        hiding = 0.28 <= p < 0.82
        if hiding:
            self.put(self.crouch, x - 4, lift=-2)
            if 0.5 <= p < 0.8 and (t // 250) % 2 == 0:
                # peeking over the top
                gfx.text("?", 104, 52, WHITE, font.sins)
            self.crate(int(cx), 104)       # in front of him while he hides
        else:
            self.crate(int(cx), 104)       # behind him while he runs
            self.put(self.gait_img(st, t), x)
        if 0.45 <= p < 0.82:               # the beams meet on the crate
            screen.pen = color.rgb(255, 255, 230, 70)
            screen.shape(shape.circle(cx + 11, 86, 16))

    def crate(self, x, foot):
        y = foot - 22
        gfx.box(x, y, 24, 22, BROWN)
        gfx.box(x, y, 24, 2, BROWN_D)
        gfx.box(x, y + 10, 24, 2, BROWN_D)
        gfx.box(x, y + 20, 24, 2, BROWN_D)
        gfx.box(x, y, 2, 22, BROWN_D)
        gfx.box(x + 22, y, 2, 22, BROWN_D)
        screen.pen = gfx.rgb(BROWN_D)
        screen.line(x + 2, y + 2, x + 22, y + 10)
        screen.line(x + 2, y + 12, x + 22, y + 20)

    # ------------------------------------------------------------ shell: a barrel goes up
    def act_shell(self, st, t, p):
        x = 66
        bx = 36
        lift = 0
        img = self.gait_img(st, t)
        if 0.3 <= p < 0.75:                # blown into the air
            q = seg(p, 0.3, 0.75)
            lift = int(math.sin(q * math.pi) * 18)
            img = self.leap
        self.put(img, x + (8 * seg(p, 0.3, 0.75) if p < 0.75 else 8 - 8 * seg(p, 0.75, 1.0)), lift=lift)
        if p < 0.3:                        # a fizzing barrel next to him
            gfx.box(bx, 90, 12, 14, (180, 40, 30))
            gfx.box(bx, 93, 12, 1, (110, 20, 16))
            gfx.box(bx, 99, 12, 1, (110, 20, 16))
            gfx.box(bx + 2, 94, 8, 4, YELLOW)
            gfx.box(bx + 6, 86, 1, 4, (200, 200, 200))
            if (t // 80) % 2:
                gfx.box(bx + 5 + (t // 40) % 3, 84, 2, 2, (255, 230, 120))
            for i in range(5):
                a = t / 70.0 + i * 1.3
                gfx.box(bx + 6 + math.cos(a) * 4, 84 + math.sin(a) * 3, 1, 1, (255, 200, 80))
        else:                              # the fireball
            q = seg(p, 0.3, 1.0)
            ex, ey = bx + 6, 94
            r = 5 + q * 26
            screen.pen = color.rgb(255, int(150 - q * 110), 20, int(255 * (1 - q * q)))
            screen.shape(shape.circle(ex, ey, r))
            screen.pen = color.rgb(255, 230, 90, int(255 * (1 - q)))
            screen.shape(shape.circle(ex, ey, r * 0.6))
            screen.pen = color.rgb(255, 255, 230, int(255 * (1 - q)))
            screen.shape(shape.circle(ex, ey, r * 0.25))
            for i in range(10):
                a = i * 0.628
                d = r * (1.1 + 0.3 * (i % 2))
                screen.pen = color.rgb(255, 220, 120, int(255 * (1 - q)))
                screen.rectangle(int(ex + math.cos(a) * d), int(ey + math.sin(a) * d * 0.7), 2, 1)
            if q < 0.6:
                w = int(gfx.width("BOOM!", font.sins))
                gfx.text("BOOM!", ex - w // 2, 54 - int(q * 6), YELLOW, font.sins, shadow=(120, 30, 0))

    # ------------------------------------------------------------ web: the drone cam
    def act_web(self, st, t, p):
        self.put(self.gait_img(st, t), 66)
        if p < 0.3:
            q = ease(seg(p, 0.0, 0.3))
            dx, dy = 150 - q * 32, 24 + q * 16
        elif p < 0.75:
            dx, dy = 118 + math.sin(t / 200.0) * 3, 40 + math.sin(t / 130.0) * 2
        else:
            q = ease(seg(p, 0.75, 1.0))
            dx, dy = 118 + q * 34, 40 - q * 16
        dx, dy = int(dx), int(dy)
        # spinning rotors: alternate long and short blur
        long_ = (t // 60) % 2 == 0
        gfx.box(dx - (3 if long_ else 1), dy, 8 if long_ else 4, 1, (220, 220, 235))
        gfx.box(dx + 14 - (1 if long_ else 0), dy, 8 if long_ else 4, 1, (220, 220, 235))
        gfx.blit(self.drone, dx, dy + 1, 2)
        if (t // 250) % 2 == 0:
            gfx.box(dx + 10, dy + 12, 2, 2, (255, 40, 40))
        if 0.3 <= p < 0.75:
            # the camera's view: a framing box on the runner and a LIVE tag
            screen.pen = color.rgb(255, 255, 255, 200)
            for (x, y, sx, sy) in ((76, 46, 1, 1), (112, 46, -1, 1), (76, 104, 1, -1), (112, 104, -1, -1)):
                screen.rectangle(min(x, x + sx * 5), y, 6, 1)
                screen.rectangle(x, min(y, y + sy * 4), 1, 5)
            gfx.box(dx - 4, dy + 18, 26, 9, BLACK)
            if (t // 250) % 2 == 0:
                screen.pen = gfx.rgb((255, 40, 40))
                screen.shape(shape.circle(dx, dy + 22, 2))
            gfx.text("LIVE", dx + 3, dy + 16, WHITE, font.sins)

    # ------------------------------------------------------------ spawn: a second runner
    def act_spawn(self, st, t, p):
        x = 66
        if p < 0.4:                        # catches up from the left
            q = ease(seg(p, 0.0, 0.4))
            self.put(self.frame(self.buddy, t + 200, 15), -60 + q * 98)
            self.put(self.gait_img(st, t), x)
        elif p < 0.65:                     # high five
            self.put(self.buddy_five, 40)
            self.put(self.five, x, flip=True)
            if p > 0.5:
                gfx.text("*", 74, 32, YELLOW, font.sins)
                screen.pen = gfx.rgb(YELLOW)
                for i in range(6):
                    a = i * 1.047
                    screen.rectangle(int(76 + math.cos(a) * 6), int(42 + math.sin(a) * 5), 1, 1)
        else:                              # and sprints off ahead on its own errand
            q = ease(seg(p, 0.65, 1.0))
            self.put(self.gait_img(st, t), x)
            self.put(self.frame(self.buddy, t + 200, 17), 40 + q * 130)
            if q < 0.6:
                gfx.text("GO!", 52 + int(q * 120), 30, (150, 240, 255), font.sins)

    # ------------------------------------------------------------ fail: zapped
    def act_fail(self, st, t, p):
        x = 66
        if p < 0.12:
            self.put(self.gait_img(st, t), x)
        elif p < 0.62:
            jit = (t // 40) % 2
            self.put(self.jolt[(t // 70) % 2], x + jit - 1, lift=2)
            # the bolt from the top of the scene
            if (t // 60) % 3 != 2:
                pts = ((98, 22), (90, 32), (100, 38), (92, 48), (98, 54))
                screen.pen = gfx.rgb(VERMILLION_L)
                for i in range(len(pts) - 1):
                    screen.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
                    screen.line(pts[i][0] + 1, pts[i][1], pts[i + 1][0] + 1, pts[i + 1][1])
            for i in range(8):
                a = t / 50.0 + i * 0.8
                d = 14 + (i * 5) % 9
                gfx.box(94 + math.cos(a) * d, 78 + math.sin(a) * d * 0.9, 1, 1, VERMILLION_L)
            screen.pen = color.rgb(213, 94, 0, 46)
            screen.rectangle(0, 22, 160, 86)
            gfx.bubble(120, 44, "ZAP!", BLACK, VERMILLION_L, font.sins)
        else:                              # shakes it off, a little smoke, back to running
            self.put(self.gait_img(st, t), x)
            q = seg(p, 0.62, 1.0)
            for i in range(3):
                screen.pen = color.rgb(160, 160, 170, int(160 * (1 - q)))
                screen.shape(shape.circle(92 + i * 5 - q * 20, 48 - q * 14 - i * 3, 2 + q * 3))

    # ------------------------------------------------------------ done: applause
    def act_done(self, st, t, p):
        x = 66
        if 0.15 <= p < 0.85:
            self.put(self.cheer[(t // 180) % 2], x)
        else:
            self.put(self.gait_img(st, t), x)
        # confetti from the top
        cols = ((255, 46, 140), (255, 214, 0), (40, 228, 255), (255, 255, 255), (86, 180, 233))
        for i in range(36):
            seed = (i * 7919) % 997
            fx = (seed * 13) % 160 + math.sin(t / 200.0 + i) * 3
            fy = 22 + ((seed % 60) + p * 120) % 86
            if p < 0.12 and fy > 22 + p * 600:
                continue
            gfx.box(fx, fy, 2 if i % 3 == 0 else 1, 1, cols[i % len(cols)])
        if 0.2 <= p < 0.9:
            k = seg(p, 0.2, 0.9)
            gfx.text("+1", 100, 44 - int(k * 14), GOLD, font.sins, shadow=BLACK)

    def over_done(self, st, t, p):  # noqa: ARG002
        on = (t // 200) % 2 == 0
        w = int(gfx.width("APPLAUSE", font.sins)) + 10
        x = 80 - w // 2
        gfx.box(x - 1, 25, w + 2, 13, SKYBLUE)
        gfx.box(x, 26, w, 11, BLACK)
        gfx.text("APPLAUSE", x + 5, 24, GOLD if on else (120, 96, 30), font.sins)
        for i in range(0, w, 4):
            if ((i // 4) + (t // 120)) % 2:
                gfx.box(x + i, 26, 1, 1, GOLD)
                gfx.box(x + i, 36, 1, 1, GOLD)

    # ------------------------------------------------------------ prompt: the host
    def act_prompt(self, st, t, p):  # noqa: ARG002
        self.put(self.gait_img(st, t), 50)

    def over_prompt(self, st, t, p):  # noqa: ARG002
        # the host slides into a picture-in-picture box, says his line, slides out
        q = ease(seg(p, 0.0, 0.2)) * (1 - ease(seg(p, 0.85, 1.0)))
        bx = int(160 - q * 52)
        top = 44
        gfx.box(bx - 2, top - 2, 52, 62, PINK)
        gfx.box(bx, top, 48, 58, (30, 10, 50))
        for i in range(6):                 # studio lights behind him
            gfx.box(bx + 3 + i * 8, top + 2, 3, 2, YELLOW if (i + t // 150) % 2 else (120, 90, 20))
        talking = 0.25 <= p < 0.8 and (t // 140) % 2 == 0
        gfx.blit(self.host[1 if talking else 0], bx - 4, top - 6, 2)
        if 0.22 <= p < 0.85:
            gfx.bubble(bx + 22, top - 1, "NEXT ROUND!", BLACK, WHITE, font.sins)

    # ------------------------------------------------------------ arrive: spotlight and a card
    def act_arrive(self, st, t, p):
        x = 66
        dim = ease(seg(p, 0.0, 0.2)) * (1 - ease(seg(p, 0.85, 1.0)))
        screen.pen = color.rgb(0, 0, 0, int(170 * dim))
        screen.rectangle(0, 22, 160, 86)
        if dim > 0.05:
            screen.pen = color.rgb(255, 250, 200, int(70 * dim))
            screen.triangle(90, 22, 70, 104, 118, 104)
            screen.pen = color.rgb(255, 250, 200, int(60 * dim))
            screen.shape(shape.circle(94, 104, 14))
        if 0.15 <= p < 0.85:
            self.put(self.pose_in if (t // 500) % 2 == 0 else self.flex[0], x)
        else:
            self.put(self.gait_img(st, t), x)

    def over_arrive(self, st, t, p):  # noqa: ARG002
        # a lower-third card slides in from the left
        q = ease(seg(p, 0.2, 0.4)) * (1 - ease(seg(p, 0.8, 0.95)))
        x = int(-90 + q * 92)
        gfx.box(x, 82, 86, 12, PINK)
        gfx.box(x, 94, 70, 9, BLACK)
        gfx.text("NEW CONTESTANT", x + 3, 80, YELLOW, font.sins)
        gfx.text("SESSION #4", x + 3, 92, WHITE, font.sins)

    # ------------------------------------------------------------ refill: commercial break
    def act_refill(self, st, t, p):  # noqa: ARG002
        self.put(self.gait_img(st, t), 66)

    def over_refill(self, st, t, p):  # noqa: ARG002
        q = ease(seg(p, 0.0, 0.12)) * (1 - ease(seg(p, 0.85, 1.0)))
        if q <= 0:
            return
        top = 22 + int((1 - q) * 86)
        h = 108 - top
        bars = ((200, 200, 200), (200, 200, 0), (0, 200, 200), (0, 200, 0), (200, 0, 200), (200, 0, 0), (0, 0, 200))
        bw = 160 // len(bars) + 1
        for i, c in enumerate(bars):
            gfx.box(i * bw, top, bw, min(h, 40), c)
        if h > 40:
            gfx.box(0, top + 40, 160, h - 40, (16, 8, 28))
            gfx.ctext("COMMERCIAL BREAK", 80, top + 42, YELLOW, font.sins)
            gfx.ctext("COLLAR RECHARGING", 80, top + 54, WHITE, font.sins)
            # a little charge bar matching the collar
            k = seg(p, 0.15, 0.8)
            gfx.meter(40, top + 66, 80, 4, k, SKYBLUE, (40, 40, 60))
