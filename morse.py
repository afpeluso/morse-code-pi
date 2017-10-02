
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

import pigpio # Using pigpio instead of RPi.GPIO for better PWM control
import time
import math
import yaml # PyYaml
# tweepy import handled below conditionally, 
# so as not to require it if Twitter integration is disabled.
# Tweepy Twitter integration library www.tweepy.org

import Adafruit_CharLCD as LCD # LCD Screen Library


def main():

    # Configuration Files

    # load morse code configuration
    with open("config.yml", 'r') as ymlfile:
        cfg = yaml.load(ymlfile)

    # Constants

    PIN_ON = 1 # Pin On Value
    PIN_OFF = 0 # Pin Off Value
    DC_OFF = 0 # PWM Duty Cycle Off Value

    # Code Key configuration
    READ_PIN = cfg['READ_PIN'] # Pin to read key input from

    # Speaker pin configuration
    BUZZER_PIN = cfg['BUZZER_PIN'] # Pin for Buzzer
    BUZZER_FREQ = cfg['BUZZER_FREQ'] # Frequency for Buzzer
    BUZZER_DC = cfg['BUZZER_DC'] # Duty Cycle for Buzzer

    # LCD pin configuration:
    LCD_RS_PIN = cfg['LCD_RS_PIN']
    LCD_EN_PIN = cfg['LCD_EN_PIN']
    LCD_D4_PIN = cfg['LCD_D4_PIN']
    LCD_D5_PIN = cfg['LCD_D5_PIN']
    LCD_D6_PIN = cfg['LCD_D6_PIN']
    LCD_D7_PIN = cfg['LCD_D7_PIN']
    LCD_BACKLIGHT_PIN = cfg['LCD_BACKLIGHT_PIN'] # not used

    # Define LCD column and row size for 16x2 LCD.
    LCD_COLUMNS = cfg['LCD_COLUMNS']
    LCD_ROWS = cfg['LCD_ROWS']

    # Initialize the LCD using the pins above.
    lcd = LCD.Adafruit_CharLCD(LCD_RS_PIN, LCD_EN_PIN, LCD_D4_PIN, LCD_D5_PIN, LCD_D6_PIN, LCD_D7_PIN,
                           LCD_COLUMNS, LCD_ROWS, LCD_BACKLIGHT_PIN)

    # clear to initialize
    lcd.clear()

    # Messaging configuration
    TRANSMIT_MODE_DURATION = cfg['TRANSMIT_MODE_DURATION'] # sec, duration of transmit mode input acceptance
    TRANSMIT_MODE_THRESHOLD = cfg['TRANSMIT_MODE_THRESHOLD'] # sec, time before transmit mode starts

    WORD_DELIMETER = cfg['WORD_DELIMETER'] # string separator for words

    KEYPRESS_THRESHOLD = cfg['KEYPRESS_THRESHOLD'] # ms, how long a press has to be to be recognized, for bounce
    DITDAH_THRESHOLD = cfg['DITDAH_THRESHOLD'] # ms, when a press goes from a dit to a dah
    CHAR_THRESHOLD = cfg['CHAR_THRESHOLD'] # ms, post-release, when to cut off a letter and add it to the message
    WORD_THRESHOLD = cfg['WORD_THRESHOLD'] # ms, post-release, when to add a space
    MESSAGE_THRESHOLD = cfg['MESSAGE_THRESHOLD'] # ms, post-release, when a message is complete

    LCD_MESSAGE_DELAY = 1.5 # seconds, amount of time to delay after an informational LCD message

    NULL_TIME = time.gmtime(0) # "null" time for timestamps not in use

    # Set up twitter stuff
    # has to be after LCD stuff for error messages
    TWITTER_ENABLED = cfg['TWITTER_ENABLED']

    # If we are integrating with Twitter...
    if (TWITTER_ENABLED):

        # this stuff is in a separate twitter config because it's sensitive
        try:
            # load the file
            with open("twitter_config.yml", 'r') as ymlfile:
                twitter_cfg = yaml.load(ymlfile)

                lcd.message("TWITTER ENABLED\nCONFIG LOADED")

                # if Twitter transmission is enabled, import tweepy library
                import tweepy

                # load twitter config
                API_KEY = twitter_cfg['API_KEY']
                API_SECRET = twitter_cfg['API_SECRET']

                ACCESS_TOKEN = twitter_cfg['ACCESS_TOKEN']
                ACCESS_TOKEN_SECRET = twitter_cfg['ACCESS_TOKEN_SECRET']

        except:
            # twitter_config.yml likely does not exist
            lcd.message("TWITTER DISABLED\nCONFIG ERROR")
            #print "(have you made the twitter_config.yml file yet?)"
            # set TWITTER_ENABLED false because we don't have configuration anyway
            TWITTER_ENABLED = False

    else:
        lcd.message("TWITTER DISABLED")


    # Variables

    press_time = NULL_TIME # time of key press, start "null"
    release_time = NULL_TIME # time of key release, start "null"

    char_buffer = "" # storage for current character, start with blank
    word_buffer = "" # storage for current word, start with blank
    message_buffer = "" # storage for morse message, start with blank
    message_buffer = "" # storage for text message

    # modes: input, transmit
    mode = "input" # default to inputs
    transmit_mode_start = NULL_TIME # initialize

    # GPIO ports

    io = pigpio.pi() # create the pigpio instance
    io.set_mode(READ_PIN, pigpio.INPUT) # set up the input
    io.set_pull_up_down(READ_PIN, pigpio.PUD_DOWN) # set input to use pulldown
    io.set_mode(BUZZER_PIN, pigpio.OUTPUT) # Buzzer Output
    io.set_PWM_frequency(BUZZER_PIN, BUZZER_FREQ) # Set Buzzer Frequency
    io.set_PWM_dutycycle(BUZZER_PIN,DC_OFF) # Start Duty Cycle at "Off"

    try:

        lcd.clear()
        # just so we know something's happening
        lcd.message("LISTENING")
        #lcd.show_cursor(true) # show blinking cursor while we wait

        # main loop
        while True:

            # while we're in input mode
            while (mode == "input"):

                if (io.read(READ_PIN) == PIN_ON): # input detected

                    if (press_time is NULL_TIME): # if this is the initial press

                        press_time = time.time()  # set pressed time
                        release_time = NULL_TIME # clear release time

                    else: # if we have a press_time

                        # find out how long we've been pressing down...
                        press_duration = math.floor((time.time() * 1000) - (press_time * 1000))

                        # if we have a valid press
                        if (press_duration > KEYPRESS_THRESHOLD):

                            # start the speaker since we're legit pressing
                            if (io.get_PWM_dutycycle(BUZZER_PIN) == DC_OFF): # if we're not already started
                                io.set_PWM_dutycycle(BUZZER_PIN, BUZZER_DC)

                else: # no input detected

                    if (press_time is not NULL_TIME): # if this is initial release

                        # turn off the buzzer since we've released
                        io.set_PWM_dutycycle(BUZZER_PIN, DC_OFF)

                        release_time = time.time() # get the release time
                        # get the press duration in milliseconds
                        press_duration = math.floor((release_time * 1000) - (press_time * 1000))

                        press_time = NULL_TIME # clear press_time
                        #release_time is used for char/word/message processing

                        if (press_duration > KEYPRESS_THRESHOLD):

                            if (press_duration < DITDAH_THRESHOLD):

                                char_buffer += "."

                                lcd.clear() # clear it
                                lcd.message(char_buffer + "\n" + (message_buffer + WORD_DELIMETER + word_buffer).strip())

                            elif (press_duration >= DITDAH_THRESHOLD):

                                char_buffer += "-"

                                lcd.clear() # clear it
                                lcd.message(char_buffer + "\n" + (message_buffer + WORD_DELIMETER + word_buffer).strip())

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
                                            char_translated = morse_translate(char_buffer)
                                            word_buffer += char_translated

                                            lcd.clear()
                                            lcd.message("CHAR+: " + char_translated + "\n" + (message_buffer + WORD_DELIMETER + word_buffer).strip())
                                            char_buffer = ""
                                            char_translated = ""

                                else:

                                    # if we have a word in process
                                    if (len(word_buffer) > 0):

                                        # add word to message, add delimeter if necessary, clear word buffer
                                        if(len(message_buffer) > 0): message_buffer += (WORD_DELIMETER)
                                        message_buffer += word_buffer

                                        lcd.clear()
                                        lcd.message("WORD+: " + word_buffer + "\n" + (message_buffer).strip())

                                        word_buffer = ""

                            else:

                                # if we have a message
                                if (len(message_buffer) > 0):

                                    #print "TEXT: " + message_buffer
                                    lcd.clear()
                                    lcd.message("MESSAGE COMPLETE\n" + message_buffer)
                                    time.sleep(LCD_MESSAGE_DELAY)

                                    # if we have twitter enabled
                                    if (TWITTER_ENABLED):
                                        lcd.clear()
                                        lcd.message("TAP TO CONFIRM\nTWITTER TRANSMIT")
                                        # wait a little bit...
                                        time.sleep(TRANSMIT_MODE_THRESHOLD)
                                        # then switch to transmit mode
                                        transmit_mode_start = time.time()
                                        mode = "transmit"
                                    else:
                                        # stay in input mode
                                        message_buffer = "" # reset string

            # transmit mode for sending to twitter
            # this mode will only get switched to if TWITTER_ENABLED is true
            while (mode == "transmit"):

                # if we are still within transmit mode time limit
                if ((time.time() - transmit_mode_start) < TRANSMIT_MODE_DURATION):

                    # if we have a tap
                    if (io.read(READ_PIN) == PIN_ON):

                        lcd.clear()
                        #lcd.show_cursor(True)
                        lcd.message("TRANSMITTING...")

                        try:
                            # Send to Twitter!
                            auth = tweepy.OAuthHandler(API_KEY, API_SECRET)
                            auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
                            api = tweepy.API(auth)
                            twitter_status = api.update_status(message_buffer)
                            lcd.clear()
                            lcd.message("TRANSMIT SUCCESS\n" + str(twitter_status.id))
                            time.sleep(LCD_MESSAGE_DELAY)

                        # Catch any twitter errors and tell the user
                        except tweepy.TweepError as e:
                            lcd.clear()
                            lcd.message("TRANSMIT ERROR:\n" + str(e.message[0]['message']))
                            print str(e.message[0]['message'])
                            time.sleep(LCD_MESSAGE_DELAY)

                        # Catch any other errors
                        except:
                            lcd.clear()
                            lcd.message("TRANSMIT ERROR\nCHECK CONFIG")
                            time.sleep(LCD_MESSAGE_DELAY)

                        # reset everything
                        message_buffer = "" # reset string
                        transmit_mode_start = NULL_TIME
                        lcd.clear()
                        lcd.message("RETURNING TO\nINPUT MODE")
                        time.sleep(LCD_MESSAGE_DELAY)
                        lcd.clear()
                        lcd.message("LISTENING")
                        mode = "input" # go back into input mode
                else:

                    # reset everything
                    message_buffer = "" # reset string
                    transmit_mode_start = NULL_TIME # reset transmit start
                    lcd.clear()
                    lcd.message("TRANSMIT SKIPPED\nRETURN TO INPUT")
                    time.sleep(LCD_MESSAGE_DELAY)
                    lcd.clear()
                    lcd.message("LISTENING")
                    mode = "input" # go back into input mode


    # quit on a break
    except KeyboardInterrupt:
        io.stop() # cleanup pins
        lcd.clear() # clear the LCD


