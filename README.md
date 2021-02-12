# Zulip bot for OBS

## Installation

* Install `requirements.txt`.
* Your OBS must have the obs-websocket plugin installed for connection
* Edit the top of the obsbot.py file to set your necessary parameters.
  * Connection parameters to your OBS
  * The names of the sources to switch to/unswitch, and mute/unmute.
* This package itself does not need to be installed.
* The bot only responds to commands from users specified (by email)
  hardcoded in the config.


## Running it

```
zulip-run-bot obsbot.py --config-file=zuliprc
```

To run it in test mode (locally in terminal, no connection):
```
zulip-terminal obsbot.py
```

## Usage

There are various commands, which have to be sent either by private
message or mentioning the bot.

* `help`
* `switch` - list scenes
* `switch [scene-name]` - switch to that scene.  React with
  *check_mark* if successful.
* `[scene-name]` - Same as above.
* `mute` - Mute audio.  Reacts with *mute notifications* if successful.
* `unmute` - Unmute audio.  Reacts with *notifications* if successful.
* If a bot reacts with *boom*, this means that an exception occurred.


## Development and maintenance

This should be considered alpha - works but may need code knowledge to
use it.

Contact: Richard Darst
