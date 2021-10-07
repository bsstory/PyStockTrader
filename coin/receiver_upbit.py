import os
import sys
import time
import pyupbit
from PyQt5.QtCore import QThread
from pyupbit import WebSocketManager
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.static import now
from utility.setting import ui_num, DICT_SET


class WebsTicker(QThread):
    def __init__(self, qlist):
        """
                    0        1       2        3       4       5          6        7      8      9     10
        qlist = [windowQ, soundQ, query1Q, query2Q, teleQ, sreceivQ, creceivQ, stockQ, coinQ, sstgQ, cstgQ,
                 tick1Q, tick2Q, tick3Q, tick4Q, tick5Q]
                   11       12      13     14      15
        """
        super().__init__()
        self.windowQ = qlist[0]
        self.creceivQ = qlist[6]
        self.coinQ = qlist[8]
        self.cstgQ = qlist[10]
        self.tick5Q = qlist[15]
        self.list_jang = []
        self.websQ_ticker = None

    def run(self):
        """ get_tickers 리턴 리스트의 갯수가 다른 버그 발견, 1초 간격 3회 조회 후 길이가 긴 리스트를 티커리스트로 정한다 """
        codes = pyupbit.get_tickers(fiat="KRW")
        time.sleep(1)
        codes2 = pyupbit.get_tickers(fiat="KRW")
        codes = codes2 if len(codes2) > len(codes) else codes
        time.sleep(1)
        codes2 = pyupbit.get_tickers(fiat="KRW")
        codes = codes2 if len(codes2) > len(codes) else codes
        dict_tsbc = {}
        self.websQ_ticker = WebSocketManager('ticker', codes)
        while True:
            if not self.creceivQ.empty():
                data = self.creceivQ.get()
                self.UpdateJango(data)

            data = self.websQ_ticker.get()
            if data == 'ConnectionClosedError':
                self.windowQ.put([ui_num['C단순텍스트'], '시스템 명령 오류 알림 - WebsTicker 연결 끊김으로 다시 연결합니다.'])
                self.websQ_ticker = WebSocketManager('ticker', codes)
            else:
                code = data['code']
                t = data['trade_time']
                v = data['trade_volume']
                gubun = data['ask_bid']
                try:
                    pret = dict_tsbc[code][0]
                    bids = dict_tsbc[code][1]
                    asks = dict_tsbc[code][2]
                except KeyError:
                    pret = None
                    bids = 0
                    asks = 0
                if gubun == 'BID':
                    dict_tsbc[code] = [t, bids + float(v), asks]
                else:
                    dict_tsbc[code] = [t, bids, asks + float(v)]
                if t != pret:
                    c = data['trade_price']
                    o = data['opening_price']
                    h = data['high_price']
                    low = data['low_price']
                    per = round(data['signed_change_rate'] * 100, 2)
                    dm = data['acc_trade_price']
                    bids = dict_tsbc[code][1]
                    asks = dict_tsbc[code][2]
                    tbids = data['acc_bid_volume']
                    tasks = data['acc_ask_volume']
                    dt = data['trade_date'] + t
                    dict_tsbc[code] = [t, 0, 0]
                    data = [code, c, o, h, low, per, dm, bids, asks, tbids, tasks, dt, now()]
                    self.tick5Q.put(data)
                    if DICT_SET['업비트트레이더']:
                        injango = code in self.list_jang
                        self.cstgQ.put(data + [injango])
                        if injango:
                            self.coinQ.put([code, c])

    def UpdateJango(self, data):
        if data[0] == '잔고편입':
            if data[1] not in self.list_jang:
                self.list_jang.append(data[1])
        elif data[0] == '잔고청산':
            if data[1] in self.list_jang:
                self.list_jang.remove(data[1])


class WebsOrderbook(QThread):
    def __init__(self, qlist):
        """
                    0        1       2        3       4       5          6        7      8      9     10
        qlist = [windowQ, soundQ, query1Q, query2Q, teleQ, sreceivQ, creceivQ, stockQ, coinQ, sstgQ, cstgQ,
                 tick1Q, tick2Q, tick3Q, tick4Q, tick5Q]
                   11       12      13     14      15
        """
        super().__init__()
        self.windowQ = qlist[0]
        self.coinQ = qlist[8]
        self.cstgQ = qlist[10]
        self.tick5Q = qlist[15]
        self.websQ_order = None

    def run(self):
        """ get_tickers 리턴 리스트의 갯수가 다른 버그 발견, 1초 간격 3회 조회 후 길이가 긴 리스트를 티커리스트로 정한다 """
        codes = pyupbit.get_tickers(fiat="KRW")
        time.sleep(1)
        codes2 = pyupbit.get_tickers(fiat="KRW")
        codes = codes2 if len(codes2) > len(codes) else codes
        time.sleep(1)
        codes2 = pyupbit.get_tickers(fiat="KRW")
        codes = codes2 if len(codes2) > len(codes) else codes
        self.cstgQ.put(['관심종목', codes])
        self.websQ_order = WebSocketManager('orderbook', codes)
        while True:
            data = self.websQ_order.get()
            if data == 'ConnectionClosedError':
                self.windowQ.put([ui_num['C단순텍스트'], '시스템 명령 오류 알림 - WebsOrderbook 연결 끊김으로 다시 연결합니다.'])
                self.websQ_order = WebSocketManager('orderbook', codes)
            else:
                code = data['code']
                tsjr = data['total_ask_size']
                tbjr = data['total_bid_size']
                s5hg = data['orderbook_units'][4]['ask_price']
                s4hg = data['orderbook_units'][3]['ask_price']
                s3hg = data['orderbook_units'][2]['ask_price']
                s2hg = data['orderbook_units'][1]['ask_price']
                s1hg = data['orderbook_units'][0]['ask_price']
                b1hg = data['orderbook_units'][0]['bid_price']
                b2hg = data['orderbook_units'][1]['bid_price']
                b3hg = data['orderbook_units'][2]['bid_price']
                b4hg = data['orderbook_units'][3]['bid_price']
                b5hg = data['orderbook_units'][4]['bid_price']
                s5jr = data['orderbook_units'][4]['ask_size']
                s4jr = data['orderbook_units'][3]['ask_size']
                s3jr = data['orderbook_units'][2]['ask_size']
                s2jr = data['orderbook_units'][1]['ask_size']
                s1jr = data['orderbook_units'][0]['ask_size']
                b1jr = data['orderbook_units'][0]['bid_size']
                b2jr = data['orderbook_units'][1]['bid_size']
                b3jr = data['orderbook_units'][2]['bid_size']
                b4jr = data['orderbook_units'][3]['bid_size']
                b5jr = data['orderbook_units'][4]['bid_size']
                data = [code, tsjr, tbjr,
                        s5hg, s4hg, s3hg, s2hg, s1hg, b1hg, b2hg, b3hg, b4hg, b5hg,
                        s5jr, s4jr, s3jr, s2jr, s1jr, b1jr, b2jr, b3jr, b4jr, b5jr]
                self.tick5Q.put(data)
                if DICT_SET['업비트트레이더']:
                    self.cstgQ.put(data)
