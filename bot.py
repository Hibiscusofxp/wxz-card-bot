# -*- coding: utf-8 -*-

import random
import datetime
import json
import os
import itertools, math
import stats
import collections

random.seed()
"""
Bot implementation. Should be reloadable
"""

leaderboard = {}
accept_challenge = 0
offer_challenge = 0
in_challenge = False
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

        self.bad_ass = 0

        self.counter = None
        print("New game started: " + str(self.gameId) + " with " + str(self.opponentId))
        bad_ass_players = set([25, 41, 9, 17, 42, 31])
        if self.playerNumber in bad_ass_players:
            # self.bad_ass = 1
            pass
        #print msg
    
    def handleRequest(self, msg):
        global in_challenge
        in_challenge = msg['state']['in_challenge']

        if msg["state"]['hand_id'] != self.handId or not self.hand:
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
        global leaderboard
        global accept_challenge
        global offer_challenge
        global in_challenge
        if not self.opponentId in  leaderboard:
            leaderboard[self.opponentId] = {
                "won": 0, 
                "lost": 0, 
                "handwon": 0, 
                "handlost": 0, 
                "handwonA": 0, 
                "handlostA": 0, 
                "handwonO": 0, 
                "handlostO": 0, 
                "oliver_accept": 0, 
                "ppp_accept": 0,
                "lost_cause": collections.Counter(),
                "won_cause": collections.Counter(),
            }
        obj = leaderboard[self.opponentId]
        self.counter = obj

        if msg['result']['type'] == "game_won":
            if msg['result']['by'] == self.playerNumber:
                obj['won'] += 1
                print "  Won Game %s" % (float(obj['won']) / float(obj['won'] + obj['lost']) * 100 ,)

                if not in_challenge:
                    obj['won_cause']['overflow'] += 1
                elif offer_challenge:
                    obj['won_cause']['offer'] += 1
                else:
                    obj['won_cause']['accept'] += 1
            else:
                obj['lost'] += 1
                print "  Lost Game %s" % (float(obj['won']) / float(obj['won'] + obj['lost']) * 100 ,)

                if not in_challenge:
                    obj['lost_cause']['overflow'] += 1
                elif offer_challenge:
                    obj['lost_cause']['offer'] += 1
                else:
                    obj['lost_cause']['accept'] += 1

        elif msg['result']['type'] == "hand_done":
            if 'by' in msg['result']:
                if msg['result']['by'] == self.playerNumber:
                    obj['handwon'] += 1
                else:
                    obj['handlost'] += 1
            if accept_challenge == 1 and in_challenge:
                print "accept"
                if 'by' in msg['result']:
                    if msg['result']['by'] == self.playerNumber:
                        obj['handwonA'] += 1
                        print "  Won Hand %s" % (float(obj['handwonA']) / float(obj['handwonA'] + obj['handlostA']) * 100 ,)
                    else:
                        obj['handlostA'] += 1
                        print "  Lost Hand %s" % (float(obj['handwonA']) / float(obj['handwonA'] + obj['handlostA']) * 100 ,)
                
            elif offer_challenge == 1 and in_challenge:
                print "offer"
                if 'by' in msg['result']:
                    if msg['result']['by'] == self.playerNumber:
                        obj['handwonO'] += 1
                        print "  Won Hand %s" % (float(obj['handwonO']) / float(obj['handwonO'] + obj['handlostO']) * 100 ,)
                    else:
                        obj['handlostO'] += 1
                        print "  Lost Hand %s" % (float(obj['handwonO']) / float(obj['handwonO'] + obj['handlostO']) * 100 ,)

        
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

        self.cardAvg = float(sum(self.cards)) / 5.0

        if len(self.cards) == 5:
            self.cardMedian = self.cards[2]

        for card in self.cards:
            parent.deck.removeCard(card)

        self.spent_cards = []
        self.parent = parent
        self.other_cards = []

        self.lastCard = None
        pass






    def getWinpercen(self, my_cards_in, his_cards_in, my_tricks_in, his_tricks_in, this_winnum, this_tienum):
        my_tricks = my_tricks_in
        his_tricks = his_tricks_in
        for idx, ele in enumerate(my_cards_in, start = 0):
            numWin = 0
            numTie = 0

            my_cards = list(my_cards_in)
            my_cards.remove(ele)
            for hisele in his_cards_in:
                my_tricks1 = int(my_tricks)
                his_tricks1 = int(his_tricks)
                if ele > hisele:
                    my_tricks1 = my_tricks1 + 1
                elif ele < hisele:
                    his_tricks1 = his_tricks1 + 1
                his_cards1 = list(his_cards_in)
                his_cards1.remove(hisele)
                for his_cards_per in itertools.permutations(his_cards1):

                    # print ele , my_cards , " VS " , hisele , his_cards_per 
                    my_tricks2 = int(my_tricks1)
                    his_tricks2 = int(his_tricks1)
                    for idx1 in range(0, len(my_cards)):
                        if my_cards[idx1] > his_cards_per[idx1]:
                            my_tricks2 += 1
                        elif my_cards[idx1] < his_cards_per[idx1]:
                            his_tricks2 += 1

                    # print my_tricks2, his_tricks2
                    if (my_tricks2 > his_tricks2):
                        numWin += 1
                    elif (my_tricks2 == his_tricks2):
                        numTie += 1
            this_winnum[idx] += numWin
            this_tienum[idx] += numTie

    def getBestCardAndPercen(self, level, my_cards, my_winnum, my_tienum, totalNum, his_cards, deck, my_tricks, his_tricks):
        if level == len(my_cards):
            self.getWinpercen(my_cards, his_cards, my_tricks, his_tricks, my_winnum, my_tienum)
            totalNum[0] += math.factorial(len(my_cards))
            # for idx, ele in enumerate(this_winpercen):
            #     my_winpercen[idx] += ele
            # for idx, ele in enumerate(this_tiepercen):
            #     my_tiepercen[idx] += ele
        else:
            if level == 0:
                pickCard = 1
            else:
                pickCard = his_cards[level - 1]
            while (pickCard <= 13 and deck[pickCard] == 0):
                pickCard += 1
            while (pickCard <= 13):
                his_cards[level] = pickCard
                deck[pickCard] -= 1
                self.getBestCardAndPercen(level + 1, my_cards, my_winnum, my_tienum, totalNum, his_cards, deck, my_tricks, his_tricks)
                deck[pickCard] += 1
                pickCard += 1
                while (pickCard <= 13 and deck[pickCard] == 0):
                    pickCard += 1
    
    def getCardPosInDeck(self, ele, deck):
        total = 0
        tienum = 0
        winnum = 0
        for card, num in enumerate(deck):
            total += num
            if card < ele:
                winnum += num
            elif card == ele:
                tienum += num
        return {
            'win': float(winnum) / total,
            'tie': float(tienum) / total,
            'lose': float(total - winnum - tienum) / total
        }

    def getBestPer(self, my_cards, deck, my_tricks, his_tricks):
        winex = float(my_tricks)
        for ele in my_cards:
            percens = self.getCardPosInDeck(ele, deck)
            winex += percens['win'] + percens['tie'] / 2.0
        return winex
        # value is 0 to 5

        # my_winnum = []
        # my_tienum = []
        # his_cards = []
        # totalNum = [0]
        # for idx in range(0, len(my_cards)):
        #     my_winnum.append(0)
        #     my_tienum.append(0)
        #     his_cards.append(0)
        # self.getBestCardAndPercen(0, my_cards, my_winnum, my_tienum, totalNum, his_cards, deck, my_tricks, his_tricks)
        # return ( float(my_winnum[0]) + float(my_tienum[0]) / 2 ) / totalNum[0]





    def challengeOfferStrat(self, msg): 
        my_tricks = msg['state']['your_tricks']
        his_tricks = msg['state']['their_tricks']
        left_tricks = 5 - msg['state']['total_tricks']
        my_points = msg['state']['your_points']
        his_points = msg['state']['their_points']

        x = my_tricks - his_tricks
        extfact = my_points - his_points

        if his_points == 9 and my_points < 9:
            return 1

        if his_points >7 and my_points < 4:
            return 1
        avg = float(sum(self.cards) / len(self.cards))
        if self.parent.bad_ass == 1:
            thres1 = 0.1
            thres2 = 1.5
        else:
            thres1 = 0.3
            thres2 = 3.0


        if 0.5*(avg-7)/6.0 - 0.3*extfact/10.0 + 0.2*his_points/10.0 > thres1:
            return 1

        if self.getBestPer(self.cards, self.parent.deck, my_tricks, his_tricks) > thres2:
        # if 0.45*(avg-7)/6.0 - 0.3*extfact/10.0 - 0.05*x/5.0 + 0.2*his_points/10.0 > 0.3:
            return 1

        if x - left_tricks >= 0: #always right
            return 1
        return 0

    def challengeReceiveStrat(self, msg):
        my_tricks = msg['state']['your_tricks']
        his_tricks = msg['state']['their_tricks']
        left_tricks = 5 - msg['state']['total_tricks']
        my_points = msg['state']['your_points']
        his_points = msg['state']['their_points']




        x = my_tricks - his_tricks
        extfact = my_points - his_points
        avg = 0

        if his_points == 9 and my_points < 9:
            return 1


        if -x - left_tricks > 0: #always right
            return 0
        if x - left_tricks > 0: #always right
            return 1

        if len(self.cards) > 0:
            avg = float(sum(self.cards) / len(self.cards))




        if self.parent.bad_ass == 1:
            thres1 = 0.8
            thres2 = 5
        else:
            thres1 = 0.5
            thres2 = 2.5

        uncertainty = 0.025*left_tricks/5.0 - 0.3*extfact/10.0  + 0.5*(avg-7) /3.0 + 0.05*his_points/9.0 + 0.125*len(self.cards)/5.0
        if uncertainty > thres1:
            print "****Oliver Accept"
            if (self.parent.counter):
                self.parent.counter['oliver_accept'] += 1
            return 1

 
        if self.getBestPer(self.cards, self.parent.deck, my_tricks, his_tricks) > thres2:
            print "****PPPPPP Accept"
            if (self.parent.counter):
                self.parent.counter['ppp_accept'] += 1
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
            # if self.cardAvg > 6 and self.cardMedian > 6:
                # return response(msg, type="accept_challenge")
            if self.challengeReceiveStrat(msg) == 1:
                accept_challenge = 1
                return response(msg, type="accept_challenge")
            else:
                accept_challenge = 0
                return response(msg, type="reject_challenge")
    
    def getCardToPlay(self, msg):
        if len(self.cards) == 5:
            #5 cards, don't know anything? Give low 66% card
            return self.cards[random.randrange(3, 5)]
        elif len(self.cards) == 4:
            if msg['state']['their_tricks'] == 0:
                #Won last card, their cards are small. 
                return self.cards[3]
                
        if len(self.cards) - (msg['state']['their_tricks'] - msg['state']['your_tricks']) > 1:
            cardsCount = 0
            for i in range(1, min(self.cards) + 1):
                cardsCount += self.parent.deck[i]

            if float(cardsCount) / float(self.parent.deck.remaining) < 0.1:
                return min(self.cards)

        return max(self.cards)

        value = 0
        count = 0
        for i in range(1, 13 + 1):
            value += i * self.parent.deck[i]
            count += self.parent.deck[i]
        avg = value / count + 1
        while (avg <=13 and avg not in self.cards):
            avg += 1
        if avg > 13:
            avg = min(self.cards)
        return avg
    
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

