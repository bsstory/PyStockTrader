import sqlite3
from utility.setting import ui_num, DB_TRADELIST, DB_SETTING, DB_STOCK_STRETEGY, DB_COIN_STRETEGY


class Query:
    def __init__(self, qlist):
        """
                    0        1       2        3       4       5          6        7      8      9     10
        qlist = [windowQ, soundQ, query1Q, query2Q, teleQ, sreceivQ, creceivQ, stockQ, coinQ, sstgQ, cstgQ,
                 tick1Q, tick2Q, tick3Q, tick4Q, tick5Q]
                   11       12      13     14      15
        """
        self.windowQ = qlist[0]
        self.query1Q = qlist[2]
        self.con1 = sqlite3.connect(DB_SETTING)
        self.cur1 = self.con1.cursor()
        self.con2 = sqlite3.connect(DB_TRADELIST)
        self.cur2 = self.con2.cursor()
        self.con3 = sqlite3.connect(DB_STOCK_STRETEGY)
        self.cur3 = self.con3.cursor()
        self.con4 = sqlite3.connect(DB_COIN_STRETEGY)
        self.cur4 = self.con4.cursor()
        self.Start()

    def __del__(self):
        self.con1.close()
        self.con2.close()
        self.con3.close()
        self.con4.close()

    def Start(self):
        while True:
            query = self.query1Q.get()
            if query[0] == 1:
                if len(query) == 2:
                    try:
                        self.cur1.execute(query[1])
                    except Exception as e:
                        self.windowQ.put([ui_num['설정텍스트'], f'시스템 명령 오류 알림 - execute {e}'])
                    else:
                        self.con1.commit()
                elif len(query) == 4:
                    try:
                        query[1].to_sql(query[2], self.con1, if_exists=query[3], chunksize=1000)
                    except Exception as e:
                        self.windowQ.put([ui_num['설정텍스트'], f'시스템 명령 오류 알림 - to_sql {e}'])
            elif query[0] == 2:
                if len(query) == 2:
                    try:
                        self.cur2.execute(query[1])
                    except Exception as e:
                        self.windowQ.put([ui_num['설정텍스트'], f'시스템 명령 오류 알림 - execute {e}'])
                    else:
                        self.con2.commit()
                elif len(query) == 4:
                    try:
                        query[1].to_sql(query[2], self.con2, if_exists=query[3], chunksize=1000)
                    except Exception as e:
                        if 's_' in query[2]:
                            self.windowQ.put([ui_num['S로그텍스트'], f'시스템 명령 오류 알림 - to_sql {e}'])
                        else:
                            self.windowQ.put([ui_num['C로그텍스트'], f'시스템 명령 오류 알림 - to_sql {e}'])
            elif query[0] == 3:
                if len(query) == 2:
                    try:
                        self.cur3.execute(query[1])
                    except Exception as e:
                        self.windowQ.put([ui_num['S전략텍스트'], f'시스템 명령 오류 알림 - execute {e}'])
                    else:
                        self.con3.commit()
                elif len(query) == 4:
                    try:
                        query[1].to_sql(query[2], self.con3, if_exists=query[3], chunksize=1000)
                    except Exception as e:
                        self.windowQ.put([ui_num['S전략텍스트'], f'시스템 명령 오류 알림 - to_sql {e}'])
            elif query[0] == 4:
                if len(query) == 2:
                    try:
                        self.con4.execute(query[1])
                    except Exception as e:
                        self.windowQ.put([ui_num['C전략텍스트'], f'시스템 명령 오류 알림 - execute {e}'])
                    else:
                        self.con4.commit()
                elif len(query) == 4:
                    try:
                        query[1].to_sql(query[2], self.con4, if_exists=query[3], chunksize=1000)
                    except Exception as e:
                        self.windowQ.put([ui_num['C전략텍스트'], f'시스템 명령 오류 알림 - to_sql {e}'])
