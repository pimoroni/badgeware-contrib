import wifi
import fetch

server = "http://SERVER_IP:8080/api/chats/CHAT_ID/messages"

badge.mode(HIRES | VSYNC)
screen.font = font.sins

BG = color.rgb(28, 20, 14)
PANEL = color.rgb(48, 35, 22)
MUTED = color.rgb(170, 145, 110)
ACCENT = color.rgb(255, 178, 55)

page = 0
feed = None
data = []


def update():
    global page, feed, data

    if feed is None and wifi.connect():
        feed = fetch.url(server)
        while not feed:
            pass
        data = feed.json()

    if not data:
        screen.pen = BG
        screen.clear()
        screen.pen = MUTED
        screen.text("Loading...", 5, 11)
        return

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

    screen.pen = PANEL
    screen.rectangle(0, 225, screen.width, 15)

    screen.pen = MUTED
    screen.text("UP / DOWN : Page " + str(page + 1), 5, 228)


run(update)
