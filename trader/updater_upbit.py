import os
import sys
import pandas as pd
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.setting import ui_num
from utility.static import now, timedelta_sec, timedelta_hour, strp_time, strf_time


class UpdaterUpbit:
    def __init__(self, windowQ, queryQ, tick2Q):
        self.windowQ = windowQ
        self.queryQ = queryQ
        self.tick2Q = tick2Q

        self.dict_df = {}                   # 틱데이터 저장용 딕셔너리 key: ticker, value: datafame
        self.dict_orderbook = {}            # 오더북 저장용 딕셔너리
        self.time_info = timedelta_sec(60)  # 틱데이터 저장주기 확인용
        self.Start()

    def Start(self):
        while True:
            data = self.tick2Q.get()
            if type(data) == list:
                self.UpdateTickData(data[0], data[1])
            else:
                self.UpdateOrderbook(data)

    def UpdateTickData(self, data_, receiv_time):
        ticker = data_['code']
        dt = data_['trade_date'] + data_['trade_time']
        dt = strf_time('%Y%m%d%H%M%S', timedelta_hour(9, strp_time('%Y%m%d%H%M%S', dt)))
        if ticker not in self.dict_orderbook.keys():
            return

        data = {
            '현재가': data_['trade_price'],
            '시가': data_['opening_price'],
            '고가': data_['high_price'],
            '저가': data_['low_price'],
            '등락율': round(data_['signed_change_rate'] * 100, 2),
            '누적거래대금': data_['acc_trade_price'],
            '매수수량': data_['매수수량'],
            '매도수량': data_['매도수량'],
            '누적매수량': data_['acc_bid_volume'],
            '누적매도량': data_['acc_ask_volume']
        }
        data.update(self.dict_orderbook[ticker])

        if ticker not in self.dict_df.keys():
            self.dict_df[ticker] = pd.DataFrame(data, index=[dt])
        else:
            self.dict_df[ticker].at[dt] = list(data.values())

        if now() > self.time_info:
            gap = (now() - receiv_time).total_seconds()
            self.windowQ.put([ui_num['C단순텍스트'], f'콜렉터 수신 기록 알림 - 수신시간과 기록시간의 차이는 [{gap}]초입니다.'])
            self.queryQ.put([4, self.dict_df])
            self.dict_df = {}
            self.time_info = timedelta_sec(60)

    def UpdateOrderbook(self, data):
        ticker = data['code']
        self.dict_orderbook[ticker] = {
            '매도호가2': data['orderbook_units'][1]['ask_price'],
            '매도호가1': data['orderbook_units'][0]['ask_price'],
            '매수호가1': data['orderbook_units'][0]['bid_price'],
            '매수호가2': data['orderbook_units'][1]['bid_price'],
            '매도잔량2': data['orderbook_units'][1]['ask_size'],
            '매도잔량1': data['orderbook_units'][0]['ask_size'],
            '매수잔량1': data['orderbook_units'][0]['bid_size'],
            '매수잔량2': data['orderbook_units'][1]['bid_size']
        }
