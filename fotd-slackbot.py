#!/usr/bin/python
import argparse
import os
import re
import sys
import time
import datetime
import urllib2
from slackclient import SlackClient
from bs4 import BeautifulSoup

def get_forecast(restaurant):
    forecast = []
    culvers_url = 'http://www.culvers.com/restaurants/{0}'.format(restaurant)
    culvers_page = urllib2.urlopen(culvers_url)
    culvers_soup = BeautifulSoup(culvers_page, "html.parser")
    culvers_upcoming_div = culvers_soup.find("div", id="entire-month")
    #culvers_upcoming_div = culvers_soup.find("div", id="upcoming")
    content_div_list = culvers_upcoming_div.find_all("div",class_="content")
    for div in content_div_list:
        fotd_div = div.find("p",class_="fotd")
        fotd = fotd_div.find("a",class_="value").string
        desc_raw = div.find("p",class_="date").string.encode('utf8')
        desc = " ".join(desc_raw.split())
        fotd_string = "{0}: {1}".format(desc,fotd)
        forecast.append(fotd_string)
    return forecast


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


def handle_command(sc,cache,command,channel):
    """
        Receives commands directed at the bot and determines if they
        are valid commands. If so, then acts on the commands. If not,
        returns back what it needs for clarification.
    """
    response = "Not sure what you mean. Use the *" + "search" + \
               "* command with some search string."
    if command.startswith("search"):
        fotd_forecast = {}
        for key in cache:
            fotd_forecast = cache[key]
        commands = command.split() 
        if len(commands) > 1:
            matches = []
            regex = " ".join(command.split()[1:])
            print regex
            for line in fotd_forecast:
                match = re.search(regex,line,flags=re.IGNORECASE)
                if match:
                    matches.append(line)

            if len(matches) > 0:
                response = "\n".join(matches)
                sc.api_call("chat.postMessage", channel=channel,text=response,as_user=True)
            else:
                response = "Sorry, I couldn't find anything that matched that!"
                sc.api_call("chat.postMessage", channel=channel,text=response,as_user=True)
        else:
            response_list = []
            response = "\n".join(fotd_forecast)
            sc.api_call("chat.postMessage", channel=channel,text=response, as_user=True)
    elif command.startswith(":") and command.endswith(":"):
        response = str(command)
        sc.api_call("chat.postMessage", channel=channel,text=response, as_user=True)


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
    parser = argparse.ArgumentParser(description="Sends notifications for FOTD")
    ## First check environment variables
    if 'BOT_TOKEN' in os.environ:
        bot_token_default = os.environ.get('BOT_TOKEN')
    else:
        bot_token_default = None

    if 'BOT_NAME' in os.environ:
        bot_name_default = os.environ.get('BOT_NAME')
    else:
        bot_name_default = None

    if 'CHANNEL_NAME' in os.environ:
        channel_name_default = os.environ.get('CHANNEL_NAME')
    else:
        channel_name_default = None

    if 'RESTAURANT' in os.environ:
        restaurant_default = os.environ.get('RESTAURANT')
    else:
        restaurant_default = None

    if 'POST_TIME' in os.environ:
        post_time_default = os.environ.get('POST_TIME')
    else:
        post_time_default = None

    if 'POST_WORKWEEK_ONLY' in os.environ:
        post_workweek_only_default = os.environ.get('POST_WORKWEEK_ONLY')
    else:
        post_workweek_only_default = None

    parser.add_argument(
            '--bot_token',dest='bot_token',
            default=bot_token_default,
            help="Token for bot from api.slack.com"
        )
    parser.add_argument(
            '--bot_name',dest='bot_name',
            default=bot_name_default,
            help="Name of the bot from Slack"
        )
    parser.add_argument(
            '--channel_name',dest='channel_name',
            default=channel_name_default,
            help="Channel Name to post FOTD alerts to"
        )
    parser.add_argument(
            '--restaurant',dest='restaurant',
            default=restaurant_default,
            help="The store string from the culver's website"
        )
    parser.add_argument(
            '--post_time',dest='post_time',
            default=post_time_default,
            help="Sets the time to post the FOTF to the specified channel"
        )
    parser.add_argument(
            '--post_workweek_only',dest='post_workweek_only',
            default=post_workweek_only_default,
            action="store_true",
            help="Only post FOTD during the workweek (M-F)"
        )
    args = parser.parse_args()

    if args.bot_token is None:
        print("bot token is missing from both env and cli")
        # env is missing bot token
        sys.exit(2)
    if args.bot_name is None:
        print("bot name is missing from both env and cli")
        # env is missing bot name
        sys.exit(3)
    if args.restaurant is None:
        print("restaurant is missing from both env and cli")
        # env is missing restaurant
        sys.exit(4)

    if args.channel_name and args.post_time:
        # These must be specified, or omitted together
        return args
    elif (args.channel_name is None) and (args.post_time is None):
        # These must be specified, or omitted together
        return args
    else:
        print("post_time and channel name are required together")
        sys.exit(10)


