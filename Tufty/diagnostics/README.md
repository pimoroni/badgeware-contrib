# Diagnostics

A Tufty-only diagnostics and hardware test app using the device's built-in
Badgeware APIs. It does not require the optional Multi Sensor Stick.

Created by Dave Hulbert.

## Features

The app has six pages:

1. **Overview**
   - Battery percentage and voltage
   - USB connection and charging state
   - Ambient light level
   - Uptime and frame time
2. **Power + Light**
   - Current battery and ambient-light readings
   - Rolling ambient-light graph sampled every 100 ms
3. **System**
   - MicroPython platform and release
   - Device UID and display resolution
   - Free and allocated RAM
   - `/system` flash usage
4. **Clock**
   - RTC date, time, and weekday
   - RTC alarm state
   - Wake source
   - Current ticks and frame delta
5. **Buttons**
   - Live held, pressed, released, and changed states
   - Per-button press counters
6. **Case Lights**
   - Current brightness of each rear LED
   - Interactive individual LED testing

## Controls

- **UP / DOWN:** move between pages
- **A / C on Case Lights:** select the previous or next rear LED
- **B on Case Lights:** cycle the selected LED through brightness levels
- **HOME:** return to the launcher

The original rear case-light values are captured when the app starts and
restored from `on_exit()` when leaving through the launcher.

## Implementation Notes

The app runs in Tufty's 160x120 `LORES` mode with `VSYNC` enabled. It uses
firmware-provided globals such as `badge`, `screen`, `rtc`, `shape`, `color`,
and button constants; these are injected by Badgeware and are not imported.

Potentially unavailable platform calls are wrapped by `safe_value()` so a
missing or failed metric displays a fallback rather than preventing the app
from launching. Host Python can syntax-check the file but cannot run it because
the Badgeware globals only exist on-device.

The ambient-light graph stores only the latest 55 samples in RAM. Diagnostics
are read-only except for the interactive case-light page.

## Limitations

- Temperature, humidity, pressure, and motion readings are not available
  without the optional Multi Sensor Stick.
- `woken_by_button()` and `woken_by_reset()` do not distinguish every possible
  wake source; the app displays unrecognized sources as `other`.
- RAM and flash readings may change while the app is running.
- `on_exit()` is not called after power loss, reset, or entering disk mode, so
  case-light restoration cannot be guaranteed in those situations.

## Testing

Run the host syntax check:

```sh
python3 -m py_compile apps/diagnostics/__init__.py
```

Then test on Tufty:

- Confirm the app appears in the launcher and opens successfully.
- Visit every page and check that values update.
- Cover and uncover the ambient-light sensor and confirm the graph responds.
- Press every front button and verify its states and counter.
- Test every rear case light at each brightness level.
- Exit with HOME and confirm the original case-light levels are restored.
