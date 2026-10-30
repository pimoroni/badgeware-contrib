# Halloween for Tufty 1.1

A little Halloween app for my Tufty 2350. A glowing pumpkin, floating ghosts, and a BOO button. Every so often a ghost, a few bats, a spider, a laughing pumpkin, or a skull turns up on its own.

The rear LEDs stay off until a BOO happens. They light up for the scare, fade out, and go back to off.

## Install

This runs on the Tufty 2350's Badgeware MicroPython firmware.

1. Plug the Tufty into the computer with a USB data cable.
2. Double-tap RESET on the back. A drive called TUFTY should appear.
3. Copy the whole `halloween` folder into its `apps` folder.
4. Eject the drive, then press RESET once.
5. Select Halloween in the launcher and press B.

## Buttons

| Button | What it does |
| --- | --- |
| A | Next BOO: ghost → bats → spider → pumpkin → skull |
| B | Cycle through all eight sayings |
| C | Pause or resume the animation and random scares |
| Up / Down | Adjust the screen brightness |
| Home | Return to the launcher |

Random BOOs wait 45 seconds to 2½ minutes after the previous scare finishes. Automatic scares choose a random character and avoid the previous one. The A button always advances through its own fixed sequence, even if an automatic scare happens between presses. Each scare lasts about 2.4 seconds and animates directly in the scene, with no box around it. The pumpkin uses a seamless 30-frame loop with gentle rocking and a moving grin, without stretching its body. The scare sky has extra muted stars behind the characters. Pressing A starts one immediately and resets the wait. A still works when paused; an active scare finishes and the lights fade back to off.

The fence rail quietly shows the charge level, in the same muted plum as the scene. It darkens from right to left as charge drops.

## Sayings

- Here for the candy
- Just here to haunt
- Probably haunted
- Nothing weird here
- Still waiting on candy
- Don’t mind the ghost
- This seemed like a good idea
- The ghost lives here now

## License

MIT License. Copyright (c) 2026 [Chris Parrish](https://github.com/KK4TSS/). See [LICENSE](LICENSE).

More of my projects are on [GitHub](https://github.com/KK4TSS/).
