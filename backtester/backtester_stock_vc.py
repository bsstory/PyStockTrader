import os
import sys
import sqlite3
import pandas as pd
from matplotlib import pyplot as plt
from multiprocessing import Process, Queue
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.setting import DB_STOCK_TICK, DB_BACKTEST, GRAPH_PATH
from utility.static import now, strf_time, strp_time, timedelta_sec, timedelta_day

BATTING = 20000000     # 종목당 배팅금액
TESTPERIOD = 14        # 백테스팅 기간(14일 경우 과거 2주간의 데이터를 백테스팅한다)
TOTALTIME = 36000      # 백테스팅 기간 동안 9시부터 10시까지의 시간 총합, 단위 초
START_TIME = 90000
END_TIME = 100000


class BackTesterStockVc:
    def __init__(self, q_, code_list_, num_, df_mt_, high):
        self.q = q_
        self.code_list = code_list_
        self.df_mt = df_mt_
        self.high = high

        if type(num_[0]) == list:
            self.gap_ch = num_[0][0]
            self.avg_time = num_[1][0]
            self.gap_sm = num_[2][0]
            self.ch_low = num_[3][0]
            self.dm_low = num_[4][0]
            self.per_low = num_[5][0]
            self.per_high = num_[6][0]
            self.cs_per = num_[7][0]
        else:
            self.gap_ch = num_[0]
            self.avg_time = num_[1]
            self.gap_sm = num_[2]
            self.ch_low = num_[3]
            self.dm_low = num_[4]
            self.per_low = num_[5]
            self.per_high = num_[6]
            self.cs_per = num_[7]

        self.code = None
        self.df = None

        self.totalcount = 0
        self.totalcount_p = 0
        self.totalcount_m = 0
        self.totalholdday = 0
        self.totaleyun = 0
        self.totalper = 0.

        self.hold = False
        self.buycount = 0
        self.buyprice = 0
        self.sellprice = 0
        self.index = 0
        self.indexb = 0

        self.indexn = 0
        self.ccond = 0
        self.csell = 0

        self.Start()

    def Start(self):
        conn = sqlite3.connect(DB_STOCK_TICK)
        tcount = len(self.code_list)
        int_daylimit = int(strf_time('%Y%m%d', timedelta_day(-TESTPERIOD)))
        for k, code in enumerate(self.code_list):
            self.code = code
            self.df = pd.read_sql(f"SELECT * FROM '{code}'", conn)
            self.df = self.df.set_index('index')
            self.df['직전초당거래대금'] = self.df['초당거래대금'].shift(1)
            self.df['직전체결강도'] = self.df['체결강도'].shift(1)
            self.df['초당거래대금평균'] = self.df['직전초당거래대금'].rolling(window=self.avg_time).mean()
            self.df['체결강도평균'] = self.df['직전체결강도'].rolling(window=self.avg_time).mean()
            self.df['최고체결강도'] = self.df['직전체결강도'].rolling(window=self.avg_time).max()
            self.df = self.df.fillna(0)
            self.totalcount = 0
            self.totalcount_p = 0
            self.totalcount_m = 0
            self.totalholdday = 0
            self.totaleyun = 0
            self.totalper = 0.
            self.ccond = 0
            lasth = len(self.df) - 1
            for h, index in enumerate(self.df.index):
                if h != 0 and index[:8] != self.df.index[h - 1][:8]:
                    self.ccond = 0
                if int(index[:8]) < int_daylimit or \
                        (not self.hold and (END_TIME <= int(index[8:]) or int(index[8:]) < START_TIME)):
                    continue
                self.index = index
                self.indexn = h
                if not self.hold and START_TIME < int(index[8:]) < END_TIME and self.BuyTerm():
                    self.Buy()
                elif self.hold and START_TIME < int(index[8:]) < END_TIME and self.SellTerm():
                    self.Sell()
                elif self.hold and (h == lasth or int(index[8:]) >= END_TIME > int(self.df.index[h - 1][8:])):
                    self.Sell()
            self.Report(k + 1, tcount)
        conn.close()

    def BuyTerm(self):
        try:
            if self.code not in self.df_mt['거래대금순위'][self.index]:
                self.ccond = 0
            else:
                self.ccond += 1
        except KeyError:
            return False
        if self.ccond < self.avg_time:
            return False

        # 여기에 본인의 전략을 작성하십시오.

        return True

    def Buy(self):
        if self.df['매도호가1'][self.index] * self.df['매도잔량1'][self.index] >= BATTING:
            s1hg = self.df['매도호가1'][self.index]
            self.buycount = int(BATTING / s1hg)
            self.buyprice = s1hg
        else:
            s1hg = self.df['매도호가1'][self.index]
            s1jr = self.df['매도잔량1'][self.index]
            s2hg = self.df['매도호가2'][self.index]
            ng = BATTING - s1hg * s1jr
            s2jc = int(ng / s2hg)
            self.buycount = s1jr + s2jc
            self.buyprice = round((s1hg * s1jr + s2hg * s2jc) / self.buycount, 2)
        if self.buycount == 0:
            return
        self.hold = True
        self.indexb = self.indexn
        self.csell = 0

    def SellTerm(self):
        if self.df['등락율'][self.index] > 29:
            return True

        bg = self.buycount * self.buyprice
        cg = self.buycount * self.df['현재가'][self.index]
        eyun, per = self.GetEyunPer(bg, cg)

        # 여기에 본인의 전략을 작성하십시오.

        return False

    def Sell(self):
        if self.df['매수잔량1'][self.index] >= self.buycount:
            self.sellprice = self.df['매수호가1'][self.index]
        else:
            b1hg = self.df['매수호가1'][self.index]
            b1jr = self.df['매수잔량1'][self.index]
            b2hg = self.df['매수호가2'][self.index]
            nc = self.buycount - b1jr
            self.sellprice = round((b1hg * b1jr + b2hg * nc) / self.buycount, 2)
        self.hold = False
        self.CalculationEyun()
        self.indexb = 0

    def CalculationEyun(self):
        self.totalcount += 1
        bg = self.buycount * self.buyprice
        cg = self.buycount * self.sellprice
        eyun, per = self.GetEyunPer(bg, cg)
        self.totalper = round(self.totalper + per, 2)
        self.totaleyun = int(self.totaleyun + eyun)
        self.totalholdday += self.indexn - self.indexb
        if per > 0:
            self.totalcount_p += 1
        else:
            self.totalcount_m += 1
        if self.high:
            self.q.put([self.index, self.code, per, eyun])

    # noinspection PyMethodMayBeStatic
    def GetEyunPer(self, bg, cg):
        gtexs = cg * 0.0023
        gsfee = cg * 0.00015
        gbfee = bg * 0.00015
        texs = gtexs - (gtexs % 1)
        sfee = gsfee - (gsfee % 10)
        bfee = gbfee - (gbfee % 10)
        pg = int(cg - texs - sfee - bfee)
        eyun = pg - bg
        per = round(eyun / bg * 100, 2)
        return eyun, per

    def Report(self, count, tcount):
        if self.totalcount > 0:
            plus_per = round((self.totalcount_p / self.totalcount) * 100, 2)
            avgholdday = round(self.totalholdday / self.totalcount, 2)
            self.q.put([self.code, self.totalcount, avgholdday, self.totalcount_p, self.totalcount_m,
                        plus_per, self.totalper, self.totaleyun])
            totalcount, avgholdday, totalcount_p, totalcount_m, plus_per, totalper, totaleyun = \
                self.GetTotal(plus_per, avgholdday)
            print(f" 종목코드 {self.code} | 평균보유기간 {avgholdday}초 | 거래횟수 {totalcount}회 | "
                  f" 익절 {totalcount_p}회 | 손절 {totalcount_m}회 | 승률 {plus_per}% |"
                  f" 수익률 {totalper}% | 수익금 {totaleyun}원 [{count}/{tcount}]")
        else:
            self.q.put([self.code, 0, 0, 0, 0, 0., 0., 0])

    def GetTotal(self, plus_per, avgholdday):
        totalcount = str(self.totalcount)
        totalcount = '  ' + totalcount if len(totalcount) == 1 else totalcount
        totalcount = ' ' + totalcount if len(totalcount) == 2 else totalcount
        avgholdday = str(avgholdday)
        avgholdday = '   ' + avgholdday if len(avgholdday.split('.')[0]) == 1 else avgholdday
        avgholdday = '  ' + avgholdday if len(avgholdday.split('.')[0]) == 2 else avgholdday
        avgholdday = ' ' + avgholdday if len(avgholdday.split('.')[0]) == 3 else avgholdday
        avgholdday = avgholdday + '0' if len(avgholdday.split('.')[1]) == 1 else avgholdday
        totalcount_p = str(self.totalcount_p)
        totalcount_p = '  ' + totalcount_p if len(totalcount_p) == 1 else totalcount_p
        totalcount_p = ' ' + totalcount_p if len(totalcount_p) == 2 else totalcount_p
        totalcount_m = str(self.totalcount_m)
        totalcount_m = '  ' + totalcount_m if len(totalcount_m) == 1 else totalcount_m
        totalcount_m = ' ' + totalcount_m if len(totalcount_m) == 2 else totalcount_m
        plus_per = str(plus_per)
        plus_per = '  ' + plus_per if len(plus_per.split('.')[0]) == 1 else plus_per
        plus_per = ' ' + plus_per if len(plus_per.split('.')[0]) == 2 else plus_per
        plus_per = plus_per + '0' if len(plus_per.split('.')[1]) == 1 else plus_per
        totalper = str(self.totalper)
        totalper = '   ' + totalper if len(totalper.split('.')[0]) == 1 else totalper
        totalper = '  ' + totalper if len(totalper.split('.')[0]) == 2 else totalper
        totalper = ' ' + totalper if len(totalper.split('.')[0]) == 3 else totalper
        totalper = totalper + '0' if len(totalper.split('.')[1]) == 1 else totalper
        totaleyun = format(self.totaleyun, ',')
        if len(totaleyun.split(',')) == 1:
            totaleyun = '         ' + totaleyun if len(totaleyun.split(',')[0]) == 1 else totaleyun
            totaleyun = '        ' + totaleyun if len(totaleyun.split(',')[0]) == 2 else totaleyun
            totaleyun = '       ' + totaleyun if len(totaleyun.split(',')[0]) == 3 else totaleyun
            totaleyun = '      ' + totaleyun if len(totaleyun.split(',')[0]) == 4 else totaleyun
        elif len(totaleyun.split(',')) == 2:
            totaleyun = '     ' + totaleyun if len(totaleyun.split(',')[0]) == 1 else totaleyun
            totaleyun = '    ' + totaleyun if len(totaleyun.split(',')[0]) == 2 else totaleyun
            totaleyun = '   ' + totaleyun if len(totaleyun.split(',')[0]) == 3 else totaleyun
            totaleyun = '  ' + totaleyun if len(totaleyun.split(',')[0]) == 4 else totaleyun
        elif len(totaleyun.split(',')) == 3:
            totaleyun = ' ' + totaleyun if len(totaleyun.split(',')[0]) == 1 else totaleyun
        return totalcount, avgholdday, totalcount_p, totalcount_m, plus_per, totalper, totaleyun


