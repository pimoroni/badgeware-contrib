import wifi
import fetch

server = "http://SERVER_IP:8080/api/chats/CHAT_ID/messages"

badge.mode(HIRES | VSYNC)
screen.font = font.sins

BG = color.rgb(12, 18, 28)
PANEL = color.rgb(25, 36, 52)
MUTED = color.rgb(125, 150, 175)
ACCENT = color.rgb(32, 205, 180)

page = 0


def draw_footer(note="UP/DOWN: pages"):
    screen.pen = PANEL
    screen.rectangle(0, 225, screen.width, 15)
    screen.pen = MUTED
    screen.text(note, 5, 228)


def update():
    global page

    if badge.pressed(BUTTON_UP):
        page = (page - 1) % len(data)
    if badge.pressed(BUTTON_DOWN):
        page = (page + 1) % len(data)

    screen.pen = BG
    screen.clear()

    screen.pen = ACCENT
    screen.text(
        data[page],
        rect(5, 11, screen.width - 10, 205)
    )

    draw_footer("UP/DOWN: messages")

while not wifi.connect():
    pass

feed = fetch.url(server)
while not feed:
    pass

data = feed.json()
run(update)
