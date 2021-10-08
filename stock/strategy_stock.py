import os
import sys
import sqlite3
import numpy as np
import pandas as pd
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.static import now, timedelta_sec
from utility.setting import columns_gj1, ui_num, DICT_SET, DB_STOCK_STRETEGY


class StrategyStock:
    def __init__(self, qlist):
        """
                    0        1       2        3       4       5          6        7      8      9     10
        qlist = [windowQ, soundQ, query1Q, query2Q, teleQ, sreceivQ, creceivQ, stockQ, coinQ, sstgQ, cstgQ,
                 tick1Q, tick2Q, tick3Q, tick4Q, tick5Q]
                   11       12      13     14      15
        """
        self.windowQ = qlist[0]
        self.soundQ = qlist[1]
        self.teleQ = qlist[4]
        self.stockQ = qlist[7]
        self.sstgQ = qlist[9]

        con = sqlite3.connect(DB_STOCK_STRETEGY)
        df = pd.read_sql('SELECT * FROM init', con).set_index('index')
        if len(df) > 0 and '현재전략' in df.index:
            self.init_var = df['전략코드']['현재전략']
        else:
            self.init_var = None

        df = pd.read_sql('SELECT * FROM buy', con).set_index('index')
        if len(df) > 0 and '현재전략' in df.index:
            self.buystrategy = df['전략코드']['현재전략']
        else:
            self.buystrategy = None

        df = pd.read_sql('SELECT * FROM sell', con).set_index('index')
        con.close()
        if len(df) > 0 and '현재전략' in df.index:
            self.sellstretegy = df['전략코드']['현재전략']
        else:
            self.sellstretegy = None

        if self.init_var is not None:
            try:
                exec(self.init_var, None, locals())
            except Exception as e:
                self.windowQ.put([ui_num['S단순텍스트'], f'전략스 설정 오류 알림 - __init__ {e}'])

        self.list_buy = []
        self.list_sell = []
        self.int_tujagm = 0

        self.dict_gsjm = {}     # key: 종목코드, value: DataFrame
        self.dict_hgjr = {}     # key: 종목코드, value: list
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
                elif len(data) == 26:
                    self.BuyStrategy(data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7], data[8],
                                     data[9], data[10], data[11], data[12], data[13], data[14], data[15], data[16],
                                     data[17], data[18], data[19], data[20], data[21], data[22], data[23], data[24],
                                     data[25])
                elif len(data) == 6:
                    self.SellStrategy(data[0], data[1], data[2], data[3], data[4], data[5])
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
        elif gubun == '조건이탈':
            if code in self.dict_gsjm.keys():
                del self.dict_gsjm[code]
        elif gubun in ['매수완료', '매수취소']:
            if code in self.list_buy:
                self.list_buy.remove(code)
        elif gubun in ['매도완료', '매도취소']:
            if code in self.list_sell:
                self.list_sell.remove(code)
        elif gubun == '매수전략':
            self.buystrategy = compile(code, '<string>', 'exec')
        elif gubun == '매도전략':
            self.sellstretegy = compile(code, '<string>', 'exec')
        elif gubun == '매수전략중지':
            self.buystrategy = None
        elif gubun == '매도전략중지':
            self.sellstretegy = None

    def BuyStrategy(self, 종목코드, 현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량,
                    VI해제시간, VI아래5호가, 매도총잔량, 매수총잔량, 매도호가2, 매도호가1, 매수호가1, 매수호가2,
                    매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 체결시간, 틱수신시간, 종목명, 잔고종목):
        if 종목코드 not in self.dict_gsjm.keys():
            return

        고저평균 = round((고가 + 저가) / 2)
        고저평균대비등락율 = round((현재가 / 고저평균 - 1) * 100, 2)
        직전당일거래대금 = self.dict_gsjm[종목코드]['당일거래대금'][0]
        초당거래대금 = 0 if 직전당일거래대금 == 0 else int(당일거래대금 - 직전당일거래대금)

        self.dict_gsjm[종목코드] = self.dict_gsjm[종목코드].shift(1)
        self.dict_gsjm[종목코드].at[0] = 등락율, 고저평균대비등락율, 초당거래대금, 당일거래대금, 체결강도, 0., 체결시간
        self.dict_hgjr[종목코드] = \
            [매도총잔량, 매수총잔량, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2]
        if self.dict_gsjm[종목코드]['체결강도'][DICT_SET[f'평균시간1']] != 0.:
            평균값인덱스 = DICT_SET['평균시간1'] + 1
            초당거래대금평균 = int(self.dict_gsjm[종목코드]['초당거래대금'][1:평균값인덱스].mean())
            체결강도평균 = round(self.dict_gsjm[종목코드]['체결강도'][1:평균값인덱스].mean(), 2)
            최고체결강도 = round(self.dict_gsjm[종목코드]['체결강도'][1:평균값인덱스].max(), 2)
            self.dict_gsjm[종목코드].at[평균값인덱스] = 0., 0., 초당거래대금평균, 0, 체결강도평균, 최고체결강도, 체결시간

            if 잔고종목:
                return
            if 종목코드 in self.list_buy:
                return

            매수 = True

            if self.buystrategy is not None:
                try:
                    exec(self.buystrategy, None, locals())
                except Exception as e:
                    self.windowQ.put([ui_num['S단순텍스트'], f'전략스 설정 오류 알림 - BuyStrategy {e}'])

        if now() > self.dict_time['연산시간']:
            gap = (now() - 틱수신시간).total_seconds()
            self.windowQ.put([ui_num['S단순텍스트'], f'전략스 연산 시간 알림 - 수신시간과 연산시간의 차이는 [{gap}]초입니다.'])
            self.dict_time['연산시간'] = timedelta_sec(60)

    def SellStrategy(self, 종목코드, 종목명, 수익률, 보유수량, 현재가, 매수시간):
        if 종목코드 not in self.dict_gsjm.keys() or 종목코드 not in self.dict_hgjr.keys():
            return
        if 종목코드 in self.list_sell:
            return
        if self.dict_gsjm[종목코드]['체결강도'][DICT_SET[f'평균시간1']] == 0.:
            return

        매도 = False
        평균값인덱스 = DICT_SET['평균시간1'] + 1
        등락율 = self.dict_gsjm[종목코드]['등락율'][0]
        체결강도 = self.dict_gsjm[종목코드]['체결강도'][0]
        고저평균대비등락율 = self.dict_gsjm[종목코드]['고저평균대비등락율'][0]
        초당거래대금평균 = self.dict_gsjm[종목코드]['초당거래대금'][평균값인덱스]
        체결강도평균 = self.dict_gsjm[종목코드]['체결강도'][평균값인덱스]
        최고체결강도 = self.dict_gsjm[종목코드]['체결강도'][평균값인덱스]
        매도총잔량, 매수총잔량, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2 = \
            self.dict_hgjr[종목코드]

        if self.sellstretegy is not None:
            try:
                exec(self.sellstretegy, None, locals())
            except Exception as e:
                self.windowQ.put([ui_num['S단순텍스트'], f'전략스 설정 오류 알림 - SellStrategy {e}'])
