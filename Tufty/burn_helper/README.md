# Burn Helper

Your Claude Code agents as a pixel game, and how much of your usage limit is left.

![Burn Helper on a Tufty 2350](https://raw.githubusercontent.com/pureyang/burn-helper/main/docs/img/device_hero.png) ![Desktop mode](https://raw.githubusercontent.com/pureyang/burn-helper/main/docs/img/device_desktop.png)

The character sleeps, walks, runs or sprints with the number of agents working, over 15 levels
up to hyperspace past 100, and acts out what they do: an edit, a command, a web lookup, a
subagent. Ten hearts show what's left of the 5-hour limit, a bar shows the weekly limit, and a
countdown runs to the reset. When a session is waiting for you, the character calls for you.
If you use more than one Claude account, each of the others gets its own row of hearts.

## It needs the bridge

The badge gets its data from a small bridge on a Mac or Windows PC, which reads Claude Code's
sessions, hooks and status line. Install it from
[github.com/pureyang/burn-helper](https://github.com/pureyang/burn-helper): one line, and it
can copy this app to the badge for you. The badge finds the bridge on your Wi-Fi by itself, or
gets the same data over the USB cable. No Claude API key goes on the badge.

**Plug the badge into the bridge's computer once.** That's how it gets the bridge's key, and it
shows "BRIDGE KEY SAVED" when it has it. Until then it can't read the bridge over Wi-Fi, and
shows "PLUG INTO BRIDGE FOR KEY".

The bridge encrypts and signs what it exchanges with other devices over the network, using that
key, and there's no setting to turn this off. The key itself never goes over the network. Someone
on the same Wi-Fi can still see that a bridge is there and when traffic flows, but not your
session names, folders or usage. Someone holding the badge can read the key from its storage.
More in the [privacy notes](https://github.com/pureyang/burn-helper/blob/main/bridge/README.md#privacy).

Without a bridge, hold **UP** for 2 seconds to play the demo.

## Installing from this folder

Copy the `burn_helper` folder into `apps` on the badge and keep its name: the app looks for its
files in `/system/apps/burn_helper`. It joins the Wi-Fi in `secrets.py`, like the other apps, or
hold **B** for 2 seconds to add a network from your phone.

## Buttons

| Button | What it does |
|---|---|
| A / C | Previous / next theme. In Desktop mode: step through the sessions waiting for you |
| B | Animation, then Desktop mode, then Debug mode. Hold 2 s for phone setup |
| Hold UP 2 s | Demo mode |
| DOWN | Brightness. Hold 2 s to switch the case LEDs on or off |
| HOME | Back to the launcher |

Settings, logs and the bridge's key are kept in `/state/burn_helper*`.

This folder is a copy of `badge/apps/burn_helper` from the main repo, where it's developed.
Issues and questions: [github.com/pureyang/burn-helper](https://github.com/pureyang/burn-helper/issues).

The three themes are homages to Zelda, *The Running Man* and Forrest Gump; those names and
characters belong to their owners.
