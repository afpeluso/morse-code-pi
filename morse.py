
#----------------------------------------------------------
# morse.py
#
# Created by Anthony Peluso
#
# Program for taking input from a Morse Code key on
# a Raspberry Pi 3, with some other features
#
# https://github.com/afpeluso/morse-code-pi/
#
#----------------------------------------------------------

import RPi.GPIO as GPIO
import time
import math
import yaml # PyYaml

def main():

    # load configuration
    with open("config.yml", 'r') as ymlfile:
        cfg = yaml.load(ymlfile)

    # Constants

    READ_PIN = cfg['READ_PIN'] # Pin to read key input from
    LED_PIN = cfg['LED_PIN'] # Pin for LED
    BUZZER_PIN = cfg['BUZZER_PIN'] # Pin for Buzzer

    CHAR_DELIMETER = cfg['CHAR_DELIMETER'] # string separator for characters
    WORD_DELIMETER = cfg['WORD_DELIMETER'] # string separator for words

    KEYPRESS_THRESHOLD = cfg['KEYPRESS_THRESHOLD'] # ms, how long a press has to be to be recognized, for bounce
    DITDAH_THRESHOLD = cfg['DITDAH_THRESHOLD'] # ms, when a press goes from a dit to a dah
    CHAR_THRESHOLD = cfg['CHAR_THRESHOLD'] # ms, post-release, when to cut off a letter and add it to the message
    WORD_THRESHOLD = cfg['WORD_THRESHOLD'] # ms, post-release, when to add a space
    MESSAGE_THRESHOLD = cfg['MESSAGE_THRESHOLD'] # ms, post-release, when a message is complete

    FLASH_INTERVAL = cfg['FLASH_INTERVAL'] # seconds of flash interval
    INITIALIZE_FLASHES = cfg['INITIALIZE_FLASHES'] # number of LED flashes on intialization
    WORD_FLASHES = cfg['WORD_FLASHES'] # number of LED flashes on word completion
    MESSAGE_FLASHES = cfg['MESSAGE_FLASHES'] # number of LED flashes on message completion

    NULL_TIME = time.gmtime(0) # "null" time for timestamps not in use

    # Variables

    press_time = NULL_TIME # time of key press, start "null"
    release_time = NULL_TIME # time of key release, start "null"

    char_buffer = "" # storage for current character, start with blank
    word_buffer = "" # storage for current word, start with blank
    message_buffer = "" # storage for whole message, start with blank

    # GPIO ports

    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(READ_PIN,GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(LED_PIN,GPIO.OUT)

    try:

        # just so we know something's happening
        print "LISTENING FOR TAP"

        # flash LED to show that we're initialized
        led_notify(LED_PIN, FLASH_INTERVAL, INITIALIZE_FLASHES)

        while True:

            if (GPIO.input(READ_PIN) == 1): # input detected

                # turn on the LED to signify we're in a character
                GPIO.output(LED_PIN,1)

                if (press_time == NULL_TIME): # if this is the initial press

                    press_time = time.time()  # set pressed time
                    release_time = NULL_TIME # clear release time

            else: # no input detected

                if (press_time != NULL_TIME): # if this is initial release

                    release_time = time.time() # get the release time
                    # get the press duration in milliseconds
                    press_duration = math.floor((release_time * 1000) - (press_time * 1000))

                    press_time = NULL_TIME # clear press_time
                    #release_time is used for char/word/message processing

                    if (press_duration > KEYPRESS_THRESHOLD):

                        if (press_duration < DITDAH_THRESHOLD):

                            char_buffer += "."
                            print "dot"

                        elif (press_duration >= DITDAH_THRESHOLD):

                            char_buffer += "-"
                            print "dash"

                else: # if we're waiting for input

                    if (release_time is not NULL_TIME):

                        # get the time since the last input was made in ms
                        time_since_last_input = math.floor((time.time() * 1000) - (release_time * 1000))

                        # if we're in the input zone...
                        if (time_since_last_input < MESSAGE_THRESHOLD):

                            # if we're waiting on a word
                            if (time_since_last_input < WORD_THRESHOLD):

                                # if we're done waiting on a character
                                if (time_since_last_input > CHAR_THRESHOLD) :

                                    # if we have a character...
                                    if (len(char_buffer) > 0):

                                        # add char to word, add delimeter if necessary, clear char buffer
                                        if (len(word_buffer) > 0): word_buffer += CHAR_DELIMETER
                                        word_buffer += char_buffer
                                        print "CHARACTER ADDED: " + char_buffer
                                        char_buffer = ""

                                        # turn off the LED to signify char completion
                                        GPIO.output(LED_PIN,0)

                            else:

                                # if we have a word in process
                                if (len(word_buffer) > 0):

                                    # add word to message, add delimeter if necessary, clear word buffer
                                    if(len(message_buffer) > 0): message_buffer += (WORD_DELIMETER)

                                    message_buffer += word_buffer
                                    print "WORD ADDED: " + word_buffer
                                    word_buffer = ""

                                    # flash LED to signify word completion
                                    led_notify(LED_PIN, FLASH_INTERVAL, WORD_FLASHES)

                        else:

                            # if we have a message
                            if (len(message_buffer) > 0):

                                print "MESSAGE COMPLETED: " + message_buffer
                                print "TEXT: " + translate_morse_code_string(message_buffer)
                                message_buffer = ""

                                # flash LED to notify message completion
                                led_notify(LED_PIN, FLASH_INTERVAL, MESSAGE_FLASHES)

    # quit on a break
    except KeyboardInterrupt:
        GPIO.cleanup()


# ------------------------------------------------------------------------------
# Morse Code string translator
# delimited with spaces for characters, and / for words
# format example "HELLO WORLD": .... . .-.. .-.. --- / .-- --- .-. .-.. -..

def translate_morse_code_string(code_string):
    
    morseAlphabet = {
        "/": " ", ".-": "A", "-.-.": "C", "-...": "B", ".": "E", "-..": "D",
        "--.": "G", "..-.": "F", "..": "I", "....": "H", "-.-": "K", ".---": "J",
        "--":  "M", ".-..": "L","---": "O", "-.": "N", "--.-": "Q", ".--.": "P",
        "...": "S", ".-.": "R", "..-": "U", "-": "T", ".--": "W", "...-": "V",
        "-.--": "Y", "-..-": "X", "--..": "Z",
        ".----": "1", "..---": "2", "...--": "3", "....-": "4", ".....": "5",
        "-....": "6", "--...": "7", "---..": "8", "----.": "9", "-----": "0"
    }

    # split on spaces for chars, words delimiters will become spaces
    characters = code_string.split(" ")

    # this next nearly unreadable line does the following:
    # join together returned values from the morseAlphabet list using the characters list as keys
    # if the key is not present in morseAlphabet, return a "?" to join into the string instead
    message = ''.join(morseAlphabet[key] if (key in morseAlphabet) else "?" for key in characters)

    return message


# ------------------------------------------------------------------------------
# Flash LED for Notifications
# This might work better as PWM...

def led_notify(pin,interval,repetitions):
    for x in range(0,repetitions):
        GPIO.output(pin,1)
        time.sleep(interval)
        GPIO.output(pin,0)
        time.sleep(interval)


# ------------------------------------------------------------------------------
# fire off main

main()
