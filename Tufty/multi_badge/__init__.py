import sys
import os
import math
import json
import gc

sys.path.insert(0, "/system/apps/multi_badge")
os.chdir("/system/apps/multi_badge")

# The Badge app targets Tufty 2350's native 320x240 framebuffer.
badge.mode(HIRES | VSYNC)

CX = screen.width / 2
CY = screen.height / 2

screen.antialias = image.X2

DEFAULT_PROFILE = {
    "ID": "",
    "NAME": "Your Name",
    "ROLE": "Role",
    "LOGO": "",
    "LOGO_LABEL": "LOGO",
    "PHONE": "",
    "EMAIL": "",
    "FIRST_NAME": "",
    "LAST_NAME": "",
    "COMPANY": "",
    "WEBSITE": "",
    "NAME_FONT_NAME": "DynaPuff-Medium.af",
    "NAME_FONT_SIZE": 22,
    "NAME_SHADOW": True,
    "ROLE_FONT_NAME": "MonaSans-Medium.af",
    "ROLE_FONT_SIZE": 14,
    "BG_COLOR": "#FFFFFF",
    "ROLE_TEXT_COLOR": "#FFFFFF"
}


DEFAULT_LAYOUT_CONFIG = {
    "BADGE_HEIGHT": 170,
    "BADGE_BG_COLOR": "#FCFCFC",
    "LOGO_X": 106,
    "LOGO_Y": 18,
    "NAME_Y": 132,
    "ROLE_TEXT_Y": 179,
    "ROLE_BG_COLOR": "#141E2D",
    "PAGE_TRANSITION": "wipe",
    "PAGE_TRANSITION_MS": 160,
    "PAGE_TRANSITION_COLOR": "#141E2D"
}


# badge.json holds your own profiles and is not tracked by git;
# badge.example.json is the template shipped with the repo and is used
# when badge.json does not exist yet.
BADGE_CONFIG_FILES = ("badge.json", "badge.example.json")


def load_badge_config():
    saved_config = {}
    for config_name in BADGE_CONFIG_FILES:
        try:
            with open(config_name, "r") as config_file:
                saved_config = json.loads(config_file.read())
            break
        except OSError:
            continue
        except ValueError as error:
            print("Unable to parse {}:".format(config_name), error)
            break
    else:
        print("No badge.json or badge.example.json found")

    layout_config = DEFAULT_LAYOUT_CONFIG.copy()

    # Current format: {"config": {...}, "profiles": [...]}.
    if isinstance(saved_config, dict) and "profiles" in saved_config:
        saved_layout = saved_config.get("config", {})
        if isinstance(saved_layout, dict):
            layout_config.update(saved_layout)
        saved_profiles = saved_config.get("profiles", [])
    else:
        # Backwards compatibility with the old array or single-profile format.
        saved_profiles = saved_config

    if isinstance(saved_profiles, dict):
        saved_profiles = [saved_profiles]
    if not isinstance(saved_profiles, list) or len(saved_profiles) == 0:
        saved_profiles = [{}]

    profiles = []
    for saved_profile in saved_profiles:
        profile = DEFAULT_PROFILE.copy()
        if isinstance(saved_profile, dict):
            profile.update(saved_profile)

            # Backwards compatibility with the previous JOB field names.
            if "ROLE" not in saved_profile and "JOB" in saved_profile:
                profile["ROLE"] = saved_profile["JOB"]
            if "ROLE_FONT_NAME" not in saved_profile and "JOB_FONT_NAME" in saved_profile:
                profile["ROLE_FONT_NAME"] = saved_profile["JOB_FONT_NAME"]
            if "ROLE_FONT_SIZE" not in saved_profile and "JOB_FONT_SIZE" in saved_profile:
                profile["ROLE_FONT_SIZE"] = saved_profile["JOB_FONT_SIZE"]

        profiles.append(profile)

    return layout_config, profiles


def parse_color(value, fallback):
    try:
        if isinstance(value, str):
            hex_value = value.strip()
            if hex_value.startswith("#"):
                hex_value = hex_value[1:]
            if len(hex_value) == 6:
                packed = int(hex_value, 16)
                return color.rgb(
                    (packed >> 16) & 255,
                    (packed >> 8) & 255,
                    packed & 255
                )

        if isinstance(value, list) and len(value) >= 3:
            return color.rgb(
                clamp(int(value[0]), 0, 255),
                clamp(int(value[1]), 0, 255),
                clamp(int(value[2]), 0, 255)
            )
    except (TypeError, ValueError):
        pass

    return color.rgb(fallback[0], fallback[1], fallback[2])


