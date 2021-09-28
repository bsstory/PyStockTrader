import os
import sys
import time
import pythoncom
from PyQt5 import QtWidgets
from threading import Lock
from PyQt5.QAxContainer import QAxWidget
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.static import *
from utility.setting import *


class TraderKiwoom:
    app = QtWidgets.QApplication(sys.argv)

    def __init__(self, windowQ, stockQ, collectorQ, sstgQ, soundQ, queryQ, teleQ):
        self.windowQ = windowQ
        self.stockQ = stockQ
        self.collectorQ = collectorQ
        self.sstgQ = sstgQ
        self.soundQ = soundQ
        self.queryQ = queryQ
        self.teleQ = teleQ
        self.lock = Lock()

        self.dict_name = {}     # key: 종목코드, value: 종목명
        self.dict_sghg = {}     # key: 종목코드, value: [상한가, 하한가]
        self.dict_vipr = {}     # key: 종목코드, value: [갱신여부, 발동시간+5초, 해제시간+180초, UVI, DVI, UVID5]
        self.dict_cond = {}     # key: 조건검색식번호, value: 조건검색식명
        self.dict_hoga = {}     # key: 호가창번호, value: [종목코드, 갱신여부, 호가잔고(DataFrame)]
        self.dict_chat = {}     # key: UI번호, value: 종목코드
        self.dict_gsjm = {}     # key: 종목코드, value: 마지막체결시간
        self.dict_df = {
            '실현손익': pd.DataFrame(columns=columns_tt),
            '거래목록': pd.DataFrame(columns=columns_td),
            '잔고평가': pd.DataFrame(columns=columns_tj),
            '잔고목록': pd.DataFrame(columns=columns_jg),
            '체결목록': pd.DataFrame(columns=columns_cj),
            'TRDF': pd.DataFrame(columns=[])
        }
        self.dict_intg = {
            '장운영상태': 1,
            '예수금': 0,
            '추정예수금': 0,
            '추정예탁자산': 0,
            '종목당투자금': 0
        }
        self.dict_strg = {
            '당일날짜': strf_time('%Y%m%d'),
            '계좌번호': ''
        }
        self.dict_bool = {
            '로그인': False,
            'TR수신': False,
            'TR다음': False,
            'CD수신': False,
            'CR수신': False
        }
        remaintime = (strp_time('%Y%m%d%H%M%S', self.dict_strg['당일날짜'] + '090100') - now()).total_seconds()
        self.exit_time = timedelta_sec(remaintime) if remaintime > 0 else timedelta_sec(600)
        self.tdtj_time = now()
        self.dict_item = None
        self.list_trcd = None
        self.list_kosd = None
        self.list_buy = []
        self.list_sell = []

        self.ocx = QAxWidget('KHOPENAPI.KHOpenAPICtrl.1')
        self.ocx.OnEventConnect.connect(self.OnEventConnect)
        self.ocx.OnReceiveTrData.connect(self.OnReceiveTrData)
        self.ocx.OnReceiveRealData.connect(self.OnReceiveRealData)
        self.ocx.OnReceiveChejanData.connect(self.OnReceiveChejanData)
        self.Start()

    def Start(self):
        self.LoadDatabase()
        self.CommConnect()
        self.EventLoop()

    def LoadDatabase(self):
        con = sqlite3.connect(DB_TRADELIST)
        df = pd.read_sql(f"SELECT * FROM s_chegeollist WHERE 체결시간 LIKE '{self.dict_strg['당일날짜']}%'", con)
        self.dict_df['체결목록'] = df.set_index('index').sort_values(by=['체결시간'], ascending=False)

        df = pd.read_sql(f"SELECT * FROM s_tradelist WHERE 체결시간 LIKE '{self.dict_strg['당일날짜']}%'", con)
        self.dict_df['거래목록'] = df.set_index('index').sort_values(by=['체결시간'], ascending=False)

        df = pd.read_sql(f'SELECT * FROM s_jangolist', con)
        self.dict_df['잔고목록'] = df.set_index('index').sort_values(by=['매입금액'], ascending=False)
        con.close()

        if len(self.dict_df['체결목록']) > 0:
            self.windowQ.put([ui_num['S체결목록'], self.dict_df['체결목록']])
        if len(self.dict_df['거래목록']) > 0:
            self.windowQ.put([ui_num['C거래목록'], self.dict_df['거래목록']])
        if len(self.dict_df['잔고목록']) > 0:
            for code in self.dict_df['잔고목록'].index:
                self.stockQ.put([sn_jscg, code, '10;12;14;30;228', 1])
                self.collectorQ.put(f'잔고편입 {code}')

        self.windowQ.put([ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 데이터베이스 정보 불러오기 완료'])

    def CommConnect(self):
        self.ocx.dynamicCall('CommConnect()')
        while not self.dict_bool['로그인']:
            pythoncom.PumpWaitingMessages()

        self.dict_strg['계좌번호'] = self.ocx.dynamicCall('GetLoginInfo(QString)', 'ACCNO').split(';')[0]

        self.list_kosd = self.GetCodeListByMarket('10')
        list_code = self.GetCodeListByMarket('0') + self.list_kosd
        dict_code = {}
        for code in list_code:
            name = self.GetMasterCodeName(code)
            self.dict_name[code] = name
            dict_code[name] = code

        self.windowQ.put([ui_num['S종목명딕셔너리'], self.dict_name])

        self.windowQ.put([ui_num['S로그텍스트'], '시스템 명령 실행 알림 - OpenAPI 로그인 완료'])
        if DICT_SET['알림소리1']:
            self.soundQ.put('키움증권 오픈에이피아이에 로그인하였습니다.')

    def EventLoop(self):
        int_time = int(strf_time('%H%M%S'))
        self.GetAccountjanGo()
        self.OperationRealreg()
        self.ViRealreg()
        if int_time > 90000:
            self.dict_intg['장운영상태'] = 3
        while True:
            if not self.stockQ.empty():
                work = self.stockQ.get()
                if type(work) == list:
                    if len(work) == 10:
                        self.SendOrder(work)
                    elif len(work) == 5:
                        self.BuySell(work[0], work[1], work[2], work[3], work[4])
                        continue
                    elif len(work) in [2, 4]:
                        self.UpdateRealreg(work)
                        continue
                elif type(work) == str:
                    self.RunWork(work)

            if self.dict_intg['장운영상태'] == 1 and now() > self.exit_time:
                break

            if int_time < DICT_SET['잔고청산'] <= int(strf_time('%H%M%S')):
                self.JangoChungsan()
            if int_time < DICT_SET['전략종료'] <= int(strf_time('%H%M%S')):
                self.AllRemoveRealreg()
                self.SaveDatabase()
                break

            if now() > self.tdtj_time:
                self.UpdateTotaljango()
                self.tdtj_time = timedelta_sec(1)

            time_loop = timedelta_sec(0.25)
            while now() < time_loop:
                pythoncom.PumpWaitingMessages()
                time.sleep(0.0001)

            int_time = int(strf_time('%H%M%S'))

        self.windowQ.put([ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 트레이더를 종료합니다.'])
        if DICT_SET['알림소리1']:
            self.soundQ.put('주식 트레이더를 종료합니다.')
        self.teleQ.put('주식 트레이더를 종료하였습니다.')
        sys.exit()

    def SendOrder(self, order):
        name = order[-1]
        del order[-1]
        ret = self.ocx.dynamicCall(
            'SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)', order)
        if ret != 0:
            self.windowQ.put([ui_num['S로그텍스트'], f'시스템 명령 오류 알림 - {name} {order[5]}주 {order[0]} 주문 실패'])

    def BuySell(self, gubun, code, name, c, oc):
        if gubun == '매수':
            if self.dict_intg['추정예수금'] < oc * c:
                cond = (self.dict_df['체결목록']['주문구분'] == '시드부족') & (self.dict_df['체결목록']['종목명'] == name)
                df = self.dict_df['체결목록'][cond]
                if len(df) == 0 or \
                        (len(df) > 0 and now() > timedelta_sec(180, strp_time('%Y%m%d%H%M%S%f', df['체결시간'][0]))):
                    self.Order('시드부족', code, name, c, oc)
                return

        self.Order(gubun, code, name, c, oc)

    def Order(self, gubun, code, name, c, oc):
        on = 0
        if gubun == '매수':
            self.dict_intg['추정예수금'] -= oc * c
            self.list_buy.append(code)
            on = 1
        elif gubun == '매도':
            self.list_sell.append(code)
            on = 2

        if DICT_SET['모의투자1'] or gubun == '시드부족':
            self.UpdateChejanData(code, name, '체결', gubun, c, c, oc, 0,
                                  strf_time('%Y%m%d%H%M%S%f'), strf_time('%Y%m%d%H%M%S%f'))
        else:
            self.stockQ.put([gubun, '4989', self.dict_strg['계좌번호'], on, code, oc, 0, '03', '', name])

    def UpdateRealreg(self, rreg):
        name = ''
        if rreg[1] == 'ALL':
            name = 'ALL'
        elif ';' in rreg[1]:
            count = len(rreg[1].split(';'))
            name = f'종목갯수 {count}'
        elif rreg[1] != ' ':
            name = self.dict_name[rreg[1]]

        sn = rreg[0]
        if len(rreg) == 2:
            self.ocx.dynamicCall('SetRealRemove(QString, QString)', rreg)
            self.windowQ.put([ui_num['S로그텍스트'], f'실시간 알림 중단 완료 - [{sn}] {name}'])
        elif len(rreg) == 4:
            ret = self.ocx.dynamicCall('SetRealReg(QString, QString, QString, QString)', rreg)
            result = '완료' if ret == 0 else '실패'
            if sn == sn_oper:
                self.windowQ.put([ui_num['S로그텍스트'], f'실시간 알림 등록 {result} - 장운영시간 [{sn}]'])
            else:
                self.windowQ.put([ui_num['S로그텍스트'], f'실시간 알림 등록 {result} - [{sn}] {name}'])

    def RunWork(self, work):
        if work == '장운영상태':
            if self.dict_intg['장운영상태'] != 3:
                self.dict_intg['장운영상태'] = 3
        elif work == '/당일체결목록':
            if len(self.dict_df['체결목록']) > 0:
                self.teleQ.put(self.dict_df['체결목록'])
            else:
                self.teleQ.put('현재는 거래목록이 없습니다.')
        elif work == '/당일거래목록':
            if len(self.dict_df['거래목록']) > 0:
                self.teleQ.put(self.dict_df['거래목록'])
            else:
                self.teleQ.put('현재는 거래목록이 없습니다.')
        elif work == '/계좌잔고평가':
            if len(self.dict_df['잔고목록']) > 0:
                self.teleQ.put(self.dict_df['잔고목록'])
            else:
                self.teleQ.put('현재는 잔고목록이 없습니다.')
        elif work == '/잔고청산주문':
            self.AllRemoveRealreg()
            self.JangoChungsan()

    def GetAccountjanGo(self):
        jggm = 0
        pggm = 0
        sigm = 0
        if len(self.dict_df['잔고목록']) > 0:
            jggm = self.dict_df['잔고목록']['매입금액'].sum()
            pggm = self.dict_df['잔고목록']['평가금액'].sum()
        if len(self.dict_df['거래목록']) > 0:
            sigm = self.dict_df['거래목록']['수익금'].sum()

        while True:
            df = self.Block_Request('opw00004', 계좌번호=self.dict_strg['계좌번호'], 비밀번호='', 상장폐지조회구분=0,
                                    비밀번호입력매체구분='00', output='계좌평가현황', next=0)
            if df['D+2추정예수금'][0] != '':
                if DICT_SET['모의투자1']:
                    self.dict_intg['예수금'] = 100000000 - jggm + sigm
                else:
                    self.dict_intg['예수금'] = int(df['D+2추정예수금'][0])
                self.dict_intg['추정예수금'] = self.dict_intg['예수금']
                break
            else:
                self.windowQ.put([ui_num['S로그텍스트'], '시스템 명령 오류 알림 - 오류가 발생하여 계좌평가현황을 재조회합니다.'])
                time.sleep(3.35)

        while True:
            df = self.Block_Request('opw00018', 계좌번호=self.dict_strg['계좌번호'], 비밀번호='', 비밀번호입력매체구분='00',
                                    조회구분=2, output='계좌평가결과', next=0)
            if df['추정예탁자산'][0] != '':
                if DICT_SET['모의투자1']:
                    self.dict_intg['추정예탁자산'] = self.dict_intg['예수금'] + pggm
                else:
                    self.dict_intg['추정예탁자산'] = int(df['추정예탁자산'][0])

                self.dict_intg['종목당투자금'] = int(self.dict_intg['추정예탁자산'] * 0.99 / DICT_SET['최대매수종목수1'])
                self.sstgQ.put(self.dict_intg['종목당투자금'])

                if DICT_SET['모의투자1']:
                    self.dict_df['잔고평가'].at[self.dict_strg['당일날짜']] = \
                        self.dict_intg['추정예탁자산'], self.dict_intg['예수금'], 0, 0, 0, 0, 0
                else:
                    tsp = float(int(df['총수익률(%)'][0]) / 100)
                    tsg = int(df['총평가손익금액'][0])
                    tbg = int(df['총매입금액'][0])
                    tpg = int(df['총평가금액'][0])
                    self.dict_df['잔고평가'].at[self.dict_strg['당일날짜']] = \
                        self.dict_intg['추정예탁자산'], self.dict_intg['예수금'], 0, tsp, tsg, tbg, tpg
                self.windowQ.put([ui_num['S잔고평가'], self.dict_df['잔고평가']])
                break
            else:
                self.windowQ.put([ui_num['S로그텍스트'], '시스템 명령 오류 알림 - 오류가 발생하여 계좌평가결과를 재조회합니다.'])
                time.sleep(3.35)

        if len(self.dict_df['거래목록']) > 0:
            self.UpdateTotaltradelist(first=True)

    def OperationRealreg(self):
        self.stockQ.put([sn_oper, ' ', '215;20;214', 0])

    def ViRealreg(self):
        self.Block_Request('opt10054', 시장구분='000', 장전구분='1', 종목코드='', 발동구분='1', 제외종목='111111011',
                           거래량구분='0', 거래대금구분='0', 발동방향='0', output='발동종목', next=0)
        self.windowQ.put([ui_num['S로그텍스트'], '시스템 명령 실행 알림 - VI발동해제 등록 완료'])
        self.windowQ.put([ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 시스템 시작 완료'])

    def JangoChungsan(self):
        if len(self.dict_df['잔고목록']) > 0:
            for code in self.dict_df['잔고목록'].index:
                if code in self.list_sell:
                    continue
                c = self.dict_df['잔고목록']['현재가'][code]
                oc = self.dict_df['잔고목록']['보유수량'][code]
                name = self.dict_name[code]
                if DICT_SET['모의투자1']:
                    self.list_sell.append(code)
                    self.UpdateChejanData(code, name, '체결', '매도', c, c, oc, 0,
                                          strf_time('%Y%m%d%H%M%S%f'), strf_time('%Y%m%d%H%M%S%f'))
                else:
                    self.Order('매도', code, name, c, oc)
        if DICT_SET['알림소리1']:
            self.soundQ.put('잔고청산 주문을 전송하였습니다.')
        self.windowQ.put([ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 잔고청산 주문 완료'])

    def AllRemoveRealreg(self):
        self.stockQ.put(['ALL', 'ALL'])
        if DICT_SET['알림소리1']:
            self.soundQ.put('실시간 데이터의 수신을 중단하였습니다.')
        self.windowQ.put([ui_num['S로그텍스트'], f'시스템 명령 실행 알림 - 실시간 데이터 중단 완료'])

    def SaveDatabase(self):
        if len(self.dict_df['거래목록']) > 0:
            df = self.dict_df['실현손익'][['총매수금액', '총매도금액', '총수익금액', '총손실금액', '수익률', '수익금합계']].copy()
            self.queryQ.put([2, df, 's_totaltradelist', 'append'])
        if DICT_SET['알림소리1']:
            self.soundQ.put('데이터베이스를 저장하였습니다.')
        self.windowQ.put([ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 데이터베이스 저장 완료'])

    @thread_decorator
    def UpdateTotaljango(self):
        if len(self.dict_df['잔고목록']) > 0:
            tsg = self.dict_df['잔고목록']['평가손익'].sum()
            tbg = self.dict_df['잔고목록']['매입금액'].sum()
            tpg = self.dict_df['잔고목록']['평가금액'].sum()
            bct = len(self.dict_df['잔고목록'])
            tsp = round(tsg / tbg * 100, 2)
            ttg = self.dict_intg['예수금'] + tpg
            self.dict_df['잔고평가'].at[self.dict_strg['당일날짜']] = \
                ttg, self.dict_intg['예수금'], bct, tsp, tsg, tbg, tpg
        else:
            self.dict_df['잔고평가'].at[self.dict_strg['당일날짜']] = \
                self.dict_intg['예수금'], self.dict_intg['예수금'], 0, 0.0, 0, 0, 0
        self.windowQ.put([ui_num['S잔고목록'], self.dict_df['잔고목록']])
        self.windowQ.put([ui_num['S잔고평가'], self.dict_df['잔고평가']])

    def OnEventConnect(self, err_code):
        if err_code == 0:
            self.dict_bool['로그인'] = True

    def OnReceiveTrData(self, screen, rqname, trcode, record, nnext):
        if screen == '' and record == '':
            return
        if 'ORD' in trcode:
            return

        items = None
        self.dict_bool['TR다음'] = True if nnext == '2' else False
        for output in self.dict_item['output']:
            record = list(output.keys())[0]
            items = list(output.values())[0]
            if record == self.dict_strg['TR명']:
                break
        rows = self.ocx.dynamicCall('GetRepeatCnt(QString, QString)', trcode, rqname)
        if rows == 0:
            rows = 1
        df2 = []
        for row in range(rows):
            row_data = []
            for item in items:
                data = self.ocx.dynamicCall('GetCommData(QString, QString, int, QString)', trcode, rqname, row, item)
                row_data.append(data.strip())
            df2.append(row_data)
        df = pd.DataFrame(data=df2, columns=items)
        self.dict_df['TRDF'] = df
        self.dict_bool['TR수신'] = True

    def OnReceiveRealData(self, code, realtype, realdata):
        if realdata == '':
            return

        if realtype == '장시작시간':
            try:
                self.dict_intg['장운영상태'] = int(self.GetCommRealData(code, 215))
                current = self.GetCommRealData(code, 20)
            except Exception as e:
                self.windowQ.put([ui_num['S로그텍스트'], f'OnReceiveRealData 장시작시간 {e}'])
            else:
                self.OperationAlert(current)
        elif realtype == 'VI발동/해제':
            try:
                code = self.GetCommRealData(code, 9001).strip('A').strip('Q')
                gubun = self.GetCommRealData(code, 9068)
                name = self.dict_name[code]
            except Exception as e:
                self.windowQ.put([ui_num['S로그텍스트'], f'OnReceiveRealData VI발동/해제 {e}'])
            else:
                if gubun == '1' and \
                        (code not in self.dict_vipr.keys() or
                         (self.dict_vipr[code][0] and now() > self.dict_vipr[code][1])):
                    self.UpdateViPrice(code, name)
        elif realtype == '주식체결':
            try:
                c = abs(int(self.GetCommRealData(code, 10)))
                o = abs(int(self.GetCommRealData(code, 16)))
                per = float(self.GetCommRealData(code, 12))
                ch = float(self.GetCommRealData(code, 228))
                name = self.dict_name[code]
            except Exception as e:
                self.windowQ.put([ui_num['S로그텍스트'], f'OnReceiveRealData 주식체결 {e}'])
            else:
                if self.dict_intg['장운영상태'] == 3:
                    if code not in self.dict_vipr.keys():
                        self.InsertViPrice(code, o)
                    elif not self.dict_vipr[code][0] and now() > self.dict_vipr[code][1]:
                        self.UpdateViPrice(code, c)
                    if code in self.dict_df['잔고목록'].index:
                        self.UpdateJango(code, name, c, per, ch)

    @thread_decorator
    def OperationAlert(self, current):
        if DICT_SET['알림소리1']:
            if current == '084000':
                self.soundQ.put('장시작 20분 전입니다.')
            elif current == '085000':
                self.soundQ.put('장시작 10분 전입니다.')
            elif current == '085500':
                self.soundQ.put('장시작 5분 전입니다.')
            elif current == '085900':
                self.soundQ.put('장시작 1분 전입니다.')
            elif current == '085930':
                self.soundQ.put('장시작 30초 전입니다.')
            elif current == '085940':
                self.soundQ.put('장시작 20초 전입니다.')
            elif current == '085950':
                self.soundQ.put('장시작 10초 전입니다.')
            elif current == '090000':
                self.soundQ.put(f"{self.dict_strg['당일날짜'][:4]}년 {self.dict_strg['당일날짜'][4:6]}월 "
                                f"{self.dict_strg['당일날짜'][6:]}일 장이 시작되었습니다.")
            elif current == '152000':
                self.soundQ.put('장마감 10분 전입니다.')
            elif current == '152500':
                self.soundQ.put('장마감 5분 전입니다.')
            elif current == '152900':
                self.soundQ.put('장마감 1분 전입니다.')
            elif current == '152930':
                self.soundQ.put('장마감 30초 전입니다.')
            elif current == '152940':
                self.soundQ.put('장마감 20초 전입니다.')
            elif current == '152950':
                self.soundQ.put('장마감 10초 전입니다.')
            elif current == '153000':
                self.soundQ.put(f"{self.dict_strg['당일날짜'][:4]}년 {self.dict_strg['당일날짜'][4:6]}월 "
                                f"{self.dict_strg['당일날짜'][6:]}일 장이 종료되었습니다.")

    def InsertViPrice(self, code, o):
        uvi, dvi, uvid5 = self.GetVIPrice(code, o)
        self.dict_vipr[code] = [True, timedelta_sec(-180), timedelta_sec(-180), uvi, dvi, uvid5]

    def GetVIPrice(self, code, std_price):
        uvi = std_price * 1.1
        x = self.GetHogaunit(code, uvi)
        if uvi % x != 0:
            uvi = uvi + (x - uvi % x)
        uvid5 = uvi - x * 5
        dvi = std_price * 0.9
        x = self.GetHogaunit(code, dvi)
        if dvi % x != 0:
            dvi = dvi - dvi % x
        return int(uvi), int(dvi), int(uvid5)

    def GetHogaunit(self, code, price):
        if price < 1000:
            x = 1
        elif 1000 <= price < 5000:
            x = 5
        elif 5000 <= price < 10000:
            x = 10
        elif 10000 <= price < 50000:
            x = 50
        elif code in self.list_kosd:
            x = 100
        elif 50000 <= price < 100000:
            x = 100
        elif 100000 <= price < 500000:
            x = 500
        else:
            x = 1000
        return x

    def UpdateViPrice(self, code, key):
        if type(key) == str:
            try:
                self.dict_vipr[code][:3] = False, timedelta_sec(5), timedelta_sec(180)
            except KeyError:
                self.dict_vipr[code] = [False, timedelta_sec(5), timedelta_sec(180), 0, 0, 0]
            self.stockQ.put([sn_vijc, code, '10;12;14;30;228', 1])
        elif type(key) == int:
            uvi, dvi, uvid5 = self.GetVIPrice(code, key)
            self.dict_vipr[code] = [True, now(), timedelta_sec(180), uvi, dvi, uvid5]
            self.stockQ.put([sn_vijc, code])

    def UpdateJango(self, code, name, c, per, ch):
        self.lock.acquire()
        prec = self.dict_df['잔고목록']['현재가'][code]
        if prec != c:
            bg = self.dict_df['잔고목록']['매입금액'][code]
            jc = int(self.dict_df['잔고목록']['보유수량'][code])
            pg, sg, sp = self.GetPgSgSp(bg, jc * c)
            columns = ['현재가', '수익률', '평가손익', '평가금액']
            self.dict_df['잔고목록'].at[code, columns] = c, sp, sg, pg
            self.sstgQ.put([code, name, per, sp, jc, ch, c])
        self.lock.release()

    # noinspection PyMethodMayBeStatic
    def GetPgSgSp(self, bg, cg):
        gtexs = cg * 0.0023
        gsfee = cg * 0.00015
        gbfee = bg * 0.00015
        texs = gtexs - (gtexs % 1)
        sfee = gsfee - (gsfee % 10)
        bfee = gbfee - (gbfee % 10)
        pg = int(cg - texs - sfee - bfee)
        sg = pg - bg
        sp = round(sg / bg * 100, 2)
        return pg, sg, sp

    def OnReceiveChejanData(self, gubun, itemcnt, fidlist):
        if gubun != '0' and itemcnt != '' and fidlist != '':
            return
        if DICT_SET['모의투자1']:
            return
        on = self.GetChejanData(9203)
        if on == '':
            return

        try:
            code = self.GetChejanData(9001).strip('A')
            name = self.dict_name[code]
            ot = self.GetChejanData(913)
            og = self.GetChejanData(905)[1:]
            op = int(self.GetChejanData(901))
            oc = int(self.GetChejanData(900))
            omc = int(self.GetChejanData(902))
            dt = self.dict_strg['당일날짜'] + self.GetChejanData(908)
        except Exception as e:
            self.windowQ.put([ui_num['S로그텍스트'], f'OnReceiveChejanData {e}'])
        else:
            try:
                cp = int(self.GetChejanData(910))
            except ValueError:
                cp = 0
            self.UpdateChejanData(code, name, ot, og, op, cp, oc, omc, on, dt)

    @thread_decorator
    def UpdateChejanData(self, code, name, ot, og, op, cp, oc, omc, on, dt):
        self.lock.acquire()
        if ot == '체결' and omc == 0 and cp != 0:
            if og == '매수':
                self.dict_intg['예수금'] -= oc * cp
                self.dict_intg['추정예수금'] = self.dict_intg['예수금']
                self.UpdateChegeoljango(code, name, og, oc, cp)
                self.windowQ.put([ui_num['S로그텍스트'], f'매매 시스템 체결 알림 - {name} {oc}주 {og}'])
            elif og == '매도':
                bp = self.dict_df['잔고목록']['매입가'][code]
                bg = bp * oc
                pg, sg, sp = self.GetPgSgSp(bg, oc * cp)
                self.dict_intg['예수금'] += pg
                self.dict_intg['추정예수금'] = self.dict_intg['예수금']
                self.UpdateChegeoljango(code, name, og, oc, cp)
                self.UpdateTradelist(name, oc, sp, sg, bg, pg, on)
                self.windowQ.put([ui_num['S로그텍스트'], f"매매 시스템 체결 알림 - {name} {oc}주 {og}, 수익률 {sp}% 수익금{format(sg, ',')}원"])
            elif og == '시드부족':
                self.sstgQ.put(['매수완료', code])
        self.UpdateChegeollist(name, og, oc, omc, op, cp, dt, on)
        self.lock.release()

    def UpdateChegeoljango(self, code, name, og, oc, cp):
        if og == '매수':
            if code not in self.dict_df['잔고목록'].index:
                bg = oc * cp
                pg, sg, sp = self.GetPgSgSp(bg, oc * cp)
                self.dict_df['잔고목록'].at[code] = name, cp, cp, sp, sg, bg, pg, oc
                self.stockQ.put([sn_jscg, code, '10;12;14;30;228', 1])
                self.collectorQ.put(f'잔고편입 {code}')
            else:
                jc = self.dict_df['잔고목록']['보유수량'][code]
                bg = self.dict_df['잔고목록']['매입금액'][code]
                jc = jc + oc
                bg = bg + oc * cp
                bp = int(bg / jc)
                pg, sg, sp = self.GetPgSgSp(bg, jc * cp)
                self.dict_df['잔고목록'].at[code] = name, bp, cp, sp, sg, bg, pg, jc

        elif og == '매도':
            jc = self.dict_df['잔고목록']['보유수량'][code]
            if jc - oc == 0:
                self.dict_df['잔고목록'].drop(index=code, inplace=True)
                self.stockQ.put([sn_jscg, code])
                self.collectorQ.put(f'잔고청산 {code}')
            else:
                bp = self.dict_df['잔고목록']['매입가'][code]
                jc = jc - oc
                bg = jc * bp
                pg, sg, sp = self.GetPgSgSp(bg, jc * cp)
                self.dict_df['잔고목록'].at[code] = name, bp, cp, sp, sg, bg, pg, jc

        columns = ['매입가', '현재가', '평가손익', '매입금액']
        self.dict_df['잔고목록'][columns] = self.dict_df['잔고목록'][columns].astype(int)
        self.dict_df['잔고목록'].sort_values(by=['매입금액'], inplace=True)
        self.queryQ.put([2, self.dict_df['잔고목록'], 's_jangolist', 'replace'])
        if DICT_SET['알림소리1']:
            self.soundQ.put(f'{name} {oc}주를 {og}하였습니다')

        if og == '매수':
            self.sstgQ.put(['매수완료', code])
            self.list_buy.remove(code)
        elif og == '매도':
            self.sstgQ.put(['매도완료', code])
            self.list_sell.remove(code)

    def UpdateTradelist(self, name, oc, sp, sg, bg, pg, on):
        d = strf_time('%Y%m%d%H%M%S')
        if DICT_SET['모의투자1'] and len(self.dict_df['거래목록']) > 0:
            if on in self.dict_df['거래목록'].index:
                while on in self.dict_df['거래목록'].index:
                    on = str(int(on) + 1)
            if d in self.dict_df['거래목록']['체결시간'].values:
                while d in self.dict_df['거래목록']['체결시간'].values:
                    d = str(int(d) + 1)

        self.dict_df['거래목록'].at[on] = name, bg, pg, oc, sp, sg, d
        self.dict_df['거래목록'].sort_values(by=['체결시간'], ascending=False, inplace=True)
        self.windowQ.put([ui_num['S거래목록'], self.dict_df['거래목록']])

        df = pd.DataFrame([[name, bg, pg, oc, sp, sg, d]], columns=columns_td, index=[on])
        self.queryQ.put([2, df, 's_tradelist', 'append'])
        self.UpdateTotaltradelist()

    def UpdateTotaltradelist(self, first=False):
        tsg = self.dict_df['거래목록']['매도금액'].sum()
        tbg = self.dict_df['거래목록']['매수금액'].sum()
        tsig = self.dict_df['거래목록'][self.dict_df['거래목록']['수익금'] > 0]['수익금'].sum()
        tssg = self.dict_df['거래목록'][self.dict_df['거래목록']['수익금'] < 0]['수익금'].sum()
        sg = self.dict_df['거래목록']['수익금'].sum()
        sp = round(sg / self.dict_intg['추정예탁자산'] * 100, 2)
        tdct = len(self.dict_df['거래목록'])
        self.dict_df['실현손익'] = pd.DataFrame([[tdct, tbg, tsg, tsig, tssg, sp, sg]],
                                            columns=columns_tt, index=[self.dict_strg['당일날짜']])
        self.windowQ.put([ui_num['S실현손익'], self.dict_df['실현손익']])

        if not first:
            self.teleQ.put(
                f"거래횟수 {len(self.dict_df['거래목록'])}회 / 총매수금액 {format(int(tbg), ',')}원 / "
                f"총매도금액 {format(int(tsg), ',')}원 / 총수익금액 {format(int(tsig), ',')}원 / "
                f"총손실금액 {format(int(tssg), ',')}원 / 수익률 {sp}% / 수익금합계 {format(int(sg), ',')}원")

    def UpdateChegeollist(self, name, og, oc, omc, op, cp, dt, on):
        if DICT_SET['모의투자1'] and len(self.dict_df['체결목록']) > 0:
            if on in self.dict_df['체결목록'].index:
                while on in self.dict_df['체결목록'].index:
                    on = str(int(on) + 1)
            if dt in self.dict_df['체결목록']['체결시간'].values:
                while dt in self.dict_df['체결목록']['체결시간'].values:
                    dt = str(int(dt) + 1)

        if on in self.dict_df['체결목록'].index:
            self.dict_df['체결목록'].at[on, ['미체결수량', '체결가', '체결시간']] = omc, cp, dt
        else:
            self.dict_df['체결목록'].at[on] = name, og, oc, omc, op, cp, dt
        self.dict_df['체결목록'].sort_values(by=['체결시간'], ascending=False, inplace=True)
        self.windowQ.put([ui_num['S체결목록'], self.dict_df['체결목록']])

        if omc == 0:
            df = pd.DataFrame([[name, og, oc, omc, op, cp, dt]], columns=columns_cj, index=[on])
            self.queryQ.put([2, df, 's_chegeollist', 'append'])

    def OnReceiveConditionVer(self, ret, msg):
        if msg == '':
            return

        if ret == 1:
            self.dict_bool['CD수신'] = True

    def OnReceiveTrCondition(self, screen, code_list, cond_name, cond_index, nnext):
        if screen == "" and cond_name == "" and cond_index == "" and nnext == "":
            return

        codes = code_list.split(';')[:-1]
        self.list_trcd = codes
        self.dict_bool['CR수신'] = True

    def Block_Request(self, *args, **kwargs):
        trcode = args[0].lower()
        lines = readEnc(trcode)
        self.dict_item = parseDat(trcode, lines)
        self.dict_strg['TR명'] = kwargs['output']
        nnext = kwargs['next']
        for i in kwargs:
            if i.lower() != 'output' and i.lower() != 'next':
                self.ocx.dynamicCall('SetInputValue(QString, QString)', i, kwargs[i])
        self.dict_bool['TR수신'] = False
        self.dict_bool['TR다음'] = False
        if trcode == 'optkwfid':
            code_list = args[1]
            code_count = args[2]
            self.ocx.dynamicCall('CommKwRqData(QString, bool, int, int, QString, QString)',
                                 code_list, 0, code_count, '0', self.dict_strg['TR명'], sn_brrq)
        elif trcode == 'opt10054':
            self.ocx.dynamicCall('CommRqData(QString, QString, int, QString)',
                                 self.dict_strg['TR명'], trcode, nnext, sn_brrd)
        else:
            self.ocx.dynamicCall('CommRqData(QString, QString, int, QString)',
                                 self.dict_strg['TR명'], trcode, nnext, sn_brrq)
        sleeptime = timedelta_sec(0.25)
        while not self.dict_bool['TR수신'] or now() < sleeptime:
            pythoncom.PumpWaitingMessages()
        if trcode != 'opt10054':
            self.DisconnectRealData(sn_brrq)
        return self.dict_df['TRDF']

    def SendCondition(self, screen, cond_name, cond_index, search):
        self.dict_bool['CR수신'] = False
        self.ocx.dynamicCall('SendCondition(QString, QString, int, int)', screen, cond_name, cond_index, search)
        while not self.dict_bool['CR수신']:
            pythoncom.PumpWaitingMessages()
        return self.list_trcd

    def DisconnectRealData(self, screen):
        self.ocx.dynamicCall('DisconnectRealData(QString)', screen)

    def GetMasterCodeName(self, code):
        return self.ocx.dynamicCall('GetMasterCodeName(QString)', code)

    def GetCodeListByMarket(self, market):
        data = self.ocx.dynamicCall('GetCodeListByMarket(QString)', market)
        tokens = data.split(';')[:-1]
        return tokens

    def GetMasterLastPrice(self, code):
        return int(self.ocx.dynamicCall('GetMasterLastPrice(QString)', code))

    def GetCommRealData(self, code, fid):
        return self.ocx.dynamicCall('GetCommRealData(QString, int)', code, fid)

    def GetChejanData(self, fid):
        return self.ocx.dynamicCall('GetChejanData(int)', fid)
