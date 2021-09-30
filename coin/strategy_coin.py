import os
import sys
import numpy as np
import pandas as pd
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.setting import columns_gj1, ui_num, DICT_SET
from utility.static import now, timedelta_sec, strf_time, timedelta_hour


class StrategyCoin:
    def __init__(self, qlist):
        """
        number      0        1       2      3       4       5       6      7      8      9       10
        qlist = [windowQ, soundQ, queryQ, teleQ, receivQ, stockQ, coinQ, sstgQ, cstgQ, tick1Q, tick2Q]
        """
        self.windowQ = qlist[0]
        self.coinQ = qlist[6]
        self.cstgQ = qlist[8]

        self.list_buy = []
        self.list_sell = []
        self.int_tujagm = 0

        self.dict_gsjm = {}     # key: 종목코드, value: DataFrame
        self.dict_time = {
            '관심종목': now(),
            '연산시간': now()
        }
        self.Start()

    def Start(self):
        while True:
            data = self.cstgQ.get()
            if type(data) == int:
                self.UpdateTotaljasan(data)
            elif type(data) == list:
                if len(data) == 2:
                    self.UpdateList(data[0], data[1])
                elif len(data) == 12:
                    self.BuyStrategy(data[0], data[1], data[2], data[3], data[4], data[5], data[6],
                                     data[7], data[8], data[9], data[10], data[11])
                elif len(data) == 5:
                    self.SellStrategy(data[0], data[1], data[2], data[3], data[4])

            if now() > self.dict_time['관심종목']:
                self.windowQ.put([ui_num['C관심종목'], self.dict_gsjm])
                self.dict_time['관심종목'] = timedelta_sec(1)

    def UpdateTotaljasan(self, data):
        self.int_tujagm = data

    def UpdateList(self, gubun, tickers):
        if '관심종목초기화' in gubun:
            self.dict_gsjm = {}
            for ticker in tickers:
                data = np.zeros((DICT_SET['평균시간2'] + 2, len(columns_gj1))).tolist()
                df = pd.DataFrame(data, columns=columns_gj1)
                df['체결시간'] = strf_time('%H%M%S', timedelta_hour(-9))
                self.dict_gsjm[ticker] = df.copy()
        elif gubun == '매수완료':
            if tickers in self.list_buy:
                self.list_buy.remove(tickers)
        elif gubun == '매도완료':
            if tickers in self.list_sell:
                self.list_sell.remove(tickers)

    def BuyStrategy(self, ticker, c, h, low, per, dm, bid, ask, t, uuidnone, injango, receivetime):
        if ticker not in self.dict_gsjm.keys():
            return

        hlm = round((h + low) / 2)
        try:
            hlmp = round((c / hlm - 1) * 100, 2)
        except ZeroDivisionError:
            hlmp = 0.
        predm = self.dict_gsjm[ticker]['누적거래대금'][1]
        sm = 0 if predm == 0 else int(dm - predm)
        try:
            ch = round(bid / ask * 100, 2)
        except ZeroDivisionError:
            ch = 500.
        self.dict_gsjm[ticker] = self.dict_gsjm[ticker].shift(1)
        if len(self.dict_gsjm[ticker]) == DICT_SET['평균시간2'] + 2 and \
                self.dict_gsjm[ticker]['체결강도'][DICT_SET['평균시간2']] != 0.:
            avg_sm = int(self.dict_gsjm[ticker]['거래대금'][1:DICT_SET['평균시간2'] + 1].mean())
            avg_ch = round(self.dict_gsjm[ticker]['체결강도'][1:DICT_SET['평균시간2'] + 1].mean(), 2)
            high_ch = round(self.dict_gsjm[ticker]['체결강도'][1:DICT_SET['평균시간2'] + 1].max(), 2)
            self.dict_gsjm[ticker].at[DICT_SET['평균시간2'] + 1] = 0., 0., avg_sm, 0, avg_ch, high_ch, t
        self.dict_gsjm[ticker].at[0] = per, hlmp, sm, dm, ch, 0., t

        if self.dict_gsjm[ticker]['체결강도'][DICT_SET['평균시간2']] == 0:
            return
        if ticker in self.list_buy:
            return

        # 전략 비공개

        oc = int(self.int_tujagm / c)
        if oc > 0:
            self.list_buy.append(ticker)
            self.coinQ.put(['매수', ticker, c, oc])

        if now() > self.dict_time['연산시간']:
            gap = (now() - receivetime).total_seconds()
            self.windowQ.put([ui_num['C단순텍스트'], f'전략스 연산 시간 알림 - 수신시간과 연산시간의 차이는 [{gap}]초입니다.'])
            self.dict_time['연산시간'] = timedelta_sec(60)

    def SellStrategy(self, ticker, sp, jc, ch, c):
        if ticker in self.list_sell:
            return

        oc = 0
        """ 아래는 매도조건 예시 """
        if sp <= -2 or sp >= 3:
            oc = jc

        # 전략 비공개

        if oc > 0:
            self.list_sell.append(ticker)
            self.coinQ.put(['매도', ticker, c, oc])
