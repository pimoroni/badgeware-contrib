# Multi Badge

A name badge with any number of **profiles**, for example one for work, one for school and
one for a makerspace. Each profile has its own name, role, logo, fonts and colours. Flip the
badge to show your phone, email and a **vCard QR code** that people can scan to save your
contact.

![Multi Badge: front, back with vCard QR code, second profile](https://raw.githubusercontent.com/carlopug/tufty2350-apps/main/docs/images/badge.png)

It installs next to the firmware's own `badge` app and does not replace it.

## Buttons

| Button | Does |
|---|---|
| UP / DOWN | previous / next profile |
| B | flip the badge: phone, email and vCard QR code |
| A / C (hold) | decrease / increase the background colour saturation |

## Your profiles

The app works straight away with the example profiles in `badge.example.json`. To use your
own, copy it to `badge.json` in the same folder and edit the copy. The app reads
`badge.json` if it exists, otherwise the example.

- `config` holds the shared layout and transition settings.
- Each entry in `profiles` has `NAME`, `ROLE`, `PHONE`, `EMAIL`, `COMPANY`, `WEBSITE`,
  `LOGO`, plus font and colour settings.
- **Logos** are transparent PNGs in `assets/logos/`, scaled to fit 100×100 px. If a logo
  file is missing, `LOGO_LABEL` is shown as text instead (see `assets/logos/README.txt`).
- **Fonts** such as `MonaSans-Medium.af` come from the firmware (`/system/assets/fonts`).

The QR codes are generated on the badge with [uQR](https://github.com/JASchilz/uQR)
(BSD licence, see `uQR_LICENSE.txt`) and cached in `/cache/multi_badge`, so flipping is
instant after the first time.

## More

Part of [tufty2350-apps](https://github.com/carlopug/tufty2350-apps), together with a WiFi
manager and a BLE presentation remote. Issues and ideas are welcome there.
