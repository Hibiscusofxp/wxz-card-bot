# -*- coding: utf-8 -*-
"""
Bot implementation. Should be reloadable
"""
class Bot(object):
    def __init__(self, socket):
        self.socket = socket
        self.gameId = None
        self.handId = None
        pass

    def handleRequest(self, msg):
        if msg["type"] == "request":
            if msg["state"]["game_id"] != self.gameId:
                self.gameId = msg["state"]["game_id"]
                self.handId = None
                print("New game started: " + str(self.gameId))
                #print msg

            if msg["state"]["hand_id"] != self.handId:
                self.handId = msg['state']['hand_id']
                print "New hand started:" + str(self.handId)
                #print msg



            if msg["request"] == "request_card":
                cardToPlay = msg["state"]["hand"][0]
                self.socket.send ({"type": "move", "request_id": msg["request_id"],
                    "response": {"type": "play_card", "card": cardToPlay}})
            elif msg["request"] == "challenge_offered":
                self.socket.send ({"type": "move", "request_id": msg["request_id"],
                        "response": {"type": "reject_challenge"}})


class Game(object):
    pass

class Hand(object):
    pass