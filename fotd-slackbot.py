#!/usr/bin/python
import argparse
import os
import sys
import urllib2
from slackclient import SlackClient
from bs4 import BeautifulSoup

def get_fotd(restaurant):
    culvers_url = 'http://www.culvers.com/restaurants/{0}'.format(restaurant)
    culvers_page = urllib2.urlopen(culvers_url)
    culvers_soup = BeautifulSoup(culvers_page, "html.parser")
    culvers_fotd_div_list = culvers_soup.find_all("div", class_="ModuleRestaurantDetail-fotd")
    if len(culvers_fotd_div_list) == 1:
        for div in culvers_fotd_div_list:
            fotd = div.find("strong").string
            if fotd:
                return fotd
            else:
                return False

def get_bot_id(sc,bot_name):
    response = sc.api_call("users.list")
    if response.get('ok'):
        # retrieve all users so we can find our bot
        users = response.get('members')
        for user in users:
            if 'name' in user and user.get('name') == bot_name:
                #print("Bot ID for '" + user['name'] + "' is " + user.get('id'))
               return user.get('id')
    else:
        print("could not find bot user with the name " + bot_name)
	sys.exit(1)


def handle_command(sc,restaurant,command,channel):
    """
        Receives commands directed at the bot and determines if they
        are valid commands. If so, then acts on the commands. If not,
        returns back what it needs for clarification.
    """
    response = "Not sure what you mean. Use the *" + "fotd" + \
               "* command with numbers, delimited by spaces."
    if command.startswith("fotd"):
        #response = "Sure...write some more code then I can do that!"
        fotd = get_fotd(restaurant)
        response = "The flavor is {0}".format(fotd)
    sc.api_call("chat.postMessage", channel=channel,
                          text=response, as_user=True)


def parse_slack_output(slack_rtm_output,bot_id):
    """
        The Slack Real Time Messaging API is an events firehose.
        this parsing function returns None unless a message is
        directed at the Bot, based on its ID.
    """
    at_bot = "<@{0}>".format(bot_id)
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'text' in output and at_bot in output['text']:
                # return text after the @ mention, whitespace removed
                return output['text'].split(at_bot)[1].strip().lower(), \
                       output['channel']
    return None, None

def get_env():
    bot_token = None
    bot_name = None
    channel_id = None
    restaurant = None
    
    if "BOT_TOKEN" in os.environ:
        bot_token = os.getenv("BOT_TOKEN")
    else:
        # env is missing bot token
        sys.exit(2)
    
    if "BOT_NAME" in os.environ:
        bot_name = os.getenv("BOT_NAME")
    else:
        # env is missing bot name
        sys.exit(3)

    if "RESTAURANT" in os.environ:
        restaurant = os.getenv("RESTAURANT")
    else:
        # env is missing restaurant
        sys.exit(4)
   
    return bot_token,bot_name,restaurant

def main():
    bot_token,bot_name,restaurant = get_env()
    sc = SlackClient(bot_token)
    bot_id = get_bot_id(sc,bot_name)

    if sc.rtm_connect():
        print("{0} is connected and running!".format(bot_name))
        while True:
            command, channel = parse_slack_output(sc.rtm_read(),bot_id)
            if command and channel:
                handle_command(sc,restaurant,command,channel)
            time.sleep(1)
 
if __name__ == '__main__':
    main()