def main():
    args = get_env()
    print args.bot_token
    sc = SlackClient(args.bot_token)
    bot_id = get_bot_id(sc,args.bot_name)
    forecast_list = get_forecast(args.restaurant)
    #print forecast_list
    now = datetime.datetime.now()
    next_post_datetime = None
    alert_sent_last_iter = False
    cache = {now: forecast_list}

    if args.post_time:
        hour,minute = args.post_time.split(":")
        next_post_datetime = now.replace(hour=int(hour),minute=int(minute),second=0,microsecond=0)
        init_time_diff = next_post_datetime - now
        #print init_time_diff.seconds
        #print init_time_diff.days

        if init_time_diff.days < 0:
            # check at startup to see if the alarm is set, if so, then check if
            # alert time has already passed. If it has, add a day to the next 
            # alert time.
            target_datetime = next_post_datetime + datetime.timedelta(days=1)
            next_post_datetime = target_datetime
        
        #print next_post_datetime

    if sc.rtm_connect():
        print("{0} is connected and running!".format(args.bot_name))
        while True:
            now = datetime.datetime.now()
            for datestamp in cache:
                delta = now - datestamp
                #print dir(delta)
                if delta.seconds > 14400:
                    #renews every 4 hours
                    forecast_list = get_forecast(args.restaurant)
                    cache = {now: forecast_list}
                    print "Updated cache at {0}".format(now)

            command, channel = parse_slack_output(sc.rtm_read(),bot_id)
            if command and channel:
                handle_command(sc,cache,command,channel)

            if next_post_datetime:
                if alert_sent_last_iter:
                    alert_sent_last_iter = False
                else:
                    time_diff = next_post_datetime - now
                    weekday = now.weekday()
                    if time_diff.days < 0:
                        if args.post_workweek_only:
                            # Only post FOTD on weekdays
                            if weekday < 6:
                                #alarm time has passed! send message!!
                                # set flag indicating to reset next run!
                                # also reset alarm time for same time tomorrow!
                                alert_sent_last_iter = True
                                target_datetime = next_post_datetime + datetime.timedelta(days=1)
                                next_post_datetime = target_datetime
                                #print "Next message will be posted {0}".format(next_post_datetime)
                                fotd = get_fotd(args.restaurant)
                                message = "Today's flavor is {0}.".format(fotd)
                                sc.api_call(
                                    "chat.postMessage",as_user="true:",
                                    channel=args.channel_name,text=message
                                )
                        else:
                            alert_sent_last_iter = True
                            target_datetime = next_post_datetime + datetime.timedelta(days=1)
                            next_post_datetime = target_datetime
                            #print "Next message will be posted {0}".format(next_post_datetime)
                            fotd = get_fotd(args.restaurant)
                            message = "Today's flavor is {0}.".format(fotd)
                            sc.api_call(
                                "chat.postMessage",as_user="true:",
                                channel=args.channel_name,text=message
                            )


            time.sleep(1)
 
if __name__ == '__main__':
    main()
