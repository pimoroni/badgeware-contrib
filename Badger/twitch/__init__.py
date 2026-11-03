# Twitch Streamer Stats for Badger 2350
# Displays follower/subscriber counts and latest follower info
# from https://badge.pausedbypaul.net/api/streamer/<uuid>
#
# Set TWITCH_UUID in secrets.py to your streamer UUID.
# Buttons: UP/DOWN = page nav, hold A = refresh data

import os
import sys

sys.path.insert(0, "/system/apps/twitch")
os.chdir("/system/apps/twitch")

import secrets
import urequests
import wifi
import json

secrets.require("TWITCH_UUID")

# Use larger built-in ROM fonts for better readability
small_font = font.nope
large_font = font.ignore

# Display constants
WIDTH = screen.width
HEIGHT = screen.height
HEADER_H = 40
FOOTER_H = 15
API_URL = "https://badge.pausedbypaul.net/api/streamer/" + secrets.TWITCH_UUID
CACHE_FILE = "/twitch_cache.json"

# Page state
current_page = 0
pages = []
data_fetched = False

# Cached streamer data
streamer = {
    "display_name": "",
    "broadcaster_type": "",
    "follower_count": 0,
    "subscriber_count": 0,
    "latest_follower": "",
    "latest_subscriber": "",
    "latest_subscriber_months": 0,
    "last_cheerer": "",
    "last_cheer_amount": 0,
    "latest_sub_gifter": "",
    "latest_sub_gift_count": 0,
    "is_live": False,
}

# badge_config flags from the API
badge_config = {
    "show_latest_follower": True,
    "show_latest_sub": True,
    "show_latest_cheer": True,
    "show_latest_gifted_sub": True,
    "auto_scroll": 0,
}


def format_number(num):
    """Format numbers with k/m suffixes and 2 decimal places.

    Examples:
        1234567 -> "1.23m"
        12345 -> "12.35k"
        999 -> "999"
    """
    if num >= 1000000:
        return f"{num / 1000000:.2f}m"
    if num >= 1000:
        return f"{num / 1000:.2f}k"
    return str(num)