class Total:
    def __init__(self, q_, last_, num_, df1_):
        super().__init__()
        self.q = q_
        self.last = last_
        self.name = df1_

        if type(num_[0]) == list:
            self.gap_ch = num_[0][0]
            self.avg_time = num_[1][0]
            self.gap_sm = num_[2][0]
            self.ch_low = num_[3][0]
            self.dm_low = num_[4][0]
            self.per_low = num_[5][0]
            self.per_high = num_[6][0]
            self.cs_per = num_[7][0]
        else:
            self.gap_ch = num_[0]
            self.avg_time = num_[1]
            self.gap_sm = num_[2]
            self.ch_low = num_[3]
            self.dm_low = num_[4]
            self.per_low = num_[5]
            self.per_high = num_[6]
            self.cs_per = num_[7]

        self.Start()

    def Start(self):
        columns1 = ['거래횟수', '평균보유기간', '익절', '손절', '승률', '수익률', '수익금']
        columns2 = ['필요자금', '종목출현빈도수', '거래횟수', '평균보유기간', '익절', '손절', '승률',
                    '평균수익률', '수익률합계', '수익금합계', '체결강도차이', '평균시간', '거래대금차이',
                    '체결강도하한', '누적거래대금하한', '등락율하한', '등락율상한', '청산수익률']
        df_back = pd.DataFrame(columns=columns1)
        df_tsg = pd.DataFrame(columns=['종목명', 'per', 'ttsg'])
        k = 0
        while True:
            data = self.q.get()
            if len(data) == 4:
                name = self.name['종목명'][data[1]]
                if data[0] in df_tsg.index:
                    df_tsg.at[data[0]] = df_tsg['종목명'][data[0]] + ';' + name, \
                                         df_tsg['per'][data[0]] + data[2], \
                                         df_tsg['ttsg'][data[0]] + data[3]
                else:
                    df_tsg.at[data[0]] = name, data[2], data[3]
            else:
                df_back.at[data[0]] = data[1], data[2], data[3], data[4], data[5], data[6], data[7]
                k += 1
            if k == self.last:
                break

        tsp = 0
        if len(df_back) > 0:
            tc = df_back['거래횟수'].sum()
            text = [self.gap_ch, self.avg_time, self.gap_sm, self.ch_low, self.dm_low,
                    self.per_low, self.per_high, self.cs_per]
            print(f' {text}')
            if tc != 0:
                pc = df_back['익절'].sum()
                mc = df_back['손절'].sum()
                pper = round(pc / tc * 100, 2)
                df_back_ = df_back[df_back['평균보유기간'] != 0]
                avghold = round(df_back_['평균보유기간'].sum() / len(df_back_), 2)
                avgsp = round(df_back['수익률'].sum() / tc, 2)
                tsg = int(df_back['수익금'].sum())
                onedaycount = round(tc / TOTALTIME, 4)
                onegm = int(BATTING * onedaycount * avghold)
                if onegm < BATTING:
                    onegm = BATTING
                tsp = round(tsg / onegm * 100, 4)
                text = f" 종목당 배팅금액 {format(BATTING, ',')}원, 필요자금 {format(onegm, ',')}원, "\
                       f" 종목출현빈도수 {onedaycount}개/초, 거래횟수 {tc}회, 평균보유기간 {avghold}초,\n 익절 {pc}회, "\
                       f" 손절 {mc}회, 승률 {pper}%, 평균수익률 {avgsp}%, 수익률합계 {tsp}%, 수익금합계 {format(tsg, ',')}원"
                print(text)
                df_back = pd.DataFrame(
                    [[onegm, onedaycount, tc, avghold, pc, mc, pper, avgsp, tsp, tsg, self.gap_ch, self.avg_time,
                      self.gap_sm, self.ch_low, self.dm_low, self.per_low, self.per_high, self.cs_per]],
                    columns=columns2, index=[strf_time('%Y%m%d%H%M%S')])
                conn = sqlite3.connect(DB_BACKTEST)
                df_back.to_sql(f"stock_vc_{strf_time('%Y%m%d')}_1", conn, if_exists='append', chunksize=1000)
                conn.close()

        if len(df_tsg) > 0:
            df_tsg['체결시간'] = df_tsg.index
            df_tsg.sort_values(by=['체결시간'], inplace=True)
            df_tsg['ttsg_cumsum'] = df_tsg['ttsg'].cumsum()
            df_tsg[['ttsg', 'ttsg_cumsum']] = df_tsg[['ttsg', 'ttsg_cumsum']].astype(int)
            conn = sqlite3.connect(DB_BACKTEST)
            df_tsg.to_sql(f"stock_vc_{strf_time('%Y%m%d')}_2", conn, if_exists='append', chunksize=1000)
            conn.close()
            df_tsg.plot(figsize=(12, 9), rot=45)
            plt.savefig(f"{GRAPH_PATH}/stock_vc_{strf_time('%Y%m%d')}.png")
        else:
            self.q.put(tsp)


