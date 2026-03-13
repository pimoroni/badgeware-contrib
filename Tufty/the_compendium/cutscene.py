import monster

SCREEN_CENTRE_X = screen.width / 2
SCREEN_CENTRE_Y = screen.height / 2


# Basic routine to calculate word wrapped text within a given box.
def word_wrap(text, font, w, h):
    screen.font = font
    words = text.split()
    lines = []
    currentline = ""
    _, y_height = screen.measure_text(text)
    total_h = y_height + 0

    for word in words:
        newline = currentline + word + " "
        text_w, text_h = screen.measure_text(newline)
        if text_w <= w:
            currentline = newline
        else:
            lines.append(currentline)
            currentline = word + " "
            total_h += 0 + text_h
            if total_h > h:
                break
    lines.append(currentline)

    return lines, y_height


# Draw the wrapped text returned by the above.
def draw_wrapped_text(text, font, area):
    lines, y_height = word_wrap(text, font, area.w, area.h)
    y = area.y
    for line in lines:
        screen.text(line, area.x, y)
        y += y_height
    return area.w, y


class CutsceneLayout:
    img_top = 0
    img_btm = 1
    img_left = 2
    img_right = 3
    img_full = 4


class CutsceneScreen:
    def __init__(self, image, text, layout, font):
        self.image = image
        self.text = text
        self.font = font

        if layout == CutsceneLayout.img_full:
            self.text_box = rect(1, 1, 158, 118)
            self.img_box = rect(0, 0, 160, 120)
        elif layout == CutsceneLayout.img_btm:
            self.text_box = rect(1, 1, 158, 58)
            self.img_box = rect(0, 60, 160, 60)
        elif layout == CutsceneLayout.img_top:
            self.text_box = rect(1, 61, 158, 58)
            self.img_box = rect(0, 0, 160, 60)
        elif layout == CutsceneLayout.img_left:
            self.text_box = rect(81, 1, 78, 118)
            self.img_box = rect(0, 0, 80, 120)
        elif layout == CutsceneLayout.img_right:
            self.text_box = rect(1, 1, 78, 118)
            self.img_box = rect(80, 0, 80, 120)

    def draw(self, screen_image):
        screen.pen = color.black
        screen.clear()
        screen.pen = color.white
        screen.blit(screen_image, self.img_box)
        draw_wrapped_text(self.text, self.font, self.text_box)


# Draws a dialogue box with an image, text and options to pick.
class DialogBox:
    def __init__(self, image, text, layout, font, options):
        self.image = image
        self.text = text
        self.font = font
        self.options = options

        if layout == CutsceneLayout.img_left:
            self.text_box = rect(SCREEN_CENTRE_X + 1, 1, SCREEN_CENTRE_X - 2, screen.height - 2)
            self.img_box = rect(0, 0, SCREEN_CENTRE_X, SCREEN_CENTRE_X)
        elif layout == CutsceneLayout.img_right:
            self.text_box = rect(1, 1, SCREEN_CENTRE_X - 2, screen.height - 2)
            self.img_box = rect(SCREEN_CENTRE_X, 0, SCREEN_CENTRE_X, SCREEN_CENTRE_X)

    def draw(self, icons):
        screen.font = self.font
        screen.pen = color.rgb(255, 255, 255, 240)
        screen.clear()
        screen.pen = color.rgb(0, 0, 0)

        _, text_y_height = screen.measure_text("Hello world")
        options_top = screen.height - (text_y_height * (len(self.options) + 1))
        size = min(options_top, SCREEN_CENTRE_X)
        if options_top > SCREEN_CENTRE_X:
            self.img_box.y = options_top - SCREEN_CENTRE_X
        self.img_box.w = size
        self.img_box.h = size
        screen.blit(self.image, self.img_box)

        y = screen.height - text_y_height - 2

        icon = len(self.options) - 1

        for option in reversed(self.options):
            screen.blit(icons.sprite(icon, 0), vec2(0, y))
            screen.text(option, 14, y)
            y -= text_y_height + 1
            icon -= 1
        self.text_box.h = y

        screen.line(vec2(0, y + text_y_height), vec2(screen.width, y + text_y_height))

        draw_wrapped_text(self.text, self.font, self.text_box)


