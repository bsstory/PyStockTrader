import os
import sys
import time
import pythoncom
from PyQt5 import QtWidgets
from PyQt5.QAxContainer import QAxWidget
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.static import *
from utility.setting import *


class TraderKiwoom:
    app = QtWidgets.QApplication(sys.argv)

    def __init__(self, qlist):
        """
                    0        1       2        3       4       5          6        7      8      9     10
        qlist = [windowQ, soundQ, query1Q, query2Q, teleQ, sreceivQ, creceivQ, stockQ, coinQ, sstgQ, cstgQ,
                 tick1Q, tick2Q, tick3Q, tick4Q, tick5Q]
                   11       12      13     14      15
        """
        self.windowQ = qlist[0]
        self.soundQ = qlist[1]
        self.query1Q = qlist[2]
        self.teleQ = qlist[4]
        self.sreceivQ = qlist[5]
        self.stockQ = qlist[7]
        self.sstgQ = qlist[9]

        self.dict_name = {}     # key: 종목코드, value: 종목명
        self.dict_vipr = {}     # key: 종목코드, value: [갱신여부, 발동시간+5초, UVI, DVI, UVID5]
        self.dict_buyt = {}     # key: 종목코드, value: 매수시간
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
            '잔고청산': False,
            '로그인': False,
            'TR수신': False,
            'TR다음': False
        }
        remaintime = (strp_time('%Y%m%d%H%M%S', self.dict_strg['당일날짜'] + '090100') - now()).total_seconds()
        self.dict_time = {
            '휴무종료': timedelta_sec(remaintime) if remaintime > 0 else timedelta_sec(600),
            '거래정보': now()
        }
        self.dict_item = None
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
            self.windowQ.put([ui_num['S거래목록'], self.dict_df['거래목록']])

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

        self.windowQ.put([ui_num['S로그텍스트'], '시스템 명령 실행 알림 - OpenAPI 로그인 완료'])
        if DICT_SET['알림소리1']:
            self.soundQ.put('키움증권 오픈에이피아이에 로그인하였습니다.')

        if len(self.dict_df['잔고목록']) > 0:
            for code in self.dict_df['잔고목록'].index:
                cond = (self.dict_df['체결목록']['주문구분'] == '매수') & \
                       (self.dict_df['체결목록']['종목명'] == self.dict_name[code])
                df = self.dict_df['체결목록'][cond]
                self.dict_buyt[code] = strp_time('%Y%m%d%H%M%S%f', df['체결시간'].loc[0])
                self.sreceivQ.put(f'잔고편입 {code}')

        if int(strf_time('%H%M%S')) > 90000:
            self.dict_intg['장운영상태'] = 3

    def EventLoop(self):
        self.GetAccountjanGo()
        self.OperationRealreg()
        while True:
            if not self.stockQ.empty():
                data = self.stockQ.get()
                if type(data) == list:
                    if len(data) == 10:
                        self.SendOrder(data)
                    elif len(data) == 5:
                        self.BuySell(data[0], data[1], data[2], data[3], data[4])
                        continue
                    elif len(data) == 2:
                        if data[0] == 'VI정보':
                            self.dict_vipr = data[1]
                    elif len(data) == 3:
                        self.UpdateJango(data[0], data[1], data[2])
                elif type(data) == str:
                    self.TelegramCmd(data)

            if self.dict_intg['장운영상태'] == 1 and now() > self.dict_time['휴무종료']:
                break
            if int(strf_time('%H%M%S')) >= DICT_SET['잔고청산'] and not self.dict_bool['잔고청산']:
                self.JangoChungsan()
            if self.dict_intg['장운영상태'] == 8:
                self.AllRemoveRealreg()
                self.SaveDayData()
                break

            if now() > self.dict_time['거래정보']:
                self.UpdateTotaljango()
                self.dict_time['거래정보'] = timedelta_sec(1)

            time_loop = timedelta_sec(0.25)
            while now() < time_loop:
                pythoncom.PumpWaitingMessages()
                time.sleep(0.0001)

        self.sstgQ.put('전략프로세스종료')
        self.windowQ.put([ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 트레이더를 종료합니다.'])
        if DICT_SET['알림소리1']:
            self.soundQ.put('주식 트레이더를 종료합니다.')
        self.teleQ.put('주식 트레이더를 종료하였습니다.')

    def SendOrder(self, order):
        name = order[-1]
        del order[-1]
        ret = self.ocx.dynamicCall(
            'SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)', order)
        if ret != 0:
            self.windowQ.put([ui_num['S로그텍스트'], f'시스템 명령 오류 알림 - {name} {order[5]}주 {order[0]} 주문 실패'])

    def BuySell(self, gubun, code, name, c, oc):
        if gubun == '매수':
            if code in self.dict_df['잔고목록'].index or self.dict_bool['잔고청산']:
                self.sstgQ.put(['매수취소', code])
                return
            if code in self.list_buy:
                self.sstgQ.put(['매수취소', code])
                self.windowQ.put([ui_num['S로그텍스트'], '매매 시스템 오류 알림 - 현재 매도 주문중인 종목입니다.'])
                return
            if self.dict_intg['추정예수금'] < oc * c:
                cond = (self.dict_df['체결목록']['주문구분'] == '시드부족') & (self.dict_df['체결목록']['종목명'] == name)
                df = self.dict_df['체결목록'][cond]
                if len(df) == 0 or \
                        (len(df) > 0 and now() > timedelta_sec(180, strp_time('%Y%m%d%H%M%S%f', df['체결시간'][0]))):
                    self.Order('시드부족', code, name, c, oc)
                self.sstgQ.put(['매수취소', code])
                return
        elif gubun == '매도':
            if code not in self.dict_df['잔고목록'].index:
                self.sstgQ.put(['매도취소', code])
                return
            if code in self.list_sell:
                self.sstgQ.put(['매도취소', code])
                self.windowQ.put([ui_num['S로그텍스트'], '매매 시스템 오류 알림 - 현재 매수 주문중인 종목입니다.'])
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
            self.UpdateChejanData(code, name, '체결', gubun, c, c, oc, 0, strf_time('%Y%m%d%H%M%S%f'))
        else:
            self.stockQ.put([gubun, '4989', self.dict_strg['계좌번호'], on, code, oc, 0, '03', '', name])

    def UpdateRealreg(self, rreg):
        if len(rreg) == 2:
            self.ocx.dynamicCall('SetRealRemove(QString, QString)', rreg)
        elif len(rreg) == 4:
            self.ocx.dynamicCall('SetRealReg(QString, QString, QString, QString)', rreg)

    def TelegramCmd(self, work):
        if work == '/당일체결목록':
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
            if not self.dict_bool['잔고청산']:
                self.JangoChungsan()

    def GetAccountjanGo(self):
        while True:
            df = self.Block_Request('opw00004', 계좌번호=self.dict_strg['계좌번호'], 비밀번호='', 상장폐지조회구분=0,
                                    비밀번호입력매체구분='00', output='계좌평가현황', next=0)
            if df['D+2추정예수금'][0] != '':
                if DICT_SET['모의투자1']:
                    con = sqlite3.connect(DB_TRADELIST)
                    df = pd.read_sql('SELECT * FROM s_tradelist', con)
                    con.close()
                    self.dict_intg['예수금'] = 100000000 - self.dict_df['잔고목록']['매입금액'].sum() + df['수익금'].sum()
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
                    self.dict_intg['추정예탁자산'] = self.dict_intg['예수금'] + self.dict_df['잔고목록']['평가금액'].sum()
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
        self.windowQ.put([ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 장운영시간 등록 완료'])
        self.windowQ.put([ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 트레이더 시작 완료'])

    def JangoChungsan(self):
        self.dict_bool['잔고청산'] = True
        if len(self.dict_df['잔고목록']) > 0:
            for code in self.dict_df['잔고목록'].index:
                if code in self.list_sell:
                    continue
                c = self.dict_df['잔고목록']['현재가'][code]
                oc = self.dict_df['잔고목록']['보유수량'][code]
                name = self.dict_name[code]
                if DICT_SET['모의투자1']:
                    self.list_sell.append(code)
                    self.UpdateChejanData(code, name, '체결', '매도', c, c, oc, 0, strf_time('%Y%m%d%H%M%S%f'))
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

    def SaveDayData(self):
        if len(self.dict_df['거래목록']) > 0:
            df = self.dict_df['실현손익'][['총매수금액', '총매도금액', '총수익금액', '총손실금액', '수익률', '수익금합계']].copy()
            self.query1Q.put([2, df, 's_totaltradelist', 'append'])
        if DICT_SET['알림소리1']:
            self.soundQ.put('일별실현손익를 저장하였습니다.')
        self.windowQ.put([ui_num['S로그텍스트'], '시스템 명령 실행 알림 - 일별실현손익 저장 완료'])

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

    def UpdateJango(self, code, name, c):
        prec = self.dict_df['잔고목록']['현재가'][code]
        if prec != c:
            bg = self.dict_df['잔고목록']['매입금액'][code]
            oc = int(self.dict_df['잔고목록']['보유수량'][code])
            pg, sg, sp = self.GetPgSgSp(bg, oc * c)
            columns = ['현재가', '수익률', '평가손익', '평가금액']
            self.dict_df['잔고목록'].at[code, columns] = c, sp, sg, pg
            if code in self.dict_buyt.keys():
                self.sstgQ.put([code, name, sp, oc, c, self.dict_buyt[code]])

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
        except Exception as e:
            self.windowQ.put([ui_num['S로그텍스트'], f'OnReceiveChejanData {e}'])
        else:
            try:
                cp = int(self.GetChejanData(910))
            except ValueError:
                cp = 0
            self.UpdateChejanData(code, name, ot, og, op, cp, oc, omc, on)

    def UpdateChejanData(self, code, name, ot, og, op, cp, oc, omc, on):
        if ot == '체결' and omc == 0 and cp != 0:
            if og == '매수':
                self.UpdateChegeoljango(code, name, og, oc, cp)
                self.dict_buyt[code] = now()
                self.list_buy.remove(code)
                self.sreceivQ.put(f'잔고편입 {code}')
                self.sstgQ.put(['매수완료', code])
                self.dict_intg['예수금'] -= oc * cp
                self.dict_intg['추정예수금'] = self.dict_intg['예수금']
                self.windowQ.put([ui_num['S로그텍스트'], f'매매 시스템 체결 알림 - {name} {oc}주 {og}'])
            elif og == '매도':
                bp = self.dict_df['잔고목록']['매입가'][code]
                bg = bp * oc
                pg, sg, sp = self.GetPgSgSp(bg, oc * cp)
                self.UpdateChegeoljango(code, name, og, oc, cp)
                self.UpdateTradelist(name, oc, sp, sg, bg, pg, on)
                self.list_sell.remove(code)
                self.sreceivQ.put(f'잔고청산 {code}')
                self.sstgQ.put(['매도완료', code])
                self.dict_intg['예수금'] += pg
                self.dict_intg['추정예수금'] = self.dict_intg['예수금']
                self.windowQ.put([ui_num['S로그텍스트'],
                                  f"매매 시스템 체결 알림 - {name} {oc}주 {og}, 수익률 {sp}% 수익금{format(sg, ',')}원"])
        self.UpdateChegeollist(name, og, oc, omc, op, cp, on)

    def UpdateChegeoljango(self, code, name, og, oc, cp):
        if og == '매수':
            if code not in self.dict_df['잔고목록'].index:
                bg = oc * cp
                pg, sg, sp = self.GetPgSgSp(bg, oc * cp)
                self.dict_df['잔고목록'].at[code] = name, cp, cp, sp, sg, bg, pg, oc
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
            else:
                bp = self.dict_df['잔고목록']['매입가'][code]
                jc = jc - oc
                bg = jc * bp
                pg, sg, sp = self.GetPgSgSp(bg, jc * cp)
                self.dict_df['잔고목록'].at[code] = name, bp, cp, sp, sg, bg, pg, jc

        columns = ['매입가', '현재가', '평가손익', '매입금액']
        self.dict_df['잔고목록'][columns] = self.dict_df['잔고목록'][columns].astype(int)
        self.dict_df['잔고목록'].sort_values(by=['매입금액'], inplace=True)
        self.query1Q.put([2, self.dict_df['잔고목록'], 's_jangolist', 'replace'])
        if DICT_SET['알림소리1']:
            self.soundQ.put(f'{name} {oc}주를 {og}하였습니다')

    def UpdateTradelist(self, name, oc, sp, sg, bg, pg, on):
        dt = strf_time('%Y%m%d%H%M%S%f')
        if DICT_SET['모의투자1'] and len(self.dict_df['거래목록']) > 0:
            if dt in self.dict_df['거래목록']['체결시간'].values:
                while dt in self.dict_df['거래목록']['체결시간'].values:
                    dt = str(int(dt) + 1)
                on = dt

        self.dict_df['거래목록'].at[on] = name, bg, pg, oc, sp, sg, dt
        self.dict_df['거래목록'].sort_values(by=['체결시간'], ascending=False, inplace=True)
        self.windowQ.put([ui_num['S거래목록'], self.dict_df['거래목록']])

        df = pd.DataFrame([[name, bg, pg, oc, sp, sg, dt]], columns=columns_td, index=[on])
        self.query1Q.put([2, df, 's_tradelist', 'append'])
        self.UpdateTotaltradelist()

    def UpdateTotaltradelist(self, first=False):
        tsg = self.dict_df['거래목록']['매도금액'].sum()
        tbg = self.dict_df['거래목록']['매수금액'].sum()
        tsig = self.dict_df['거래목록'][self.dict_df['거래목록']['수익금'] > 0]['수익금'].sum()
        tssg = self.dict_df['거래목록'][self.dict_df['거래목록']['수익금'] < 0]['수익금'].sum()
        sg = self.dict_df['거래목록']['수익금'].sum()
        sp = round(sg / self.dict_intg['추정예탁자산'] * 100, 2)
        tdct = len(self.dict_df['거래목록'])
        self.dict_df['실현손익'] = pd.DataFrame(
            [[tdct, tbg, tsg, tsig, tssg, sp, sg]], columns=columns_tt, index=[self.dict_strg['당일날짜']]
        )
        self.windowQ.put([ui_num['S실현손익'], self.dict_df['실현손익']])

        if not first:
            self.teleQ.put(
                f"거래횟수 {len(self.dict_df['거래목록'])}회 / 총매수금액 {format(int(tbg), ',')}원 / "
                f"총매도금액 {format(int(tsg), ',')}원 / 총수익금액 {format(int(tsig), ',')}원 / "
                f"총손실금액 {format(int(tssg), ',')}원 / 수익률 {sp}% / 수익금합계 {format(int(sg), ',')}원")

    def UpdateChegeollist(self, name, og, oc, omc, op, cp, on):
        dt = strf_time('%Y%m%d%H%M%S%f')
        if DICT_SET['모의투자1'] and len(self.dict_df['체결목록']) > 0:
            if dt in self.dict_df['거래목록']['체결시간'].values:
                while dt in self.dict_df['거래목록']['체결시간'].values:
                    dt = str(int(dt) + 1)
                on = dt

        if on in self.dict_df['체결목록'].index:
            self.dict_df['체결목록'].at[on, ['미체결수량', '체결가', '체결시간']] = omc, cp, dt
        else:
            if og == '시드부족':
                self.dict_df['체결목록'].at[on] = name, og, oc, 0, op, 0, dt
            else:
                self.dict_df['체결목록'].at[on] = name, og, oc, omc, op, cp, dt
        self.dict_df['체결목록'].sort_values(by=['체결시간'], ascending=False, inplace=True)
        self.windowQ.put([ui_num['S체결목록'], self.dict_df['체결목록']])

        if omc == 0:
            df = pd.DataFrame([[name, og, oc, omc, op, cp, dt]], columns=columns_cj, index=[on])
            self.query1Q.put([2, df, 's_chegeollist', 'append'])

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

    def DisconnectRealData(self, screen):
        self.ocx.dynamicCall('DisconnectRealData(QString)', screen)

    def GetMasterCodeName(self, code):
        return self.ocx.dynamicCall('GetMasterCodeName(QString)', code)

    def GetCodeListByMarket(self, market):
        data = self.ocx.dynamicCall('GetCodeListByMarket(QString)', market)
        tokens = data.split(';')[:-1]
        return tokens

    def GetCommRealData(self, code, fid):
        return self.ocx.dynamicCall('GetCommRealData(QString, int)', code, fid)

    def GetChejanData(self, fid):
        return self.ocx.dynamicCall('GetChejanData(int)', fid)
