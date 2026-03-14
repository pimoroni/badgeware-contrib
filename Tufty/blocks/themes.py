"""
Colour themes for Tetris.

Each theme defines the full palette needed for Tetris rendering.
Dr. Mario uses its own fixed colours and ignores themes.
"""


def _t(r, g, b, a=255):
    """Shorthand colour constructor."""
    return color.rgb(r, g, b, a)


def _pc(r, g, b):
    """Generate piece colour tuple: (main, highlight, shadow)."""
    return (
        _t(r, g, b),
        _t(min(255, r + 80), min(255, g + 80), min(255, b + 80)),
        _t(max(0, r - 70), max(0, g - 70), max(0, b - 70)),
    )


def classic():
    return {
        "name": "Classic",
        "bg": _t(10, 10, 20), "bbg": _t(6, 6, 14),
        "grd": _t(20, 22, 36), "pbg": _t(16, 18, 32), "pbr": _t(40, 45, 65),
        "lbl": _t(90, 100, 130), "val": _t(255, 255, 255),
        "gho": _t(255, 255, 255, 30), "dng": _t(255, 30, 30, 45),
        "ts": _t(0, 0, 0, 150),
        "pc": {
            "I": _pc(0, 220, 220), "O": _pc(230, 230, 0),
            "T": _pc(180, 0, 220), "S": _pc(0, 220, 0),
            "Z": _pc(230, 0, 0), "J": _pc(40, 40, 240),
            "L": _pc(240, 140, 0),
        },
    }


def neon():
    return {
        "name": "Neon",
        "bg": _t(4, 0, 16), "bbg": _t(6, 0, 20),
        "grd": _t(20, 6, 38), "pbg": _t(10, 3, 24), "pbr": _t(60, 12, 100),
        "lbl": _t(150, 80, 230), "val": _t(255, 230, 255),
        "gho": _t(255, 0, 255, 25), "dng": _t(255, 0, 70, 45),
        "ts": _t(0, 0, 0, 190),
        "pc": {
            "I": _pc(0, 255, 255), "O": _pc(255, 255, 0),
            "T": _pc(255, 0, 255), "S": _pc(0, 255, 80),
            "Z": _pc(255, 50, 50), "J": _pc(80, 80, 255),
            "L": _pc(255, 150, 0),
        },
    }


def gameboy():
    return {
        "name": "Game Boy",
        "bg": _t(15, 56, 15), "bbg": _t(20, 64, 20),
        "grd": _t(35, 80, 35), "pbg": _t(25, 66, 25), "pbr": _t(100, 160, 40),
        "lbl": _t(100, 150, 50), "val": _t(200, 230, 80),
        "gho": _t(155, 188, 15, 30), "dng": _t(200, 220, 60, 40),
        "ts": _t(8, 30, 8, 140),
        "pc": {
            "I": _pc(200, 230, 80), "O": _pc(155, 188, 15),
            "T": _pc(60, 110, 30), "S": _pc(180, 210, 50),
            "Z": _pc(90, 140, 20), "J": _pc(40, 80, 15),
            "L": _pc(130, 170, 40),
        },
    }


def pastel():
    return {
        "name": "Pastel",
        "bg": _t(240, 232, 226), "bbg": _t(250, 244, 238),
        "grd": _t(224, 216, 210), "pbg": _t(236, 228, 222), "pbr": _t(190, 172, 166),
        "lbl": _t(130, 112, 106), "val": _t(50, 40, 38),
        "gho": _t(0, 0, 0, 20), "dng": _t(240, 80, 80, 30),
        "ts": _t(255, 255, 255, 100),
        "pc": {
            "I": _pc(60, 170, 200), "O": _pc(220, 190, 60),
            "T": _pc(170, 90, 180), "S": _pc(80, 190, 100),
            "Z": _pc(210, 90, 90), "J": _pc(80, 100, 190),
            "L": _pc(210, 150, 70),
        },
    }


def hacker():
    return {
        "name": "Hacker",
        "bg": _t(0, 0, 0), "bbg": _t(0, 4, 0),
        "grd": _t(0, 16, 0), "pbg": _t(0, 6, 0), "pbr": _t(0, 50, 0),
        "lbl": _t(0, 100, 0), "val": _t(0, 255, 0),
        "gho": _t(0, 200, 0, 25), "dng": _t(0, 255, 0, 40),
        "ts": _t(0, 0, 0, 190),
        "pc": {
            "I": _pc(0, 255, 0), "O": _pc(50, 200, 50),
            "T": _pc(0, 160, 0), "S": _pc(80, 255, 80),
            "Z": _pc(0, 120, 0), "J": _pc(30, 180, 30),
            "L": _pc(0, 220, 60),
        },
    }