# Draws a simple message across the screen.
class StatusMessage():
    def __init__(self, text, given_item=None, removed_item=None):
        self.text = text
        self.text_box = rect(screen.width * 0.125, screen.height * 0.5, screen.width * 0.75, screen.height * 0.25)
        self.given_item = given_item
        self.removed_item = removed_item

    def draw(self):
        lines, y_height = word_wrap(self.text, screen.font, self.text_box.w, self.text_box.h)
        y = self.text_box.y
        self.text_box.h = y_height * len(lines)
        screen.pen = color.rgb(255, 255, 255, 160)
        screen.rectangle(self.text_box)
        screen.pen = color.black
        for line in lines:
            line_w, _ = screen.measure_text(line)
            x = self.text_box.x + ((self.text_box.w - line_w) / 2)
            screen.text(line, x, y)
            y += y_height


# Little tiny message in dialogue to tell you you received an item.
class InDialogueMessage():
    def __init__(self, text):
        self.text = text
        self.text_box = rect(0, 0, SCREEN_CENTRE_X, screen.height)

    def draw(self):
        lines, y_height = word_wrap(self.text, screen.font, self.text_box.w, self.text_box.h)
        y = self.text_box.y
        screen.pen = color.black
        for line in lines:
            line_w, _ = screen.measure_text(line)
            x = self.text_box.x + ((self.text_box.w - line_w) / 2)
            screen.text(line, x, y)
            y += y_height

# Just draws the background image then lists the player's inventory.
# If the item is marked hidden it is skipped, otherwise it is split between the top or bottom
# part. Coordinate lists are hard coded in two columns, but only the first column is used here so the descriptions can be longer.
class InventoryScreen():

    def draw(self, player):
        items = []
        notes = []

        item_locs = [
            vec2(17, 20),
            vec2(17, 28),
            vec2(17, 36),
            vec2(17, 44),
            vec2(17, 52),
            vec2(17, 60),
            vec2(17, 68),
            vec2(164, 20),
            vec2(164, 28),
            vec2(164, 36),
            vec2(164, 44),
            vec2(164, 52),
            vec2(164, 60),
            vec2(164, 68)
        ]

        note_locs = [
            vec2(17, 139),
            vec2(17, 147),
            vec2(17, 155),
            vec2(17, 163),
            vec2(17, 171),
            vec2(17, 179),
            vec2(17, 187),
            vec2(164, 139),
            vec2(164, 147),
            vec2(164, 155),
            vec2(164, 163),
            vec2(164, 171),
            vec2(164, 179),
            vec2(164, 187)
        ]

        bg = image.load("assets/inventory.png")
        screen.blit(bg, rect(0, 0, screen.width, screen.height))

        for item in player.inventory:
            item_data = monster.item_db[item]
            if item_data.hidden:
                continue

            if item_data.tangible_status:
                items.append(item_data.text)
            else:
                notes.append(item_data.text)

        screen.pen = color.black

        print(items)
        print(notes)

        for i in range(len(items)):
            if i > 13:
                continue
            screen.text(items[i], item_locs[i])

        for i in range(len(notes)):
            if i > 13:
                continue
            screen.text(notes[i], note_locs[i])


class Cutscene:
    def __init__(self, screens):
        self.screens = screens
        self.index = 0

    def advance(self):
        self.index += 1
        if self.index >= len(self.screens):
            return False
        return True

    def draw(self):
        screen_image = image.load("assets/" + self.screens[self.index].image + ".png")
        self.screens[self.index].draw(screen_image)