def show_message(text):
    """Display a centred status message (fast refresh)."""
    badge.mode(FAST_UPDATE)
    screen.pen = color.white
    screen.clear()
    screen.pen = color.black
    screen.font = large_font
    tw, _ = screen.measure_text(text)
    screen.text(text, (WIDTH - tw) // 2, (HEIGHT // 2) - 8)
    badge.update()


def draw_header():
    """Consistent header across all pages: name + broadcaster type (centered, prominent)."""
    screen.pen = color.black
    screen.shape(shape.rectangle(0, 0, WIDTH, HEADER_H))

    # Draw display name at top - centered and large
    screen.pen = color.white
    screen.font = large_font
    name = streamer["display_name"] or "---"
    tw, _ = screen.measure_text(name)
    screen.text(name, (WIDTH - tw) // 2, 2)

    # Draw broadcaster status below username - centered with more spacing
    btype = streamer["broadcaster_type"]
    if btype in ("affiliate", "partner"):
        screen.font = small_font
        screen.pen = color.white
        if btype == "partner":
            status = "Twitch Partner"
        else:
            status = "Twitch Affiliate"
        tw, _ = screen.measure_text(status)
        screen.text(status, (WIDTH - tw) // 2, 26)

    # LIVE indicator in top-right corner (no box, just text)
    if streamer["is_live"]:
        screen.font = small_font
        screen.pen = color.white
        screen.text("LIVE", WIDTH - 30, 2)

    # Battery indicator in top-right corner
    level = badge.battery_level()
    bx = WIDTH - 22  # top-right position
    by = 28
    bw = 18  # battery body width
    bh = 9   # battery body height
    nw = 2   # nub width
    nh = 5   # nub height

    # Battery body outline (white on black header)
    screen.pen = color.white
    screen.shape(shape.rectangle(bx, by, bw, bh).stroke(1))
    # Battery nub (positive terminal)
    screen.shape(shape.rectangle(bx + bw, by + (bh - nh) // 2, nw, nh))

    # Fill level inside the body
    inner_margin = 2
    inner_max_w = bw - (inner_margin * 2)
    fill_w = max(1, int(inner_max_w * level / 100))
    screen.shape(shape.rectangle(bx + inner_margin, by + inner_margin, fill_w, bh - (inner_margin * 2)))


def draw_footer():
    """Page navigation footer with dots."""
    total = len(pages)
    y = HEIGHT - FOOTER_H

    # Page indicator dots
    dot_y = y + (FOOTER_H // 2) + 1
    spacing = 12
    total_w = (total - 1) * spacing
    sx = (WIDTH // 2) - (total_w // 2)
    for i in range(total):
        dx = sx + (i * spacing)
        screen.pen = color.black
        if i == current_page:
            screen.shape(shape.circle(dx, dot_y, 3))
        else:
            screen.shape(shape.circle(dx, dot_y, 3).stroke(1))


def draw_page_stats():
    """Page 1: Follower count and subscriber count (if affiliate/partner)."""
    screen.pen = color.white
    screen.clear()
    draw_header()
    screen.pen = color.black

    btype = streamer["broadcaster_type"]
    has_subs = btype in ("affiliate", "partner")

    # Calculate vertical center of available space
    available_h = HEIGHT - HEADER_H - FOOTER_H
    content_h = 52  # Approximate height of number + label
    y = HEADER_H + (available_h - content_h) // 2

    if has_subs:
        # Two-column layout for affiliate/partner
        mid = WIDTH // 2

        # Left column - Followers
        screen.font = large_font
        count_text = format_number(streamer["follower_count"])
        tw, _ = screen.measure_text(count_text)
        screen.text(count_text, (mid // 2) - (tw // 2), y)

        screen.font = small_font
        screen.pen = color.dark_grey
        label = "followers"
        tw, _ = screen.measure_text(label)
        screen.text(label, (mid // 2) - (tw // 2), y + 26)

        # Right column - Subscribers (no divider line)
        screen.pen = color.black
        screen.font = large_font
        count_text = format_number(streamer["subscriber_count"])
        tw, _ = screen.measure_text(count_text)
        screen.text(count_text, mid + (mid // 2) - (tw // 2), y)

        screen.font = small_font
        screen.pen = color.dark_grey
        label = "subscribers"
        tw, _ = screen.measure_text(label)
        screen.text(label, mid + (mid // 2) - (tw // 2), y + 26)
    else:
        # Centered layout for non-affiliate
        screen.font = large_font
        count = format_number(streamer["follower_count"])
        tw, _ = screen.measure_text(count)
        screen.text(count, (WIDTH - tw) // 2, y)

        screen.font = small_font
        screen.pen = color.dark_grey
        label = "followers"
        tw, _ = screen.measure_text(label)
        screen.text(label, (WIDTH - tw) // 2, y + 26)

    draw_footer()


def draw_page_latest_follower():
    """Latest follower name with total follower count (centered layout)."""
    screen.pen = color.white
    screen.clear()
    draw_header()
    screen.pen = color.black

    # Calculate vertical center - two sections with gap
    available_h = HEIGHT - HEADER_H - FOOTER_H
    content_h = 95  # Total height of both sections
    start_y = HEADER_H + (available_h - content_h) // 2

    # Centered follower count at top
    y = start_y
    screen.font = large_font
    count_text = format_number(streamer["follower_count"])
    tw, _ = screen.measure_text(count_text)
    screen.text(count_text, (WIDTH - tw) // 2, y)

    screen.font = small_font
    screen.pen = color.dark_grey
    label_text = "followers"
    tw, _ = screen.measure_text(label_text)
    screen.text(label_text, (WIDTH - tw) // 2, y + 26)

    # Latest follower below
    y = start_y + 48
    screen.font = small_font
    screen.pen = color.dark_grey
    label = "latest follower"
    tw, _ = screen.measure_text(label)
    screen.text(label, (WIDTH - tw) // 2, y)

    screen.font = large_font
    screen.pen = color.black
    follower = streamer["latest_follower"] or "---"
    tw, _ = screen.measure_text(follower)
    screen.text(follower, (WIDTH - tw) // 2, y + 20)

    draw_footer()


def draw_page_latest_subscriber():
    """Latest subscriber name with total subscriber count (centered layout)."""
    screen.pen = color.white
    screen.clear()
    draw_header()
    screen.pen = color.black

    # Calculate vertical center - two sections with gap
    available_h = HEIGHT - HEADER_H - FOOTER_H
    content_h = 95  # Total height of both sections
    start_y = HEADER_H + (available_h - content_h) // 2

    # Centered subscriber count at top
    y = start_y
    screen.font = large_font
    count_text = format_number(streamer["subscriber_count"])
    tw, _ = screen.measure_text(count_text)
    screen.text(count_text, (WIDTH - tw) // 2, y)

    screen.font = small_font
    screen.pen = color.dark_grey
    label_text = "subscribers"
    tw, _ = screen.measure_text(label_text)
    screen.text(label_text, (WIDTH - tw) // 2, y + 26)

    # Latest subscriber below
    y = start_y + 48
    screen.font = small_font
    screen.pen = color.dark_grey
    label = "latest subscriber"
    tw, _ = screen.measure_text(label)
    screen.text(label, (WIDTH - tw) // 2, y)

    screen.font = large_font
    screen.pen = color.black
    sub = streamer["latest_subscriber"] or "---"
    months = streamer["latest_subscriber_months"]
    if months and months > 1:
        sub = sub + " x" + str(months)
    tw, _ = screen.measure_text(sub)
    screen.text(sub, (WIDTH - tw) // 2, y + 20)

    draw_footer()


def draw_page_latest_cheer():
    """Latest cheerer with bit amount (centered layout)."""
    screen.pen = color.white
    screen.clear()
    draw_header()
    screen.pen = color.black

    # Calculate vertical center - two sections with gap
    available_h = HEIGHT - HEADER_H - FOOTER_H
    content_h = 95  # Total height of both sections
    start_y = HEADER_H + (available_h - content_h) // 2

    # Centered cheer label at top
    y = start_y
    screen.font = small_font
    screen.pen = color.dark_grey
    label = "latest cheer"
    tw, _ = screen.measure_text(label)
    screen.text(label, (WIDTH - tw) // 2, y)

    # Bit amount
    screen.font = large_font
    screen.pen = color.black
    bits_text = format_number(streamer["last_cheer_amount"]) + " bits"
    tw, _ = screen.measure_text(bits_text)
    screen.text(bits_text, (WIDTH - tw) // 2, y + 20)

    # "from" label and cheerer name below
    y = start_y + 48
    screen.font = small_font
    screen.pen = color.dark_grey
    from_label = "from"
    tw, _ = screen.measure_text(from_label)
    screen.text(from_label, (WIDTH - tw) // 2, y)

    screen.font = large_font
    screen.pen = color.black
    cheerer = streamer["last_cheerer"] or "---"
    tw, _ = screen.measure_text(cheerer)
    screen.text(cheerer, (WIDTH - tw) // 2, y + 20)

    draw_footer()


def draw_page_latest_gifted_sub():
    """Latest gifted sub with gift count (centered layout)."""
    screen.pen = color.white
    screen.clear()
    draw_header()
    screen.pen = color.black

    # Calculate vertical center - two sections with gap
    available_h = HEIGHT - HEADER_H - FOOTER_H
    content_h = 95  # Total height of both sections
    start_y = HEADER_H + (available_h - content_h) // 2

    # Centered gifted sub label at top
    y = start_y
    screen.font = small_font
    screen.pen = color.dark_grey
    label = "gifted subs"
    tw, _ = screen.measure_text(label)
    screen.text(label, (WIDTH - tw) // 2, y)

    # Gift count
    screen.font = large_font
    screen.pen = color.black
    count_text = format_number(streamer["latest_sub_gift_count"])
    tw, _ = screen.measure_text(count_text)
    screen.text(count_text, (WIDTH - tw) // 2, y + 20)

    # "from" label and gifter name below
    y = start_y + 48
    screen.font = small_font
    screen.pen = color.dark_grey
    from_label = "from"
    tw, _ = screen.measure_text(from_label)
    screen.text(from_label, (WIDTH - tw) // 2, y)

    screen.font = large_font
    screen.pen = color.black
    gifter = streamer["latest_sub_gifter"] or "---"
    tw, _ = screen.measure_text(gifter)
    screen.text(gifter, (WIDTH - tw) // 2, y + 20)

    draw_footer()


def build_pages():
    """Build the page list dynamically based on badge_config flags."""
    global pages
    pages = [draw_page_stats]

    if badge_config.get("show_latest_follower", True):
        pages.append(draw_page_latest_follower)

    if badge_config.get("show_latest_sub", True):
        pages.append(draw_page_latest_subscriber)

    if badge_config.get("show_latest_cheer", True):
        pages.append(draw_page_latest_cheer)

    if badge_config.get("show_latest_gifted_sub", True):
        pages.append(draw_page_latest_gifted_sub)


def load_cache():
    """Load cached Twitch data from file if available."""
    try:
        with open(CACHE_FILE, "r") as f:
            data = json.load(f)

        # Load streamer data from cache
        streamer["display_name"] = data.get("display_name", "---")
        streamer["broadcaster_type"] = data.get("broadcaster_type", "")
        streamer["follower_count"] = data.get("follower_count", 0)
        streamer["subscriber_count"] = data.get("subscriber_count", 0)
        streamer["latest_follower"] = data.get("latest_follower", "---")
        streamer["latest_subscriber"] = data.get("latest_subscriber", "---")
        streamer["latest_subscriber_months"] = data.get("latest_subscriber_months", 0)
        streamer["last_cheerer"] = data.get("last_cheerer", "---")
        streamer["last_cheer_amount"] = data.get("last_cheer_amount", 0)
        streamer["latest_sub_gifter"] = data.get("latest_sub_gifter", "---")
        streamer["latest_sub_gift_count"] = data.get("latest_sub_gift_count", 0)
        streamer["is_live"] = data.get("is_live", False)

        # Load badge_config from cache
        cfg = data.get("badge_config", {})
        if cfg:
            badge_config["show_latest_follower"] = cfg.get("show_latest_follower", True)
            badge_config["show_latest_sub"] = cfg.get("show_latest_sub", True)
            badge_config["show_latest_cheer"] = cfg.get("show_latest_cheer", True)
            badge_config["show_latest_gifted_sub"] = cfg.get("show_latest_gifted_sub", True)
            badge_config["auto_scroll"] = cfg.get("auto_scroll", 0)

        build_pages()
        print("Loaded cached Twitch data")
        return True
    except (AttributeError, OSError, ValueError) as e:
        print(f"No cache available: {e}")
        return False


def save_cache(data):
    """Save Twitch data to cache file."""
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(data, f)
        print("Saved Twitch data to cache")
    except OSError as e:
        print(f"Failed to save cache: {e}")


def clear_cache():
    """Remove cached data to force fresh fetch."""
    try:
        if CACHE_FILE in os.listdir("/"):
            os.remove(CACHE_FILE)
            print("Cleared cache")
    except OSError as e:
        print(f"Failed to clear cache: {e}")


def fetch_data():
    """Connect to WiFi and fetch streamer data from the API."""
    try:
        # Ensure WiFi is disconnected first for fresh connection
        try:
            wifi.disconnect()
        except OSError:
            pass

        show_message("Connecting to WiFi...")

        # Wait for connection (connect() polls and returns True once connected)
        while not wifi.connect():
            pass

        show_message("Fetching Twitch data...")
        r = urequests.get(API_URL)
        j = r.json()
        r.close()

        streamer["display_name"] = j.get("display_name", "---")
        streamer["broadcaster_type"] = j.get("broadcaster_type", "")
        streamer["follower_count"] = j.get("follower_count", 0)
        streamer["subscriber_count"] = j.get("subscriber_count", 0)
        streamer["latest_follower"] = j.get("latest_follower", "---")
        streamer["latest_subscriber"] = j.get("latest_subscriber", "---")
        streamer["latest_subscriber_months"] = j.get("latest_subscriber_months", 0)
        streamer["last_cheerer"] = j.get("last_cheerer", "---")
        streamer["last_cheer_amount"] = j.get("last_cheer_amount", 0)
        streamer["latest_sub_gifter"] = j.get("latest_sub_gifter", "---")
        streamer["latest_sub_gift_count"] = j.get("latest_sub_gift_count", 0)
        streamer["is_live"] = j.get("is_live", False)

        # Update badge_config from API response
        cfg = j.get("badge_config", {})
        if cfg:
            badge_config["show_latest_follower"] = cfg.get("show_latest_follower", True)
            badge_config["show_latest_sub"] = cfg.get("show_latest_sub", True)
            badge_config["show_latest_cheer"] = cfg.get("show_latest_cheer", True)
            badge_config["show_latest_gifted_sub"] = cfg.get("show_latest_gifted_sub", True)
            badge_config["auto_scroll"] = cfg.get("auto_scroll", 0)

        build_pages()

        # Save to cache for offline use
        save_cache(j)

        # Disconnect WiFi to save battery
        try:
            wifi.disconnect()
        except OSError:
            pass

        return True
    except (AttributeError, OSError, TypeError, ValueError) as e:
        print(f"Error fetching data: {e}")
        show_message(f"Error: {str(e)[:20]}")
        try:
            wifi.disconnect()
        except OSError:
            pass
        wait_for_button_or_alarm(timeout=3000)
        return False


auto_scroll_pending = False


def update():
    global current_page, data_fetched, auto_scroll_pending

    # Check for refresh command (hold A)
    # Use held() which checks current physical state without consuming press events
    if badge.held(BUTTON_A):
        print("Refresh triggered!")
        show_message("Refreshing...")
        clear_cache()
        # Immediately fetch fresh data (shows progress messages)
        if not fetch_data():
            # fetch_data() already shows error message
            data_fetched = False
            wait_for_button_or_alarm(timeout=2000)
            return
        data_fetched = True
        current_page = 0
        auto_scroll_pending = False

    # Try to load from cache on first run
    if not data_fetched:
        if load_cache():
            # Cache loaded successfully, can work offline
            data_fetched = True
        else:
            # No cache, need to fetch from API
            if not fetch_data():
                show_message("Error fetching data!")
                wait_for_button_or_alarm(timeout=5000)
                return
            data_fetched = True

    # Auto-scroll: advance page if woken by alarm (not a button press)
    if auto_scroll_pending:
        auto_scroll_pending = False
        if not badge.pressed(BUTTON_UP) and not badge.pressed(BUTTON_DOWN):
            current_page = (current_page + 1) % len(pages)

    # Page navigation with UP/DOWN (pressed = edge-triggered, won't conflict with held check)
    if badge.pressed(BUTTON_UP):
        current_page = max(0, current_page - 1)
    if badge.pressed(BUTTON_DOWN):
        current_page = min(len(pages) - 1, current_page + 1)

    # Draw the active page
    badge.mode(MEDIUM_UPDATE)
    pages[current_page]()
    badge.update()

    auto_scroll = badge_config.get("auto_scroll", 0)
    if auto_scroll >= 30 and len(pages) > 1:
        # Auto-scroll: wake after the configured interval to cycle pages
        auto_scroll_pending = True
        rtc.set_alarm(seconds=auto_scroll)
        # Keep polling long enough for the alarm to fire (avoids dormant sleep
        # which would cause a full hardware reset and lose page state)
        wait_for_button_or_alarm(timeout=(auto_scroll + 2) * 1000)
    else:
        # No auto-scroll: wake from sleep in 15 minutes to refresh data
        rtc.set_alarm(minutes=15)
        wait_for_button_or_alarm(timeout=5000)


def on_exit():
    rtc.clear_alarm()


run(update)
