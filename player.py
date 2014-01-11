#!/usr/bin/python2

# This should work in both recent Python 2 and Python 3.

import socket
import json
import struct
import time
import sys
import os
import traceback

import bot

BOT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.py")
BOT_MODIFIED = os.path.getmtime(BOT_FILE)

def sample_bot(host, port):
    global BOT_MODIFIED

    print "*** (Re)connecting ***"

    s = SocketLayer(host, port)

    botInst = None

    msg = s.pump()
    if msg["type"] == "error":
        print("The server doesn't know your IP. It saw: " + msg["seen_host"])
        print "Press Enter to Retry"
        sys.stdin.readline()
        return

    botInst = bot.Bot(s)

    while True:
        if os.path.getmtime(BOT_FILE) > BOT_MODIFIED:
            print "*** Reloading bot ***"
            BOT_MODIFIED = os.path.getmtime(BOT_FILE)
            reload(bot)
            botInst = bot.Bot(s)

        botInst.handleRequest(msg)

        msg = s.pump()



def loop(player, *args):
    while True:
        try:
            player(*args)
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            print traceback.format_exc()
            print "*** Aborted ***"

        time.sleep(10)

class SocketLayer:
    def __init__(self, host, port):
        self.s = socket.socket()
        self.s.connect((host, port))

    def pump(self):
        """Gets the next message from the socket."""
        sizebytes = self.s.recv(4)
        (size,) = struct.unpack("!L", sizebytes)

        #Maybe use buffers?
        msg = []
        bytesToGet = size
        while bytesToGet > 0:
            b = self.s.recv(bytesToGet)
            bytesToGet -= len(b)
            msg.append(b)

        msg = "".join([chunk.decode('utf-8') for chunk in msg])

        return json.loads(msg)

    def send(self, obj):
        """Send a JSON message down the socket."""
        b = json.dumps(obj)
        length = struct.pack("!L", len(b))
        self.s.send(length + b.encode('utf-8'))

    def raw_send(self, data):
        self.s.send(data)

if __name__ == "__main__":
    loop(sample_bot, "cuda.contest", 9999)
