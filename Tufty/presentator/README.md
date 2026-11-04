# Presentator

Turn the Tufty 2350 into a **wireless presentation remote** and a pocket "macro keyboard"
for your PC.

![Presentator: main menu, presentation mode with timer, command list](https://raw.githubusercontent.com/carlopug/tufty2350-apps/main/docs/images/presentator.png)

```
Tufty 2350 (this app) --BLE--> ESP32-S3 dongle --USB HID keyboard--> PC
```

> **This app needs a small USB dongle** (an ESP32-S3 board with native USB, about the size
> of a thumb drive). The firmware, the key generator and a 3D-printable case are in
> [tufty2350-apps](https://github.com/carlopug/tufty2350-apps/tree/main/presentator_dongle).

**Why a dongle?** The stock firmware has no BLE pairing support, so the badge cannot act as a
Bluetooth keyboard. The dongle receives the badge's commands over BLE and types them as a
plain USB keyboard: nothing to install on the PC, and the badge keeps the official firmware.

The on-screen texts are in Italian.

## What it does

- **Presentation mode:** next / previous slide, start the show (F5) or from the current
  slide (Shift+F5), end it (Esc), black screen, slide counter and timer.
- **Commands mode:** a menu of websites, programs, text snippets, keyboard shortcuts and
  small macros, read from `comandi.json`. Start from `comandi.example.json`; the format is
  documented at the top of `comandi.py`.
- **Signed messages:** every message carries an HMAC-SHA256 signature with a key shared by
  badge and dongle, plus a per-connection nonce and a counter. The dongle ignores forged,
  replayed or incomplete messages.
- **Keyboard layout:** text is translated into key codes for an **Italian** layout
  (`_layout_italiano()` in `comandi.py`). For another layout, adapt that table.

## Setup

1. Build and flash the dongle, and generate the shared key, following
   [presentator_dongle/README.md](https://github.com/carlopug/tufty2350-apps/blob/main/presentator_dongle/README.md).
2. Copy this folder to `apps/presentator` on the badge, then add the generated
   `chiave.txt` (the key) to it. Without the key the app tells you it is missing.
3. Optional: copy `comandi.example.json` to `comandi.json` and add your own commands.
4. Plug the dongle into the PC and open the app: it connects by itself.
