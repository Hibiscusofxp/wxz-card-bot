# -*- coding: utf-8 -*-

import random

import datetime

import json

import os

random.seed()
"""
Bot implementation. Should be reloadable
"""

won = 0
lost = 0
def checkDir(fn):
    dn = os.path.dirname(fn)
    if not os.path.isdir(dn):
        os.makedirs(dn)

    return fn

class Bot(object):
    def __init__(self, socket):
        self.socket = socket
        self.gameId = None
        self.opponentId = None
        self.game = None
        self.logger = None
        pass

    def handleMessage(self, msg):
        if msg["type"] == "request":
            if msg["state"]["game_id"] != self.gameId:
                self.gameId = msg["state"]["game_id"]
                self.game = Game(msg)

            if msg['state']['opponent_id'] != self.opponentId:
                self.opponentId = msg['state']['opponent_id']
                logfn = "strates/%s/%s/%s.log" % (STRATEGY, self.opponentId, datetime.datetime.now().strftime("%Y%m%dT%H%M%S"))
                logfn = checkDir(logfn)
                self.logger = open(logfn, "w")

            response = self.game.handleRequest(msg)
            self.socket.send(response)

        elif msg['type'] == "result":
            pass
            if self.game:
                self.game.handleResult(msg)

        if self.logger:
            self.logger.write(json.dumps(msg))
            self.logger.write("\n")


        if self.logger and msg['type'] == "request":
            self.logger.write(json.dumps(response))
            self.logger.write("\n")


class Game(object):
    def __init__(self, msg):
        self.gameId = msg['state']['game_id']
        self.opponentId = msg['state']['opponent_id']
        self.playerNumber = msg['state']['player_number']
        self.handId = None
        self.hand = None
        self.hands = []

        print("New game started: " + str(self.gameId) + " with " + str(self.opponentId))
        #print msg
    
    def handleRequest(self, msg):
        if msg["state"]['hand_id'] != self.handId:
            if self.hand:
                self.hands.append(self.hand)
            self.handId = msg['state']['hand_id']
            self.hand = Hand(msg)

        return self.hand.handleRequest(msg)

    def handleResult(self, msg):
        global won, lost
        if msg['result']['type'] == "game_won":
            if msg['result']['by'] == self.playerNumber:
                won += 1
                print "  Won Game %s" % (float(won) / float(won + lost) * 100 ,)
            else:
                lost += 1
                print "  Lost Game %s" % (float(won) / float(won + lost) * 100 ,)
        pass
        #print msg
        

def response(msg, **response):
    return {"type": "move", "request_id": msg['request_id'], "response": dict(response)}

class Hand(object):
    def __init__(self, msg):
        self.cards = msg['state']['hand']
        self.spent_cards = []
        pass

    def challengeAcceptStrat(self, msg): # Oliver
        my_tricks = msg['state']['your_tricks']
        his_tricks = msg['state']['their_tricks']
        left_tricks = 5 - msg['state']['total_tricks'] # ???
        if my_tricks - his_tricks >= left_tricks:
            return 1
        return 0

    def challengeRejectStrat(self, msg):
        my_tricks = msg['state']['your_tricks']
        his_tricks = msg['state']['their_tricks']
        left_tricks = 5 - msg['state']['total_tricks'] # ???
        if my_tricks - his_tricks < left_tricks:
            return 1
        return 0        


    def handleRequest(self, msg):
        if msg["request"] == "request_card":
            #@todo Remove for performance
            if msg['state']['can_challenge']:
                    if self.challengeAcceptStrat(msg) == 1:
                        return response(msg, type="offer_challenge")

            if len(self.cards) > len(msg['state']['hand']):
                self.cards = msg['state']['hand']

            if sorted(self.cards) != sorted(msg['state']['hand']):
                print "**** Warning: Mismatched hands %s != %s ****" % (repr(self.cards), msg['state']['hand'])
                self.cards = msg['state']['hand']

            cardToPlay = self.getCardToPlay()
            self.cards.remove(cardToPlay)
            self.spent_cards.append(cardToPlay)
            return response(msg, type="play_card", card=cardToPlay)
        elif msg["request"] == "challenge_offered":
            if self.challengeRejectStrat(msg) == 1:
                return response(msg, type="accept_challenge")
    
    def getCardToPlay(self):
        return self.cards[random.randrange(0, len(self.cards))]
        #if len(self.cards) == 5:
        #    return min(self.cards)
        #else:
        #    return max(self.cards)


STRATEGY = "rand-challenge"

