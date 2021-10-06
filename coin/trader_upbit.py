import os
import sys
import time
import pyupbit
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.setting import *
from utility.static import now, timedelta_sec, strf_time, strp_time


class TraderUpbit:
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
        self.creceivQ = qlist[6]
        self.coinQ = qlist[8]
        self.cstgQ = qlist[10]

        self.upbit = None                               # 매도수 주문 및 체결 확인용 객체
        self.buy_uuid = None                            # 매수 주문 저장용 list: [티커명, uuid]
        self.sell_uuid = None                           # 매도 주문 저장용 list: [티커명, uuid]
        self.websocketQ = None                          # 실시간데이터 수신용 웹소켓큐

        self.df_cj = pd.DataFrame(columns=columns_cj)   # 체결목록
        self.df_jg = pd.DataFrame(columns=columns_jg)   # 잔고목록
        self.df_tj = pd.DataFrame(columns=columns_tj)   # 잔고평가
        self.df_td = pd.DataFrame(columns=columns_td)   # 거래목록
        self.df_tt = pd.DataFrame(columns=columns_tt)   # 실현손익

        self.str_today = strf_time('%Y%m%d')

        self.dict_jcdt = {}                             # 종목별 체결시간 저장용
        self.dict_intg = {
            '예수금': 0,
            '종목당투자금': 0,                            # 종목당 투자금은 int((예수금 + 매입금액) * 0.99 / 최대매수종목수)로 계산
            '업비트수수료': 0.0005                        # 0.05%
        }
        self.dict_bool = {
            '최소주문금액': False,                        # 업비트 주문가능 최소금액, 종목당투자금이 5천원 미만일 경우 False
            '실현손익저장': False
        }
        self.dict_time = {
            '매수체결확인': now(),                          # 1초 마다 매수 체결 확인용
            '매도체결확인': now(),                          # 1초 마다 매도 체결 확인용
            '거래정보': now()                              # 잔고목록 및 잔고평가 갱신용
        }
        self.Start()

    def Start(self):
        self.LoadDatabase()
        self.GetKey()
        self.GetBalances()
        self.EventLoop()

    def LoadDatabase(self):
        """
        프로그램 구동 시 당일 체결목록, 당일 거래목록, 잔고목록을 불러온다.
        체결과 거래목록은 바로 갱신하고 잔고목록은 예수금을 불러온 이후 갱신한다.
        """
        con = sqlite3.connect(DB_TRADELIST)
        df = pd.read_sql(f"SELECT * FROM c_chegeollist WHERE 체결시간 LIKE '{self.str_today}%'", con)
        self.df_cj = df.set_index('index').sort_values(by=['체결시간'], ascending=False)
        df = pd.read_sql(f'SELECT * FROM c_jangolist', con)
        self.df_jg = df.set_index('index').sort_values(by=['매입금액'], ascending=False)
        df = pd.read_sql(f"SELECT * FROM c_tradelist WHERE 체결시간 LIKE '{self.str_today}%'", con)
        self.df_td = df.set_index('index').sort_values(by=['체결시간'], ascending=False)
        con.close()

        if len(self.df_cj) > 0:
            self.windowQ.put([ui_num['C체결목록'], self.df_cj])
        if len(self.df_td) > 0:
            self.windowQ.put([ui_num['C거래목록'], self.df_td])
        if len(self.df_jg) > 0:
            for code in self.df_jg.index:
                self.creceivQ.put(['잔고편입',  code])

        self.windowQ.put([ui_num['C로그텍스트'], '시스템 명령 실행 알림 - 데이터베이스 불러오기 완료'])

    def GetKey(self):
        """ 매도수 주문 및 체결확인용 self.upbit 객체 생성 """
        if DICT_SET['Access_key'] is not None:
            self.upbit = pyupbit.Upbit(DICT_SET['Access_key'], DICT_SET['Secret_key'])
            self.windowQ.put([ui_num['C로그텍스트'], '시스템 명령 실행 알림 - 주문 및 체결확인용 업비트 객체 생성 완료'])
        else:
            self.windowQ.put([ui_num['C로그텍스트'], '시스템 명령 오류 알림 - 업비트 키값이 설정되지 않았습니다.'])

    def GetBalances(self):
        """ 예수금 조회 및 종목당투자금 계산 """
        if DICT_SET['모의투자2']:
            con = sqlite3.connect(DB_TRADELIST)
            df = pd.read_sql('SELECT * FROM c_tradelist', con)
            con.close()
            tbg = df['매수금액'].sum()
            tsg = df['매도금액'].sum()
            tcg = df['수익금'].sum()
            bfee = int(round(tbg * 0.0005))
            sfee = int(round(tsg * 0.0005))
            cbg = self.df_jg['매입금액'].sum()
            cfee = int(round(cbg * 0.0005))
            chujeonjasan = 100000000 + tcg - bfee - sfee
            self.dict_intg['예수금'] = int(chujeonjasan - cbg - cfee)
            self.dict_intg['종목당투자금'] = int(chujeonjasan * 0.99 / DICT_SET['최대매수종목수2'])
        elif self.upbit is not None:
            cbg = self.df_jg['매입금액'].sum()
            self.dict_intg['예수금'] = int(float(self.upbit.get_balances()[0]['balance']))
            self.dict_intg['종목당투자금'] = int((self.dict_intg['예수금'] + cbg) * 0.99 / DICT_SET['최대매수종목수2'])
        else:
            self.windowQ.put([ui_num['C로그텍스트'], '시스템 명령 오류 알림 - 업비트 키값이 설정되지 않았습니다.'])

        self.cstgQ.put(self.dict_intg['종목당투자금'])
        self.dict_bool['최소주문금액'] = True if self.dict_intg['종목당투자금'] > 5000 else False

        if len(self.df_td) > 0:
            self.UpdateTotaltradelist(first=True)
        self.windowQ.put([ui_num['C로그텍스트'], '시스템 명령 실행 알림 - 예수금 조회 완료'])

    def EventLoop(self):
        while True:
            if not self.coinQ.empty():
                data = self.coinQ.get()
                if data[0] == '매수':
                    self.Buy(data[1], data[2], data[3])
                elif data[0] == '매도':
                    self.Sell(data[1], data[2], data[3])
                else:
                    """ 잔고목록 갱신 및 매도조건 확인 """
                    code, c, tbids, tasks = data
                    if code in self.df_jg.index:
                        try:
                            ch = round(tbids / tasks * 100, 2)
                        except ZeroDivisionError:
                            ch = 500.
                        if ch > 500:
                            ch = 500.
                        self.UpdateJango(code, c, ch)

            """ 주문의 체결확인은 1초마다 반복한다. """
            if self.buy_uuid is not None and now() > self.dict_time['매수체결확인']:
                self.CheckBuyChegeol()
                self.dict_time['매수체결확인'] = timedelta_sec(1)
            if self.sell_uuid is not None and now() > self.dict_time['매도체결확인']:
                self.CheckSellChegeol()
                self.dict_time['매도체결확인'] = timedelta_sec(1)

            """ 잔고평가 및 잔고목록 갱신도 1초마다 반복한다. """
            if now() > self.dict_time['거래정보']:
                self.UpdateTotaljango()
                self.dict_time['거래정보'] = timedelta_sec(1)

            """ 0시 초기화 """
            if 0 < int(strf_time('%H%M%S')) < 100 and not self.dict_bool['실현손익저장']:
                self.SaveTotalGetbalDelcjtd()
            time.sleep(0.0001)

    """
    모의투자 시 실제 매도수 주문을 전송하지 않고 바로 체결목록, 잔고목록 등을 갱신한다.
    실매매 시 매도수 아이디 및 티커명을 매도, 매수 구분하여 변수에 저장하고
    해당 변수값이 None이 아닐 경우 get_order 함수로 체결확인을 1초마다 반복실행한다.
    체결이 완료되면 관련목록을 갱신하고 변수값이 다시 None으로 변경된다.
    체결확인 후 잔고목록를 갱신 한 이후에 전략 연산 프로세스로 체결완료 신호를 보낸다.
    모든 목록은 갱신될 때마다 쿼리 프로세스로 보내어 DB에 실시간으로 기록된다.
    매수 주문은 예수금 부족인지 아닌지를 우선 확인하여 예수금 부족일 경우 주문구분을 시드부족으로 체결목록에 기록하고
    전략 연산 프로세스의 주문 리스트 삭제용 매수취소 신호만 보낸다.
    예수금 부족 상태이며 잔고목록에 없는 상태일 경우 전략 프로세스에서 지속적으로 매수 신호가 발생할 수 있다.
    그러므로 재차 시드부족이 발생한 종목은 체결목록에서 마지막 체결시간이 3분이내면 체결목록에 기록하지 않는다.
    """
    def Buy(self, code, c, oc):
        if not self.dict_bool['최소주문금액']:
            self.windowQ.put([ui_num['C로그텍스트'], '매매 시스템 오류 알림 - 종목당 투자금이 5천원 미만이라 주문할 수 없습니다.'])
            self.cstgQ.put(['매수취소', code])
            return
        if self.buy_uuid is not None or code in self.df_jg.index:
            self.cstgQ.put(['매수취소', code])
            return
        if self.dict_intg['예수금'] < c * oc:
            df = self.df_cj[(self.df_cj['주문구분'] == '시드부족') & (self.df_cj['종목명'] == code)]
            if len(df) == 0 or now() > timedelta_sec(180, strp_time('%Y%m%d%H%M%S%f', df['체결시간'][0])):
                self.UpdateBuy(code, c, oc, cancle=True)
            self.cstgQ.put(['매수취소', code])
            return

        if DICT_SET['모의투자2']:
            self.UpdateBuy(code, c, oc)
        elif self.upbit is not None:
            ret = self.upbit.buy_market_order(code, self.dict_intg['종목당투자금'])
            if ret is not None:
                if list(ret.keys())[0] != 'error':
                    self.buy_uuid = [code, ret['uuid']]
                    self.dict_time['매수체결확인'] = timedelta_sec(1)
                else:
                    self.ErrorCode(ret['error'])
            else:
                self.cstgQ.put(['매수취소', code])
                self.windowQ.put([ui_num['C로그텍스트'], f'매매 시스템 오류 알림 - 주문 실패 {code}'])
        else:
            text = '시스템 명령 오류 알림 - 업비트 키값이 설정되지 않아 주문을 전송할 수 없습니다.'
            self.windowQ.put([ui_num['C로그텍스트'], text])

        if self.dict_bool['실현손익저장'] and int(strf_time('%H%M%S')) > 100:
            self.dict_bool['실현손익저장'] = False

    def Sell(self, code, c, oc):
        if self.sell_uuid is not None or code not in self.df_jg.index:
            self.cstgQ.put(['매도취소', code])
            return

        if DICT_SET['모의투자2']:
            self.UpdateSell(code, c, oc)
        elif self.upbit is not None:
            ret = self.upbit.sell_market_order(code, oc)
            if ret is not None:
                if list(ret.keys())[0] != 'error':
                    self.sell_uuid = [code, ret['uuid']]
                    self.dict_time['매도체결확인'] = timedelta_sec(1)
                else:
                    self.ErrorCode(ret['error'])
            else:
                self.cstgQ.put(['매도취소', code])
                self.windowQ.put([ui_num['C로그텍스트'], f'매매 시스템 오류 알림 - 주문 실패 {code}'])
        else:
            text = '시스템 명령 오류 알림 - 업비트 키값이 설정되지 않아 주문을 전송할 수 없습니다.'
            self.windowQ.put([ui_num['C로그텍스트'], text])

    def UpdateJango(self, code, c, ch):
        prec = self.df_jg['현재가'][code]
        if prec != c:
            bg = self.df_jg['매입금액'][code]
            oc = self.df_jg['보유수량'][code]
            pg, sg, sp, bfee, sfee = self.GetPgSgSp(bg, oc * c)
            columns = ['현재가', '수익률', '평가손익', '평가금액']
            self.df_jg.at[code, columns] = c, sp, sg, pg
            df = self.df_cj[(self.df_cj['종목명'] == code) & (self.df_cj['주문구분'] == '매수')]
            if len(df) > 0:
                buytime = strp_time('%Y%m%d%H%M%S%f', df['체결시간'][0])
                self.cstgQ.put([code, sp, ch, oc, c, buytime])

    def CheckBuyChegeol(self):
        code = self.buy_uuid[0]
        ret = self.upbit.get_order(self.buy_uuid[1])
        if ret is not None:
            if list(ret.keys())[0] != 'error':
                trades = ret['trades']
                if len(trades) == 1:
                    cp = float(trades[0]['price'])
                    cc = float(trades[0]['volume'])
                else:
                    tg = 0
                    cc = 0
                    for i in range(len(trades)):
                        tg += float(trades[i]['price']) * float(trades[i]['volume'])
                        cc += float(trades[i]['volume'])
                    cp = round(tg / cc, 2)
                self.UpdateBuy(code, cp, cc)
            else:
                self.ErrorCode(ret['error'])

    def CheckSellChegeol(self):
        code = self.buy_uuid[0]
        ret = self.upbit.get_order(self.sell_uuid[1])
        if ret is not None:
            if list(ret.keys())[0] != 'error':
                if ret['state'] == 'done':
                    trades = ret['trades']
                    if len(trades) == 1:
                        cp = float(trades[0]['price'])
                        cc = float(trades[0]['volume'])
                    else:
                        tg = 0
                        cc = 0
                        for i in range(len(trades)):
                            tg += float(trades[i]['price']) * float(trades[i]['volume'])
                            cc += float(trades[i]['volume'])
                        cp = round(tg / cc, 2)
                    self.UpdateSell(code, cp, cc)
            else:
                self.ErrorCode(ret['error'])

    def ErrorCode(self, error):
        self.windowQ.put([ui_num['C로그텍스트'], f"{error['name']} : {error['message']}"])

    def UpdateBuy(self, code, cp, cc, cancle=False):
        dt = strf_time('%Y%m%d%H%M%S%f')
        if DICT_SET['모의투자2'] and len(self.df_cj) > 0:
            if dt in self.df_cj['체결시간'].values:
                while dt in self.df_cj['체결시간'].values:
                    dt = str(int(dt) + 1)

        order_gubun = '매수' if not cancle else '시드부족'
        if cancle:
            self.df_cj.at[dt] = code, order_gubun, cc, 0, cp, 0, dt
        else:
            self.df_cj.at[dt] = code, order_gubun, cc, 0, cp, cp, dt
        self.df_cj.sort_values(by=['체결시간'], ascending=False, inplace=True)
        self.windowQ.put([ui_num['C체결목록'], self.df_cj])

        if not cancle:
            self.buy_uuid = None
            self.creceivQ.put(['잔고편입', code])
            self.cstgQ.put(['매수완료', code])
            bg = cp * cc
            pg, sg, sp, bfee, sfee = self.GetPgSgSp(bg, bg)
            self.dict_intg['예수금'] -= bg + bfee
            self.df_jg.at[code] = code, cp, cp, sp, sg, bg, pg, cc
            self.query1Q.put([2, self.df_jg, 'c_jangolist', 'replace'])
            self.windowQ.put([ui_num['C로그텍스트'], f'매매 시스템 체결 알림 - [매수] {code} 코인 {cp}원 {cc}개'])
            if DICT_SET['알림소리2']:
                self.soundQ.put(f'{code[4:]} 코인을 매수하였습니다.')
            self.teleQ.put(f'매수 알림 - {code} {cp} {cc}')

        df = pd.DataFrame([[code, order_gubun, cc, 0, cp, cp, dt]], columns=columns_cj, index=[dt])
        self.query1Q.put([2, df, 'c_chegeollist', 'append'])

    def UpdateSell(self, code, cp, cc):
        dt = strf_time('%Y%m%d%H%M%S%f')
        if DICT_SET['모의투자2'] and len(self.df_cj) > 0:
            if dt in self.df_cj['체결시간'].values:
                while dt in self.df_cj['체결시간'].values:
                    dt = str(int(dt) + 1)

        bp = self.df_jg['매입가'][code]
        bg = bp * cc
        pg, sg, sp, bfee, sfee = self.GetPgSgSp(bg, cp * cc)
        self.dict_intg['예수금'] += bg + sg - sfee

        self.df_jg.drop(index=code, inplace=True)
        self.df_cj.at[dt] = code, '매도', cc, 0, cp, cp, dt
        self.df_td.at[dt] = code, bg, pg, cc, sp, sg, dt
        self.df_cj.sort_values(by=['체결시간'], ascending=False, inplace=True)
        self.df_td.sort_values(by=['체결시간'], ascending=False, inplace=True)

        self.sell_uuid = None
        self.creceivQ.put(['잔고청산', code])
        self.cstgQ.put(['매도완료', code])
        self.windowQ.put([ui_num['C체결목록'], self.df_cj])
        self.windowQ.put([ui_num['C거래목록'], self.df_td])

        self.windowQ.put([ui_num['C로그텍스트'], f'매매 시스템 체결 알림 - [매도] {code} 코인 {cp}원 {cc}개'])
        if DICT_SET['알림소리2']:
            self.soundQ.put(f'{code[4:]} 코인을 매도하였습니다.')

        self.query1Q.put([2, self.df_jg, 'c_jangolist', 'replace'])
        df = pd.DataFrame([[code, '매도', cc, 0, cp, cp, dt]], columns=columns_cj, index=[dt])
        self.query1Q.put([2, df, 'c_chegeollist', 'append'])
        df = pd.DataFrame([[code, bg, pg, cc, sp, sg, dt]], columns=columns_td, index=[dt])
        self.query1Q.put([2, df, 'c_tradelist', 'append'])

        self.teleQ.put(f'매도 알림 - {code} {cp} {cc}')
        self.UpdateTotaltradelist()

    def UpdateTotaltradelist(self, first=False):
        tsg = self.df_td['매도금액'].sum()
        tbg = self.df_td['매수금액'].sum()
        tsig = self.df_td[self.df_td['수익금'] > 0]['수익금'].sum()
        tssg = self.df_td[self.df_td['수익금'] < 0]['수익금'].sum()
        sg = self.df_td['수익금'].sum()
        sp = round(sg / tbg * 100, 2)
        tdct = len(self.df_td)
        self.df_tt = pd.DataFrame([[tdct, tbg, tsg, tsig, tssg, sp, sg]], columns=columns_tt, index=[self.str_today])
        self.windowQ.put([ui_num['C실현손익'], self.df_tt])
        if not first:
            self.teleQ.put(f'손익 알림 - 총매수금액 {tbg}, 총매도금액 {tsg}, 수익 {tsig}, 손실 {tssg}, 수익금합계 {sg}')

    def GetPgSgSp(self, bg, cg):
        sfee = cg * self.dict_intg['업비트수수료']
        bfee = bg * self.dict_intg['업비트수수료']
        pg = int(round(cg))
        sg = int(round(pg - bg))
        sp = round(sg / bg * 100, 2)
        return pg, sg, sp, bfee, sfee

    def UpdateTotaljango(self):
        if len(self.df_jg) > 0:
            tsg = self.df_jg['평가손익'].sum()
            tbg = self.df_jg['매입금액'].sum()
            tpg = self.df_jg['평가금액'].sum()
            bct = len(self.df_jg)
            tsp = round(tsg / tbg * 100, 2)
            ttg = self.dict_intg['예수금'] + tpg
            self.df_tj.at[self.str_today] = ttg, self.dict_intg['예수금'], bct, tsp, tsg, tbg, tpg
        else:
            self.df_tj.at[self.str_today] = self.dict_intg['예수금'], self.dict_intg['예수금'], 0, 0.0, 0, 0, 0
        self.windowQ.put([ui_num['C잔고목록'], self.df_jg])
        self.windowQ.put([ui_num['C잔고평가'], self.df_tj])

    """
    일별 일현손익 저장, 날짜 변경, 종목당투자금 재계산, 체결목록 및 거래목록 초기화가 진행된다.
    저장확인용 변수 self.bool_save는 0시 이후 첫번째 매수 주문시 False로 재변경된다.
    """
    def SaveTotalGetbalDelcjtd(self):
        df = self.df_tt[['총매수금액', '총매도금액', '총수익금액', '총손실금액', '수익률', '수익금합계']].copy()
        self.query1Q.put([2, df, 'c_totaltradelist', 'append'])
        self.str_today = strf_time('%Y%m%d')
        self.df_cj = pd.DataFrame(columns=columns_cj)
        self.df_td = pd.DataFrame(columns=columns_td)
        self.GetBalances()
        self.dict_bool['실현손익저장'] = True
