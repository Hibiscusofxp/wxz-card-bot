# -*- coding: utf-8 -*-

import random
import datetime
import json
import os
import stats

random.seed()
"""
Bot implementation. Should be reloadable
"""

won = 0
lost = 0
handwon = 0
handlost = 0
accept_challenge = 0
offer_challenge = 0
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
                print "--- New Opponent %s (%s) ---" % (self.opponentId, stats.PLAYERS[self.opponentId] if self.opponentId in stats.PLAYERS else "unknown")
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


class Deck(list):
    def __init__(self):
        self.extend(8 for x in range(0, 14))
        self[0] = 0
        self.remaining = 104


    def removeCard(self, card):
        if self[card] > 0:
            self[card] -= 1
            self.remaining -= 1
        elif card < 13:
            #Justification: Guesses the lowest possible
            self.removeCard(card + 1)

    def getLowestRemaining(self):
        """
        Return the lowest card that is still available in the entire deck
        """

        for n in range(1, 14):
            if self[n] > 0:
                return n


class Game(object):
    def __init__(self, msg):
        self.gameId = msg['state']['game_id']
        self.opponentId = msg['state']['opponent_id']
        self.playerNumber = msg['state']['player_number']
        self.handId = None
        self.hand = None
        self.hands = []

        self.cards = []       #Not used (yet)
        self.other_cards = [] #Not used (yet)

        self.deck = Deck()

        print("New game started: " + str(self.gameId) + " with " + str(self.opponentId))
        #print msg
    
    def handleRequest(self, msg):
        if msg["state"]['hand_id'] != self.handId:
            if self.hand:
                self.hands.append(self.hand)

                #@consider Should we also do estimate for op based on min?
                for card in self.hand.cards:
                    self.deck.removeCard(card)

            if len(self.hands) % 10 == 0:
                self.deck = Deck()

            self.handId = msg['state']['hand_id']
            self.hand = Hand(msg, self)

        return self.hand.handleRequest(msg)

    def handleResult(self, msg):
        global won, lost
        global handwon, handlost
        global accept_challenge
        global offer_challenge
        if msg['result']['type'] == "game_won":
            if msg['result']['by'] == self.playerNumber:
                won += 1
                print "  Won Game %s" % (float(won) / float(won + lost) * 100 ,)
            else:
                lost += 1
                print "  Lost Game %s" % (float(won) / float(won + lost) * 100 ,)
        elif msg['result']['type'] == "hand_done":
            if accept_challenge == 1:
                print "accept"
            elif offer_challenge == 1:
                print "offer"

            if 'by' in msg['result']:
                if msg['result']['by'] == self.playerNumber:
                    handwon += 1
                    print "  Won Hand %s" % (float(handwon) / float(handwon + handlost) * 100 ,)
                else:
                    handlost += 1
                    print "  Lost Hand %s" % (float(handwon) / float(handwon + handlost) * 100 ,)
        
        if self.hand:
            self.hand.handleResult(msg)

    def useMyCard(self, card):
        pass

    def estimateOpponentCard(self, card):
        self.deck.removeCard(card)
        

def response(msg, **response):
    return {"type": "move", "request_id": msg['request_id'], "response": dict(response)}

