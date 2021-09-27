import sqlite3
from utility.setting import ui_num, DB_TRADELIST, DB_STOCK_TICK, DB_COIN_TICK, DB_SETTING


class Query:
    def __init__(self, windowQ, queryQ):
        self.windowQ = windowQ
        self.queryQ = queryQ
        self.con1 = sqlite3.connect(DB_SETTING)
        self.cur1 = self.con1.cursor()
        self.con2 = sqlite3.connect(DB_TRADELIST)
        self.cur2 = self.con2.cursor()
        self.con3 = sqlite3.connect(DB_STOCK_TICK)
        self.con4 = sqlite3.connect(DB_COIN_TICK)
        self.Start()

    def __del__(self):
        self.con1.close()
        self.con2.close()
        self.con3.close()
        self.con4.close()

    def Start(self):
        while True:
            query = self.queryQ.get()
            if query[0] == 1:
                if len(query) == 2:
                    try:
                        self.cur1.execute(query[1])
                    except Exception as e:
                        self.windowQ.put([ui_num['설정텍스트'], f'시스템 명령 오류 알림 - 입력값이 잘못되었습니다. {e}'])
                    else:
                        self.con1.commit()
                elif len(query) == 4:
                    try:
                        query[1].to_sql(query[2], self.con1, if_exists=query[3], chunksize=1000)
                    except Exception as e:
                        self.windowQ.put([ui_num['설정텍스트'], f'시스템 명령 오류 알림 - {e}'])
            elif query[0] == 2:
                if len(query) == 2:
                    try:
                        self.cur2.execute(query[1])
                    except Exception as e:
                        self.windowQ.put([ui_num['S로그텍스트'], f'시스템 명령 오류 알림 - 입력값이 잘못되었습니다. {e}'])
                    else:
                        self.con2.commit()
                elif len(query) == 4:
                    try:
                        query[1].to_sql(query[2], self.con2, if_exists=query[3], chunksize=1000)
                    except Exception as e:
                        self.windowQ.put([ui_num['S로그텍스트'], f'시스템 명령 오류 알림 - {e}'])
            elif query[0] == 3:
                if len(query) == 2:
                    j = 1
                    for code in list(query[1].keys()):
                        query[1][code].to_sql(code, self.con3, if_exists='append', chunksize=1000)
                        text = f'시스템 명령 실행 알림 - 틱데이터 저장 중...Dict[{j}/{len(query)}]'
                        self.windowQ.put([ui_num['S단순텍스트'], text])
                        j += 1
                elif len(query) == 4:
                    try:
                        query[1].to_sql(query[2], self.con3, if_exists=query[3], chunksize=1000)
                    except Exception as e:
                        self.windowQ.put([ui_num['S단순텍스트'], f'시스템 명령 오류 알림 - {e}'])
            elif query[0] == 4:
                for ticker in list(query[1].keys()):
                    query[1][ticker].to_sql(ticker, self.con4, if_exists='append', chunksize=1000)
                self.windowQ.put([ui_num['C단순텍스트'], '시스템 명령 실행 알림 - 틱데이터 저장 완료'])