FONT_CACHE = {}
LOGO_CACHE = {}


def load_vector_font(font_name, fallback_name):
    font_name = str(font_name).strip()
    if not font_name.endswith(".af"):
        font_name += ".af"
    font_path = font_name if font_name.startswith("/") else f"/system/assets/fonts/{font_name}"

    if font_path in FONT_CACHE:
        return FONT_CACHE[font_path]

    try:
        loaded_font = font.load(font_path)
    except (OSError, ValueError) as error:
        print("Unable to load configured font:", error)
        fallback_path = f"/system/assets/fonts/{fallback_name}"
        if fallback_path not in FONT_CACHE:
            FONT_CACHE[fallback_path] = font.load(fallback_path)
        loaded_font = FONT_CACHE[fallback_path]

    FONT_CACHE[font_path] = loaded_font
    return loaded_font


def load_logo(logo_path):
    logo_path = str(logo_path).strip()
    if not logo_path:
        return None
    if logo_path in LOGO_CACHE:
        return LOGO_CACHE[logo_path]

    try:
        loaded_logo = image.load(logo_path)
    except (OSError, ValueError) as error:
        print("Unable to load configured logo:", logo_path, error)
        loaded_logo = None

    LOGO_CACHE[logo_path] = loaded_logo
    return loaded_logo


def parse_font_size(value, fallback):
    try:
        return clamp(int(value), 8, 32)
    except (TypeError, ValueError):
        return fallback


def parse_boolean(value, fallback):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
    return fallback


def parse_coordinate(value, fallback, minimum, maximum):
    try:
        return clamp(int(value), minimum, maximum)
    except (TypeError, ValueError):
        return fallback


def fit_font_size(font_face, message, requested_size, max_width, minimum_size=8):
    screen.font = font_face
    fitted_size = requested_size
    while fitted_size > minimum_size:
        width, _ = screen.measure_text(message, fitted_size)
        if width <= max_width:
            break
        fitted_size -= 1
    return fitted_size


def fit_logo_rect(logo, x, y, width, height):
    if logo is None:
        return None

    scale = min(width / logo.width, height / logo.height)
    fitted_width = logo.width * scale
    fitted_height = logo.height * scale
    return rect(
        x + ((width - fitted_width) / 2),
        y + ((height - fitted_height) / 2),
        fitted_width,
        fitted_height
    )


def vcard_escape(value):
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(";", "\\;")
        .replace(",", "\\,")
    )


def build_vcard(config):
    lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        "N:{};{};;;".format(
            vcard_escape(config["LAST_NAME"]),
            vcard_escape(config["FIRST_NAME"])
        ),
        "FN:{}".format(vcard_escape(config["NAME"]))
    ]

    if config["COMPANY"]:
        lines.append("ORG:{}".format(vcard_escape(config["COMPANY"])))
    if config["ROLE"]:
        lines.append("TITLE:{}".format(vcard_escape(config["ROLE"])))
    if config["PHONE"]:
        lines.append("TEL;TYPE=CELL:{}".format(vcard_escape(config["PHONE"])))
    if config["EMAIL"]:
        lines.append(
            "EMAIL;TYPE=INTERNET:{}".format(vcard_escape(config["EMAIL"]))
        )
    if config["WEBSITE"]:
        lines.append("URL:{}".format(vcard_escape(config["WEBSITE"])))

    lines.append("END:VCARD")
    return "\r\n".join(lines) + "\r\n"


QR_CACHE_ROOT = "/cache"
QR_CACHE_DIR = "/cache/multi_badge"
QR_CACHE_MAGIC = b"BQR1"
QR_CACHE_HEADER_SIZE = 9


def qr_fingerprint(payload):
    # Deterministic FNV-1a fingerprint; unlike hash(), it is stable after reboot.
    fingerprint = 2166136261
    for value in payload.encode("utf-8"):
        fingerprint ^= value
        fingerprint = (fingerprint * 16777619) & 0xFFFFFFFF
    return fingerprint


def qr_cache_key(profile_id):
    key = []
    previous_was_separator = False
    for character in str(profile_id).strip().lower():
        allowed = (
            "a" <= character <= "z"
            or "0" <= character <= "9"
            or character in "-_"
        )
        if allowed:
            key.append(character)
            previous_was_separator = False
        elif not previous_was_separator:
            key.append("_")
            previous_was_separator = True

    normalized = "".join(key).strip("_")
    return normalized if normalized else "profile"


