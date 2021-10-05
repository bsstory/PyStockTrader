import os
import sys
import time
import pyupbit
from PyQt5.QtCore import QThread
from pyupbit import WebSocketManager
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.static import now
from utility.setting import ui_num


class WebsTicker(QThread):
    def __init__(self, qlist):
        """
                    0        1       2        3       4       5       6       7      8      9
        qlist = [windowQ, soundQ, query1Q, query2Q, teleQ, receivQ, stockQ, coinQ, sstgQ, cstgQ,
                 tick1Q, tick2Q, tick3Q, tick4Q, tick5Q]
                   10       11      12     13      14
        """
        super().__init__()
        self.windowQ = qlist[0]
        self.tick5Q = qlist[14]
        self.websQ_ticker = None

    def run(self):
        """ get_tickers 리턴 리스트의 갯수가 다른 버그 발견, 1초 간격 3회 조회 후 길이가 긴 리스트를 티커리스트로 정한다 """
        tickers = pyupbit.get_tickers(fiat="KRW")
        time.sleep(1)
        tickers2 = pyupbit.get_tickers(fiat="KRW")
        tickers = tickers2 if len(tickers2) > len(tickers) else tickers
        time.sleep(1)
        tickers2 = pyupbit.get_tickers(fiat="KRW")
        tickers = tickers2 if len(tickers2) > len(tickers) else tickers
        dict_askbid = {}
        self.websQ_ticker = WebSocketManager('ticker', tickers)
        while True:
            data = self.websQ_ticker.get()
            if data == 'ConnectionClosedError':
                self.windowQ.put([ui_num['C단순텍스트'], '시스템 명령 오류 알림 - WebsTicker 연결 끊김으로 다시 연결합니다.'])
                self.websQ_ticker = WebSocketManager('ticker', tickers)
            else:
                ticker = data['code']
                t = data['trade_time']
                v = data['trade_volume']
                ask_bid = data['ask_bid']
                try:
                    pret = dict_askbid[ticker][0]
                    bid_volumns = dict_askbid[ticker][1]
                    ask_volumns = dict_askbid[ticker][2]
                except KeyError:
                    pret = None
                    bid_volumns = 0
                    ask_volumns = 0
                if ask_bid == 'BID':
                    dict_askbid[ticker] = [t, bid_volumns + float(v), ask_volumns]
                else:
                    dict_askbid[ticker] = [t, bid_volumns, ask_volumns + float(v)]
                if t != pret:
                    data['매수수량'] = dict_askbid[ticker][1]
                    data['매도수량'] = dict_askbid[ticker][2]
                    dict_askbid[ticker] = [t, 0, 0]
                    self.tick5Q.put([data, now()])


class WebsOrderbook(QThread):
    def __init__(self, qlist):
        """
        number      0        1       2      3       4       5       6      7      8      9       10
        qlist = [windowQ, soundQ, queryQ, teleQ, receivQ, stockQ, coinQ, sstgQ, cstgQ, tick1Q, tick2Q]
        """
        super().__init__()
        self.windowQ = qlist[0]
        self.tick5Q = qlist[14]
        self.websQ_order = None

    def run(self):
        """ get_tickers 리턴 리스트의 갯수가 다른 버그 발견, 1초 간격 3회 조회 후 길이가 긴 리스트를 티커리스트로 정한다 """
        tickers = pyupbit.get_tickers(fiat="KRW")
        time.sleep(1)
        tickers2 = pyupbit.get_tickers(fiat="KRW")
        tickers = tickers2 if len(tickers2) > len(tickers) else tickers
        time.sleep(1)
        tickers2 = pyupbit.get_tickers(fiat="KRW")
        tickers = tickers2 if len(tickers2) > len(tickers) else tickers
        self.websQ_order = WebSocketManager('orderbook', tickers)
        while True:
            data = self.websQ_order.get()
            if data == 'ConnectionClosedError':
                self.windowQ.put([ui_num['C단순텍스트'], '시스템 명령 오류 알림 - WebsOrderbook 연결 끊김으로 다시 연결합니다.'])
                self.websQ_order = WebSocketManager('orderbook', tickers)
            else:
                self.tick5Q.put(data)
