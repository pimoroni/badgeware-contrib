badge.mode(LORES | VSYNC)
screen.font = font.sins

BG = color.rgb(28, 20, 14)
PANEL = color.rgb(48, 35, 22)
MUTED = color.rgb(170, 145, 110)
ACCENT = color.rgb(255, 178, 55)

team_a = 0
team_b = 0
team_c = 0
latest_team = "a"

def update():
    global team_a, team_b, team_c, latest_team

    if badge.pressed(BUTTON_A):
        team_a += 1
        latest_team = "a"

    if badge.pressed(BUTTON_B):
        team_b += 1
        latest_team = "b"

    if badge.pressed(BUTTON_C):
        team_c += 1
        latest_team = "c"

    if badge.pressed(BUTTON_UP):
        team_a = 0
        team_b = 0
        team_c = 0

    if badge.pressed(BUTTON_DOWN):
        exec("team_"+latest_team+" += -1")

    screen.pen = BG
    screen.clear()

    screen.pen = ACCENT
    screen.text(
        "Score counter \nA: "+str(team_a)+", \nB: "+str(team_b)+", \nC: "+str(team_c),
        rect(5, 11, 155, 109)
        )

run(update)