if __name__ == "__main__":
    start = now()

    con = sqlite3.connect(DB_STOCK_TICK)
    df1 = pd.read_sql('SELECT * FROM codename', con)
    df1 = df1.set_index('index')
    df2 = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
    df3 = pd.read_sql('SELECT * FROM moneytop', con)
    df3 = df3.set_index('index')
    con.close()
    table_list = list(df2['name'].values)
    table_list.remove('moneytop')
    table_list.remove('codename')
    last = len(table_list)

    q = Queue()
    gap_chs = [3, 4, 5, 6, 7, 8, 9]
    avg_times = [30, 60, 90, 120, 150, 180]
    htsp = -100
    high_var = []

    for gap_ch in gap_chs:
        for avg_time in avg_times:
            num = [gap_ch, avg_time, 50, 50, 0, 0, 25, 3]
            w = Process(target=Total, args=(q, last, num, df1))
            w.start()
            procs = []
            workcount = int(last / 6) + 1
            for j in range(0, last, workcount):
                code_list = table_list[j:j + workcount]
                p = Process(target=BackTesterStockVc, args=(q, code_list, num, df3, False))
                procs.append(p)
                p.start()
            for p in procs:
                p.join()
            w.join()
            sp = q.get()
            if sp >= htsp:
                htsp = sp
                high_var = num
                print(f' 최고수익률 갱신 {htsp}%')

    gap_ch = [high_var[0] - 0.9, high_var[0] + 0.9, 0.1, 0.1]
    avg_time = [high_var[1], high_var[1], 30, 3]
    gap_sm = [0, 500, 50, 10]
    ch_low = [50, 100, 10, 10]
    dm_low = [0, 100000, 10000, 1000]
    per_low = [0, 10, 1, 0.1]
    per_high = [25, 15, -1, -1]
    cs_per = [3, 10, 1, 0.2]
    num = [gap_ch, avg_time, gap_sm, ch_low, dm_low, per_low, per_high, cs_per]

    ogin_var = high_var[0]
    high_var = high_var[0]

    i = 0
    while True:
        w = Process(target=Total, args=(q, last, num, df1))
        w.start()
        procs = []
        workcount = int(last / 6) + 1
        for j in range(0, last, workcount):
            code_list = table_list[j:j + workcount]
            p = Process(target=BackTesterStockVc, args=(q, code_list, num, df3, False))
            procs.append(p)
            p.start()
        for p in procs:
            p.join()
        w.join()
        sp = q.get()
        if sp >= htsp:
            htsp = sp
            high_var = num[i][0]
            print(f' 최고수익률 갱신 {htsp}%')
        if num[i][0] == num[i][1]:
            num[i][0] = high_var
            if num[i][2] != num[i][3]:
                if num[i][0] != ogin_var:
                    num[i][0] -= num[i][2]
                    num[i][1] = round(num[i][0] + num[i][2] * 2 - num[i][3], 1)
                else:
                    num[i][1] = round(num[i][0] + num[i][2] - num[i][3], 1)
                num[i][2] = num[i][3]
            elif i < len(num) - 1:
                i += 1
                if i == 1:
                    num[i][0] -= num[i][2]
                    num[i][1] = round(num[i][0] + num[i][2] * 2 - num[i][3], 1)
                    num[i][2] = num[i][3]
                ogin_var = num[i][0]
                high_var = num[i][0]
            else:
                break
        num[i][0] = round(num[i][0] + num[i][2], 1)

    w = Process(target=Total, args=(q, last, num, df1))
    w.start()
    procs = []
    workcount = int(last / 6) + 1
    for j in range(0, last, workcount):
        db_list = table_list[j:j + workcount]
        p = Process(target=BackTesterStockVc, args=(q, db_list, num, df3, True))
        procs.append(p)
        p.start()
    for p in procs:
        p.join()
    w.join()

    end = now()
    print(f" 백테스팅 소요시간 {end - start}")
