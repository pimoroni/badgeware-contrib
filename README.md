# Badgeware Contributions

This repo is the home for **extra** Badgeware apps - community contributions and a few of our own that didn't quite fit into the shipping firmware. If you're looking for inspiration or if you've built a cool app and want to share it with other badgeware users, you're in the right place!

If you're looking for the shipping firmware and examples, you can find them at the links below:

- [Badger 2350](https://github.com/pimoroni/badger2350)
- [Tufty 2350](https://github.com/pimoroni/tufty2350)
- [Blinky 2350](https://github.com/pimoroni/blinky2350)

If you want to learn more about Badgeware (or would like to buy a badge of your own) check out [badgewa.re](https://badgewa.re/)!

## How to download an app to your badge

1) Download this repo (either via `git clone https://github.com/pimoroni/badgeware-contrib` or by clicking the dropdown on the 'Code' button on the front page, and clicking 'Download ZIP')
2) Double press the 'RESET' button on your badge to put it into Disk Mode
3) Find the app you want in the downloaded repo
4) Copy the directory into the 'apps' directory on the BADGER/TUFTY/BLINKY drive.
5) Eject the badge from your computer once the files have finished copying
6) The new app should now be showing in the launcher.

## How to add a new app to this repo

1) Fork this repo
2) Create a new directory in your fork for your app
3) Add your app `__init__.py` to the directory. Don't forget to include a 24x24 icon for the launcher!
4) Submit a Pull Request back to this repo
5) Make more apps! 🎉
