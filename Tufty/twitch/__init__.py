# Your app's directory
APP_DIR = "/system/apps/twitch"

import sys
import os

# Standalone bootstrap for finding app assets
os.chdir(APP_DIR)

# Standalone bootstrap for module imports
sys.path.insert(0, APP_DIR)

import random
import math
import network
from urllib.urequest import urlopen
import gc
import json

# URL encoding helper
def url_quote(s):
    """Simple URL encoding for special characters."""
    result = ""
    safe = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~"
    for c in s:
        if c in safe:
            result += c
        else:
            result += "%{:02X}".format(ord(c))
    return result

# Twitch purple color scheme
twitch_purple = color.rgb(145, 70, 255)  # Main Twitch purple
twitch_purple_dark = color.rgb(100, 65, 165)  # Darker purple
twitch_purple_light = color.rgb(169, 112, 255, 150)  # Light purple accent
white = color.rgb(255, 255, 255)
faded = color.rgb(255, 255, 255, 100)
black = color.rgb(24, 24, 27)  # Twitch dark background

small_font = font.ark
large_font = font.absolute

WIFI_TIMEOUT = 60

# Badge API endpoint (unified Twitch data)
BADGE_API_URL = "https://badge.pausedbypaul.net/api/streamer/{uuid}"
AVATAR_PROXY = "https://wsrv.nl/?url={avatar_url}&w=55&output=png"

# View modes
VIEW_AVATAR_FOLLOWERS = 0
VIEW_FOLLOWERS_LATEST = 1
VIEW_LAST_SUB = 2
VIEW_LAST_GIFT = 3
VIEW_LAST_CHEER = 4

WIFI_PASSWORD = None
WIFI_SSID = None
TWITCH_UUID = None

wlan = None
connected = False
ticks_start = None
current_view = 0
last_view_change = 0
auth_error = False
wifi_was_used = False  # Track if we used WiFi this session (for disconnect)


def message(text):
    print(text)


def clear_cached_data():
    """Remove cached Twitch data files to force fresh fetch."""
    # New unified API cache
    files_to_remove = ["/twitch_data.json", "/twitch_avatar.png"]
    # Old separate cache files (for cleanup)
    files_to_remove.extend(["/twitch_user.json", "/twitch_followers.json", "/twitch_subs.json"])
    for f in files_to_remove:
        try:
            if file_exists(f):
                os.remove(f)
                message(f"Removed cached file: {f}")
        except OSError as e:
            message(f"Failed to remove {f}: {e}")


def get_connection_details():
    global WIFI_PASSWORD, WIFI_SSID, TWITCH_UUID

    if WIFI_SSID is not None and TWITCH_UUID is not None:
        return True

    try:
        sys.path.insert(0, "/")
        try:
            from secrets import WIFI_PASSWORD, WIFI_SSID, TWITCH_UUID
        finally:
            try:
                sys.path.pop(0)
            except IndexError:
                pass
    except (ImportError, SyntaxError):
        WIFI_PASSWORD = None
        WIFI_SSID = None
        TWITCH_UUID = None

    if not WIFI_SSID:
        return False

    if not TWITCH_UUID:
        return False

    return True


def wlan_start():
    global wlan, ticks_start, connected

    if ticks_start is None:
        ticks_start = badge.ticks

    if connected:
        return True

    if wlan is None:
        wlan = network.WLAN(network.STA_IF)

    # Make sure WiFi is active
    if not wlan.active():
        wlan.active(True)

    # Already connected?
    if wlan.isconnected():
        connected = True
        return True

    # Need to connect - only call connect() once per attempt
    if ticks_start == badge.ticks:  # First frame of this connection attempt
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        print("Connecting to WiFi...")

    connected = wlan.isconnected()

    if badge.ticks - ticks_start < WIFI_TIMEOUT * 1000:
        if connected:
            print("WiFi connected!")
            return True
    elif not connected:
        return False

    return True


def wlan_disconnect():
    """Disconnect WiFi to save battery."""
    global wlan, ticks_start

    if wlan is not None:
        try:
            wlan.disconnect()
            wlan.active(False)
            message("WiFi disconnected to save battery")
        except OSError as e:
            message(f"WiFi disconnect error: {e}")
        finally:
            # Don't reset connected - that tracks whether we have data, not WiFi state
            ticks_start = None


