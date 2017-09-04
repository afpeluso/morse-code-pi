# morse-code-pi
A Morse Code Key interpreter for Raspberry Pi 3 in Python with Twitter Integration

## Project Goals
My partner Julia has an old J-38 WWII Telegraphy Key (Transmitter). One of the last antiques she bought with her mother before her passing.

The goal of this project is to make that key transmit text to Twitter and make it a permanent fixture in our apartment.

## Setup

![J-38 Telegraph Key with Raspberry Pi Attached](./images/j38key-pi.jpg  "J-38 Telegraph Key with Raspberry Pi Attached")

### Telegraph Key

The J-38 telegraph key has two binding posts attached to its base on the opposite end from the key knob. In operation, it simply completes a circuit between these on a downward press of the knob.

### Controller

I had an old [Arduino Duemilanove](https://www.arduino.cc/en/Main/ArduinoBoardDuemilanove)  I was planning to use for this project, but decided to pick up a Raspberry Pi 3 instead, as a WiFi hat for the old Arduino seemed to cost just as much, if not more.

It feels like overkill to have a gigabyte of ram and such to run this, but who doesn't want an excuse to mess with a Raspberry Pi? Come on. :)

### Interface

I attached two leads from the J-38 telegraph key binding posts to Pins 1 (3.3.V) and 11 (GPIO17) on the GPIO header, using the internal pull-down resistor setting to steady the input.

This seems to make for a totally detectable input, with some thresholding in code to make up for a bit of bounciness.

## Running This Project

### Software Requirements
This project was initially made in Python 2.7.13 since that's what came default on the default Raspbian installation.

- Python 2.7.13
- PyYaml
- [pigpio](http://abyz.co.uk/rpi/pigpio/)
- [Tweepy](http://www.tweepy.org) (not required if Twitter disabled)
- Raspbian 9 (Probably not required, but it's what I'm running at the moment.)

PyYaml, pigpio and Tweepy are available through pip.

Originally used RPi.GPIO, but software PWM proved somewhat inconsistent. pigpio ended up being more stable.

### Physical Requirements

By default...

- Connect Morse Code key or other button to header Pins 1 and 11 (GPIO17).
- Connect LED to Pin 13 (GPIO27) (with appropriate resistor) and Ground.
- Connect Buzzer to Pin 15 (GPIO22) and Ground.

Pins, frequencies, timing, etc. are all adjustable in `config.yml`.

Note: For pigpio to work, pins must be referred to by their [Broadcom GPIO Numbers](http://elinux.org/RPi_Low-level_peripherals#General_Purpose_Input.2FOutput_.28GPIO.29) in this config file.

### Configuration
Raspberry Pi must be connected to Internet for Twitter Integration, but this is not required to interpret and practice Morse Code input.

#### config.yml
This file sets all of the pins, timing thresholds, etc. Does not need to be adjusted to function out-of-the-box.

If `TWITTER_ENABLED` is set to false, it won't try to load `twitter_config.yml`

#### twitter_config.yml
In order to enable Twitter integration, this file should be created by the user, and should contain the API Keys and Access Tokens. (You will need to set up an application on your Twitter account to get these keys.)

`twitter_config.example.yml` contains the template. Copy it to `twitter_config.yml` and replace the values appropriately.

The Morse Code interpreter will still run without this file. If the file is not detected, Twitter integration will be disabled.

### Running

First, the pigpio daemon should be initialized with sudo. The default settings worked for me.
```
sudo pigpiod
```

To start listening for input, run the morse.py file like so
```
python morse.py
```
KeyboardInterrupt (^C) to stop.

If pigpiod is already running, there is no need to re-run it to run morse.py again.

## Operation

### Input

On a keypress, input is measured from release time, taking a measurement of the duration of the press to determine a dit (.) or a dah (-) (according to a configurable threshold).

Subsequent measurement of the time elapsed since release to determine whether we've passed the threshold to cut off characters, words, and eventually the final message.

This is recorded into a string in a common style of dashes, dots, spaces and slashes, wherein HELLO WORLD would be recorded as follows:

.... . .-.. .-.. --- / .-- --- .-. .-.. -..

Upon detection of a completed message, this is then translated into english characters using a simple stored Morse Code dictionary in the same format.

If Twitter integration is enabled, the program switches to "transmit" mode and awaits a confirmation tap before transmitting to the Twitter account configured in `twitter_config.yml`.

### Twitter Integration

If Twitter integration is enabled, after a message is translated, the program switches to "transmit" mode, flashing the LED for a set duration and waiting for the user to tap to confirm transmission to Twitter.

If a tap is detected, transmission is attempted using the configuration found in `twitter_config.yml`, and then the program is returned to "input" mode.

If no tap is detected after the set duration, the program returns to "input" mode.

### Feedback

#### Visual

An LED on Pin 13 (GPIO27) displays input status without relying on a screen.

- Initialization
	- 3 Rapid Flashes
- Character Input In Progress
	- LED on
- Character Input Complete
	- LED off
- Word Input Complete
	- 1 Flash
- Message Input Complete
	- 3 Rapid Flashes
- "Transmit" Mode Active
	- Blinking for a period

Uses [pigpio's PWM](http://abyz.co.uk/rpi/pigpio/python.html#set_PWM_frequency) (Pulse Width Modulation) with frequency and duty cycle settable in the config file.

#### Audio

A buzzer on Pin 15 (GPIO22) plays audio feedback when a keypress is detected.

Uses the [pigpio's PWM](http://abyz.co.uk/rpi/pigpio/python.html#set_PWM_frequency) (Pulse Width Modulation) with frequency and duty cycle settable in the config file.
