import os
import sys
import warnings
import numpy as np
import pandas as pd
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.setting import ui_num
from utility.static import now, strf_time, timedelta_sec
warnings.filterwarnings("ignore", category=np.VisibleDeprecationWarning)


class UpdaterKiwoom:
    def __init__(self, windowQ, queryQ, tick1Q):
        self.windowQ = windowQ
        self.queryQ = queryQ
        self.tick1Q = tick1Q

        self.dict_df = {}
        self.time_info = now()
        self.str_tday = strf_time('%Y%m%d')
        self.Start()

    def Start(self):
        while True:
            tick = self.tick1Q.get()
            if len(tick) != 2:
                self.UpdateTickData(tick[0], tick[1], tick[2], tick[3], tick[4], tick[5], tick[6], tick[7],
                                    tick[8], tick[9], tick[10], tick[11], tick[12], tick[13], tick[14],
                                    tick[15], tick[16], tick[17], tick[18], tick[19], tick[20], tick[21], tick[22])
            elif tick[0] == '틱데이터저장':
                self.SaveTickData(tick[1])

    def UpdateTickData(self, code, c, o, h, low, per, dm, ch, vp, bids, asks, vitime, vid5,
                       s2hg, s1hg, b1hg, b2hg, s2jr, s1jr, b1jr, b2jr, d, receiv_time):
        try:
            hlm = int(round((h + low) / 2))
            hlmp = round((c / hlm - 1) * 100, 2)
        except ZeroDivisionError:
            return
        d = self.str_tday + d
        if code not in self.dict_df.keys():
            self.dict_df[code] = pd.DataFrame(
                [[c, o, h, per, hlmp, dm, dm, ch, vp, bids, asks, vitime, vid5,
                  s2hg, s1hg, b1hg, b2hg, s2jr, s1jr, b1jr, b2jr]],
                columns=['현재가', '시가', '고가', '등락율', '고저평균대비등락율', '거래대금', '누적거래대금', '체결강도',
                         '전일거래량대비', '매수수량', '매도수량', 'VI발동시간', '상승VID5가격',
                         '매도호가2', '매도호가1', '매수호가1', '매수호가2',
                         '매도잔량2', '매도잔량1', '매수잔량1', '매수잔량2'],
                index=[d])
        else:
            sm = int(dm - self.dict_df[code]['누적거래대금'][-1])
            self.dict_df[code].at[d] = \
                c, o, h, per, hlmp, sm, dm, ch, vp, bids, asks, vitime, vid5,\
                s2hg, s1hg, b1hg, b2hg, s2jr, s1jr, b1jr, b2jr

        if now() > self.time_info:
            gap = (now() - receiv_time).total_seconds()
            self.windowQ.put([ui_num['S단순텍스트'], f'콜렉터 수신 기록 알림 - 수신시간과 기록시간의 차이는 [{gap}]초입니다.'])
            self.time_info = timedelta_sec(60)

    def SaveTickData(self, codes):
        for code in list(self.dict_df.keys()):
            columns = ['현재가', '시가', '고가', '거래대금', '누적거래대금', '상승VID5가격', '매수수량', '매도수량',
                       '매도호가2', '매도호가1', '매수호가1', '매수호가2', '매도잔량2', '매도잔량1', '매수잔량1', '매수잔량2']
            self.dict_df[code][columns] = self.dict_df[code][columns].astype(int)
        """
        당일 거래목록만 저장하기
        for code in list(self.dict_df.keys()):
            if code in codes:
                columns = ['현재가', '시가', '고가', '거래대금', '누적거래대금', '상승VID5가격', '매수수량', '매도수량',
                           '매도호가2', '매도호가1', '매수호가1', '매수호가2', '매도잔량2', '매도잔량1', '매수잔량1', '매수잔량2']
                self.dict_df[code][columns] = self.dict_df[code][columns].astype(int)
            else:
                del self.dict_df[code]
        """
        self.queryQ.put([3, self.dict_df])
        sys.exit()