def async_fetch_to_disk(url, file, force_update=False, timeout_ms=25000, headers=None):
    """
    Fetch a URL to disk as a generator, yielding between chunks so callers
    can interleave UI updates.
    """
    if not force_update and file_exists(file):
        return

    start_ticks = badge.ticks
    try:
        if headers is None:
            headers = {}
        headers["User-Agent"] = "twitch-badge-app/1.0"

        response = urlopen(url, headers=headers)
        data = bytearray(512)
        total = 0
        with open(file, "wb") as f:
            while True:
                if timeout_ms is not None and (badge.ticks - start_ticks) > timeout_ms:
                    raise OSError(f"Fetch timed out after {timeout_ms} ms")

                if (length := response.readinto(data)) == 0:
                    break
                total += length
                message(f"Fetched {total} bytes")
                f.write(data[:length])
                yield
        del data
        del response
    except OSError as e:
        # OSError includes HTTP errors - check for 401
        error_str = str(e)
        try:
            if file_exists(file):
                os.remove(file)
        except OSError:
            pass
        # Re-raise with preserved error info
        if "401" in error_str or "Unauthorized" in error_str:
            raise RuntimeError("401_UNAUTHORIZED") from e
        raise RuntimeError(f"Fetch from {url} to {file} failed. {e}") from e
    except Exception as e:
        try:
            if file_exists(file):
                os.remove(file)
        except OSError:
            pass
        raise RuntimeError(f"Fetch from {url} to {file} failed. {e}") from e


def get_api_headers():
    """Return headers for badge API requests."""
    return {
        "User-Agent": "twitch-badge-app/1.0"
    }


def get_streamer_data(user, force_update=False):
    """Fetch all streamer data from unified badge API."""
    global auth_error
    message("Getting Twitch data from badge API...")
    try:
        headers = get_api_headers()
        yield from async_fetch_to_disk(
            BADGE_API_URL.format(uuid=TWITCH_UUID),
            "/twitch_data.json",
            force_update,
            timeout_ms=25000,
            headers=headers
        )
    except RuntimeError as e:
        error_msg = str(e)
        if "401_UNAUTHORIZED" in error_msg:
            message("Auth error - invalid UUID")
            auth_error = True
            user.display_name = "Auth Error"
            user.user_id = None
            return
        else:
            message(f"Failed to fetch data: {e}")
            user.display_name = "Fetch Error"
            user.user_id = None
            return

    try:
        with open("/twitch_data.json", "r") as f:
            content = f.read()
            message(f"API JSON: {content[:200]}")
            data = json.loads(content)

        # Check for API error response
        if "error" in data:
            message(f"API Error: {data.get('message', 'Unknown error')}")
            user.display_name = "API Error"
            user.user_id = None
            return

        # Parse unified API response
        user.username = data.get("handle")
        user.display_name = data.get("display_name", user.username)
        user.user_id = data.get("user_id")
        user.avatar_url = data.get("profile_image_url", "")
        user.broadcaster_type = data.get("broadcaster_type", "")
        user.total_followers = data.get("follower_count", 0)
        user.latest_follower = data.get("latest_follower", "No followers")
        user.total_subs = data.get("subscriber_count", 0)
        user.latest_sub = data.get("latest_subscriber", "No subs")
        user.latest_subscriber_months = data.get("latest_subscriber_months", 0)
        user.latest_gifter = data.get("latest_sub_gifter")
        user.latest_gift_count = data.get("latest_sub_gift_count")
        user.latest_cheerer = data.get("last_cheerer")
        user.latest_cheer_amount = data.get("last_cheer_amount")
        user.is_live = data.get("is_live", False)

        # Parse badge config settings
        badge_config = data.get("badge_config", {})
        user.auto_scroll = badge_config.get("auto_scroll", 30)  # seconds, 0 = disabled
        user.show_latest_sub = badge_config.get("show_latest_sub", True)
        user.show_latest_follower = badge_config.get("show_latest_follower", True)
        user.show_latest_gifted_sub = badge_config.get("show_latest_gifted_sub", True)
        user.show_latest_cheer = badge_config.get("show_latest_cheer", True)

        message(f"Got user: {user.display_name}, followers: {user.total_followers}, subs: {user.total_subs}")
        message(f"Broadcaster type: {user.broadcaster_type}, avatar: {user.avatar_url[:50] if user.avatar_url else 'None'}")
        message(f"Badge config - auto_scroll: {user.auto_scroll}, show_follower: {user.show_latest_follower}, show_sub: {user.show_latest_sub}")

        del data
        gc.collect()
    except (AttributeError, OSError, TypeError, ValueError) as e:
        message(f"Failed to parse API data: {e}")
        user.display_name = "Parse Error"
        user.user_id = None


