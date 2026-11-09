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

## What it does

- **Presentation mode:** next / previous slide, start the show (F5) or from the current
  slide (Shift+F5), end it (Esc), black screen, slide counter and timer.
- **Commands mode:** a menu of websites, programs, text snippets, keyboard shortcuts and
  small macros, read from `comandi.json`. Start from `comandi.example.json` (or
  `comandi.example.it.json` for an Italian keyboard); keys can be written in English
  (`groups`, `name`, `url`, `open`, `text`, `keys`, `steps`) or Italian. The format is
  documented at the top of `comandi.py`.
- **Language and keyboard** (third entry of the main menu, saved on the badge):
  - interface in **English** (default) or **Italian**;
  - the PC's keyboard layout: **US**, **UK** or **Italian**. Use the plain US layout on the
    PC, not US-International (its dead keys garble `' " ` ~ ^`).
- **Signed messages:** every message carries an HMAC-SHA256 signature with a key shared by
  badge and dongle, plus a per-connection nonce and a counter. The dongle ignores forged,
  replayed or incomplete messages.

### Adding a language

Copy `lang/en.json` to `lang/<code>.json`, translate the values (keep the keys and the `%s` /
`%d` placeholders) and set `"_name"` to the language's own name: it shows up in the menu by
itself, and missing keys fall back to English. The test that checks keys and placeholders,
and the tools for adding a keyboard layout, are in
[tufty2350-apps](https://github.com/carlopug/tufty2350-apps#adding-a-language).

## Setup

1. Build and flash the dongle, and generate the shared key, following
   [presentator_dongle/README.md](https://github.com/carlopug/tufty2350-apps/blob/main/presentator_dongle/README.md).
2. Copy this folder to `apps/presentator` on the badge, then add the generated
   `chiave.txt` (the key) to it. Without the key the app tells you it is missing.
3. Optional: copy `comandi.example.json` to `comandi.json` and add your own commands.
4. Plug the dongle into the PC and open the app: it connects by itself.
5. In **Language and keyboard**, pick the PC's keyboard layout (US by default).

Updating from the previous version needs no dongle reflash: languages and layouts live in
the badge app only.
