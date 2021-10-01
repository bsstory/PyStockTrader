import os
import sys
import numpy as np
import pandas as pd
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.static import now, timedelta_sec, strf_time
from utility.setting import columns_gj1, ui_num, DICT_SET


class StrategyStock:
    def __init__(self, qlist):
        """
        number      0        1       2      3       4       5       6      7      8      9       10
        qlist = [windowQ, soundQ, queryQ, teleQ, receivQ, stockQ, coinQ, sstgQ, cstgQ, tick1Q, tick2Q]
        """
        self.windowQ = qlist[0]
        self.soundQ = qlist[1]
        self.teleQ = qlist[3]
        self.stockQ = qlist[5]
        self.sstgQ = qlist[7]

        self.list_buy = []
        self.list_sell = []
        self.int_tujagm = 0

        self.dict_gsjm = {}     # key: 종목코드, value: 10시이전 DataFrame, 10시이후 list
        self.dict_time = {
            '관심종목': now(),
            '연산시간': now()
        }
        self.Start()

    def Start(self):
        while True:
            data = self.sstgQ.get()
            if type(data) == int:
                self.UpdateTotaljasan(data)
            elif type(data) == list:
                if len(data) == 2:
                    self.UpdateList(data[0], data[1])
                elif len(data) == 14:
                    self.BuyStrategy(data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7],
                                     data[8], data[9], data[10], data[11], data[12], data[13])
                elif len(data) == 7:
                    self.SellStrategy(data[0], data[1], data[2], data[3], data[4], data[5], data[6])
            elif data == '잔략프로세스종료':
                break

            if now() > self.dict_time['관심종목']:
                self.windowQ.put([ui_num['S관심종목'], self.dict_gsjm])
                self.dict_time['관심종목'] = timedelta_sec(1)

        self.windowQ.put([ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 트레이더를 종료합니다.'])
        if DICT_SET['알림소리1']:
            self.soundQ.put('주식 전략 연산 프로세스를 종료합니다.')
        self.teleQ.put('주식 전략 연산 프로세스를 종료하였습니다.')

    def UpdateTotaljasan(self, data):
        self.int_tujagm = data

    def UpdateList(self, gubun, code):
        if '조건진입' in gubun:
            if code not in self.dict_gsjm.keys():
                data = np.zeros((DICT_SET['평균시간1'] + 2, len(columns_gj1))).tolist()
                df = pd.DataFrame(data, columns=columns_gj1)
                df['체결시간'] = '090000'
                self.dict_gsjm[code] = df.copy()
            if gubun == '조건진입마지막':
                self.windowQ.put([ui_num['S관심종목'], self.dict_gsjm])
        elif gubun == '조건이탈':
            if code in self.dict_gsjm.keys():
                del self.dict_gsjm[code]
        elif gubun == '매수완료':
            if code in self.list_buy:
                self.list_buy.remove(code)
        elif gubun == '매도완료':
            if code in self.list_sell:
                self.list_sell.remove(code)

    def BuyStrategy(self, code, name, c, o, h, low, per, ch, dm, t, injango, vitimedown, vid5priceup, receivetime):
        if code not in self.dict_gsjm.keys():
            return

        hlm = round((h + low) / 2)
        hlmp = round((c / hlm - 1) * 100, 2)
        predm = self.dict_gsjm[code]['누적거래대금'][1]
        sm = 0 if predm == 0 else int(dm - predm)
        self.dict_gsjm[code] = self.dict_gsjm[code].shift(1)
        if self.dict_gsjm[code]['체결강도'][DICT_SET[f'평균시간1']] != 0.:
            avg_sm = int(self.dict_gsjm[code]['거래대금'][1:DICT_SET['평균시간1'] + 1].mean())
            avg_ch = round(self.dict_gsjm[code]['체결강도'][1:DICT_SET['평균시간1'] + 1].mean(), 2)
            high_ch = round(self.dict_gsjm[code]['체결강도'][1:DICT_SET['평균시간1'] + 1].max(), 2)
            self.dict_gsjm[code].at[DICT_SET['평균시간1'] + 1] = 0., 0., avg_sm, 0, avg_ch, high_ch, t
        self.dict_gsjm[code].at[0] = per, hlmp, sm, dm, ch, 0., t

        if self.dict_gsjm[code]['체결강도'][DICT_SET['평균시간1']] == 0:
            return
        if code in self.list_buy:
            return

        # 전략 비공개

        oc = int(self.int_tujagm / c)
        if oc > 0:
            self.list_buy.append(code)
            self.stockQ.put(['매수', code, name, c, oc])

        if now() > self.dict_time['연산시간']:
            gap = (now() - receivetime).total_seconds()
            self.windowQ.put([ui_num['S단순텍스트'], f'전략스 연산 시간 알림 - 수신시간과 연산시간의 차이는 [{gap}]초입니다.'])
            self.dict_time['연산시간'] = timedelta_sec(60)

    def SellStrategy(self, code, name, per, sp, jc, ch, c):
        if code not in self.dict_gsjm.keys():
            return
        if code in self.list_sell:
            return

        oc = 0
        """ 아래는 매도조건 예시 """
        if per >= 29 or sp <= -2 or sp >= 3:
            oc = jc

        # 전략 비공개

        if oc > 0:
            self.list_sell.append(code)
            self.stockQ.put(['매도', code, name, c, oc])
