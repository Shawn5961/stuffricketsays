#!/usr/bin/env python
import socket
import re
import time
from datetime import date
import urllib
import urllib2
import json
import cPickle as pickle
import random
import pycurl 
import tweepy
import filecmp
import gspread
import logging
from oauth2client.service_account import ServiceAccountCredentials
from shutil import copyfile

#Auth init
authfile = open("authfile", "r")
authjson = json.loads(authfile.read())
authfile.close()

#Twitch auth
server = "irc.chat.twitch.tv"
port = 6667
channel = "#ncpricket"
nick = "StuffRicketSays"
password = authjson["password"] 

#Twitter auth
CONSUMER_KEY = authjson["CONSUMER_KEY"]
CONSUMER_SECRET = authjson["CONSUMER_SECRET"]
ACCESS_KEY = authjson["ACCESS_KEY"]
ACCESS_SECRET = authjson["ACCESS_SECRET"]
auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)
api = tweepy.API(auth)

#Google Docs Auth
scope = ['https://spreadsheets.google.com/feeds']
credentials = ServiceAccountCredentials.from_json_keyfile_name('StuffRicketSays-7ee29640605b.json', scope)

#Oauth for Ricket's channel info
RICKET_AUTH = authjson["RICKET_AUTH"]
#Logging setup
logging.basicConfig(filename='error.log', level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger=logging.getLogger(__name__)

def errorlog(error):
    errorlog = open("error.log", 'a')
    errorlog.write(str(error))
    errorlog.close

quoteblacklist = "8"

#Basic Twitch IRC Functionality
def ping():
    con.send("PONG :Pong\n")

def sendmsg(chan, msg):
    con.send("PRIVMSG " + chan + " :" + msg + "\n")

def joinchan(chan):
    con.send("JOIN " + chan + "\n")

def hello():
    con.send("PRIVMSG " + channel + " :HELLO!\n")

def send_nick(nick):
    con.send('NICK ' + nick + "\n")

def send_pass(password):
    con.send('PASS ' + password + '\n')

def send_req():
    con.send('CAP REQ :twitch.tv/membership\n')
    con.send('CAP REQ :twitch.tv/tags\n')

#Updating channel info
#!!
#!! May need to be updated now that Twitch requires authentication !!
#!!
def updatejson():
    channeljsonurl = urllib2.urlopen("https://api.twitch.tv/kraken/streams/ncpricket")
    channeljson = json.loads(channeljsonurl.read())
    return channeljson

def updatesubsjson():
    subsjsonsurl = urllib2.urlopen("https://api.twitch.tv/kraken/channels/ncpricket/subscriptions?oauth_token=" + RICKET_AUTH)
    subsjson = json.loads(subsjsonsurl.read())
    return subsjson

#Admin chat commands
def parse_message_admin(msg, name):
    if len(msg) >= 1:
        msg1 = msg.split(' ', 1)
        msg2 = msg.split(' ', 2)
        msg = msg.split(' ')
        options = {'$test': command_test,
                   '$sub': command_sub,
                   '$hey': command_hey,
                   '$chair' : command_chair,
                   '$subcount' : command_subcount,
                   '$emotes' : command_emotes,
                   '$song' : command_song,
                   '!songrequest' : command_songrequest,
                   '$quote' : command_quote}
        msg[0] = msg[0].lower()
        if msg[0] == "$quote":
            try:
                if len(msg) > 1:
                    if msg[1] == "add":
                        options[msg[0]](msg[1], "Ricket", msg2[2])
                    elif msg[1] == "stats":
                        options[msg[0]](msg[1])
                    elif msg[1] == "remove":
                        options[msg[0]](msg[1])
                    elif msg[1].isdigit() == True:
                        options[msg[0]]("default", "Ricket", "null", msg[1])
                    else:
                        options[msg[0]]("default", name=name)
                else:
                    options[msg[0]]("default", name=name)
            except Exception as e:
                logging.error(e) 
                options[msg[0]]()
        elif msg[0] == '$antlers':
            try:
                if len(msg) > 1:
                    options[msg[0]](msg[1])
                else:
                    options[msg[0]]()
            except Exception as e:
                logging.error(e)
                options[msg[0]]()
        elif msg[0] == '$song' or msg[0] == "!songrequest":
            try:
                if len(msg) > 1:
                    print msg1[1]
                    options[msg[0]](msg1[1])
                else:
                    options[msg[0]]()
            except Exception as e:
                logging.error(e)
                options[msg[0]]()
        elif msg[0] in options:
            try:
                options[msg[0]](msg[1])
            except Exception as e:
                print "poop"
                logging.error(e) 
                options[msg[0]]()

#Sub chat commands
def parse_message_sub(msg, name):
    if len(msg) >= 1:
        msg2 = msg.split(' ', 2)
        msg = msg.split(' ')
        options = {'$quote' : command_quote_sub,
                   '$chair' : command_chair,
                   '$sub' : command_sub,
                   '$emotes' : command_emotes,
                   '$song' : command_song
                   }
        msg[0] = msg[0].lower()
        if msg[0] == "$quote":
            try:
                if len(msg) > 1:
                    if msg[1] == "add":
                        options[msg[0]](msg[1], "Ricket", msg2[2], "null", name)
                    elif msg[1] == "stats":
                        options[msg[2]](msg[1])
                    elif msg[1].isdigit() == True:
                        options[msg[0]]("default", "Ricket", "null", msg[1])
                    else:
                        options[msg[0]]()
                else:
                    options[msg[0]]()
            except Exception as e:
                logging.error(e) 
                options[msg[0]]()
        elif msg[0] in options:
            try:
                options[msg[0]](msg[1])
            except Exception as e:
                logging.error(e) 
                options[msg[0]]()

#Viewer chat commands
def parse_message(msg):
    if len(msg) >= 1:
        msg = msg.split(' ')
        options = {'$quote' : command_quote}
        msg[0] = msg[0].lower()
        if msg[0] == "$quote":
            try:
                if len(msg) > 1:
                    if msg[1].isdigit() == True:
                        options[msg[0]]("default", "Ricket", "null", msg[1])
                    else:
                        options[msg[0]]()
                else:
                    options[msg[0]]()
            except Exception as e:
                logging.error(e) 
                options[msg[0]]()
        elif msg[0] in options:
            options[msg[0]]()

def command_test():
    sendmsg(channel, 'testing some stuff')

#Standard quote functionality
def command_quote(func="default", quoter="Ricket", msg="null", quotechoice="null", name="null"):
    if func == "default":
        quotefile = open('quotefile', 'rb')
        quotepickle = pickle.load(quotefile)
        while quotechoice == "null" or quotechoice == str(quoteblacklist):
            quotechoice = str(random.randint(0, (len(quotepickle) - 1)))
        sendmsg(channel, "#" + quotechoice + ': "' + quotepickle[int(quotechoice)][0] + '" - ' + quotepickle[int(quotechoice)][1] + ", " + quotepickle[int(quotechoice)][2])
        quotefile.close()
    elif func == "add":
        gc = gspread.authorize(credentials)
        wks = gc.open("StuffRicketSays").sheet1
        copyfile('quotefile', 'quotefile.bak')
        quotefile = open('quotefile', 'rb')
        quotepickle = pickle.load(quotefile)
        quotefile.close()
        today = time.strftime("%b %d, %Y")
        quotelist = [msg, quoter, today] 
        quotedict = {len(quotepickle): quotelist}
        quotepickle.update(quotedict)
        quotefile = open('quotefile', 'wb')
        pickle.dump(quotepickle, quotefile)
        quotefile.close()
        sendmsg(channel, 'Quote added')
        api.update_status(msg)
        wks.update_cell(len(quotepickle)+1, 1, len(quotepickle)-1)
        wks.update_cell(len(quotepickle)+1, 2, msg)
        wks.update_cell(len(quotepickle)+1, 3, today)
    elif func == "remove":
        if filecmp.cmp('quotefile', 'quotefile.bak') == False:
            copyfile('quotefile.bak', 'quotefile')
            timeline = tweepy.Cursor(api.user_timeline).items(1)

            for tweet in timeline:
                api.destroy_status(tweet.id)

            quotefile = open('quotefile', 'rb')
            quotepickle = pickle.load(quotefile)
            quotefile.close()
            gc = gspread.authorize(credentials)
            wks = gc.open("StuffRicketSays").sheet1
            wks.update_cell(len(quotepickle)+2, 1, "")
            wks.update_cell(len(quotepickle)+2, 2, "")
            wks.update_cell(len(quotepickle)+2, 3, "")
            sendmsg(channel, 'Quote removed')
    elif func == "stats":
        quotefile = open('quotefile', 'rb')
        quotepickle = pickle.load(quotefile)
        quotefile.close()
        quotenum = len(quotepickle)
        date1 = date(2016,2,17)
        date2 = date.today()
        quoteavg = (quotenum - 55) / float((date2 - date1).days)
        quoteavg = round(quoteavg, 3)
        sendmsg(channel, "I currently hold " + str(quotenum) + " ridiculous things Ricket has said. Since February 17th, 2016, we have added " + str(quotenum-55) + " quotes, for an average of " + str(quoteavg) + " quotes per day. For a complete list of quotes, www.tinyurl.com/StuffRicketSays")

#Allow subs to suggest quotes
#!!
#!! Need to add usertype to args so can combine into one quote function
#!!
def command_quote_sub(func="default", quoter="Ricket", msg="null", quotechoice="null", name="null"):
    if func == "default":
        quotefile = open('quotefile', 'rb')
        quotepickle = pickle.load(quotefile)
        if quotechoice == "null":
            quotechoice = random.randint(0, (len(quotepickle) - 1))
        sendmsg(channel, "#" + str(quotechoice) + ': "' + quotepickle[int(quotechoice)][0] + '" - ' + quotepickle[int(quotechoice)][1] + ", " + quotepickle[int(quotechoice)][2])
        quotefile.close()
    elif func == "add":
        quotefile = open('quotefile.sub', 'a')
        json.dump([msg, quoter, time.strftime("%b %d, %Y"), name], quotefile)
        quotefile.write("\n")
        quotefile.close()
        sendmsg(channel, "Quote suggested")
    elif func == "stats":
        quotefile = open('quotefile', 'rb')
        quotepickle = pickle.load(quotefile)
        quotefile.close()
        quotenum = len(quotepickle)
        date1 = date(2016,2,17)
        date2 = date.today()
        quoteavg = (quotenum - 55) / float((date2 - date1).days)
        quoteavg = round(quoteavg, 3)
        sendmsg(channel, "I currently hold " + str(quotenum) + " ridiculous things Ricket has said. Since February 17th, 2016, we have added " + str(quotenum-55) + " quotes, for an average of " + str(quoteavg) + " quotes per day. For a complete list of quotes, www.tinyurl.com/StuffRicketSays")

#Song database/request commands
#!!
#!! Find a prettier way to deal with adding songs to database
#!!
def command_song(songname=None):
    if songname == None:
        songlist()
    else:
        sendmsg(channel, '!songrequest ' + songname)

def songlist(func="default", song="null"):
    if func == "default":
        songfile = open('songfile', 'rb')
        songpickle = pickle.load(songfile)
        songchoice = random.randint(0, (len(songpickle) - 1))
        sendmsg(channel, "!songrequest " + songpickle[int(songchoice)])
        songfile.close()
    elif func == "add":
        songfile = open('songfile', 'rb')
        songpickle = pickle.load(songfile)
        songfile.close()
        if song in songpickle:
            print "already there"
        else:
            songdict = {len(songpickle): song}
            songpickle.update(songdict)
            songfile = open('songfile', 'wb')
            pickle.dump(songpickle, songfile)
            songfile.close()

def command_songrequest(song):
    songlist("add", song)

def command_wrongsong():
    sendmsg(channel, "!wrongsong")

#Random commands
def command_chair():
    sendmsg(channel, 'ricketChair ricketChair ricketChair ricketChair ricketChair ricketChair ricketChair ricketChair ricketChair ricketChair ricketChair ricketChair ricketChair ricketChair ricketChair ricketChair ricketChair') 

def command_emotes():
    sendmsg(channel, 'https://drive.google.com/open?id=0Bzh4-gG9mFEpTHNVQUV6X0hiZFk - WoW Twitch Emotes addon with Ricket\'s emotes!')

def command_hey():
    sendmsg(channel, 'ricketHey')

def command_sub():
    sendmsg(channel, 'ricketLove ricketSub ricketLove ricketSub ricketLove ricketSub ricketLove ricketSub ricketLove ricketSub ricketLove ricketSub ricketChair ricketLove ricketSub ricketLove ricketSub ricketLove ricketSub ricketLove ricketSub')

def command_subcount():
    subsjson = updatesubsjson()
    sendmsg(channel, 'Only ' + str(250 - int(subsjson["_total"])) + ' subs to go until new emotes!')

#Check if channel is online or not
def channelstatus():
    channeljson = updatejson()
    if channeljson["stream"] == None:
        return False
    else:
        return True

#Connect to Twitch, send credentials, and join channel
con = socket.socket()
con.connect((server, port))
send_pass(password)
send_nick(nick)
send_req()
time.sleep(1)
joinchan(channel)

while 1:
    try:
        data = con.recv(2048)
        data_split = re.split(r"[\r\n]+", data)
        data = data_split.pop()

        for line in data_split:
            line2 = line
            line = str.rstrip(line)
            line = str.split(line)

            if len(line) >= 1:
                try:
                    if line[0] == 'PING':
                        ping()
                        print time.strftime("%x %X") +" - " + line2

                    elif line[2] == 'PRIVMSG':
                        userline = str.rstrip(line[0])
                        userline = str.split(userline, ";")
                        userdct = dict([kv.split('=') for kv in userline])
                        message = " ".join(line[4:])
                        message = str.strip(message, " :")

                        #Send to correct set of commands based upon user level
                        if userdct.has_key("user-type") and userdct["user-type"] == "mod":
                            parse_message_admin(message, userdct["display-name"])
                        elif userdct.has_key("subscriber") and userdct["subscriber"] == "1":
                            parse_message_sub(message, userdct["display-name"])
                        else:
                            parse_message(message)

                        print(userdct["display-name"] + ": " + message)
                except Exception as e:
                    logging.error(e) 

    except Exception as e:
        logging.error(e)
