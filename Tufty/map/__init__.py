import json
import math
from datetime import datetime, timezone
import random

badge.mode(HIRES | VSYNC)

screen.antialias = image.X4
screen.font = font.sins

STAR_PATTERN = brush.pattern(
    color.rgb(0, 0, 0),
    color.grey,
    20
)

SEA_PATTERN = brush.pattern(
    color.navy,
    color.rgb(255, 255, 255, 140),
    32
)

NIGHT_COLOR = color.rgb(0, 0, 0, 64)

coastlines = []
coastline_bounds = []
coastline_lats = []


def load_coastlines():
    with open("/system/assets/world.geo.json", "r") as f:
        data = json.loads(f.read())

    for country in data:
        for polygon in country["polygons"]:
            mn = 180
            mx = -180
            lat_mn = 90
            lat_mx = -90
            path = []

            for p in polygon:
                lon = p[0]
                lat = -p[1]

                path.append(vec2(lon, lat))

                mn = min(mn, lon)
                mx = max(mx, lon)
                lat_mn = min(lat_mn, lat)
                lat_mx = max(lat_mx, lat)

            coastline_lats.append(
                (lat_mx + lat_mn) / 2
            )

            coastlines.append(shape.custom(path))
            coastline_bounds.append((mn, mx))


def get_tau_and_dec():
    dt = datetime.now(timezone.utc)

    year = dt.year

    start = datetime(
        year,
        1,
        1,
        tzinfo=timezone.utc
    )

    days_into_year = (
        dt - start
    ).total_seconds() / 86400

    seconds_since_midnight = (
        dt.hour * 3600
        + dt.minute * 60
        + dt.second
    )

    degrees = (
        seconds_since_midnight / 86400
    ) * 360

    declination = -23.45 * math.cos(
        math.radians(
            (360 / 365) * (days_into_year + 10)
        )
    )

    return degrees - 180, declination


def calc_day_night_latitude(longitude, dec):
    cos_lat = math.cos(
        math.radians(longitude)
    )

    try:
        tan_lat = (
            -cos_lat
            / math.tan(math.radians(dec))
        )

        return math.degrees(
            math.atan(tan_lat)
        )

    except ZeroDivisionError:
        if cos_lat > 0:
            return 90.0
        elif cos_lat < 0:
            return -90.0
        else:
            return 0


load_coastlines()

x = 160
y = 120
speed = 20
scale = 4


def update():
    global x, y, scale

    screen.antialias = image.X4

    screen.pen = STAR_PATTERN
    screen.clear()

    if badge.held(BUTTON_DOWN):
        y -= speed

    if badge.held(BUTTON_C):
        x -= speed

    if badge.held(BUTTON_UP):
        y += speed

    if badge.held(BUTTON_A):
        x += speed

    if badge.held(BUTTON_B):
        scale += 4

    tau, dec = get_tau_and_dec()

    daynight = [
        vec2(-180, 90)
    ]

    for i in range(-180, 181):
        lat = calc_day_night_latitude(
            i + tau,
            dec
        )

        daynight.append(
            vec2(i, -lat)
        )

    daynight.append(
        vec2(180, 90)
    )

    daynight_shape = shape.custom(daynight)

    world_copies = [-360, 0, 360]

    for offset in world_copies:
        transform = (
            mat3()
            .translate(
                x + offset * scale,
                y
            )
            .scale(
                scale,
                scale
            )
        )

        screen.pen = SEA_PATTERN

        screen.rectangle(
            x + offset * scale - 180 * scale,
            y - 90 * scale,
            360 * scale,
            180 * scale
        )

        for i, coastline in enumerate(coastlines):
            latitude = coastline_lats[i]
            random.seed(i)
            if abs(latitude) > 60:
                screen.pen = random.choice([color.smoke, color.white])
            elif -22 <= latitude <= 10:
                screen.pen = random.choice([color.yellow, color.yellow, color.orange])
            else:
                screen.pen = color.lime

            coastline.transform = transform
            screen.shape(coastline)

        screen.pen = NIGHT_COLOR

        daynight_shape.transform = transform
        screen.shape(daynight_shape)


run(update)


world_copies = [-360, 0, 360]