def qr_cache_path(cache_key):
    return "{}/qr_{}.bin".format(QR_CACHE_DIR, cache_key)


def ensure_qr_cache_directory():
    for directory in (QR_CACHE_ROOT, QR_CACHE_DIR):
        try:
            os.mkdir(directory)
        except OSError:
            pass


def read_qr_cache(path, expected_fingerprint):
    try:
        with open(path, "rb") as cache_file:
            header = cache_file.read(QR_CACHE_HEADER_SIZE)
            packed = cache_file.read()
    except OSError:
        return None

    if len(header) != QR_CACHE_HEADER_SIZE or header[:4] != QR_CACHE_MAGIC:
        return None

    stored_fingerprint = (
        (header[4] << 24)
        | (header[5] << 16)
        | (header[6] << 8)
        | header[7]
    )
    matrix_size = header[8]
    expected_size = ((matrix_size * matrix_size) + 7) // 8

    if (
        stored_fingerprint != expected_fingerprint
        or matrix_size < 29
        or matrix_size > QR_SIZE
        or len(packed) != expected_size
    ):
        return None

    return matrix_size, packed


def write_qr_cache(path, fingerprint, matrix_size, packed):
    ensure_qr_cache_directory()
    header = QR_CACHE_MAGIC + bytes([
        (fingerprint >> 24) & 255,
        (fingerprint >> 16) & 255,
        (fingerprint >> 8) & 255,
        fingerprint & 255,
        matrix_size
    ])

    try:
        with open(path, "wb") as cache_file:
            cache_file.write(header)
            cache_file.write(packed)
        return True
    except OSError as error:
        print("Unable to write QR cache:", path, error)
        return False


