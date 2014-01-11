# -*- coding: utf-8 -*-
"""
Bot implementation. Should be reloadable
"""
class Bot(object):
    def __init__(self, socket):
        self.socket = socket
        self.gameId = None
        self.game = None
        pass

    def handleMessage(self, msg):
        if msg["type"] == "request":
            if msg["state"]["game_id"] != self.gameId:
                self.gameId = msg["state"]["game_id"]
                self.game = Game(msg)
                
            self.socket.send(self.game.handleRequest(msg))

        elif msg['type'] == "result":
            pass
            if self.game:
                self.game.handleResult(msg)


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
        if msg['result']['type'] == "game_won":
            if msg['result']['by'] == self.playerNumber:
                print "  Won Game"
            else:
                print "  Lost Game"
        pass
        #print msg
        

def response(msg, **response):
    return {"type": "move", "request_id": msg['request_id'], "response": dict(response)}

class Hand(object):
    def __init__(self, msg):
        self.cards = msg['state']['hand']
        self.spent_cards = []
        pass

    def handleRequest(self, msg):
        if msg["request"] == "request_card":
            #@todo Remove for performance
            if sorted(self.cards) != sorted(msg['state']['hand']):
                print "**** Warning: Mismatched hands %s != %s ****" % (repr(self.cards), msg['state']['hand'])
                self.cards = msg['state']['hand']

            cardToPlay = self.getCardToPlay()
            self.cards.remove(cardToPlay)
            self.spent_cards.append(cardToPlay)
            return response(msg, type="play_card", card=cardToPlay)
        elif msg["request"] == "challenge_offered":
            return response(msg, type="accept_challenge")
    
    def getCardToPlay(self):
        if len(self.cards) == 5:
            return min(self.cards)
        else:
            return max(self.cards)