class Hand(object):
    def __init__(self, msg, parent):
        self.cards = msg['state']['hand']

        for card in self.cards:
            parent.deck.removeCard(card)

        self.spent_cards = []
        self.parent = parent
        self.other_cards = []

        self.lastCard = None
        pass

    def challengeOfferStrat(self, msg): 
        my_tricks = msg['state']['your_tricks']
        his_tricks = msg['state']['their_tricks']
        left_tricks = len(self.cards) 
        my_points = msg['state']['your_points']
        his_points = msg['state']['their_tricks']

        x = my_tricks - his_tricks
        extfact = my_points - his_points


        avg = sum(self.cards) / len(self.cards)
        if 0.45*(avg-7)/6.0 - 0.3*extfact/10.0 - 0.05*x/5.0 + 0.2*his_points/10.0 > 0.3:
            return 1

        if x - left_tricks >= 0: #always right
            return 1
        return 0

    def challengeReceiveStrat(self, msg):
        my_tricks = msg['state']['your_tricks']
        his_tricks = msg['state']['their_tricks']
        left_tricks = len(self.cards) 
        my_points = msg['state']['your_points']
        his_points = msg['state']['their_tricks']

        x = my_tricks - his_tricks
        extfact = my_points - his_points
        avg = 0

        if -x - left_tricks > 0: #always right
            return 0
        if x - left_tricks >= 0: #always right
            return 1

        if len(self.cards) != 0: #??
            avg = sum(self.cards) / len(self.cards)

        if his_points == 9 and my_points < 9:
            return 1

        if his_points >7 and my_points < 4:
            return 1

        uncertainty = 0.025*left_tricks/5.0 - 0.4*extfact/10.0 - 0.025*x/5.0 + 0.35*(avg-7) /3.0 + 0.025*his_points/10.0 + 0.175*len(self.cards)/5.0
        if uncertainty > 0.4:
            return 1

        # if extfact < -2:
        #     return 1
        # if x - left_tricks < 0:
        #     return 0
        return 0


    def handleRequest(self, msg):
        global accept_challenge
        global offer_challenge
        if msg["request"] == "request_card":
            #@todo Remove for performance
            if msg['state']['can_challenge']:
                    if self.challengeOfferStrat(msg) == 1:
                        offer_challenge = 1
                        return response(msg, type="offer_challenge")
                    else:
                        offer_challenge = 0

            if len(self.cards) > len(msg['state']['hand']):
                self.cards = msg['state']['hand']

            if sorted(self.cards) != sorted(msg['state']['hand']):
                print "**** Warning: Mismatched hands %s != %s ****" % (repr(self.cards), msg['state']['hand'])
                self.cards = msg['state']['hand']

            cardToPlay = self.getCardToPlay(msg)
            self.cards.remove(cardToPlay)
            self.spent_cards.append(cardToPlay)
            self.lastCard = cardToPlay
            self.parent.useMyCard(cardToPlay)

            return response(msg, type="play_card", card=cardToPlay)
        elif msg["request"] == "challenge_offered":
            if self.challengeReceiveStrat(msg) == 1:
                accept_challenge = 1
                return response(msg, type="accept_challenge")
            else:
                accept_challenge = 0
                return response(msg, type="reject_challenge")
    
    def getCardToPlay(self, msg):
        if len(self.cards) - (msg['state']['their_tricks'] - msg['state']['your_tricks']) > 1:
            cardsCount = 0
            for i in range(1, min(self.cards) + 1):
                cardsCount += self.parent.deck[i]

            if float(cardsCount) / float(self.parent.deck.remaining) < 0.1:
                return min(self.cards)

        return max(self.cards)
    
    def handleResult(self, msg):
        if msg['result']['type'] == "trick_tied":
            self.other_cards.append(self.lastCard)
            self.parent.estimateOpponentCard(self.lastCard)
        elif msg['result']['type'] == "trick_won":
            if msg['result']['card'] != self.lastCard:
                self.other_cards.append(msg['result']['card'])
                self.parent.estimateOpponentCard(msg['result']['card'])
            elif msg['result']['by'] == msg['your_player_num']:
                #ooops, don't know what their card is. Estimate lowest
                lowestEstimate = self.parent.deck.getLowestRemaining()
                #self.other_cards.append(lowestEstimate)
                self.parent.estimateOpponentCard(lowestEstimate)
            else:
                #They won?! Should be my card + 1
                #self.other_cards.append(self.lastCard + 1)
                self.parent.estimateOpponentCard(self.lastCard + 1)

STRATEGY = "rand-challenge"