def pack_qr_matrix(matrix):
    matrix_size = len(matrix)
    packed = bytearray(((matrix_size * matrix_size) + 7) // 8)
    bit_index = 0

    for row in matrix:
        for filled in row:
            if filled:
                packed[bit_index >> 3] |= 0x80 >> (bit_index & 7)
            bit_index += 1

    return matrix_size, packed


def generate_qr_bits(payload):
    # Importing the 36 KB QR module is intentionally deferred to cache misses.
    from uQR import QRCode, ERROR_CORRECT_L

    qr = QRCode(error_correction=ERROR_CORRECT_L, border=4)
    qr.add_data(payload, optimize=0)
    matrix = qr.get_matrix()
    matrix_size, packed = pack_qr_matrix(matrix)
    del matrix
    del qr
    gc.collect()
    return matrix_size, packed


def render_qr_image(matrix_size, packed):
    scale = QR_SIZE // matrix_size
    if scale < 1:
        print("vCard QR code is too large:", matrix_size)
        return None

    rendered_size = matrix_size * scale
    offset = (QR_SIZE - rendered_size) // 2
    qr_image = image(QR_SIZE, QR_SIZE)
    qr_image.pen = color.rgb(255, 255, 255)
    qr_image.clear()
    qr_image.pen = color.rgb(0, 0, 0)

    # Draw horizontal runs instead of allocating one shape per QR module.
    for row_index in range(matrix_size):
        run_start = -1
        for column in range(matrix_size + 1):
            bit_index = (row_index * matrix_size) + column
            filled = (
                column < matrix_size
                and packed[bit_index >> 3] & (0x80 >> (bit_index & 7))
            )
            if filled and run_start < 0:
                run_start = column
            elif not filled and run_start >= 0:
                qr_image.rectangle(
                    offset + (run_start * scale),
                    offset + (row_index * scale),
                    (column - run_start) * scale,
                    scale
                )
                run_start = -1

    return qr_image


def make_qr_image(payload, cache_key):
    fingerprint = qr_fingerprint(payload)
    path = qr_cache_path(cache_key)
    cached = read_qr_cache(path, fingerprint)

    try:
        if cached is None:
            matrix_size, packed = generate_qr_bits(payload)
            if matrix_size > QR_SIZE:
                print("vCard QR code is too large:", matrix_size)
                return None
            write_qr_cache(path, fingerprint, matrix_size, packed)
        else:
            matrix_size, packed = cached

        return render_qr_image(matrix_size, packed)
    except Exception as error:  # noqa: BLE001 - show the badge without the QR rather than crash
        print("Unable to prepare vCard QR code:", error)
        gc.collect()
        return None


contact_font = load_vector_font("MonaSans-Medium.af", "MonaSans-Medium.af")


layout_config, profile_configs = load_badge_config()

# Card layout. Increasing BADGE_HEIGHT keeps the lower edge fixed and moves
# the upper edge upwards.
CARD_X = 12
CARD_BOTTOM = 228
CARD_WIDTH = screen.width - (CARD_X * 2)
CARD_HEIGHT = parse_coordinate(layout_config["BADGE_HEIGHT"], 170, 100, 220)
CARD_Y = CARD_BOTTOM - CARD_HEIGHT
CARD_RADIUS = 14
DEFAULT_BADGE_BACKGROUND = layout_config["BADGE_BG_COLOR"]
LOGO_FRAME_SIZE = 108
LOGO_FRAME_X = parse_coordinate(
    layout_config["LOGO_X"], 106, 0, screen.width - LOGO_FRAME_SIZE
)
LOGO_FRAME_Y = parse_coordinate(
    layout_config["LOGO_Y"], 18, 0, screen.height - LOGO_FRAME_SIZE
)
DEFAULT_NAME_Y = parse_coordinate(layout_config["NAME_Y"], 132, 0, screen.height)
DEFAULT_ROLE_TEXT_Y = parse_coordinate(
    layout_config["ROLE_TEXT_Y"], 179, 0, screen.height
)
DEFAULT_ROLE_BACKGROUND = layout_config["ROLE_BG_COLOR"]
PAGE_TRANSITION = str(layout_config["PAGE_TRANSITION"]).strip().lower()
if PAGE_TRANSITION not in ("wipe", "none"):
    PAGE_TRANSITION = "wipe"
PAGE_TRANSITION_MS = parse_coordinate(
    layout_config["PAGE_TRANSITION_MS"], 160, 80, 1000
)
PAGE_TRANSITION_COLOR = parse_color(
    layout_config["PAGE_TRANSITION_COLOR"], (20, 30, 45)
)
ROLE_X = 30
ROLE_Y = 169
ROLE_WIDTH = screen.width - (ROLE_X * 2)
ROLE_HEIGHT = 36

# The rear card leaves the same 12-pixel animated border on every side.
REAR_CARD_MARGIN = 12
REAR_CARD_Y = REAR_CARD_MARGIN
REAR_CARD_WIDTH = screen.width - (REAR_CARD_MARGIN * 2)
REAR_CARD_HEIGHT = screen.height - (REAR_CARD_MARGIN * 2)
REAR_CARD_RADIUS = 14
REAR_NAME_Y = 16
CONTACT_ICON_X = 29
CONTACT_TEXT_X = 58
PHONE_Y = 49
EMAIL_Y = 72
QR_SIZE = 130
QR_X = (screen.width - QR_SIZE) // 2
QR_Y = 94


def prepare_profile(config, cache_key):
    name = str(config["NAME"])
    role = str(config["ROLE"])
    phone = str(config["PHONE"])
    email = str(config["EMAIL"])
    name_font = load_vector_font(config["NAME_FONT_NAME"], DEFAULT_PROFILE["NAME_FONT_NAME"])
    role_font = load_vector_font(config["ROLE_FONT_NAME"], DEFAULT_PROFILE["ROLE_FONT_NAME"])
    name_size = parse_font_size(config["NAME_FONT_SIZE"], DEFAULT_PROFILE["NAME_FONT_SIZE"])
    role_size = parse_font_size(config["ROLE_FONT_SIZE"], DEFAULT_PROFILE["ROLE_FONT_SIZE"])
    logo = load_logo(config["LOGO"])
    qr_image = make_qr_image(build_vcard(config), cache_key)

    return {
        "id": str(config["ID"]),
        "name": name,
        "role": role,
        "phone": phone,
        "email": email,
        "qr_image": qr_image,
        "logo": logo,
        "logo_label": str(config["LOGO_LABEL"]),
        "logo_rect": fit_logo_rect(
            logo, LOGO_FRAME_X + 4, LOGO_FRAME_Y + 4, 100, 100
        ),
        "name_font": name_font,
        "name_size": fit_font_size(name_font, name, name_size, 270, 12),
        "name_shadow": parse_boolean(config["NAME_SHADOW"], True),
        "name_y": parse_coordinate(
            config.get("NAME_Y", DEFAULT_NAME_Y), DEFAULT_NAME_Y, 0, screen.height
        ),
        "role_font": role_font,
        "role_size": fit_font_size(role_font, role, role_size, 238, 10),
        "role_text_y": parse_coordinate(
            config.get("ROLE_TEXT_Y", DEFAULT_ROLE_TEXT_Y),
            DEFAULT_ROLE_TEXT_Y,
            0,
            screen.height
        ),
        "phone_size": fit_font_size(contact_font, phone, 16, 232, 10),
        "email_size": fit_font_size(contact_font, email, 15, 232, 9),
        "background": parse_color(config["BG_COLOR"], (255, 255, 255)),
        "badge_background": parse_color(
            config.get("BADGE_BG_COLOR", DEFAULT_BADGE_BACKGROUND),
            (252, 252, 252)
        ),
        "role_background": parse_color(
            config.get("ROLE_BG_COLOR", DEFAULT_ROLE_BACKGROUND), (20, 30, 45)
        ),
        "role_text_color": parse_color(config["ROLE_TEXT_COLOR"], (255, 255, 255))
    }


profiles = []
profile_cache_keys = []
for profile_config in profile_configs:
    profile_id = str(profile_config["ID"]).strip()
    if not profile_id:
        profile_id = "profile_{:08x}".format(
            qr_fingerprint(build_vcard(profile_config))
        )
        print("Profile without ID; using:", profile_id)

    cache_key = qr_cache_key(profile_id)
    if cache_key in profile_cache_keys:
        cache_key += "_{:08x}".format(qr_fingerprint(build_vcard(profile_config)))
        print("Duplicate profile ID; using cache key:", cache_key)

    profile_cache_keys.append(cache_key)
    profiles.append(prepare_profile(profile_config, cache_key))

profile_index = 0
active_profile = profiles[profile_index]

id_name = active_profile["name"]
id_role = active_profile["role"]
id_phone = active_profile["phone"]
id_email = active_profile["email"]
id_qr = active_profile["qr_image"]
id_logo = active_profile["logo"]
id_logo_label = active_profile["logo_label"]
id_logo_rect = active_profile["logo_rect"]
name_font = active_profile["name_font"]
role_font = active_profile["role_font"]
NAME_FONT_SIZE = active_profile["name_size"]
NAME_SHADOW = active_profile["name_shadow"]
name_y = active_profile["name_y"]
ROLE_FONT_SIZE = active_profile["role_size"]
role_text_y = active_profile["role_text_y"]
PHONE_FONT_SIZE = active_profile["phone_size"]
EMAIL_FONT_SIZE = active_profile["email_size"]
badge_background = active_profile["badge_background"]
role_background = active_profile["role_background"]
role_text_color = active_profile["role_text_color"]

id_body = shape.rounded_rectangle(0, 0, CARD_WIDTH, CARD_HEIGHT, CARD_RADIUS)
id_outline = shape.rounded_rectangle(0, 0, CARD_WIDTH, CARD_HEIGHT, CARD_RADIUS).stroke(3)
rear_body = shape.rounded_rectangle(
    0, 0, REAR_CARD_WIDTH, REAR_CARD_HEIGHT, REAR_CARD_RADIUS
)
rear_outline = shape.rounded_rectangle(
    0, 0, REAR_CARD_WIDTH, REAR_CARD_HEIGHT, REAR_CARD_RADIUS
).stroke(3)
logo_shadow = shape.rounded_rectangle(LOGO_FRAME_X + 4, LOGO_FRAME_Y + 4, LOGO_FRAME_SIZE, LOGO_FRAME_SIZE, 14)
logo_frame = shape.rounded_rectangle(LOGO_FRAME_X, LOGO_FRAME_Y, LOGO_FRAME_SIZE, LOGO_FRAME_SIZE, 14)
logo_outline = shape.rounded_rectangle(LOGO_FRAME_X, LOGO_FRAME_Y, LOGO_FRAME_SIZE, LOGO_FRAME_SIZE, 14).stroke(2)
role_pill = shape.rounded_rectangle(ROLE_X, ROLE_Y, ROLE_WIDTH, ROLE_HEIGHT, ROLE_HEIGHT / 2)
phone_icon_panel = shape.rounded_rectangle(
    CONTACT_ICON_X - 3, PHONE_Y - 2, 24, 22, 6
)
email_icon_panel = shape.rounded_rectangle(
    CONTACT_ICON_X - 3, EMAIL_Y - 2, 24, 22, 6
)
phone_icon = shape.custom([
    vec2(CONTACT_ICON_X + 3, PHONE_Y),
    vec2(CONTACT_ICON_X + 7, PHONE_Y),
    vec2(CONTACT_ICON_X + 10, PHONE_Y + 5),
    vec2(CONTACT_ICON_X + 8, PHONE_Y + 7),
    vec2(CONTACT_ICON_X + 12, PHONE_Y + 11),
    vec2(CONTACT_ICON_X + 14, PHONE_Y + 9),
    vec2(CONTACT_ICON_X + 18, PHONE_Y + 12),
    vec2(CONTACT_ICON_X + 17, PHONE_Y + 16),
    vec2(CONTACT_ICON_X + 14, PHONE_Y + 18),
    vec2(CONTACT_ICON_X + 10, PHONE_Y + 17),
    vec2(CONTACT_ICON_X + 5, PHONE_Y + 13),
    vec2(CONTACT_ICON_X + 1, PHONE_Y + 7),
    vec2(CONTACT_ICON_X, PHONE_Y + 3)
])
email_icon = shape.rounded_rectangle(
    CONTACT_ICON_X, EMAIL_Y + 2, 18, 14, 2
).stroke(2)
email_flap = shape.custom([
    vec2(CONTACT_ICON_X + 1, EMAIL_Y + 3),
    vec2(CONTACT_ICON_X + 9, EMAIL_Y + 9),
    vec2(CONTACT_ICON_X + 17, EMAIL_Y + 3),
    vec2(CONTACT_ICON_X + 17, EMAIL_Y + 5),
    vec2(CONTACT_ICON_X + 9, EMAIL_Y + 11),
    vec2(CONTACT_ICON_X + 1, EMAIL_Y + 5)
])
qr_shadow = shape.rounded_rectangle(QR_X + 3, QR_Y + 3, QR_SIZE, QR_SIZE, 4)

hue = 255
chroma = 0
background = active_profile["background"]
rear_view = False
page_transition_active = False
page_transition_elapsed = 0
page_transition_target_rear = False

# Pre-calculate the HIRES ripple so each frame only draws cached 8x8 tiles.
RIPPLE_TILE_SIZE = 8
RIPPLE_LEVELS = 16
RIPPLE_LUT_SIZE = 256
RIPPLE_COLUMNS = (screen.width + RIPPLE_TILE_SIZE - 1) // RIPPLE_TILE_SIZE
RIPPLE_ROWS = (screen.height + RIPPLE_TILE_SIZE - 1) // RIPPLE_TILE_SIZE
RIPPLE_CYCLE = math.pi * 2
RIPPLE_TIME_SCALE = RIPPLE_LUT_SIZE / (RIPPLE_CYCLE * 400)
RIPPLE_DISTANCE_SCALE = RIPPLE_LUT_SIZE / (RIPPLE_CYCLE * 12)

RIPPLE_PENS = []
for level in range(RIPPLE_LEVELS):
    alpha = 80 + ((50 * level) // (RIPPLE_LEVELS - 1))
    RIPPLE_PENS.append(color.rgb(0, 0, 0, alpha))

RIPPLE_LEVEL_LUT = bytearray(RIPPLE_LUT_SIZE)
for index in range(RIPPLE_LUT_SIZE):
    wave = (math.sin(index * RIPPLE_CYCLE / RIPPLE_LUT_SIZE) + 1) / 2
    RIPPLE_LEVEL_LUT[index] = int(wave * (RIPPLE_LEVELS - 1))

RIPPLE_PHASES = bytearray()
ripple_cy = CY - 16
for row in range(RIPPLE_ROWS):
    tile_y = (row * RIPPLE_TILE_SIZE) + (RIPPLE_TILE_SIZE / 2)
    for column in range(RIPPLE_COLUMNS):
        tile_x = (column * RIPPLE_TILE_SIZE) + (RIPPLE_TILE_SIZE / 2)
        distance = math.sqrt((tile_x - CX) ** 2 + (tile_y - ripple_cy) ** 2)
        RIPPLE_PHASES.append(int(distance * RIPPLE_DISTANCE_SCALE) & 255)


def draw_background():
    time_phase = int(-badge.ticks * RIPPLE_TIME_SCALE) & 255
    phase_index = 0

    for row in range(RIPPLE_ROWS):
        y = row * RIPPLE_TILE_SIZE
        for column in range(RIPPLE_COLUMNS):
            x = column * RIPPLE_TILE_SIZE
            phase = (time_phase + RIPPLE_PHASES[phase_index]) & 255
            screen.pen = RIPPLE_PENS[RIPPLE_LEVEL_LUT[phase]]
            screen.rectangle(x, y, RIPPLE_TILE_SIZE, RIPPLE_TILE_SIZE)
            phase_index += 1


def shadow_text(message, x, y, size):
    screen.pen = color.rgb(20, 40, 60, 100)
    screen.text(message, x + 2, y + 2, size)
    screen.pen = color.rgb(0, 0, 0)
    screen.text(message, x, y, size)


def center_text(message, y, size, use_shadow):
    width, _ = screen.measure_text(message, size)
    x = CX - (width / 2)
    if use_shadow:
        shadow_text(message, x, y, size)
    else:
        screen.pen = color.rgb(0, 0, 0)
        screen.text(message, x, y, size)


def center_colored_text(message, y, size, pen):
    width, _ = screen.measure_text(message, size)
    screen.pen = pen
    screen.text(message, CX - (width / 2), y, size)


def center_text_in_rect(message, bounds, size, pen):
    width, height = screen.measure_text(message, size)
    screen.pen = pen
    screen.text(
        message,
        bounds.x + ((bounds.w - width) / 2),
        bounds.y + ((bounds.h - height) / 2),
        size
    )


def draw_logo():
    screen.pen = color.rgb(20, 30, 45, 80)
    screen.shape(logo_shadow)
    screen.pen = color.rgb(255, 255, 255)
    screen.shape(logo_frame)
    screen.pen = color.rgb(20, 30, 45, 100)
    screen.shape(logo_outline)

    if id_logo is not None:
        screen.blit(id_logo, id_logo_rect)
    else:
        screen.font = contact_font
        label_size = fit_font_size(contact_font, id_logo_label, 24, 88, 12)
        center_text_in_rect(
            id_logo_label,
            rect(LOGO_FRAME_X + 4, LOGO_FRAME_Y + 4, 100, 100),
            label_size,
            color.rgb(20, 30, 45)
        )


def draw_front():
    draw_logo()

    screen.font = name_font
    center_text(id_name, name_y, NAME_FONT_SIZE, NAME_SHADOW)

    screen.pen = role_background
    screen.shape(role_pill)
    screen.font = role_font
    center_colored_text(id_role, role_text_y, ROLE_FONT_SIZE, role_text_color)

    # Profile indicators belong exclusively to the front of the badge.
    spacing = 14
    start_x = CX - (((len(profiles) - 1) * spacing) / 2)
    for index in range(len(profiles)):
        screen.pen = color.rgb(20, 30, 45) if index == profile_index else color.rgb(130, 135, 145)
        screen.circle(
            start_x + (index * spacing),
            218,
            3 if index == profile_index else 2
        )


def draw_contact_value(value, y, value_size):
    screen.font = contact_font
    screen.pen = color.rgb(20, 30, 45)
    screen.text(value if value else "-", CONTACT_TEXT_X, y + 1, value_size)


def draw_contact_icons():
    screen.pen = color.rgb(235, 237, 240)
    screen.shape(phone_icon_panel)
    screen.shape(email_icon_panel)
    screen.pen = color.rgb(20, 30, 45)
    screen.shape(phone_icon)
    screen.shape(email_icon)
    screen.shape(email_flap)


def draw_rear():
    screen.font = name_font
    center_text(id_name, REAR_NAME_Y, NAME_FONT_SIZE, NAME_SHADOW)

    draw_contact_icons()
    draw_contact_value(id_phone, PHONE_Y, PHONE_FONT_SIZE)
    draw_contact_value(id_email, EMAIL_Y, EMAIL_FONT_SIZE)

    screen.pen = color.rgb(20, 30, 45, 60)
    screen.shape(qr_shadow)
    if id_qr is not None:
        screen.blit(id_qr, vec2(QR_X, QR_Y))
    else:
        screen.pen = color.rgb(255, 255, 255)
        screen.rectangle(QR_X, QR_Y, QR_SIZE, QR_SIZE)
        screen.font = contact_font
        center_colored_text(
            "QR unavailable", QR_Y + 54, 12, color.rgb(20, 30, 45)
        )


def change_background(chroma_delta):
    global background, chroma

    chroma += chroma_delta
    chroma = clamp(chroma, 0, 255)
    background = color.oklch(255, chroma, hue)


def change_profile(offset):
    global profile_index, active_profile
    global id_name, id_role, id_phone, id_email, id_qr
    global id_logo, id_logo_label, id_logo_rect
    global name_font, role_font, NAME_FONT_SIZE, NAME_SHADOW, ROLE_FONT_SIZE
    global name_y, role_text_y
    global PHONE_FONT_SIZE, EMAIL_FONT_SIZE, background, hue, chroma
    global badge_background, role_background, role_text_color

    profile_index = (profile_index + offset) % len(profiles)
    active_profile = profiles[profile_index]
    id_name = active_profile["name"]
    id_role = active_profile["role"]
    id_phone = active_profile["phone"]
    id_email = active_profile["email"]
    id_qr = active_profile["qr_image"]
    id_logo = active_profile["logo"]
    id_logo_label = active_profile["logo_label"]
    id_logo_rect = active_profile["logo_rect"]
    name_font = active_profile["name_font"]
    role_font = active_profile["role_font"]
    NAME_FONT_SIZE = active_profile["name_size"]
    NAME_SHADOW = active_profile["name_shadow"]
    name_y = active_profile["name_y"]
    ROLE_FONT_SIZE = active_profile["role_size"]
    role_text_y = active_profile["role_text_y"]
    PHONE_FONT_SIZE = active_profile["phone_size"]
    EMAIL_FONT_SIZE = active_profile["email_size"]
    background = active_profile["background"]
    badge_background = active_profile["badge_background"]
    role_background = active_profile["role_background"]
    role_text_color = active_profile["role_text_color"]
    hue = 255
    chroma = 0


def init():
    pass


def update():
    global rear_view
    global page_transition_active, page_transition_elapsed
    global page_transition_target_rear

    if badge.pressed(BUTTON_B):
        if PAGE_TRANSITION == "none":
            rear_view = not rear_view
        elif not page_transition_active:
            page_transition_active = True
            page_transition_elapsed = 0
            page_transition_target_rear = not rear_view

    if badge.pressed(BUTTON_UP):
        change_profile(-1)

    if badge.pressed(BUTTON_DOWN):
        change_profile(1)

    if badge.held(BUTTON_C):
        change_background(5)

    if badge.held(BUTTON_A):
        change_background(-5)

    curtain_width = 0
    if page_transition_active:
        page_transition_elapsed += max(0, badge.ticks_delta)
        progress = min(1, page_transition_elapsed / PAGE_TRANSITION_MS)

        if progress >= 0.5:
            rear_view = page_transition_target_rear

        # Smoothstep easing: expand to full width, then retract.
        phase = 1 - abs((progress * 2) - 1)
        eased_phase = phase * phase * (3 - (2 * phase))
        curtain_width = int(REAR_CARD_WIDTH * eased_phase)

        if progress >= 1:
            page_transition_active = False

    screen.pen = background
    screen.clear()
    draw_background()

    if rear_view:
        card_body = rear_body
        card_outline = rear_outline
        card_y = REAR_CARD_Y
        card_width = REAR_CARD_WIDTH
    else:
        card_body = id_body
        card_outline = id_outline
        card_y = CARD_Y
        card_width = CARD_WIDTH

    card_body.transform = mat3().translate(CX, card_y)
    card_outline.transform = mat3().translate(CX, card_y)
    card_body.transform = card_body.transform.translate(-(card_width / 2), 0)
    card_outline.transform = card_outline.transform.translate(-(card_width / 2), 0)

    screen.pen = color.rgb(20, 30, 45, 90)
    card_body.transform = card_body.transform.translate(5, 5)
    screen.shape(card_body)
    screen.pen = badge_background
    card_body.transform = card_body.transform.translate(-5, -5)
    screen.shape(card_body)
    screen.pen = color.rgb(20, 30, 45, 100)
    screen.shape(card_outline)

    if rear_view:
        draw_rear()
    else:
        draw_front()

    if curtain_width > 0:
        curtain_x = int(CX - (curtain_width / 2))
        screen.pen = PAGE_TRANSITION_COLOR
        screen.rectangle(
            curtain_x,
            REAR_CARD_Y,
            curtain_width,
            REAR_CARD_HEIGHT
        )


def on_exit():
    pass


init()
run(update)