def vaporwave():
    return {
        "name": "Vaporwave",
        "bg": _t(18, 0, 36), "bbg": _t(12, 0, 28),
        "grd": _t(35, 8, 55), "pbg": _t(22, 4, 40), "pbr": _t(255, 60, 160),
        "lbl": _t(255, 100, 180), "val": _t(80, 255, 255),
        "gho": _t(255, 80, 180, 30), "dng": _t(255, 40, 80, 40),
        "ts": _t(0, 0, 0, 170),
        "pc": {
            "I": _pc(0, 255, 255), "O": _pc(255, 255, 60),
            "T": _pc(255, 50, 160), "S": _pc(60, 255, 160),
            "Z": _pc(255, 60, 60), "J": _pc(100, 60, 255),
            "L": _pc(255, 180, 40),
        },
    }


def monochrome():
    return {
        "name": "Mono",
        "bg": _t(0, 0, 0), "bbg": _t(4, 4, 4),
        "grd": _t(20, 20, 20), "pbg": _t(8, 8, 8), "pbr": _t(60, 60, 60),
        "lbl": _t(120, 120, 120), "val": _t(255, 255, 255),
        "gho": _t(255, 255, 255, 25), "dng": _t(255, 255, 255, 35),
        "ts": _t(0, 0, 0, 190),
        "pc": {
            "I": _pc(255, 255, 255), "O": _pc(190, 190, 190),
            "T": _pc(140, 140, 140), "S": _pc(220, 220, 220),
            "Z": _pc(100, 100, 100), "J": _pc(165, 165, 165),
            "L": _pc(210, 210, 210),
        },
    }


def forest():
    return {
        "name": "Forest",
        "bg": _t(8, 14, 6), "bbg": _t(12, 18, 8),
        "grd": _t(26, 36, 18), "pbg": _t(18, 24, 12), "pbr": _t(50, 70, 35),
        "lbl": _t(100, 130, 70), "val": _t(190, 220, 150),
        "gho": _t(130, 180, 80, 30), "dng": _t(180, 80, 40, 40),
        "ts": _t(0, 0, 0, 150),
        "pc": {
            "I": _pc(60, 200, 120), "O": _pc(210, 190, 60),
            "T": _pc(150, 90, 50), "S": _pc(40, 200, 40),
            "Z": _pc(200, 60, 40), "J": _pc(50, 110, 80),
            "L": _pc(200, 150, 40),
        },
    }


def lava():
    return {
        "name": "Lava",
        "bg": _t(14, 4, 0), "bbg": _t(18, 6, 0),
        "grd": _t(36, 12, 4), "pbg": _t(22, 8, 2), "pbr": _t(110, 35, 8),
        "lbl": _t(190, 100, 40), "val": _t(255, 200, 100),
        "gho": _t(255, 80, 0, 30), "dng": _t(255, 50, 0, 50),
        "ts": _t(0, 0, 0, 190),
        "pc": {
            "I": _pc(255, 210, 40), "O": _pc(255, 150, 0),
            "T": _pc(210, 40, 10), "S": _pc(255, 120, 0),
            "Z": _pc(170, 20, 0), "J": _pc(130, 30, 20),
            "L": _pc(255, 70, 0),
        },
    }


def ice():
    return {
        "name": "Ice",
        "bg": _t(4, 8, 22), "bbg": _t(6, 12, 30),
        "grd": _t(16, 28, 50), "pbg": _t(8, 16, 34), "pbr": _t(50, 85, 140),
        "lbl": _t(100, 150, 200), "val": _t(200, 230, 255),
        "gho": _t(160, 200, 240, 30), "dng": _t(80, 160, 240, 40),
        "ts": _t(0, 0, 0, 150),
        "pc": {
            "I": _pc(160, 220, 255), "O": _pc(220, 240, 255),
            "T": _pc(80, 130, 210), "S": _pc(130, 210, 240),
            "Z": _pc(60, 100, 190), "J": _pc(40, 80, 180),
            "L": _pc(190, 215, 255),
        },
    }


THEME_LIST = [
    "classic", "neon", "gameboy", "pastel", "hacker",
    "vaporwave", "monochrome", "forest", "lava", "ice",
]

THEME_FUNCS = {
    "classic": classic, "neon": neon, "gameboy": gameboy,
    "pastel": pastel, "hacker": hacker, "vaporwave": vaporwave,
    "monochrome": monochrome, "forest": forest, "lava": lava, "ice": ice,
}


def get_theme(name):
    """Load a theme by name. Falls back to Classic."""
    return THEME_FUNCS.get(name, classic)()


def get_theme_names():
    """Return list of all theme names."""
    return list(THEME_LIST)
