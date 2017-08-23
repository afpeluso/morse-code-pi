# morse-code-pi
A Morse Code Key interpreter for Raspberry Pi 3 in Python

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

I attached two leads from the J-38 telegraph key binding posts to Pins 1 (3.3.V) and 11 (GPIO17) on the GPIO header, using the internal pull-down resistor to steady the input.

This seems to make for a totally detectable input, with some thresholding in code to make up for a bit of bounciness.

## Approach

On a keypress, input is measured from release time, taking a measurement of the duration of the press to determine a dit (.) or a dah (-) (according to a configurable threshold), and subsequent measurement of the time elapsed since release to determine whether we've passed the threshold to cut off characters, words, and eventually the final message.

This is recorded into a buffer in a common style of dashes, dots, spaces and slashes, wherein HELLO WORLD would be recorded as follows:

.... . .-.. .-.. --- / .-- --- .-. .-.. -..

Upon detection of a completed message, this is then translated into english characters using a simple stored Morse Code dictionary in the same format.

### Feedback

#### Visual

I added an LED to the mix on Pin 13 (GPIO27) to display input status without relying on a screen.

- Initialization
	- 3 Blinks
- Character Input In Progress
	- LED on
- Character Input Complete
	- LED off
- Word Input Complete
	- 1 Blink
- Message Input Complete
	- 3 Blinks

#### Audio

I attached a buzzer on Pin 15 (GPIO22) to play audio feedback when a keypress is detected.

This uses the Pi's GPIO.PWM (Pulse Width Modulation) with frequency and duty cycle settable in the config file.

## Running This Project

### Software Requirements
This project was initially made in Python 2.7.13 since that's what came default on the default Raspbian installation.

- Python 2.7.13
- RPi.GPIO
- PyYaml
- Raspbian 9 (Probably not required)

### Physical Requirements

Pins, frequencies, timing, etc. are all adjustable in config.yml.

By default...

- Connect your Morse Code key or other button to header Pins 1 and 11.

- Connect your LED to Pin 13 (with appropriate resistor) and Ground.

- Connect Buzzer to Pin 15 and Ground.

### Running

To get it to start listening for input just run the morse.py file.
```
python morse.py
```
KeyboardInterrupt (^C) to stop.

### Code Caveat
I am not the most Pythonic programmer. While it functions at the moment, it's also probably garbage, style-wise. I hope to clean that up soon.

## Twitter Interface
Coming soon :)
