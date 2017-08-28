
#----------------------------------------------------------
# morse.py
#
# Created by Anthony Peluso
#
# Program for taking input from a Morse Code key on
# a Raspberry Pi 3, with audio/visual feedback
# and Twitter posting capabilities
#
# https://github.com/afpeluso/morse-code-pi/
#
#----------------------------------------------------------

import RPi.GPIO as GPIO
import time
import math
import yaml # PyYaml
import tweepy # Tweepy Twitter integration library www.tweepy.org

def main():

    # Configuration Files

    # load morse code configuration
    with open("config.yml", 'r') as ymlfile:
        cfg = yaml.load(ymlfile)

    # Eventually leave them the option
    # if (cfg['TWITTER_ENABLED'] == True)

    # separate twitter config because it's sensitive
    # possibly allow for it to not exist if someone doesn't want to post to twitter
    try:
        # load the file
        with open("twitter_config.yml", 'r') as ymlfile:
            twitter_cfg = yaml.load(ymlfile)
    except FileNotFoundError:
        # twitter_config.yml does not exist
        print "Twitter Configuration Not Found"
        exit() # bail

    # Constants

    READ_PIN = cfg['READ_PIN'] # Pin to read key input from
    LED_PIN = cfg['LED_PIN'] # Pin for LED
    BUZZER_PIN = cfg['BUZZER_PIN'] # Pin for Buzzer

    BUZZER_FREQ = cfg['BUZZER_FREQ'] # Frequency for Buzzer
    BUZZER_DC = cfg['BUZZER_DC'] # Duty Cycle for Buzzer
    BLINKER_FREQ = cfg['BLINKER_FREQ'] # Frequency for LED Blinks
    BLINKER_DC = cfg['BLINKER_DC'] # Duty Cycle for Blinker Pulse Width Modulation

    COMMAND_MODE_DURATION = cfg['COMMAND_MODE_DURATION'] # sec, duration of command mode input acceptance
    COMMAND_MODE_THRESHOLD = cfg['COMMAND_MODE_THRESHOLD'] # sec, time before command mode starts

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
    TRANSMITTED_FLASHES = cfg['TRANSMITTED_FLASHES'] # number of LED flashes on successful transmission

    NULL_TIME = time.gmtime(0) # "null" time for timestamps not in use

    # Twitter Constants

    API_KEY = twitter_cfg['API_KEY']
    API_SECRET = twitter_cfg['API_SECRET']

    ACCESS_TOKEN = twitter_cfg['ACCESS_TOKEN']
    ACCESS_TOKEN_SECRET = twitter_cfg['ACCESS_TOKEN_SECRET']

    # Variables

    press_time = NULL_TIME # time of key press, start "null"
    release_time = NULL_TIME # time of key release, start "null"

    char_buffer = "" # storage for current character, start with blank
    word_buffer = "" # storage for current word, start with blank
    morse_buffer = "" # storage for morse message, start with blank
    text_output = "" # storage for text message

    # modes: input, command
    mode = "input" # default to inputs
    command_mode_start = NULL_TIME # initialize

    # GPIO ports

    GPIO.setmode(GPIO.BOARD) # Pin Number Mode
    GPIO.setup(READ_PIN,GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Morse Code Key Input
    GPIO.setup(LED_PIN,GPIO.OUT) # LED Output
    GPIO.setup(BUZZER_PIN,GPIO.OUT) # Buzzer Output
    buzzer = GPIO.PWM(BUZZER_PIN,BUZZER_FREQ) # Buzzer Pulse Width Modulation
    blinker = GPIO.PWM(LED_PIN,BLINKER_FREQ) # Blinker Pulse Width Modulation

    try:

        # just so we know something's happening
        print "LISTENING FOR TAP"

        # flash LED to show that we're initialized
        led_notify(LED_PIN, FLASH_INTERVAL, INITIALIZE_FLASHES)

        # main loop
        while True:

            # while we're in input mode
            while (mode == "input"):

                if (GPIO.input(READ_PIN) == 1): # input detected

                    if (press_time == NULL_TIME): # if this is the initial press

                        press_time = time.time()  # set pressed time
                        release_time = NULL_TIME # clear release time

                    else: # if we have a press_time

                        # find out how long we've been pressing down...
                        press_duration = math.floor((time.time() * 1000) - (press_time * 1000))

                        # if we have a valid press
                        if (press_duration > KEYPRESS_THRESHOLD):

                            # turn on the LED to signify we're in a character
                            if (GPIO.input(LED_PIN) == 0): # if we're not already started
                                GPIO.output(LED_PIN,1)

                            # start the speaker since we're legit pressing
                            if (GPIO.input(BUZZER_PIN) == 0): # if we're not already started
                                buzzer.start(BUZZER_DC)

                else: # no input detected

                    if (press_time != NULL_TIME): # if this is initial release

                        # turn off the buzzer since we've released
                        buzzer.stop()

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
                                        if(len(morse_buffer) > 0): morse_buffer += (WORD_DELIMETER)

                                        morse_buffer += word_buffer
                                        print "WORD ADDED: " + word_buffer
                                        word_buffer = ""

                                        # flash LED to signify word completion
                                        led_notify(LED_PIN, FLASH_INTERVAL, WORD_FLASHES)

                            else:

                                # if we have a message
                                if (len(morse_buffer) > 0):

                                    print "MESSAGE COMPLETED: " + morse_buffer
                                    text_output = translate_morse_code_string(morse_buffer)

                                    print "TEXT: " + text_output
                                    morse_buffer = "" # reset string

                                    # flash LED to notify message completion
                                    led_notify(LED_PIN, FLASH_INTERVAL, MESSAGE_FLASHES)

                                    # If we have a message completed, switch to command mode
                                    print "PREPARING TO SEND MESSAGE"
                                    print "TAP WHILE LED IS FLASHING TO CONFIRM TRANSMISSION TO TWITTER"
                                    time.sleep(COMMAND_MODE_THRESHOLD)
                                    command_mode_start = time.time()
                                    mode = "command"

            while (mode == "command"):

                # if the LED isn't already blinking
                if (GPIO.input(LED_PIN) == 0):
                    blinker.start(BLINKER_DC)

                # if we are still within command mode time limit
                if ((time.time() - command_mode_start) < COMMAND_MODE_DURATION):

                    # if we have a tap
                    if (GPIO.input(READ_PIN) == 1):

                        print "TRANSMITTING..."

                        # Send to Twitter!
                        auth = tweepy.OAuthHandler(API_KEY, API_SECRET)
                        auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
                        api = tweepy.API(auth)
                        twitter_status = api.update_status(text_output)
                        # say something about twitter send?

                        # make sure twitter send happened here!

                        blinker.stop() # stop the blinking
                        # Flash LED
                        led_notify(LED_PIN, FLASH_INTERVAL, TRANSMITTED_FLASHES)
                        print "TRANSMISSION SENT"

                        # reset everything
                        text_output = "" # reset string
                        command_mode_start = NULL_TIME
                        print "RETURNING TO INPUT MODE"
                        print "LISTENING FOR TAP"
                        mode = "input" # go back into input mode
                else:

                    # reset everything
                    blinker.stop() # stop the blinking
                    text_output = "" # reset string
                    command_mode_start = NULL_TIME # reset command start
                    print "COMMAND INTERVAL ENDED, RETURNING TO INPUT MODE"
                    print "LISTENING FOR TAP"
                    mode = "input" # go back into input mode


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