# ------------------------------------------------------------------------------
# Morse Code string translator
# delimited with spaces for characters, and / for words
# format example "HELLO WORLD": .... . .-.. .-.. --- / .-- --- .-. .-.. -..

def morse_translate_string(code_string):

    if len(code_string) == 0:
        return ''

    # split on spaces for chars, words delimiters will become spaces
    characters = code_string.split(" ")

    morseAlphabet = {
        "/": " ", ".-": "A", "-.-.": "C", "-...": "B", ".": "E", "-..": "D",
        "--.": "G", "..-.": "F", "..": "I", "....": "H", "-.-": "K", ".---": "J",
        "--":  "M", ".-..": "L","---": "O", "-.": "N", "--.-": "Q", ".--.": "P",
        "...": "S", ".-.": "R", "..-": "U", "-": "T", ".--": "W", "...-": "V",
        "-.--": "Y", "-..-": "X", "--..": "Z",
        ".----": "1", "..---": "2", "...--": "3", "....-": "4", ".....": "5",
        "-....": "6", "--...": "7", "---..": "8", "----.": "9", "-----": "0"
    }

    # this next nearly unreadable line does the following:
    # join together returned values from the morseAlphabet list using the characters list as keys
    # if the key is not present in morseAlphabet, return a "?" to join into the string instead
    message = ''.join(morseAlphabet[key] if (key in morseAlphabet) else "?" for key in characters)

    return message

# ------------------------------------------------------------------------------
# Morse Code char translator

def morse_translate(char):

    if len(char) == 0:
        return ''

    morseAlphabet = {
        "/": " ", ".-": "A", "-.-.": "C", "-...": "B", ".": "E", "-..": "D",
        "--.": "G", "..-.": "F", "..": "I", "....": "H", "-.-": "K", ".---": "J",
        "--":  "M", ".-..": "L","---": "O", "-.": "N", "--.-": "Q", ".--.": "P",
        "...": "S", ".-.": "R", "..-": "U", "-": "T", ".--": "W", "...-": "V",
        "-.--": "Y", "-..-": "X", "--..": "Z",
        ".----": "1", "..---": "2", "...--": "3", "....-": "4", ".....": "5",
        "-....": "6", "--...": "7", "---..": "8", "----.": "9", "-----": "0"
    }

    if char in morseAlphabet:
        return morseAlphabet[char]
    else:
        return '?'


# ------------------------------------------------------------------------------
# fire off main

main()