def get_avatar(user, force_update=False):
    if not user.avatar_url:
        message("No avatar URL available")
        user.avatar = False
        return

    message(f"Getting avatar for {user.display_name}...")
    avatar_path = "/twitch_avatar.png"
    try:
        # Use proxy to resize and convert avatar - URL encode the avatar URL
        encoded_url = url_quote(user.avatar_url)
        proxy_url = AVATAR_PROXY.format(avatar_url=encoded_url)
        message(f"Avatar proxy URL: {proxy_url[:80]}...")
        yield from async_fetch_to_disk(proxy_url, avatar_path, force_update, timeout_ms=25000, headers=None)

        if file_exists(avatar_path):
            user.avatar = image.load(avatar_path)
        else:
            message("Avatar file not found after download")
            user.avatar = False
    except (MemoryError, OSError, RuntimeError, TypeError, ValueError) as e:
        message(f"Failed to get avatar: {e}")
        user.avatar = False


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


def fake_number():
    return random.randint(100, 9999)


def fake_username():
    """Generate a random fake username for loading states."""
    prefixes = ["Cool", "Epic", "Pro", "Super", "Mega", "Ultra", "Twitch", "Stream", "Game", "Elite", "Ninja", "Gamer"]
    suffixes = ["Player", "Gamer", "King", "Queen", "Master", "Legend", "Pro", "Hero", "Wizard", "Ninja", "Boss", "Star"]
    numbers = ["", "42", "69", "420", "123", "999", "2000", "XD"]

    # Use ticks for randomness
    seed_val = (badge.ticks // 500) % 1000  # Changes every 500ms
    prefix = prefixes[seed_val % len(prefixes)]
    suffix = suffixes[(seed_val * 7) % len(suffixes)]
    number = numbers[(seed_val * 13) % len(numbers)]

    return prefix + suffix + number


def scroll_text(text, max_width, y_pos, center_x=80):
    """Draw text that scrolls horizontally if too long.

    Args:
        text: The text to display
        max_width: Maximum width before scrolling (in pixels)
        y_pos: Y position to draw text
        center_x: Center X position (default 80 for screen center)
    """
    text_width, _ = screen.measure_text(text)

    if text_width <= max_width:
        # Text fits, center it normally
        screen.text(text, center_x - (text_width / 2), y_pos)
    else:
        # Text is too long, scroll it
        # Calculate scroll parameters
        overflow = text_width - max_width
        cycle_time = 3000  # Total time for one left-right-left cycle (ms)
        scroll_speed = (overflow * 2) / cycle_time  # pixels per ms

        # Calculate current position in cycle
        cycle_pos = badge.ticks % cycle_time

        if cycle_pos < cycle_time / 2:
            # Scrolling left (showing right side of text)
            scroll_offset = -(cycle_pos * scroll_speed)
        else:
            # Scrolling right (back to start)
            scroll_offset = -(overflow - ((cycle_pos - cycle_time / 2) * scroll_speed))

        # Draw text with scroll offset
        x_pos = center_x - (max_width / 2) + scroll_offset
        screen.text(text, x_pos, y_pos)


class TwitchUser:
    def __init__(self):
        self.username = None
        self.display_name = None
        self.user_id = None
        self.avatar_url = None
        self.avatar = None
        self.broadcaster_type = None
        self.total_followers = None
        self.latest_follower = None
        self.total_subs = None
        self.latest_sub = None
        self.latest_subscriber_months = 0
        self.latest_gifter = None
        self.latest_gift_count = None
        self.latest_cheerer = None
        self.latest_cheer_amount = None
        self.is_live = False
        # Badge config settings
        self.auto_scroll = 30  # seconds between auto-scrolls, 0 = disabled
        self.show_latest_sub = True
        self.show_latest_follower = True
        self.show_latest_gifted_sub = True
        self.show_latest_cheer = True
        self._task = None
        self._force_update = False

    def is_affiliate_or_partner(self):
        """Check if user is affiliate or partner (can have subscribers)."""
        return self.broadcaster_type in ["affiliate", "partner"]

    def get_enabled_views(self):
        """Get list of enabled view indices based on config."""
        views = [VIEW_AVATAR_FOLLOWERS]  # Always show avatar/stats view

        # Add latest follower view if enabled
        if self.show_latest_follower:
            views.append(VIEW_FOLLOWERS_LATEST)

        # Add latest sub view if enabled and user is affiliate/partner
        if self.show_latest_sub and self.is_affiliate_or_partner():
            views.append(VIEW_LAST_SUB)

        # Add gifted sub view if enabled and user is affiliate/partner
        if self.show_latest_gifted_sub and self.is_affiliate_or_partner():
            views.append(VIEW_LAST_GIFT)

        # Add cheer view if enabled and user is affiliate/partner
        if self.show_latest_cheer and self.is_affiliate_or_partner():
            views.append(VIEW_LAST_CHEER)

        return views

    def update(self, force_update=False):
        global auth_error, ticks_start
        self.display_name = None
        self.user_id = None
        self.avatar_url = None
        self.avatar = None
        self.broadcaster_type = None
        self.total_followers = None
        self.latest_follower = None
        self.total_subs = None
        self.latest_sub = None
        self.latest_subscriber_months = 0
        self.latest_gifter = None
        self.latest_gift_count = None
        self.latest_cheerer = None
        self.latest_cheer_amount = None
        self.is_live = False
        self.auto_scroll = 30  # seconds between auto-scrolls, 0 = disabled
        self.show_latest_sub = True
        self.show_latest_follower = True
        self.show_latest_gifted_sub = True
        self.show_latest_cheer = True
        self._task = None
        self._force_update = force_update
        auth_error = False  # Reset auth error on retry
        ticks_start = None  # Reset WiFi connection timer
        if force_update:
            clear_cached_data()

    def is_data_ready(self):
        """Check if essential data has been fetched."""
        # Avatar can fail to load, so don't block on it
        # Only check subs if affiliate/partner
        base_ready = (self.user_id is not None and
                      self.total_followers is not None and
                      self.broadcaster_type is not None)

        if self.is_affiliate_or_partner():
            return base_ready and self.total_subs is not None
        return base_ready

    def draw_stat(self, title, value, x, y):
        screen.pen = white if value is not None else faded
        screen.font = large_font
        display_value = format_number(value) if value is not None else str(fake_number())
        screen.text(display_value, x, y)
        screen.font = small_font
        screen.pen = twitch_purple_light
        screen.text(title, x - 1, y + 13)

    def draw_stat_centered(self, title, value, y):
        """Draw a stat centered on screen."""
        screen.font = large_font
        screen.pen = white if value is not None else faded
        display_value = format_number(value) if value is not None else str(fake_number())
        w, _ = screen.measure_text(display_value)
        screen.text(display_value, 80 - (w / 2), y)
        screen.font = small_font
        screen.pen = twitch_purple_light
        w, _ = screen.measure_text(title)
        screen.text(title, 80 - (w / 2), y + 14)

    def draw_header(self, handle):
        """Draw the username header with broadcaster status."""
        # Draw display name at top
        screen.font = large_font
        w, _ = screen.measure_text(handle)
        screen.pen = white
        screen.text(handle, 80 - (w / 2), 4)

        # Draw broadcaster status below username
        screen.font = small_font
        screen.pen = twitch_purple_light
        if self.broadcaster_type:
            if self.broadcaster_type == "partner":
                status = "Twitch Partner"
            elif self.broadcaster_type == "affiliate":
                status = "Twitch Affiliate"
            else:
                status = "Streamer"
        else:
            status = ""

        if status:
            w, _ = screen.measure_text(status)
            screen.text(status, 80 - (w / 2), 18)

    def draw(self, connected):
        global current_view, last_view_change

        # Draw animated purple gradient background
        if badge.battery_level() > 20 or badge.is_charging():
            draw_twitch_background()
        else:
            # Dark base
            screen.pen = black
            screen.shape(shape.rectangle(0, 0, screen.width, screen.height))

        screen.font = small_font

        # Draw battery status at top-right
        if badge.is_charging():
            battery_level = (badge.ticks / 20) % 100
        else:
            battery_level = badge.battery_level()
        pos = (137, 4)
        size = (16, 8)
        screen.pen = twitch_purple_dark
        screen.shape(shape.rectangle(*pos, *size))
        screen.shape(shape.rectangle(pos[0] + size[0], pos[1] + 2, 1, 4))
        screen.pen = black
        screen.shape(shape.rectangle(pos[0] + 1, pos[1] + 1, size[0] - 2, size[1] - 2))

        # draw the battery fill level
        width = ((size[0] - 4) / 100) * battery_level
        screen.pen = twitch_purple
        screen.shape(shape.rectangle(pos[0] + 2, pos[1] + 2, width, size[1] - 4))

        # Draw LIVE indicator if streaming (below battery in red)
        if self.is_live:
            screen.font = small_font
            screen.pen = color.rgb(255, 0, 0)  # Red color
            live_text = "LIVE"
            live_w, _ = screen.measure_text(live_text)
            # Center under battery (battery center x = pos[0] + size[0]/2)
            live_x = pos[0] + (size[0] / 2) - (live_w / 2)
            screen.text(live_text, live_x, pos[1] + size[1] + 3)

        # Draw username/handle area with loading status
        handle = self.display_name or self.username

        # Check if WiFi is actually connected for fetching
        # connected parameter means "we have some cached data to display"
        # but we need actual WiFi to fetch missing data
        wifi_connected = wlan is not None and wlan.isconnected()

        # Use the handle area to show loading progress if not everything is ready
        # avatar can be None (not fetched), False (fetch failed), or an Image object
        # Check if ANY data is missing AND WiFi is actually connected
        if ((self.display_name is None or self.total_followers is None) or
            (self.avatar is None or self.avatar is False)) and wifi_connected:
            if not self.display_name or self.total_followers is None:
                handle = "fetching data..."
                if not self._task:
                    self._task = get_streamer_data(self, self._force_update)
            elif self.avatar is None or self.avatar is False:
                handle = "fetching avatar..."
                if not self._task:
                    self._task = get_avatar(self, self._force_update)

            try:
                next(self._task)
            except StopIteration:
                self._task = None
            except (AttributeError, MemoryError, OSError, RuntimeError, TypeError, ValueError):
                self._task = None
                handle = "fetch error"

        if not wifi_connected and not connected:
            handle = "connecting..."

        # Draw header with current handle/status
        self.draw_header(handle if handle else self.username)

        # Handle view rotation and manual navigation
        if last_view_change == 0:
            last_view_change = badge.ticks

        # Get enabled views based on config
        enabled_views = self.get_enabled_views()
        num_views = len(enabled_views)

        # Manual navigation with buttons UP and DOWN (only when we have display data)
        # Don't require avatar since it can fail to load
        if self.display_name and self.total_followers is not None and num_views > 0:
            if badge.pressed(BUTTON_UP):
                # Find current index in enabled views and go to previous
                try:
                    current_idx = enabled_views.index(current_view)
                    current_view = enabled_views[(current_idx - 1) % num_views]
                except ValueError:
                    current_view = enabled_views[0]
                last_view_change = badge.ticks
            elif badge.pressed(BUTTON_DOWN):
                # Find current index in enabled views and go to next
                try:
                    current_idx = enabled_views.index(current_view)
                    current_view = enabled_views[(current_idx + 1) % num_views]
                except ValueError:
                    current_view = enabled_views[0]
                last_view_change = badge.ticks
            elif self.auto_scroll > 0 and (badge.ticks - last_view_change) > (self.auto_scroll * 1000):
                # Auto-scroll if enabled (auto_scroll > 0 is seconds between scrolls)
                try:
                    current_idx = enabled_views.index(current_view)
                    current_view = enabled_views[(current_idx + 1) % num_views]
                except ValueError:
                    current_view = enabled_views[0]
                last_view_change = badge.ticks

        # Draw the current view content
        if current_view == VIEW_AVATAR_FOLLOWERS:
            # Draw avatar on left (scaled down to 55x55)
            if self.avatar and not isinstance(self.avatar, bool):
                try:
                    screen.blit(self.avatar, vec2(5, 37))
                except (TypeError, ValueError):
                    draw_default_avatar()
            else:
                draw_default_avatar()
            # Draw follower count and subscriber count (if affiliate/partner)
            if self.is_affiliate_or_partner():
                self.draw_stat("followers", self.total_followers, 70, 40)
                self.draw_stat("subscribers", self.total_subs, 70, 75)
            else:
                # Center followers stat when no subs
                self.draw_stat("followers", self.total_followers, 70, 57)
        elif current_view == VIEW_FOLLOWERS_LATEST:
            self.draw_stat_centered("followers", self.total_followers, 35)
            screen.font = small_font
            screen.pen = twitch_purple_light
            label = "latest follower"
            w, _ = screen.measure_text(label)
            screen.text(label, 80 - (w / 2), 70)
            screen.font = large_font
            # None = loading (show fake), string = actual data (even if "No followers")
            if self.latest_follower is None:
                screen.pen = faded
                follower_name = fake_username()
            else:
                screen.pen = white
                follower_name = self.latest_follower
            scroll_text(follower_name, 140, 85)
        elif current_view == VIEW_LAST_SUB:
            self.draw_stat_centered("subscribers", self.total_subs, 35)
            screen.font = small_font
            screen.pen = twitch_purple_light
            label = "latest subscriber"
            w, _ = screen.measure_text(label)
            screen.text(label, 80 - (w / 2), 70)
            screen.font = large_font
            # None = loading (show fake), string = actual data (even if "No subs")
            if self.latest_sub is None:
                screen.pen = faded
                sub_name = fake_username()
            else:
                screen.pen = white
                sub_name = self.latest_sub
                if self.latest_subscriber_months and self.latest_subscriber_months > 1:
                    sub_name = sub_name + " x" + str(self.latest_subscriber_months)
            scroll_text(sub_name, 140, 85)
        elif current_view == VIEW_LAST_GIFT:
            # Gifted subs view
            # Check if we're loading (display_name is None) or have actual data
            if self.display_name is None:
                # Still loading - show fake data
                screen.font = small_font
                screen.pen = twitch_purple_light
                label = "gifted subs"
                w, _ = screen.measure_text(label)
                screen.text(label, 80 - (w / 2), 35)

                screen.font = large_font
                screen.pen = faded
                gift_count = format_number(fake_number())
                w, _ = screen.measure_text(gift_count)
                screen.text(gift_count, 80 - (w / 2), 50)

                screen.font = small_font
                screen.pen = twitch_purple_light
                gifter_label = "from"
                w, _ = screen.measure_text(gifter_label)
                screen.text(gifter_label, 80 - (w / 2), 70)

                screen.font = large_font
                screen.pen = faded
                gifter_name = fake_username()
                scroll_text(gifter_name, 140, 85)
            elif self.latest_gifter is not None and self.latest_gift_count is not None:
                # Have actual gift data from API (even if count is 0)
                screen.font = small_font
                screen.pen = twitch_purple_light
                label = "gifted subs"
                w, _ = screen.measure_text(label)
                screen.text(label, 80 - (w / 2), 35)

                screen.font = large_font
                screen.pen = white
                gift_count = format_number(self.latest_gift_count)
                w, _ = screen.measure_text(gift_count)
                screen.text(gift_count, 80 - (w / 2), 50)

                screen.font = small_font
                screen.pen = twitch_purple_light
                gifter_label = "from"
                w, _ = screen.measure_text(gifter_label)
                screen.text(gifter_label, 80 - (w / 2), 70)

                screen.font = large_font
                screen.pen = white
                gifter_name = self.latest_gifter
                scroll_text(gifter_name, 140, 85)
            else:
                # Data loaded but no gifts (API returned null)
                screen.font = large_font
                screen.pen = white
                no_data = "No Data"
                w, _ = screen.measure_text(no_data)
                screen.text(no_data, 80 - (w / 2), 50)
                screen.font = small_font
                screen.pen = twitch_purple_light
                label = "gifted subs"
                w, _ = screen.measure_text(label)
                screen.text(label, 80 - (w / 2), 70)
        elif current_view == VIEW_LAST_CHEER:
            # Latest cheer view
            # Check if we're loading (display_name is None) or have actual data
            if self.display_name is None:
                # Still loading - show fake data
                screen.font = small_font
                screen.pen = twitch_purple_light
                label = "latest cheer"
                w, _ = screen.measure_text(label)
                screen.text(label, 80 - (w / 2), 35)

                screen.font = large_font
                screen.pen = faded
                cheer_amount = format_number(fake_number()) + " bits"
                w, _ = screen.measure_text(cheer_amount)
                screen.text(cheer_amount, 80 - (w / 2), 50)

                screen.font = small_font
                screen.pen = twitch_purple_light
                cheerer_label = "from"
                w, _ = screen.measure_text(cheerer_label)
                screen.text(cheerer_label, 80 - (w / 2), 70)

                screen.font = large_font
                screen.pen = faded
                cheerer_name = fake_username()
                scroll_text(cheerer_name, 140, 85)
            elif self.latest_cheerer is not None and self.latest_cheer_amount is not None:
                # Have actual cheer data from API (even if amount is 0)
                screen.font = small_font
                screen.pen = twitch_purple_light
                label = "latest cheer"
                w, _ = screen.measure_text(label)
                screen.text(label, 80 - (w / 2), 35)

                screen.font = large_font
                screen.pen = white
                cheer_amount = format_number(self.latest_cheer_amount) + " bits"
                w, _ = screen.measure_text(cheer_amount)
                screen.text(cheer_amount, 80 - (w / 2), 50)

                screen.font = small_font
                screen.pen = twitch_purple_light
                cheerer_label = "from"
                w, _ = screen.measure_text(cheerer_label)
                screen.text(cheerer_label, 80 - (w / 2), 70)

                screen.font = large_font
                screen.pen = white
                cheerer_name = self.latest_cheerer
                scroll_text(cheerer_name, 140, 85)
            else:
                # Data loaded but no cheers (API returned null)
                screen.font = large_font
                screen.pen = white
                no_data = "No Data"
                w, _ = screen.measure_text(no_data)
                screen.text(no_data, 80 - (w / 2), 50)
                screen.font = small_font
                screen.pen = twitch_purple_light
                label = "latest cheer"
                w, _ = screen.measure_text(label)
                screen.text(label, 80 - (w / 2), 70)

        # Draw view indicator dots at bottom (only for enabled views)
        enabled_views = self.get_enabled_views()
        num_views = len(enabled_views)
        if num_views > 1:  # Only show dots if there are multiple views
            for i, view_id in enumerate(enabled_views):
                if view_id == current_view:
                    screen.pen = white
                else:
                    screen.pen = twitch_purple_dark
                # Center dots based on number of views
                if num_views == 2:
                    x_offset = 76
                elif num_views == 3:
                    x_offset = 72
                else:
                    x_offset = 80 - (num_views * 4)
                screen.shape(shape.circle(x_offset + i * 8, 115, 2))


def draw_twitch_background():
    """Draw animated Twitch-themed purple background."""
    # Dark base
    screen.pen = black
    screen.shape(shape.rectangle(0, 0, screen.width, screen.height))

    # Animated purple glow circles in background
    screen.pen = color.rgb(100, 65, 165, 30)

    # Floating circles animation
    for i in range(3):
        offset = math.sin((badge.ticks / 3000) + i * 2) * 20
        x = 40 + i * 50 + offset
        y = 60 + math.cos((badge.ticks / 2500) + i) * 30
        radius = 25 + math.sin((badge.ticks / 2000) + i) * 10
        screen.shape(shape.circle(x, y, radius))


def draw_default_avatar():
    """Draw animated loading placeholder for avatar."""
    screen.pen = color.rgb(145, 70, 255, 50)
    # Draw animated circles as placeholder
    for i in range(4):
        angle = (badge.ticks / 40 + i * 90) % 360
        radius_offset = math.sin(badge.ticks / 1000) * 3
        radius = 10 + i * 3 + radius_offset
        x = 32 + math.cos(math.radians(angle)) * 15
        y = 62 + math.sin(math.radians(angle)) * 15
        screen.shape(shape.circle(x, y, radius))


user = TwitchUser()
# connected will be set by load_cached_data() based on what was actually loaded
connected = False

# Load connection details from secrets first
get_connection_details()


def load_cached_data():
    """Load cached data on app startup if available."""

    # Clean up old cache files from previous API structure
    old_files = ["/twitch_user.json", "/twitch_followers.json", "/twitch_subs.json"]
    for old_file in old_files:
        if file_exists(old_file):
            try:
                os.remove(old_file)
                message(f"Removed old cache file: {old_file}")
            except OSError as e:
                message(f"Failed to remove old cache: {e}")

    # Try to load unified API data
    if file_exists("/twitch_data.json"):
        try:
            with open("/twitch_data.json", "r") as f:
                data = json.loads(f.read())

            # Check for API error response
            if "error" not in data:
                # Parse unified API response
                user.username = data.get("handle")
                user.display_name = data.get("display_name", user.username)
                user.user_id = data.get("user_id")
                user.avatar_url = data.get("profile_image_url", "")
                user.broadcaster_type = data.get("broadcaster_type", "")
                user.total_followers = data.get("follower_count", 0)
                user.latest_follower = data.get("latest_follower", "No followers")
                user.total_subs = data.get("subscriber_count", 0)
                user.latest_sub = data.get("latest_subscriber", "No subs")
                user.latest_gifter = data.get("latest_sub_gifter")
                user.latest_gift_count = data.get("latest_sub_gift_count")
                user.latest_cheerer = data.get("last_cheerer")
                user.latest_cheer_amount = data.get("last_cheer_amount")
                user.is_live = data.get("is_live", False)

                # Parse badge config settings
                badge_config = data.get("badge_config", {})
                user.auto_scroll = badge_config.get("auto_scroll", 30)
                user.show_latest_sub = badge_config.get("show_latest_sub", True)
                user.show_latest_follower = badge_config.get("show_latest_follower", True)
                user.show_latest_gifted_sub = badge_config.get("show_latest_gifted_sub", True)
                user.show_latest_cheer = badge_config.get("show_latest_cheer", True)

                message("Loaded cached API data")
            else:
                message(f"Cached data has error: {data.get('message', 'Unknown')}")
        except (AttributeError, OSError, TypeError, ValueError) as e:
            message(f"Failed to load cached data: {e}")

    # Try to load avatar
    if file_exists("/twitch_avatar.png"):
        try:
            user.avatar = image.load("/twitch_avatar.png")
            message("Loaded cached avatar")
        except (MemoryError, OSError, RuntimeError, ValueError) as e:
            message(f"Failed to load cached avatar: {e}")
            user.avatar = False  # Mark as failed so it can be retried
    else:
        # No cache file - leave as None to trigger fetch
        message("No avatar cache - will fetch")

    # Set connected=True if we loaded essential data (user info and followers)
    # This allows instant display from cache without WiFi
    # Avatar is optional - can be fetched later if needed
    global connected
    if user.display_name is not None and user.total_followers is not None:
        connected = True
        message("Cache loaded - ready to display")
    else:
        message("Cache incomplete - will need to fetch")


# Load cached data on startup
load_cached_data()


def center_text(text, y):
    w, _ = screen.measure_text(text)
    screen.text(text, 80 - (w / 2), y)


def wrap_text(text, x, y):
    lines = text.splitlines()
    for line in lines:
        _, h = screen.measure_text(line)
        screen.text(line, x, y)
        y += h * 0.8


def no_secrets_error():
    """Show instructions when Twitch credentials are missing."""
    screen.pen = black
    screen.shape(shape.rectangle(0, 0, screen.width, screen.height))

    screen.font = large_font
    screen.pen = white
    center_text("Twitch Setup", 5)

    screen.text("1:", 10, 23)
    screen.text("2:", 10, 55)
    screen.text("3:", 10, 87)

    screen.pen = twitch_purple_light
    screen.font = small_font
    wrap_text("""Put your badge into\ndisk mode (tap\nRESET twice)""", 30, 24)

    wrap_text("""Edit 'secrets.py' and\nadd your TWITCH_UUID""", 30, 56)

    wrap_text("""Reload to see your\nTwitch stats!""", 30, 88)


def auth_error_screen():
    """Show authentication error message."""
    screen.pen = black
    screen.shape(shape.rectangle(0, 0, screen.width, screen.height))

    screen.font = large_font
    screen.pen = white
    center_text("Auth Error!", 5)

    screen.text("1:", 10, 50)

    screen.pen = twitch_purple_light
    screen.font = small_font
    wrap_text("""Invalid UUID (401)\n\n:-(""", 16, 20)

    wrap_text("""Check TWITCH_UUID in\n'secrets.py'""", 30, 51)


def connection_error():
    """Show connection failure message."""
    screen.pen = black
    screen.shape(shape.rectangle(0, 0, screen.width, screen.height))

    screen.font = large_font
    screen.pen = white
    center_text("Connection Failed!", 5)

    screen.text("1:", 10, 63)
    screen.text("2:", 10, 95)

    screen.pen = twitch_purple_light
    screen.font = small_font
    wrap_text("""Could not connect\nto the WiFi network.\n\n:-(""", 16, 20)

    wrap_text("""Check WiFi settings\nin 'secrets.py'""", 30, 65)

    wrap_text("""Reload to try again!""", 30, 96)


def update():
    global connected, wifi_was_used, wlan, ticks_start

    # Check for force refresh (hold A + C)
    if badge.held(BUTTON_A) and badge.held(BUTTON_C):
        connected = False
        wifi_was_used = False
        # Reactivate WiFi if it was turned off
        if wlan is not None and not wlan.active():
            wlan.active(True)
            message("WiFi reactivated for refresh")
        user.update(True)

    if not get_connection_details():
        no_secrets_error()
        return

    # If authentication failed, show auth error screen
    if auth_error:
        auth_error_screen()
        return

    # If we have cached data, display directly without touching WiFi
    # But if avatar is missing, we need to fetch it
    if connected:
        # Check if we need to fetch avatar (it's missing or failed)
        if (user.avatar is None or user.avatar is False):
            if wlan is None:
                wlan = network.WLAN(network.STA_IF)

            # Turn on WiFi and connect if needed
            if not wlan.active():
                wlan.active(True)
                message("Activating WiFi to fetch avatar...")

            if not wlan.isconnected():
                if ticks_start is None:
                    ticks_start = badge.ticks
                    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
                    message("Connecting to WiFi for avatar...")

                # Wait for connection (timeout after 60 seconds)
                if badge.ticks - ticks_start < WIFI_TIMEOUT * 1000:
                    if wlan.isconnected():
                        message("WiFi connected for avatar fetch!")
                        wifi_was_used = True
                        ticks_start = None

        user.draw(True)
        # Check if WiFi is still on and should be disconnected (after a refresh)
        if wlan is not None and wlan.active() and user.is_data_ready():
            # Also check that avatar is loaded (not None or False)
            if user.avatar is not None and user.avatar is not False:
                wlan_disconnect()
        return

    # Need fresh data - try to connect WiFi
    if wlan_start():
        # Track that we used WiFi
        if not wifi_was_used and wlan is not None and wlan.isconnected():
            wifi_was_used = True

        user.draw(connected)

        # Disconnect WiFi after all data is fetched to save battery
        if wifi_was_used and user.is_data_ready() and wlan is not None and wlan.active():
            wlan_disconnect()
            connected = True  # Mark as connected so we use cache path next frame
    else:
        connection_error()


run(update)
