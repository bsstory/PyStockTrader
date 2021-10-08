import os
import sys
import time
import pythoncom
from PyQt5 import QtWidgets
from PyQt5.QtCore import QTimer
from PyQt5.QAxContainer import QAxWidget
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.static import *
from utility.setting import *

MONEYTOP_CHANGE = 100000    # 최근거래대금순위로 변경할 시간
MONEYTOP_MINUTE = 10        # 최근거래대금순위을 집계할 시간
MONEYTOP_RANK = 10          # 최근거래대금순위중 관심종목으로 선정할 순위


class ReceiverKiwoom:
    app = QtWidgets.QApplication(sys.argv)

    def __init__(self, qlist):
        """
                    0        1       2        3       4       5          6        7      8      9     10
        qlist = [windowQ, soundQ, query1Q, query2Q, teleQ, sreceivQ, creceivQ, stockQ, coinQ, sstgQ, cstgQ,
                 tick1Q, tick2Q, tick3Q, tick4Q, tick5Q]
                   11       12      13     14      15
        """
        self.windowQ = qlist[0]
        self.query2Q = qlist[3]
        self.sreceivQ = qlist[5]
        self.stockQ = qlist[7]
        self.sstgQ = qlist[9]
        self.tick1Q = qlist[11]
        self.tick2Q = qlist[12]
        self.tick3Q = qlist[13]
        self.tick4Q = qlist[14]

        self.dict_bool = {
            '실시간조건검색시작': False,
            '실시간조건검색중단': False,
            '장중단타전략시작': False,

            '로그인': False,
            'TR수신': False,
            'TR다음': False,
            'CD수신': False,
            'CR수신': False
        }
        self.dict_gsjm = {}
        self.dict_cdjm = {}
        self.dict_vipr = {}
        self.dict_tick = {}
        self.dict_hoga = {}
        self.dict_cond = {}
        self.dict_name = {}

        self.list_gsjm = []
        self.list_trcd = []
        self.list_jang = []
        self.pre_top = []
        self.list_kosd = None
        self.list_code = None
        self.list_code1 = None
        self.list_code2 = None
        self.list_code3 = None
        self.list_code4 = None

        self.df_tr = None
        self.dict_item = None
        self.str_tname = None

        self.operation = 1
        self.df_mt = pd.DataFrame(columns=['거래대금순위'])
        self.df_mc = pd.DataFrame(columns=['최근거래대금'])
        self.str_tday = strf_time('%Y%m%d')
        self.str_jcct = self.str_tday + '090000'
        self.dt_mtct = None

        remaintime = (strp_time('%Y%m%d%H%M%S', self.str_tday + '090100') - now()).total_seconds()
        self.dict_time = {
            '휴무종료': timedelta_sec(remaintime) if remaintime > 0 else timedelta_sec(600),
            '거래대금순위기록': now(),
            '거래대금순위저장': now()
        }

        self.timer = QTimer()
        self.timer.setInterval(60000)
        self.timer.timeout.connect(self.ConditionSearch)

        self.ocx = QAxWidget('KHOPENAPI.KHOpenAPICtrl.1')
        self.ocx.OnEventConnect.connect(self.OnEventConnect)
        self.ocx.OnReceiveTrData.connect(self.OnReceiveTrData)
        self.ocx.OnReceiveRealData.connect(self.OnReceiveRealData)
        self.ocx.OnReceiveTrCondition.connect(self.OnReceiveTrCondition)
        self.ocx.OnReceiveConditionVer.connect(self.OnReceiveConditionVer)
        self.ocx.OnReceiveRealCondition.connect(self.OnReceiveRealCondition)
        self.Start()

    def Start(self):
        self.CommConnect()
        self.EventLoop()

    def CommConnect(self):
        self.ocx.dynamicCall('CommConnect()')
        while not self.dict_bool['로그인']:
            pythoncom.PumpWaitingMessages()

        self.dict_bool['CD수신'] = False
        self.ocx.dynamicCall('GetConditionLoad()')
        while not self.dict_bool['CD수신']:
            pythoncom.PumpWaitingMessages()

        self.list_kosd = self.GetCodeListByMarket('10')
        list_code = self.GetCodeListByMarket('0') + self.list_kosd
        dict_code = {}
        df = pd.DataFrame(columns=['종목명'])
        for code in list_code:
            name = self.GetMasterCodeName(code)
            df.at[code] = name
            self.dict_name[name] = code
            dict_code[name] = code

        self.query2Q.put([1, df, 'codename', 'replace'])
        self.windowQ.put([ui_num['S종목명딕셔너리'], self.dict_name, dict_code])

        data = self.ocx.dynamicCall('GetConditionNameList()')
        conditions = data.split(';')[:-1]
        for condition in conditions:
            cond_index, cond_name = condition.split('^')
            self.dict_cond[int(cond_index)] = cond_name

        print(self.dict_cond)
        print('위 조건검색의 번호와 이름은 두번째 계정의 조건검색식들입니다.')
        print('조건검색식 번호를 확인하여 OperationRealreg 함수에 검색식번호를 감시검색식 번호로')
        print('예: self.list_code = self.SendCondition(sn_oper, self.dict_cond[1], 1, 0) 여기서 1 숫자 두개만 수정')
        print('ConditionSearchStart 함수에 검색식번호를 매매검색식 번호로 설정하십시오.')
        print('예: codes = self.SendCondition(sn_cond, self.dict_cond[0], 0, 1) 여기서 0 숫자 두개만 수정')
        self.windowQ.put([ui_num['S단순텍스트'], '시스템 명령 실행 알림 - OpenAPI 로그인 완료'])

    def EventLoop(self):
        self.OperationRealreg()
        self.ViRealreg()
        while True:
            if not self.sreceivQ.empty():
                data = self.sreceivQ.get()
                if type(data) == list:
                    self.UpdateRealreg(data)
                elif type(data) == str:
                    self.UpdateJangolist(data)
                continue

            if self.operation == 1 and now() > self.dict_time['휴무종료']:
                break
            if self.operation == 3:
                if int(strf_time('%H%M%S')) < MONEYTOP_CHANGE:
                    if not self.dict_bool['실시간조건검색시작']:
                        self.ConditionSearchStart()
                if MONEYTOP_CHANGE <= int(strf_time('%H%M%S')):
                    if self.dict_bool['실시간조건검색시작'] and not self.dict_bool['실시간조건검색중단']:
                        self.ConditionSearchStop()
                    if not self.dict_bool['장중단타전략시작']:
                        self.StartJangjungStrategy()
            if self.operation == 8:
                self.AllRemoveRealreg()
                self.SaveTickData()
                break

            if now() > self.dict_time['거래대금순위기록']:
                if len(self.dict_vipr) > 0:
                    self.stockQ.put(['VI정보', self.dict_vipr])
                if len(self.list_gsjm) > 0:
                    self.UpdateMoneyTop()
                self.dict_time['거래대금순위기록'] = timedelta_sec(1)

            time_loop = timedelta_sec(0.25)
            while now() < time_loop:
                pythoncom.PumpWaitingMessages()
                time.sleep(0.0001)

        self.windowQ.put([ui_num['S단순텍스트'], '시스템 명령 실행 알림 - 리시버 종료'])

    def UpdateRealreg(self, rreg):
        sn = rreg[0]
        if len(rreg) == 2:
            self.ocx.dynamicCall('SetRealRemove(QString, QString)', rreg)
            self.windowQ.put([ui_num['S단순텍스트'], f'실시간 알림 중단 완료 - 모든 실시간 데이터 수신 중단'])
        elif len(rreg) == 4:
            ret = self.ocx.dynamicCall('SetRealReg(QString, QString, QString, QString)', rreg)
            result = '완료' if ret == 0 else '실패'
            if sn == sn_oper:
                self.windowQ.put([ui_num['S단순텍스트'], f'실시간 알림 등록 {result} - 장운영시간 [{sn}]'])
            else:
                text = f"실시간 알림 등록 {result} - [{sn}] 종목갯수 {len(rreg[1].split(';'))}"
                self.windowQ.put([ui_num['S단순텍스트'], text])

    def UpdateJangolist(self, work):
        code = work.split(' ')[1]
        if '잔고편입' in work and code not in self.list_jang:
            self.list_jang.append(code)
            if code not in self.dict_gsjm.keys():
                self.dict_gsjm[code] = '090000'
                self.sstgQ.put(['조건진입', code])
        elif '잔고청산' in work and code in self.list_jang:
            self.list_jang.remove(code)
            if code not in self.list_gsjm and code in self.dict_gsjm.keys():
                self.sstgQ.put(['조건이탈', code])
                del self.dict_gsjm[code]

    def OperationRealreg(self):
        self.sreceivQ.put([sn_oper, ' ', '215;20;214', 0])
        self.list_code = self.SendCondition(sn_oper, self.dict_cond[1], 1, 0)
        self.list_code1 = [code for i, code in enumerate(self.list_code) if i % 4 == 0]
        self.list_code2 = [code for i, code in enumerate(self.list_code) if i % 4 == 1]
        self.list_code3 = [code for i, code in enumerate(self.list_code) if i % 4 == 2]
        self.list_code4 = [code for i, code in enumerate(self.list_code) if i % 4 == 3]
        k = 0
        for i in range(0, len(self.list_code), 100):
            self.sreceivQ.put([sn_jchj + k, ';'.join(self.list_code[i:i + 100]), '10;12;14;30;228;41;61;71;81', 1])
            k += 1
        self.windowQ.put([ui_num['S단순텍스트'], '시스템 명령 실행 알림 - 장운영시간 등록 완료'])

    def ViRealreg(self):
        self.Block_Request('opt10054', 시장구분='000', 장전구분='1', 종목코드='', 발동구분='1', 제외종목='111111011',
                           거래량구분='0', 거래대금구분='0', 발동방향='0', output='발동종목', next=0)
        self.windowQ.put([ui_num['S단순텍스트'], '시스템 명령 실행 알림 - VI발동해제 등록 완료'])
        self.windowQ.put([ui_num['S단순텍스트'], '시스템 명령 실행 알림 - 콜렉터 시작 완료'])

    def ConditionSearchStart(self):
        self.dict_bool['실시간조건검색시작'] = True
        codes = self.SendCondition(sn_cond, self.dict_cond[0], 0, 1)
        if len(codes) > 0:
            for code in codes:
                self.InsertGsjmlist(code)
        self.windowQ.put([ui_num['S단순텍스트'], '시스템 명령 실행 알림 - 실시간조건검색 등록 완료'])

    def ConditionSearchStop(self):
        self.dict_bool['실시간조건검색중단'] = True
        self.ocx.dynamicCall("SendConditionStop(QString, QString, int)", sn_cond, self.dict_cond[0], 0)
        self.windowQ.put([ui_num['S단순텍스트'], '시스템 명령 실행 알림 - 실시간조건검색 중단 완료'])

    def StartJangjungStrategy(self):
        self.dict_bool['장중단타전략시작'] = True
        self.df_mc.sort_values(by=['최근거래대금'], ascending=False, inplace=True)
        list_top = list(self.df_mc.index[:MONEYTOP_RANK])
        insert_list = set(list_top) - set(self.list_gsjm)
        if len(insert_list) > 0:
            for code in list(insert_list):
                self.InsertGsjmlist(code)
        delete_list = set(self.list_gsjm) - set(list_top)
        if len(delete_list) > 0:
            for code in list(delete_list):
                self.DeleteGsjmlist(code)
        self.pre_top = list_top
        self.timer.start()

    def ConditionSearch(self):
        self.df_mc.sort_values(by=['최근거래대금'], ascending=False, inplace=True)
        list_top = list(self.df_mc.index[:MONEYTOP_RANK])
        insert_list = set(list_top) - set(self.pre_top)
        if len(insert_list) > 0:
            for code in list(insert_list):
                self.InsertGsjmlist(code)
        delete_list = set(self.pre_top) - set(list_top)
        if len(delete_list) > 0:
            for code in list(delete_list):
                self.DeleteGsjmlist(code)
        self.pre_top = list_top

    def InsertGsjmlist(self, code):
        if code not in self.list_gsjm:
            self.list_gsjm.append(code)
        if code not in self.list_jang and code not in self.dict_gsjm.keys():
            self.sstgQ.put(['조건진입', code])
            self.dict_gsjm[code] = '090000'

    def DeleteGsjmlist(self, code):
        if code in self.list_gsjm:
            self.list_gsjm.remove(code)
        if code not in self.list_jang and code in self.dict_gsjm.keys():
            self.sstgQ.put(['조건이탈', code])
            del self.dict_gsjm[code]

    def AllRemoveRealreg(self):
        self.sreceivQ.put(['ALL', 'ALL'])
        self.windowQ.put([ui_num['S단순텍스트'], '시스템 명령 실행 알림 - 실시간 데이터 중단 완료'])

    def SaveTickData(self):
        con = sqlite3.connect(DB_TRADELIST)
        df = pd.read_sql(f"SELECT * FROM s_tradelist WHERE 체결시간 LIKE '{self.str_tday}%'", con).set_index('index')
        con.close()
        codes = []
        for index in df.index:
            code = self.dict_name[df['종목명'][index]]
            if code not in codes:
                codes.append(code)
        self.tick1Q.put(['콜렉터종료', codes])
        self.tick2Q.put(['콜렉터종료', codes])
        self.tick3Q.put(['콜렉터종료', codes])
        self.tick4Q.put(['콜렉터종료', codes])

    def UpdateMoneyTop(self):
        timetype = '%Y%m%d%H%M%S'
        list_text = ';'.join(self.list_gsjm)
        curr_time = self.str_jcct
        curr_datetime = strp_time(timetype, curr_time)
        if self.dt_mtct is not None:
            gap_seconds = (curr_datetime - self.dt_mtct).total_seconds()
            while gap_seconds > 2:
                gap_seconds -= 1
                pre_time = strf_time(timetype, timedelta_sec(-gap_seconds, curr_datetime))
                self.df_mt.at[pre_time] = list_text
        self.df_mt.at[curr_time] = list_text
        self.dt_mtct = curr_datetime

        if now() > self.dict_time['거래대금순위저장']:
            self.query2Q.put([1, self.df_mt, 'moneytop', 'append'])
            self.df_mt = pd.DataFrame(columns=['거래대금순위'])
            self.dict_time['거래대금순위저장'] = timedelta_sec(10)

    def OnEventConnect(self, err_code):
        if err_code == 0:
            self.dict_bool['로그인'] = True

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

    def OnReceiveRealCondition(self, code, IorD, cname, cindex):
        if cname == '' and cindex == '':
            return
        if int(strf_time('%H%M%S')) > MONEYTOP_CHANGE:
            return

        if IorD == 'I':
            self.InsertGsjmlist(code)
        elif IorD == 'D':
            self.DeleteGsjmlist(code)

    def OnReceiveRealData(self, code, realtype, realdata):
        if realdata == '':
            return

        if realtype == '장시작시간':
            try:
                self.operation = int(self.GetCommRealData(code, 215))
                current = self.GetCommRealData(code, 20)
                remain = self.GetCommRealData(code, 214)
            except Exception as e:
                self.windowQ.put([1, f'OnReceiveRealData 장시작시간 {e}'])
            else:
                self.windowQ.put([1, f'장운영 시간 수신 알림 - {self.operation} {current[:2]}:{current[2:4]}:{current[4:]} '
                                     f'남은시간 {remain[:2]}:{remain[2:4]}:{remain[4:]}'])
        elif realtype == 'VI발동/해제':
            try:
                code = self.GetCommRealData(code, 9001).strip('A').strip('Q')
                gubun = self.GetCommRealData(code, 9068)
                name = self.GetMasterCodeName(code)
            except Exception as e:
                self.windowQ.put([ui_num['S단순텍스트'], f'OnReceiveRealData VI발동/해제 {e}'])
            else:
                if gubun == '1' and code in self.list_code and \
                        (code not in self.dict_vipr.keys() or
                         (self.dict_vipr[code][0] and now() > self.dict_vipr[code][1])):
                    self.UpdateViPrice(code, name)
        elif realtype == '주식체결':
            try:
                c = abs(int(self.GetCommRealData(code, 10)))
                o = abs(int(self.GetCommRealData(code, 16)))
                v = int(self.GetCommRealData(code, 15))
                t = self.GetCommRealData(code, 20)
            except Exception as e:
                self.windowQ.put([ui_num['S단순텍스트'], f'OnReceiveRealData 주식체결 {e}'])
            else:
                if self.operation == 1:
                    self.operation = 3
                if t != self.str_jcct[8:]:
                    self.str_jcct = self.str_tday + t
                if code not in self.dict_vipr.keys():
                    self.InsertViPrice(code, o)
                if code in self.dict_vipr.keys() and not self.dict_vipr[code][0] and now() > self.dict_vipr[code][1]:
                    self.UpdateViPrice(code, c)
                try:
                    pret = self.dict_tick[code][0]
                    bid_volumns = self.dict_tick[code][1]
                    ask_volumns = self.dict_tick[code][2]
                except KeyError:
                    pret = None
                    bid_volumns = 0
                    ask_volumns = 0
                if v > 0:
                    self.dict_tick[code] = [t, bid_volumns + abs(v), ask_volumns]
                else:
                    self.dict_tick[code] = [t, bid_volumns, ask_volumns + abs(v)]
                if t != pret:
                    bids = self.dict_tick[code][1]
                    asks = self.dict_tick[code][2]
                    self.dict_tick[code] = [t, 0, 0]
                    try:
                        h = abs(int(self.GetCommRealData(code, 17)))
                        low = abs(int(self.GetCommRealData(code, 18)))
                        per = float(self.GetCommRealData(code, 12))
                        dm = int(self.GetCommRealData(code, 14))
                        ch = float(self.GetCommRealData(code, 228))
                        name = self.GetMasterCodeName(code)
                    except Exception as e:
                        self.windowQ.put([ui_num['S단순텍스트'], f'OnReceiveRealData 주식체결 {e}'])
                    else:
                        self.UpdateTickData(code, name, c, o, h, low, per, dm, ch, bids, asks, t, now())
        elif realtype == '주식호가잔량':
            try:
                tsjr = int(self.GetCommRealData(code, 121))
                tbjr = int(self.GetCommRealData(code, 125))
                s2hg = abs(int(self.GetCommRealData(code, 42)))
                s1hg = abs(int(self.GetCommRealData(code, 41)))
                b1hg = abs(int(self.GetCommRealData(code, 51)))
                b2hg = abs(int(self.GetCommRealData(code, 52)))
                s2jr = int(self.GetCommRealData(code, 62))
                s1jr = int(self.GetCommRealData(code, 61))
                b1jr = int(self.GetCommRealData(code, 71))
                b2jr = int(self.GetCommRealData(code, 72))
            except Exception as e:
                self.windowQ.put([ui_num['S단순텍스트'], f'OnReceiveRealData 주식호가잔량 {e}'])
            else:
                self.dict_hoga[code] = [tsjr, tbjr, s2hg, s1hg, b1hg, b2hg, s2jr, s1jr, b1jr, b2jr]

    def InsertViPrice(self, code, o):
        uvi, dvi, vid5price = self.GetVIPrice(code, o)
        self.dict_vipr[code] = [True, timedelta_sec(-180), uvi, dvi, vid5price]

    def GetVIPrice(self, code, std_price):
        uvi = std_price * 1.1
        x = self.GetHogaunit(code, uvi)
        if uvi % x != 0:
            uvi = uvi + (x - uvi % x)
        vid5price = uvi - x * 5
        dvi = std_price * 0.9
        x = self.GetHogaunit(code, dvi)
        if dvi % x != 0:
            dvi = dvi - dvi % x
        return int(uvi), int(dvi), int(vid5price)

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
                self.dict_vipr[code][:2] = False, timedelta_sec(5)
            except KeyError:
                self.dict_vipr[code] = [False, timedelta_sec(5), 0, 0, 0]
            self.windowQ.put([ui_num['S로그텍스트'], f'변동성 완화 장치 발동 - [{code}] {key}'])
        elif type(key) == int:
            uvi, dvi, vid5price = self.GetVIPrice(code, key)
            self.dict_vipr[code] = [True, timedelta_sec(5), uvi, dvi, vid5price]

    def UpdateTickData(self, code, name, c, o, h, low, per, dm, ch, bids, asks, t, receivetime):
        dt = self.str_tday + t[:4]
        if code not in self.dict_cdjm.keys():
            columns = ['1분누적거래대금', '1분전당일거래대금']
            self.dict_cdjm[code] = pd.DataFrame([[0, dm]], columns=columns, index=[dt])
        elif dt != self.dict_cdjm[code].index[-1]:
            predm = self.dict_cdjm[code]['1분전당일거래대금'][-1]
            self.dict_cdjm[code].at[dt] = dm - predm, dm
            if len(self.dict_cdjm[code]) == MONEYTOP_MINUTE:
                if per > 0:
                    self.df_mc.at[code] = self.dict_cdjm[code]['1분누적거래대금'].sum()
                self.dict_cdjm[code].drop(index=self.dict_cdjm[code].index[0], inplace=True)

        vitime = self.dict_vipr[code][1]
        vid5price = self.dict_vipr[code][4]
        try:
            tsjr, tbjr, s2hg, s1hg, b1hg, b2hg, s2jr, s1jr, b1jr, b2jr = self.dict_hoga[code]
        except KeyError:
            tsjr, tbjr, s2hg, s1hg, b1hg, b2hg, s2jr, s1jr, b1jr, b2jr = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0

        data = [code, c, o, h, low, per, dm, ch, bids, asks, vitime, vid5price,
                tsjr, tbjr, s2hg, s1hg, b1hg, b2hg, s2jr, s1jr, b1jr, b2jr, t, receivetime]

        if DICT_SET['키움트레이더'] and code in self.dict_gsjm.keys():
            injango = code in self.list_jang
            data.append(name)
            data.append(injango)
            self.sstgQ.put(data)
            if injango:
                self.stockQ.put([code, name, c])

        data[10] = strf_time('%Y%m%d%H%M%S', vitime)
        if code in self.list_code1:
            self.tick1Q.put(data)
        elif code in self.list_code2:
            self.tick2Q.put(data)
        elif code in self.list_code3:
            self.tick3Q.put(data)
        elif code in self.list_code4:
            self.tick4Q.put(data)

    def OnReceiveTrData(self, screen, rqname, trcode, record, nnext):
        if screen == '' and record == '':
            return
        items = None
        self.dict_bool['TR다음'] = True if nnext == '2' else False
        for output in self.dict_item['output']:
            record = list(output.keys())[0]
            items = list(output.values())[0]
            if record == self.str_tname:
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
        self.df_tr = df
        self.dict_bool['TR수신'] = True

    def Block_Request(self, *args, **kwargs):
        trcode = args[0].lower()
        lines = readEnc(trcode)
        self.dict_item = parseDat(trcode, lines)
        self.str_tname = kwargs['output']
        nnext = kwargs['next']
        for i in kwargs:
            if i.lower() != 'output' and i.lower() != 'next':
                self.ocx.dynamicCall('SetInputValue(QString, QString)', i, kwargs[i])
        self.dict_bool['TR수신'] = False
        self.dict_bool['TR다음'] = False
        self.ocx.dynamicCall('CommRqData(QString, QString, int, QString)', self.str_tname, trcode, nnext, sn_brrq)
        sleeptime = timedelta_sec(0.25)
        while not self.dict_bool['TR수신'] or now() < sleeptime:
            pythoncom.PumpWaitingMessages()
        return self.df_tr

    def SendCondition(self, screen, cond_name, cond_index, search):
        self.dict_bool['CR수신'] = False
        self.ocx.dynamicCall('SendCondition(QString, QString, int, int)', screen, cond_name, cond_index, search)
        while not self.dict_bool['CR수신']:
            pythoncom.PumpWaitingMessages()
        return self.list_trcd

    def GetMasterCodeName(self, code):
        return self.ocx.dynamicCall('GetMasterCodeName(QString)', code)

    def GetCodeListByMarket(self, market):
        data = self.ocx.dynamicCall('GetCodeListByMarket(QString)', market)
        tokens = data.split(';')[:-1]
        return tokens

    def GetCommRealData(self, code, fid):
        return self.ocx.dynamicCall('GetCommRealData(QString, int)', code, fid)
