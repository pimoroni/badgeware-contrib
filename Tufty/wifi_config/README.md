# WiFi Config

Manage the badge's WiFi networks **on the badge itself**: scan, pick a network, type the
password on an on-screen keyboard, and keep a list of known networks. No need to edit
`secrets.py` on a computer every time you change place.

![WiFi Config: connected menu, network scan, virtual keyboard](https://raw.githubusercontent.com/carlopug/tufty2350-apps/main/docs/images/wifi_config.png)

The on-screen texts are in Italian.

## What it does

- Tries your known networks in order (8 s each) and shows the one it connected to, with IP
  and signal strength.
- **Add a network:** the scan lists each network with signal bars, a star if it is already
  known and a padlock if it needs a password. Open networks connect at once; for the others
  a keyboard opens (with the saved password already typed in, if known).
- **Change**, **delete** or **re-import** networks from a menu.
- Keeps `/secrets.py` in sync with the last network that worked, so every other app keeps
  using plain `wifi.connect()` and just works.
- Uses `network.WLAN` directly, so repeated failed connections never reboot the badge.

## Setup

1. Copy this folder to `apps/wifi_config` on the badge (Disk Mode).
2. Optional: to start with more than one network, put a `multi_secrets.py` in the root of
   the drive:

   ```python
   NETWORKS = [
       {"ssid": "HomeNetwork", "password": "home-password"},
       {"ssid": "PhoneHotspot", "password": "hotspot-password"},
   ]
   ```

   The app imports it once into the badge's internal storage (`/multi_secrets.py`) and then
   tells you the copy on the drive can be deleted. Without it, the app starts from the
   network in your `secrets.py`, or lets you scan.

Passwords are stored in plain text on the badge, like the firmware's own `secrets.py`.

## More

Full details (files, volumes, every screen):
[docs/wifi-config.md](https://github.com/carlopug/tufty2350-apps/blob/main/docs/wifi-config.md)
in [tufty2350-apps](https://github.com/carlopug/tufty2350-apps).
