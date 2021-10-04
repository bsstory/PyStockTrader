import os
import sys
import psutil
import logging
import subprocess
from PyQt5.QtTest import QTest
from multiprocessing import Process, Queue
from coin.receiver_upbit import WebsTicker, WebsOrderbook
from coin.collector_upbit import CollectorUpbit
from coin.strategy_coin import StrategyCoin
from coin.trader_upbit import TraderUpbit
from stock.receiver_kiwoom import ReceiverKiwoom
from stock.collector_kiwoom import CollectorKiwoom
from stock.strategy_stock import StrategyStock
from stock.trader_kiwoom import TraderKiwoom
from utility.setui import *
from utility.sound import Sound
from utility.query import Query
from utility.query_tick import QueryTick
from utility.telegram_msg import TelegramMsg
from utility.static import now, strf_time, strp_time, changeFormat, thread_decorator, comma2int, comma2float


class Window(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.log1 = logging.getLogger('Stock')
        self.log1.setLevel(logging.INFO)
        filehandler = logging.FileHandler(filename=f"{SYSTEM_PATH}/log/S{strf_time('%Y%m%d')}.txt", encoding='utf-8')
        self.log1.addHandler(filehandler)

        self.log2 = logging.getLogger('Coin')
        self.log2.setLevel(logging.INFO)
        filehandler = logging.FileHandler(filename=f"{SYSTEM_PATH}/log/C{strf_time('%Y%m%d')}.txt", encoding='utf-8')
        self.log2.addHandler(filehandler)

        SetUI(self)

        if int(strf_time('%H%M%S')) < 80000 or 160000 < int(strf_time('%H%M%S')):
            self.main_tabWidget.setCurrentWidget(self.ct_tab)

        self.cpu_per = 0
        self.int_time = int(strf_time('%H%M%S'))
        self.dict_name = {}

        self.writer = Writer()
        self.writer.data1.connect(self.UpdateTexedit)
        self.writer.data2.connect(self.UpdateTablewidget)
        self.writer.data3.connect(self.UpdateGaonsimJongmok)
        self.writer.start()

        self.qtimer1 = QtCore.QTimer()
        self.qtimer1.setInterval(1000)
        self.qtimer1.timeout.connect(self.ProcessStarter)
        self.qtimer1.start()

        self.qtimer2 = QtCore.QTimer()
        self.qtimer2.setInterval(500)
        self.qtimer2.timeout.connect(self.UpdateProgressBar)
        self.qtimer2.start()

        self.qtimer3 = QtCore.QTimer()
        self.qtimer3.setInterval(500)
        self.qtimer3.timeout.connect(self.UpdateCpuper)
        self.qtimer3.start()

        self.showqsize = False
        self.backtester_proc = None

        self.receiver_coin_thread1 = WebsTicker(qlist)
        self.receiver_coin_thread2 = WebsOrderbook(qlist)
        self.collector_coin_proc = Process(target=CollectorUpbit, args=(qlist,), daemon=True)
        self.strategy_coin_proc = Process(target=StrategyCoin, args=(qlist,), daemon=True)
        self.trader_coin_thread = TraderUpbit(qlist)

        self.receiver_stock_proc = Process(target=ReceiverKiwoom, args=(qlist,), daemon=True)
        self.collector_stock_proc1 = Process(target=CollectorKiwoom, args=(1, qlist), daemon=True)
        self.collector_stock_proc2 = Process(target=CollectorKiwoom, args=(2, qlist), daemon=True)
        self.collector_stock_proc3 = Process(target=CollectorKiwoom, args=(3, qlist), daemon=True)
        self.collector_stock_proc4 = Process(target=CollectorKiwoom, args=(4, qlist), daemon=True)
        self.strategy_stock_proc = Process(target=StrategyStock, args=(qlist,), daemon=True)
        self.trader_stock_proc = Process(target=TraderKiwoom, args=(qlist,), daemon=True)

    def ProcessStarter(self):
        if now().weekday() not in [6, 7]:
            if DICT_SET['키움콜렉터'] and self.int_time < DICT_SET['콜렉터'] <= int(strf_time('%H%M%S')):
                self.KiwoomCollectorStart()
            if DICT_SET['키움트레이더'] and self.int_time < DICT_SET['트레이더'] <= int(strf_time('%H%M%S')):
                self.KiwoomTraderStart()
        if DICT_SET['백테스터'] and self.int_time < DICT_SET['백테스터시작시간'] <= int(strf_time('%H%M%S')):
            self.BacktestStart()
        if DICT_SET['업비트콜렉터']:
            self.UpbitCollectorStart()
        if DICT_SET['업비트트레이더']:
            self.UpbitTraderStart()
        if self.int_time < 83000 <= int(strf_time('%H%M%S')):
            self.ClearTextEdit()
        self.ChangeWindowTitle()
        self.int_time = int(strf_time('%H%M%S'))

    # noinspection PyArgumentList
    def KiwoomCollectorStart(self):
        self.backtester_proc = None
        if DICT_SET['아이디2'] is not None:
            os.system(f'python {LOGIN_PATH}/versionupdater.py')
            os.system(f'python {LOGIN_PATH}/autologin2.py')
            if not self.collector_stock_proc1.is_alive():
                self.collector_stock_proc1.start()
            if not self.collector_stock_proc2.is_alive():
                self.collector_stock_proc2.start()
            if not self.collector_stock_proc3.is_alive():
                self.collector_stock_proc3.start()
            if not self.collector_stock_proc4.is_alive():
                self.collector_stock_proc4.start()
            if not self.receiver_stock_proc.is_alive():
                self.receiver_stock_proc.start()
            text = '주식 리시버 및 콜렉터를 시작하였습니다.'
            soundQ.put(text)
            teleQ.put(text)
        else:
            QtWidgets.QMessageBox.critical(
                self, '오류 알림',
                '키움 두번째 계정이 설정되지 않아\n콜렉터를 시작할 수 없습니다.\n계정 설정 후 다시 시작하십시오.\n'
            )

    # noinspection PyArgumentList
    def KiwoomTraderStart(self):
        if DICT_SET['아이디1'] is not None:
            os.system(f'python {LOGIN_PATH}/autologin1.py')
            if not self.strategy_stock_proc.is_alive():
                self.strategy_stock_proc.start()
            if not self.trader_stock_proc.is_alive():
                self.trader_stock_proc.start()
            text = '주식 트레이더를 시작하였습니다.'
            soundQ.put(text)
            teleQ.put(text)
        else:
            QtWidgets.QMessageBox.critical(
                self, '오류 알림',
                '키움 첫번째 계정이 설정되지 않아\n트레이더를 시작할 수 없습니다.\n계정 설정 후 다시 시작하십시오.\n'
            )

    # noinspection PyArgumentList
    def BacktestStart(self):
        if self.backtester_proc is None or self.backtester_proc.poll() == 0:
            self.ButtonClicked_8()
            QTest.qWait(3000)
            self.ButtonClicked_9()

    def UpbitCollectorStart(self):
        if not self.receiver_coin_thread1.isRunning():
            self.receiver_coin_thread1.start()
        if not self.receiver_coin_thread2.isRunning():
            self.receiver_coin_thread2.start()
        if not self.collector_coin_proc.is_alive():
            self.collector_coin_proc.start()
            text = '코인 리시버 및 콜렉터를 시작하였습니다.'
            soundQ.put(text)
            teleQ.put(text)

    def UpbitTraderStart(self):
        if DICT_SET['Access_key'] is not None:
            if not self.strategy_coin_proc.is_alive():
                self.strategy_coin_proc.start()
            if not self.trader_coin_thread.isRunning():
                self.trader_coin_thread.start()
                text = '코인 트레이더를 시작하였습니다.'
                soundQ.put(text)
                teleQ.put(text)
        else:
            QtWidgets.QMessageBox.critical(
                self, '오류 알림',
                '업비트 계정이 설정되지 않아\n트레이더를 시작할 수 없습니다.\n계정 설정 후 다시 시작하십시오.\n'
            )

    def ClearTextEdit(self):
        self.st_textEdit.clear()
        self.ct_textEdit.clear()
        self.sc_textEdit.clear()
        self.cc_textEdit.clear()

    def ChangeWindowTitle(self):
        if self.showqsize:
            queryQ_size = query1Q.qsize() + query2Q.qsize()
            stocktickQ_size = tick1Q.qsize() + tick2Q.qsize() + tick3Q.qsize() + tick4Q.qsize()
            text = f'PyStockTrader                                                                   '\
                   f'windowQ[{windowQ.qsize()}] | soundQ[{soundQ.qsize()}] | '\
                   f'queryQ[{queryQ_size}] | teleQ[{teleQ.qsize()}] | receivQ[{receivQ.qsize()}] | '\
                   f'stockQ[{stockQ.qsize()}] | coinQ[{coinQ.qsize()}] | sstgQ[{sstgQ.qsize()}] | '\
                   f'cstgQ[{cstgQ.qsize()}] | stocktickQ[{stocktickQ_size}] | cointickQ[{tick5Q.qsize()}]'
            self.setWindowTitle(text)
        elif self.windowTitle() != 'PyStockTrader':
            self.setWindowTitle('PyStockTrader')

    def UpdateProgressBar(self):
        self.progressBar.setValue(int(self.cpu_per))

    @thread_decorator
    def UpdateCpuper(self):
        self.cpu_per = psutil.cpu_percent(interval=1)

    def ShowQsize(self):
        self.showqsize = True if not self.showqsize else False

    # noinspection PyMethodMayBeStatic
    def SpecialStrategy(self):
        buttonReply = QtWidgets.QMessageBox.question(
            self, '스패셜전략 활성화', f'스패셜전략 활성화 시 매도 후 관심종목이 초기화됩니다.\n계속하시겠습니까?\n',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No
        )
        if buttonReply == QtWidgets.QMessageBox.Yes:
            coinQ.put('스패셜전략')

    def CheckboxChanged_01(self, state):
        if state == Qt.Checked:
            con = sqlite3.connect(DB_SETTING)
            df = pd.read_sql('SELECT * FROM kiwoom', con).set_index('index')
            con.close()
            if len(df) == 0 or df['아이디2'][0] == '':
                self.sj_main_checkBox_01.nextCheckState()
                QtWidgets.QMessageBox.critical(
                    self, '오류 알림',
                    '키움 두번째 계정이 설정되지 않아\n콜렉터를 선택할 수 없습니다.\n계정 설정 후 다시 선택하십시오.\n'
                )

    def CheckboxChanged_02(self, state):
        if state == Qt.Checked:
            con = sqlite3.connect(DB_SETTING)
            df = pd.read_sql('SELECT * FROM kiwoom', con).set_index('index')
            con.close()
            if len(df) == 0 or df['아이디1'][0] == '':
                self.sj_main_checkBox_02.nextCheckState()
                QtWidgets.QMessageBox.critical(
                    self, '오류 알림',
                    '키움 첫번째 계정이 설정되지 않아\n트레이더를 선택할 수 없습니다.\n계정 설정 후 다시 선택하십시오.\n'
                )

    def CheckboxChanged_03(self, state):
        if state == Qt.Checked:
            con = sqlite3.connect(DB_SETTING)
            df = pd.read_sql('SELECT * FROM upbit', con).set_index('index')
            con.close()
            if len(df) == 0 or df['Access_key'][0] == '':
                self.sj_main_checkBox_04.nextCheckState()
                QtWidgets.QMessageBox.critical(
                    self, '오류 알림',
                    '업비트 계정이 설정되지 않아\n트레이더를 선택할 수 없습니다.\n계정 설정 후 다시 선택하십시오.\n'
                )

    @QtCore.pyqtSlot(int)
    def CellClicked_01(self, row):
        item = self.sjg_tableWidget.item(row, 0)
        if item is None:
            return
        name = item.text()
        oc = comma2int(self.sjg_tableWidget.item(row, columns_jg.index('보유수량')).text())
        c = comma2int(self.sjg_tableWidget.item(row, columns_jg.index('현재가')).text())
        buttonReply = QtWidgets.QMessageBox.question(
            self, '주식 시장가 매도', f'{name} {oc}주를 시장가매도합니다.\n계속하시겠습니까?\n',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No
        )
        if buttonReply == QtWidgets.QMessageBox.Yes:
            stockQ.put(['매도', self.dict_code[name], name, c, oc])

    @QtCore.pyqtSlot(int)
    def CellClicked_02(self, row):
        item = self.cjg_tableWidget.item(row, 0)
        if item is None:
            return
        ticker = item.text()
        oc = comma2float(self.cjg_tableWidget.item(row, columns_jg.index('보유수량')).text())
        c = comma2float(self.cjg_tableWidget.item(row, columns_jg.index('현재가')).text())
        buttonReply = QtWidgets.QMessageBox.question(
            self, '코인 시장가 매도', f'{ticker} {oc}개를 시장가매도합니다.\n계속하시겠습니까?\n',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No
        )
        if buttonReply == QtWidgets.QMessageBox.Yes:
            coinQ.put(['매도', ticker, c, oc])

    def ButtonClicked_1(self):
        if self.main_tabWidget.currentWidget() == self.st_tab:
            if not self.s_calendarWidget.isVisible():
                boolean1 = False
                boolean2 = True
                self.tt_pushButton.setStyleSheet(style_bc_dk)
            else:
                boolean1 = True
                boolean2 = False
                self.tt_pushButton.setStyleSheet(style_bc_bt)
            self.stt_tableWidget.setVisible(boolean1)
            self.std_tableWidget.setVisible(boolean1)
            self.stj_tableWidget.setVisible(boolean1)
            self.sjg_tableWidget.setVisible(boolean1)
            self.sgj_tableWidget.setVisible(boolean1)
            self.scj_tableWidget.setVisible(boolean1)
            self.s_calendarWidget.setVisible(boolean2)
            self.sdt_tableWidget.setVisible(boolean2)
            self.sds_tableWidget.setVisible(boolean2)
            self.snt_pushButton_01.setVisible(boolean2)
            self.snt_pushButton_02.setVisible(boolean2)
            self.snt_pushButton_03.setVisible(boolean2)
            self.snt_tableWidget.setVisible(boolean2)
            self.sns_tableWidget.setVisible(boolean2)
        elif self.main_tabWidget.currentWidget() == self.ct_tab:
            if not self.c_calendarWidget.isVisible():
                boolean1 = False
                boolean2 = True
                self.tt_pushButton.setStyleSheet(style_bc_dk)
            else:
                boolean1 = True
                boolean2 = False
                self.tt_pushButton.setStyleSheet(style_bc_bt)
            self.ctt_tableWidget.setVisible(boolean1)
            self.ctd_tableWidget.setVisible(boolean1)
            self.ctj_tableWidget.setVisible(boolean1)
            self.cjg_tableWidget.setVisible(boolean1)
            self.cgj_tableWidget.setVisible(boolean1)
            self.ccj_tableWidget.setVisible(boolean1)
            self.c_calendarWidget.setVisible(boolean2)
            self.cdt_tableWidget.setVisible(boolean2)
            self.cds_tableWidget.setVisible(boolean2)
            self.cnt_pushButton_01.setVisible(boolean2)
            self.cnt_pushButton_02.setVisible(boolean2)
            self.cnt_pushButton_03.setVisible(boolean2)
            self.cnt_tableWidget.setVisible(boolean2)
            self.cns_tableWidget.setVisible(boolean2)
        else:
            QtWidgets.QMessageBox.warning(self, '오류 알림', '해당 버튼은 트레이더탭에서만 작동합니다.\n')

    # noinspection PyArgumentList
    def ButtonClicked_2(self):
        buttonReply = QtWidgets.QMessageBox.question(
            self, '주식 수동 시작', '주식 콜렉터 또는 트레이더를 시작합니다.\n계속하시겠습니까?\n',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No
        )
        if buttonReply == QtWidgets.QMessageBox.Yes:
            if DICT_SET['아이디1'] is None:
                QtWidgets.QMessageBox.critical(
                    self, '오류 알림',
                    '키움 첫번째 계정이 설정되지 않아\n콜렉터를 시작할 수 없습니다.\n계정 설정 후 다시 시작하십시오.\n'
                )
            else:
                self.KiwoomCollectorStart()
                QTest.qWait(20000)
            if DICT_SET['아이디2'] is None:
                QtWidgets.QMessageBox.critical(
                    self, '오류 알림',
                    '키움 두번째 계정이 설정되지 않아\n트레이더를 시작할 수 없습니다.\n계정 설정 후 다시 시작하십시오.\n'
                )
            else:
                self.KiwoomTraderStart()

    def ButtonClicked_3(self):
        if self.geometry().width() > 1000:
            self.setFixedSize(722, 383)
            self.zo_pushButton.setStyleSheet(style_bc_dk)
        else:
            self.setFixedSize(1403, 763)
            self.zo_pushButton.setStyleSheet(style_bc_bt)

    def ButtonClicked_4(self):
        buttonReply = QtWidgets.QMessageBox.warning(
            self, '최적화 백테스터 초기화', '최적화 백테스터의 기본값이 모두 초기화됩니다.\n계속하시겠습니까?\n',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No
        )
        if buttonReply == QtWidgets.QMessageBox.Yes:
            columns = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25,
                       26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47]
            data = [10, 14, 36000, 90000, 100000, 3, 4, 5, 6, 7, 8, 9, 0.1, 0.1,
                    30, 60, 90, 120, 150, 180, 30, 3, 0, 500, 50, 10, 50, 100, 10, 10,
                    0, 100000, 10000, 1000, 0, 10, 1, 0.1, 25, 15, -1, -1, 3, 10, 1, 0.2, 6]
            df = pd.DataFrame([data], columns=columns, index=[0])
            query1Q.put([1, df, 'stockback_jcv', 'replace'])
            data = [10, 14, 1008000, 90000, 100000, 3, 4, 5, 6, 7, 8, 9, 0.1, 0.1,
                    30, 60, 90, 120, 150, 180, 30, 3, 0, 100000000, 10000000, 10000000,
                    50, 100, 10, 10, 0, 1000000000, 100000000, 100000000,
                    0, 10, 1, 0.1, 25, 15, -1, -1, 3, 10, 1, 0.2, 6]
            df = pd.DataFrame([data], columns=columns, index=[0])
            query1Q.put([1, df, 'coinback_jjv', 'replace'])
            self.bd_pushButton.setStyleSheet(style_bc_dk)

    def ButtonClicked_5(self):
        buttonReply = QtWidgets.QMessageBox.warning(
            self, '데이터베이스 초기화', '체결목록, 잔고목록, 거래목록, 일별목록이 모두 초기화됩니다.\n계속하시겠습니까?\n',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No
        )
        if buttonReply == QtWidgets.QMessageBox.Yes:
            query1Q.put([2, 'DELETE FROM s_jangolist'])
            query1Q.put([2, 'DELETE FROM s_tradelist'])
            query1Q.put([2, 'DELETE FROM s_chegeollist'])
            query1Q.put([2, 'DELETE FROM s_totaltradelist'])
            query1Q.put([2, 'DELETE FROM c_jangolist'])
            query1Q.put([2, 'DELETE FROM c_tradelist'])
            query1Q.put([2, 'DELETE FROM c_chegeollist'])
            query1Q.put([2, 'DELETE FROM c_totaltradelist'])
            self.dd_pushButton.setStyleSheet(style_bc_dk)

    def ButtonClicked_6(self):
        buttonReply = QtWidgets.QMessageBox.warning(
            self, '계정 설정 초기화', '계정 설정 항목이 모두 초기화됩니다.\n계속하시겠습니까?\n',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No
        )
        if buttonReply == QtWidgets.QMessageBox.Yes:
            query1Q.put([1, 'DELETE FROM kiwoom'])
            query1Q.put([1, 'DELETE FROM upbit'])
            query1Q.put([1, 'DELETE FROM telegram'])
            self.sd_pushButton.setStyleSheet(style_bc_dk)

    def ButtonClicked_7(self, cmd):
        if '집계' in cmd:
            if 'S' in cmd:
                gubun = 'S'
                table = 's_totaltradelist'
            else:
                gubun = 'C'
                table = 'c_totaltradelist'
            con = sqlite3.connect(DB_TRADELIST)
            df = pd.read_sql(f'SELECT * FROM {table}', con)
            con.close()
            df = df[::-1]
            if len(df) > 0:
                sd = strp_time('%Y%m%d', df['index'][df.index[0]])
                ld = strp_time('%Y%m%d', df['index'][df.index[-1]])
                pr = str((sd - ld).days + 1) + '일'
                nbg, nsg = df['총매수금액'].sum(), df['총매도금액'].sum()
                sp = round((nsg / nbg - 1) * 100, 2)
                npg, nmg = df['총수익금액'].sum(), df['총손실금액'].sum()
                nsig = df['수익금합계'].sum()
                df2 = pd.DataFrame(columns=columns_nt)
                df2.at[0] = pr, nbg, nsg, npg, nmg, sp, nsig
                self.UpdateTablewidget([ui_num[f'{gubun}누적합계'], df2])
            else:
                QtWidgets.QMessageBox.critical(self, '오류 알림', '거래목록이 존재하지 않습니다.\n')
                return
            if cmd == '일별집계':
                df = df.rename(columns={'index': '일자'})
                self.UpdateTablewidget([ui_num[f'{gubun}누적상세'], df])
            elif cmd == '월별집계':
                df['일자'] = df['index'].apply(lambda x: x[:6])
                df2 = pd.DataFrame(columns=columns_nd)
                lastmonth = df['일자'][df.index[-1]]
                month = strf_time('%Y%m')
                while int(month) >= int(lastmonth):
                    df3 = df[df['일자'] == month]
                    if len(df3) > 0:
                        tbg, tsg = df3['총매수금액'].sum(), df3['총매도금액'].sum()
                        sp = round((tsg / tbg - 1) * 100, 2)
                        tpg, tmg = df3['총수익금액'].sum(), df3['총손실금액'].sum()
                        ttsg = df3['수익금합계'].sum()
                        df2.at[month] = month, tbg, tsg, tpg, tmg, sp, ttsg
                    month = str(int(month) - 89) if int(month[4:]) == 1 else str(int(month) - 1)
                self.UpdateTablewidget([ui_num[f'{gubun}누적상세'], df2])
            elif cmd == '연도별집계':
                df['일자'] = df['index'].apply(lambda x: x[:4])
                df2 = pd.DataFrame(columns=columns_nd)
                lastyear = df['일자'][df.index[-1]]
                year = strf_time('%Y')
                while int(year) >= int(lastyear):
                    df3 = df[df['일자'] == year]
                    if len(df3) > 0:
                        tbg, tsg = df3['총매수금액'].sum(), df3['총매도금액'].sum()
                        sp = round((tsg / tbg - 1) * 100, 2)
                        tpg, tmg = df3['총수익금액'].sum(), df3['총손실금액'].sum()
                        ttsg = df3['수익금합계'].sum()
                        df2.at[year] = year, tbg, tsg, tpg, tmg, sp, ttsg
                    year = str(int(year) - 1)
                self.UpdateTablewidget([ui_num[f'{gubun}누적상세'], df2])

    def ButtonClicked_8(self):
        con = sqlite3.connect(DB_SETTING)
        df = pd.read_sql('SELECT * FROM stockback_jcv', con)
        df = df.set_index('index')
        con.close()
        self.sbvc_lineEdit_01.setText(str(df['1'][0]))
        self.sbvc_lineEdit_02.setText(str(df['2'][0]))
        self.sbvc_lineEdit_03.setText(str(df['3'][0]))
        self.sbvc_lineEdit_04.setText(str(df['4'][0]))
        self.sbvc_lineEdit_05.setText(str(df['5'][0]))
        self.sbvc_lineEdit_06.setText(str(df['6'][0]))
        self.sbvc_lineEdit_07.setText(str(df['7'][0]))
        self.sbvc_lineEdit_08.setText(str(df['8'][0]))
        self.sbvc_lineEdit_09.setText(str(df['9'][0]))
        self.sbvc_lineEdit_10.setText(str(df['10'][0]))
        self.sbvc_lineEdit_11.setText(str(df['11'][0]))
        self.sbvc_lineEdit_12.setText(str(df['12'][0]))
        self.sbvc_lineEdit_13.setText(str(df['13'][0]))
        self.sbvc_lineEdit_14.setText(str(df['14'][0]))
        self.sbvc_lineEdit_15.setText(str(df['15'][0]))
        self.sbvc_lineEdit_16.setText(str(df['16'][0]))
        self.sbvc_lineEdit_17.setText(str(df['17'][0]))
        self.sbvc_lineEdit_18.setText(str(df['18'][0]))
        self.sbvc_lineEdit_19.setText(str(df['19'][0]))
        self.sbvc_lineEdit_20.setText(str(df['20'][0]))
        self.sbvc_lineEdit_21.setText(str(df['21'][0]))
        self.sbvc_lineEdit_22.setText(str(df['22'][0]))
        self.sbvc_lineEdit_23.setText(str(df['23'][0]))
        self.sbvc_lineEdit_24.setText(str(df['24'][0]))
        self.sbvc_lineEdit_25.setText(str(df['25'][0]))
        self.sbvc_lineEdit_26.setText(str(df['26'][0]))
        self.sbvc_lineEdit_27.setText(str(df['27'][0]))
        self.sbvc_lineEdit_28.setText(str(df['28'][0]))
        self.sbvc_lineEdit_29.setText(str(df['29'][0]))
        self.sbvc_lineEdit_30.setText(str(df['30'][0]))
        self.sbvc_lineEdit_31.setText(str(df['31'][0]))
        self.sbvc_lineEdit_32.setText(str(df['32'][0]))
        self.sbvc_lineEdit_33.setText(str(df['33'][0]))
        self.sbvc_lineEdit_34.setText(str(df['34'][0]))
        self.sbvc_lineEdit_35.setText(str(df['35'][0]))
        self.sbvc_lineEdit_36.setText(str(df['36'][0]))
        self.sbvc_lineEdit_37.setText(str(df['37'][0]))
        self.sbvc_lineEdit_38.setText(str(df['38'][0]))
        self.sbvc_lineEdit_39.setText(str(df['39'][0]))
        self.sbvc_lineEdit_40.setText(str(df['40'][0]))
        self.sbvc_lineEdit_41.setText(str(df['41'][0]))
        self.sbvc_lineEdit_42.setText(str(df['42'][0]))
        self.sbvc_lineEdit_43.setText(str(df['43'][0]))
        self.sbvc_lineEdit_44.setText(str(df['44'][0]))
        self.sbvc_lineEdit_45.setText(str(df['45'][0]))
        self.sbvc_lineEdit_46.setText(str(df['46'][0]))
        self.sbvc_lineEdit_47.setText(str(df['47'][0]))

    def ButtonClicked_9(self):
        if self.backtester_proc is not None and self.backtester_proc.poll() != 0:
            QtWidgets.QMessageBox.critical(self, '오류 알림', '현재 백테스터가 실행중입니다.\n중복 실행할 수 없습니다.\n')
            return
        textfull = True
        if self.sbvc_lineEdit_01.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_02.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_03.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_04.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_05.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_06.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_07.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_08.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_09.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_10.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_11.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_12.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_13.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_14.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_15.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_16.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_17.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_18.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_19.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_20.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_21.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_22.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_23.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_24.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_25.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_26.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_27.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_28.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_29.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_30.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_31.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_32.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_33.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_34.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_35.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_36.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_37.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_38.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_39.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_40.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_41.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_42.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_43.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_44.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_45.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_46.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_47.text() == '':
            textfull = False
        if not textfull:
            QtWidgets.QMessageBox.critical(self, '오류 알림', '일부 변수값이 입력되지 않았습니다.\n')
            return
        self.backtester_proc = subprocess.Popen(
            f'python {SYSTEM_PATH}/backtester/backtester_stock_vc.py '
            f'{self.sbvc_lineEdit_01.text()} {self.sbvc_lineEdit_02.text()} {self.sbvc_lineEdit_03.text()} '
            f'{self.sbvc_lineEdit_04.text()} {self.sbvc_lineEdit_05.text()} {self.sbvc_lineEdit_06.text()} '
            f'{self.sbvc_lineEdit_07.text()} {self.sbvc_lineEdit_08.text()} {self.sbvc_lineEdit_09.text()} '
            f'{self.sbvc_lineEdit_10.text()} {self.sbvc_lineEdit_11.text()} {self.sbvc_lineEdit_12.text()} '
            f'{self.sbvc_lineEdit_13.text()} {self.sbvc_lineEdit_14.text()} {self.sbvc_lineEdit_15.text()} '
            f'{self.sbvc_lineEdit_16.text()} {self.sbvc_lineEdit_17.text()} {self.sbvc_lineEdit_18.text()} '
            f'{self.sbvc_lineEdit_19.text()} {self.sbvc_lineEdit_20.text()} {self.sbvc_lineEdit_21.text()} '
            f'{self.sbvc_lineEdit_22.text()} {self.sbvc_lineEdit_23.text()} {self.sbvc_lineEdit_24.text()} '
            f'{self.sbvc_lineEdit_25.text()} {self.sbvc_lineEdit_26.text()} {self.sbvc_lineEdit_27.text()} '
            f'{self.sbvc_lineEdit_28.text()} {self.sbvc_lineEdit_29.text()} {self.sbvc_lineEdit_30.text()} '
            f'{self.sbvc_lineEdit_31.text()} {self.sbvc_lineEdit_32.text()} {self.sbvc_lineEdit_33.text()} '
            f'{self.sbvc_lineEdit_34.text()} {self.sbvc_lineEdit_35.text()} {self.sbvc_lineEdit_36.text()} '
            f'{self.sbvc_lineEdit_37.text()} {self.sbvc_lineEdit_38.text()} {self.sbvc_lineEdit_39.text()} '
            f'{self.sbvc_lineEdit_40.text()} {self.sbvc_lineEdit_41.text()} {self.sbvc_lineEdit_42.text()} '
            f'{self.sbvc_lineEdit_43.text()} {self.sbvc_lineEdit_44.text()} {self.sbvc_lineEdit_45.text()} '
            f'{self.sbvc_lineEdit_46.text()} {self.sbvc_lineEdit_47.text()}'
        )

    def ButtonClicked_10(self):
        textfull = True
        if self.sbvc_lineEdit_01.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_02.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_03.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_04.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_05.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_06.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_07.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_08.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_09.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_10.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_11.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_12.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_13.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_14.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_15.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_16.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_17.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_18.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_19.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_20.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_21.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_22.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_23.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_24.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_25.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_26.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_27.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_28.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_29.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_30.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_31.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_32.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_33.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_34.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_35.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_36.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_37.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_38.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_39.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_40.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_41.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_42.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_43.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_44.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_45.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_46.text() == '':
            textfull = False
        elif self.sbvc_lineEdit_47.text() == '':
            textfull = False
        if not textfull:
            QtWidgets.QMessageBox.critical(self, '오류 알림', '일부 변수값이 입력되지 않았습니다.\n')
            return
        data = [
            self.sbvc_lineEdit_01.text(), self.sbvc_lineEdit_02.text(), self.sbvc_lineEdit_03.text(),
            self.sbvc_lineEdit_04.text(), self.sbvc_lineEdit_05.text(), self.sbvc_lineEdit_06.text(),
            self.sbvc_lineEdit_07.text(), self.sbvc_lineEdit_08.text(), self.sbvc_lineEdit_09.text(),
            self.sbvc_lineEdit_10.text(), self.sbvc_lineEdit_11.text(), self.sbvc_lineEdit_12.text(),
            self.sbvc_lineEdit_13.text(), self.sbvc_lineEdit_14.text(), self.sbvc_lineEdit_15.text(),
            self.sbvc_lineEdit_16.text(), self.sbvc_lineEdit_17.text(), self.sbvc_lineEdit_18.text(),
            self.sbvc_lineEdit_19.text(), self.sbvc_lineEdit_20.text(), self.sbvc_lineEdit_21.text(),
            self.sbvc_lineEdit_22.text(), self.sbvc_lineEdit_23.text(), self.sbvc_lineEdit_24.text(),
            self.sbvc_lineEdit_25.text(), self.sbvc_lineEdit_26.text(), self.sbvc_lineEdit_27.text(),
            self.sbvc_lineEdit_28.text(), self.sbvc_lineEdit_29.text(), self.sbvc_lineEdit_30.text(),
            self.sbvc_lineEdit_31.text(), self.sbvc_lineEdit_32.text(), self.sbvc_lineEdit_33.text(),
            self.sbvc_lineEdit_34.text(), self.sbvc_lineEdit_35.text(), self.sbvc_lineEdit_36.text(),
            self.sbvc_lineEdit_37.text(), self.sbvc_lineEdit_38.text(), self.sbvc_lineEdit_39.text(),
            self.sbvc_lineEdit_40.text(), self.sbvc_lineEdit_41.text(), self.sbvc_lineEdit_42.text(),
            self.sbvc_lineEdit_43.text(), self.sbvc_lineEdit_44.text(), self.sbvc_lineEdit_45.text(),
            self.sbvc_lineEdit_46.text(), self.sbvc_lineEdit_47.text()
        ]
        columns = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25,
                   26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47]
        df = pd.DataFrame([data], columns=columns, index=[0])
        query1Q.put([1, df, 'stockback_jcv', 'replace'])

    def ButtonClicked_11(self):
        con = sqlite3.connect(DB_SETTING)
        df = pd.read_sql('SELECT * FROM stock', con)
        df = df.set_index('index')
        con.close()
        self.sbvj_lineEdit_01.setText(str(df['종목당투자금'][0]))
        self.sbvj_lineEdit_02.setText(str(df['백테스팅기간'][0]))
        self.sbvj_lineEdit_03.setText(str(df['백테스팅시간'][0]))
        self.sbvj_lineEdit_04.setText(str(df['시작시간'][0]))
        self.sbvj_lineEdit_05.setText(str(df['종료시간'][0]))
        self.sbvj_lineEdit_06.setText(str(df['체결강도차이'][0]))
        self.sbvj_lineEdit_07.setText(str(df['평균시간'][0]))
        self.sbvj_lineEdit_08.setText(str(df['거래대금차이'][0]))
        self.sbvj_lineEdit_09.setText(str(df['체결강도하한'][0]))
        self.sbvj_lineEdit_10.setText(str(df['누적거래대금하한'][0]))
        self.sbvj_lineEdit_11.setText(str(df['등락율하한'][0]))
        self.sbvj_lineEdit_12.setText(str(df['등락율상한'][0]))
        self.sbvj_lineEdit_13.setText(str(df['청산수익률'][0]))
        self.sbvj_lineEdit_14.setText(str(df['멀티프로세스'][0]))

    def ButtonClicked_12(self):
        if self.backtester_proc is not None and self.backtester_proc.poll() != 0:
            QtWidgets.QMessageBox.critical(self, '오류 알림', '현재 백테스터가 실행중입니다.\n중복 실행할 수 없습니다.\n')
            return
        textfull = True
        if self.sbvj_lineEdit_01.text() == '':
            textfull = False
        elif self.sbvj_lineEdit_02.text() == '':
            textfull = False
        elif self.sbvj_lineEdit_03.text() == '':
            textfull = False
        elif self.sbvj_lineEdit_04.text() == '':
            textfull = False
        elif self.sbvj_lineEdit_05.text() == '':
            textfull = False
        elif self.sbvj_lineEdit_06.text() == '':
            textfull = False
        elif self.sbvj_lineEdit_07.text() == '':
            textfull = False
        elif self.sbvj_lineEdit_08.text() == '':
            textfull = False
        elif self.sbvj_lineEdit_09.text() == '':
            textfull = False
        elif self.sbvj_lineEdit_10.text() == '':
            textfull = False
        elif self.sbvj_lineEdit_11.text() == '':
            textfull = False
        elif self.sbvj_lineEdit_12.text() == '':
            textfull = False
        elif self.sbvj_lineEdit_13.text() == '':
            textfull = False
        elif self.sbvj_lineEdit_14.text() == '':
            textfull = False
        if not textfull:
            QtWidgets.QMessageBox.critical(self, '오류 알림', '일부 변수값이 입력되지 않았습니다.\n')
            return
        self.backtester_proc = subprocess.Popen(
            f'python {SYSTEM_PATH}/backtester/backtester_stock_vj.py '
            f'{self.sbvj_lineEdit_01.text()} {self.sbvj_lineEdit_02.text()} {self.sbvj_lineEdit_03.text()} '
            f'{self.sbvj_lineEdit_04.text()} {self.sbvj_lineEdit_05.text()} {self.sbvj_lineEdit_06.text()} '
            f'{self.sbvj_lineEdit_07.text()} {self.sbvj_lineEdit_08.text()} {self.sbvj_lineEdit_09.text()} '
            f'{self.sbvj_lineEdit_10.text()} {self.sbvj_lineEdit_11.text()} {self.sbvj_lineEdit_12.text()} '
            f'{self.sbvj_lineEdit_13.text()} {self.sbvj_lineEdit_14.text()}'
        )

    def ButtonClicked_13(self):
        con = sqlite3.connect(DB_SETTING)
        df = pd.read_sql('SELECT * FROM coinback_jjv', con)
        df = df.set_index('index')
        con.close()
        self.cbvc_lineEdit_01.setText(str(df['1'][0]))
        self.cbvc_lineEdit_02.setText(str(df['2'][0]))
        self.cbvc_lineEdit_03.setText(str(df['3'][0]))
        self.cbvc_lineEdit_04.setText(str(df['4'][0]))
        self.cbvc_lineEdit_05.setText(str(df['5'][0]))
        self.cbvc_lineEdit_06.setText(str(df['6'][0]))
        self.cbvc_lineEdit_07.setText(str(df['7'][0]))
        self.cbvc_lineEdit_08.setText(str(df['8'][0]))
        self.cbvc_lineEdit_09.setText(str(df['9'][0]))
        self.cbvc_lineEdit_10.setText(str(df['10'][0]))
        self.cbvc_lineEdit_11.setText(str(df['11'][0]))
        self.cbvc_lineEdit_12.setText(str(df['12'][0]))
        self.cbvc_lineEdit_13.setText(str(df['13'][0]))
        self.cbvc_lineEdit_14.setText(str(df['14'][0]))
        self.cbvc_lineEdit_15.setText(str(df['15'][0]))
        self.cbvc_lineEdit_16.setText(str(df['16'][0]))
        self.cbvc_lineEdit_17.setText(str(df['17'][0]))
        self.cbvc_lineEdit_18.setText(str(df['18'][0]))
        self.cbvc_lineEdit_19.setText(str(df['19'][0]))
        self.cbvc_lineEdit_20.setText(str(df['20'][0]))
        self.cbvc_lineEdit_21.setText(str(df['21'][0]))
        self.cbvc_lineEdit_22.setText(str(df['22'][0]))
        self.cbvc_lineEdit_23.setText(str(df['23'][0]))
        self.cbvc_lineEdit_24.setText(str(df['24'][0]))
        self.cbvc_lineEdit_25.setText(str(df['25'][0]))
        self.cbvc_lineEdit_26.setText(str(df['26'][0]))
        self.cbvc_lineEdit_27.setText(str(df['27'][0]))
        self.cbvc_lineEdit_28.setText(str(df['28'][0]))
        self.cbvc_lineEdit_29.setText(str(df['29'][0]))
        self.cbvc_lineEdit_30.setText(str(df['30'][0]))
        self.cbvc_lineEdit_31.setText(str(df['31'][0]))
        self.cbvc_lineEdit_32.setText(str(df['32'][0]))
        self.cbvc_lineEdit_33.setText(str(df['33'][0]))
        self.cbvc_lineEdit_34.setText(str(df['34'][0]))
        self.cbvc_lineEdit_35.setText(str(df['35'][0]))
        self.cbvc_lineEdit_36.setText(str(df['36'][0]))
        self.cbvc_lineEdit_37.setText(str(df['37'][0]))
        self.cbvc_lineEdit_38.setText(str(df['38'][0]))
        self.cbvc_lineEdit_39.setText(str(df['39'][0]))
        self.cbvc_lineEdit_40.setText(str(df['40'][0]))
        self.cbvc_lineEdit_41.setText(str(df['41'][0]))
        self.cbvc_lineEdit_42.setText(str(df['42'][0]))
        self.cbvc_lineEdit_43.setText(str(df['43'][0]))
        self.cbvc_lineEdit_44.setText(str(df['44'][0]))
        self.cbvc_lineEdit_45.setText(str(df['45'][0]))
        self.cbvc_lineEdit_46.setText(str(df['46'][0]))
        self.cbvc_lineEdit_47.setText(str(df['47'][0]))

    def ButtonClicked_14(self):
        if self.backtester_proc is not None and self.backtester_proc.poll() != 0:
            QtWidgets.QMessageBox.critical(self, '오류 알림', '현재 백테스터가 실행중입니다.\n중복 실행할 수 없습니다.\n')
            return
        textfull = True
        if self.cbvc_lineEdit_01.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_02.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_03.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_04.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_05.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_06.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_07.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_08.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_09.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_10.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_11.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_12.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_13.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_14.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_15.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_16.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_17.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_18.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_19.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_20.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_21.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_22.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_23.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_24.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_25.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_26.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_27.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_28.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_29.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_30.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_31.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_32.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_33.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_34.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_35.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_36.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_37.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_38.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_39.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_40.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_41.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_42.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_43.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_44.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_45.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_46.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_47.text() == '':
            textfull = False
        if not textfull:
            QtWidgets.QMessageBox.critical(self, '오류 알림', '일부 변수값이 입력되지 않았습니다.\n')
            return
        self.backtester_proc = subprocess.Popen(
            f'python {SYSTEM_PATH}/backtester/backtester_coin_vc.py '
            f'{self.cbvc_lineEdit_01.text()} {self.cbvc_lineEdit_02.text()} {self.cbvc_lineEdit_03.text()} '
            f'{self.cbvc_lineEdit_04.text()} {self.cbvc_lineEdit_05.text()} {self.cbvc_lineEdit_06.text()} '
            f'{self.cbvc_lineEdit_07.text()} {self.cbvc_lineEdit_08.text()} {self.cbvc_lineEdit_09.text()} '
            f'{self.cbvc_lineEdit_10.text()} {self.cbvc_lineEdit_11.text()} {self.cbvc_lineEdit_12.text()} '
            f'{self.cbvc_lineEdit_13.text()} {self.cbvc_lineEdit_14.text()} {self.cbvc_lineEdit_15.text()} '
            f'{self.cbvc_lineEdit_16.text()} {self.cbvc_lineEdit_17.text()} {self.cbvc_lineEdit_18.text()} '
            f'{self.cbvc_lineEdit_19.text()} {self.cbvc_lineEdit_20.text()} {self.cbvc_lineEdit_21.text()} '
            f'{self.cbvc_lineEdit_22.text()} {self.cbvc_lineEdit_23.text()} {self.cbvc_lineEdit_24.text()} '
            f'{self.cbvc_lineEdit_25.text()} {self.cbvc_lineEdit_26.text()} {self.cbvc_lineEdit_27.text()} '
            f'{self.cbvc_lineEdit_28.text()} {self.cbvc_lineEdit_29.text()} {self.cbvc_lineEdit_30.text()} '
            f'{self.cbvc_lineEdit_31.text()} {self.cbvc_lineEdit_32.text()} {self.cbvc_lineEdit_33.text()} '
            f'{self.cbvc_lineEdit_34.text()} {self.cbvc_lineEdit_35.text()} {self.cbvc_lineEdit_36.text()} '
            f'{self.cbvc_lineEdit_37.text()} {self.cbvc_lineEdit_38.text()} {self.cbvc_lineEdit_39.text()} '
            f'{self.cbvc_lineEdit_40.text()} {self.cbvc_lineEdit_41.text()} {self.cbvc_lineEdit_42.text()} '
            f'{self.cbvc_lineEdit_43.text()} {self.cbvc_lineEdit_44.text()} {self.cbvc_lineEdit_45.text()} '
            f'{self.cbvc_lineEdit_46.text()} {self.cbvc_lineEdit_47.text()}'
        )

    def ButtonClicked_15(self):
        textfull = True
        if self.cbvc_lineEdit_01.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_02.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_03.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_04.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_05.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_06.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_07.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_08.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_09.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_10.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_11.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_12.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_13.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_14.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_15.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_16.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_17.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_18.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_19.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_20.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_21.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_22.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_23.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_24.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_25.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_26.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_27.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_28.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_29.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_30.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_31.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_32.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_33.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_34.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_35.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_36.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_37.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_38.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_39.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_40.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_41.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_42.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_43.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_44.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_45.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_46.text() == '':
            textfull = False
        elif self.cbvc_lineEdit_47.text() == '':
            textfull = False
        if not textfull:
            QtWidgets.QMessageBox.critical(self, '오류 알림', '일부 변수값이 입력되지 않았습니다.\n')
            return
        data = [
            self.cbvc_lineEdit_01.text(), self.cbvc_lineEdit_02.text(), self.cbvc_lineEdit_03.text(),
            self.cbvc_lineEdit_04.text(), self.cbvc_lineEdit_05.text(), self.cbvc_lineEdit_06.text(),
            self.cbvc_lineEdit_07.text(), self.cbvc_lineEdit_08.text(), self.cbvc_lineEdit_09.text(),
            self.cbvc_lineEdit_10.text(), self.cbvc_lineEdit_11.text(), self.cbvc_lineEdit_12.text(),
            self.cbvc_lineEdit_13.text(), self.cbvc_lineEdit_14.text(), self.cbvc_lineEdit_15.text(),
            self.cbvc_lineEdit_16.text(), self.cbvc_lineEdit_17.text(), self.cbvc_lineEdit_18.text(),
            self.cbvc_lineEdit_19.text(), self.cbvc_lineEdit_20.text(), self.cbvc_lineEdit_21.text(),
            self.cbvc_lineEdit_22.text(), self.cbvc_lineEdit_23.text(), self.cbvc_lineEdit_24.text(),
            self.cbvc_lineEdit_25.text(), self.cbvc_lineEdit_26.text(), self.cbvc_lineEdit_27.text(),
            self.cbvc_lineEdit_28.text(), self.cbvc_lineEdit_29.text(), self.cbvc_lineEdit_30.text(),
            self.cbvc_lineEdit_31.text(), self.cbvc_lineEdit_32.text(), self.cbvc_lineEdit_33.text(),
            self.cbvc_lineEdit_34.text(), self.cbvc_lineEdit_35.text(), self.cbvc_lineEdit_36.text(),
            self.cbvc_lineEdit_37.text(), self.cbvc_lineEdit_38.text(), self.cbvc_lineEdit_39.text(),
            self.cbvc_lineEdit_40.text(), self.cbvc_lineEdit_41.text(), self.cbvc_lineEdit_42.text(),
            self.cbvc_lineEdit_43.text(), self.cbvc_lineEdit_44.text(), self.cbvc_lineEdit_45.text(),
            self.cbvc_lineEdit_46.text(), self.cbvc_lineEdit_47.text()
        ]
        columns = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25,
                   26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47]
        df = pd.DataFrame([data], columns=columns, index=[0])
        query1Q.put([1, df, 'coinback_jjv', 'replace'])

    def ButtonClicked_16(self):
        con = sqlite3.connect(DB_SETTING)
        df = pd.read_sql('SELECT * FROM coin', con)
        df = df.set_index('index')
        con.close()
        self.cbvj_lineEdit_01.setText(str(df['종목당투자금'][0]))
        self.cbvj_lineEdit_02.setText(str(df['백테스팅기간'][0]))
        self.cbvj_lineEdit_03.setText(str(df['백테스팅시간'][0]))
        self.cbvj_lineEdit_04.setText(str(df['시작시간'][0]))
        self.cbvj_lineEdit_05.setText(str(df['종료시간'][0]))
        self.cbvj_lineEdit_06.setText(str(df['체결강도차이'][0]))
        self.cbvj_lineEdit_07.setText(str(df['평균시간'][0]))
        self.cbvj_lineEdit_08.setText(str(df['거래대금차이'][0]))
        self.cbvj_lineEdit_09.setText(str(df['체결강도하한'][0]))
        self.cbvj_lineEdit_10.setText(str(df['누적거래대금하한'][0]))
        self.cbvj_lineEdit_11.setText(str(df['등락율하한'][0]))
        self.cbvj_lineEdit_12.setText(str(df['등락율상한'][0]))
        self.cbvj_lineEdit_13.setText(str(df['청산수익률'][0]))
        self.cbvj_lineEdit_14.setText(str(df['멀티프로세스'][0]))

    def ButtonClicked_17(self):
        if self.backtester_proc is not None and self.backtester_proc.poll() != 0:
            QtWidgets.QMessageBox.critical(self, '오류 알림', '현재 백테스터가 실행중입니다.\n중복 실행할 수 없습니다.\n')
            return
        textfull = True
        if self.cbvj_lineEdit_01.text() == '':
            textfull = False
        elif self.cbvj_lineEdit_02.text() == '':
            textfull = False
        elif self.cbvj_lineEdit_03.text() == '':
            textfull = False
        elif self.cbvj_lineEdit_04.text() == '':
            textfull = False
        elif self.cbvj_lineEdit_05.text() == '':
            textfull = False
        elif self.cbvj_lineEdit_06.text() == '':
            textfull = False
        elif self.cbvj_lineEdit_07.text() == '':
            textfull = False
        elif self.cbvj_lineEdit_08.text() == '':
            textfull = False
        elif self.cbvj_lineEdit_09.text() == '':
            textfull = False
        elif self.cbvj_lineEdit_10.text() == '':
            textfull = False
        elif self.cbvj_lineEdit_11.text() == '':
            textfull = False
        elif self.cbvj_lineEdit_12.text() == '':
            textfull = False
        elif self.cbvj_lineEdit_13.text() == '':
            textfull = False
        elif self.cbvj_lineEdit_14.text() == '':
            textfull = False
        if not textfull:
            QtWidgets.QMessageBox.critical(self, '오류 알림', '일부 변수값이 입력되지 않았습니다.\n')
            return
        self.backtester_proc = subprocess.Popen(
            f'python {SYSTEM_PATH}/backtester/backtester_coin_vj.py '
            f'{self.cbvj_lineEdit_01.text()} {self.cbvj_lineEdit_02.text()} {self.cbvj_lineEdit_03.text()} '
            f'{self.cbvj_lineEdit_04.text()} {self.cbvj_lineEdit_05.text()} {self.cbvj_lineEdit_06.text()} '
            f'{self.cbvj_lineEdit_07.text()} {self.cbvj_lineEdit_08.text()} {self.cbvj_lineEdit_09.text()} '
            f'{self.cbvj_lineEdit_10.text()} {self.cbvj_lineEdit_11.text()} {self.cbvj_lineEdit_12.text()} '
            f'{self.cbvj_lineEdit_13.text()} {self.cbvj_lineEdit_14.text()}'
        )

    def ButtonClicked_18(self):
        con = sqlite3.connect(DB_SETTING)
        df = pd.read_sql('SELECT * FROM main', con)
        df = df.set_index('index')
        con.close()
        if len(df) > 0:
            self.sj_main_checkBox_01.setChecked(True) if df['키움콜렉터'][0] else self.sj_main_checkBox_01.setChecked(False)
            self.sj_main_checkBox_02.setChecked(True) if df['키움트레이더'][0] else self.sj_main_checkBox_02.setChecked(False)
            self.sj_main_checkBox_03.setChecked(True) if df['업비트콜렉터'][0] else self.sj_main_checkBox_03.setChecked(False)
            self.sj_main_checkBox_04.setChecked(True) if df['업비트트레이더'][0] else self.sj_main_checkBox_04.setChecked(False)
            self.sj_main_checkBox_05.setChecked(True) if df['백테스터'][0] else self.sj_main_checkBox_05.setChecked(False)
            self.sj_main_lineEdit_01.setText(str(df['시작시간'][0]))
            self.UpdateTexedit([ui_num['설정텍스트'], '시스템 기본 설정값 불러오기 완료'])
        else:
            QtWidgets.QMessageBox.critical(self, '오류 알림', '시스템 기본 설정값이\n존재하지 않습니다.\n')

    def ButtonClicked_19(self):
        con = sqlite3.connect(DB_SETTING)
        df = pd.read_sql('SELECT * FROM kiwoom', con)
        df = df.set_index('index')
        con.close()
        if len(df) > 0:
            self.sj_sacc_lineEdit_01.setText(df['아이디1'][0])
            self.sj_sacc_lineEdit_02.setText(df['비밀번호1'][0])
            self.sj_sacc_lineEdit_03.setText(df['인증서비밀번호1'][0])
            self.sj_sacc_lineEdit_04.setText(df['계좌비밀번호1'][0])
            self.sj_sacc_lineEdit_05.setText(df['아이디2'][0])
            self.sj_sacc_lineEdit_06.setText(df['비밀번호2'][0])
            self.sj_sacc_lineEdit_07.setText(df['인증서비밀번호2'][0])
            self.sj_sacc_lineEdit_08.setText(df['계좌비밀번호2'][0])
            self.UpdateTexedit([ui_num['설정텍스트'], '키움증권 계정 설정값 불러오기 완료'])
        else:
            QtWidgets.QMessageBox.critical(self, '오류 알림', '키움증권 계정 설정값이\n존재하지 않습니다.\n')

    def ButtonClicked_20(self):
        con = sqlite3.connect(DB_SETTING)
        df = pd.read_sql('SELECT * FROM upbit', con)
        df = df.set_index('index')
        con.close()
        if len(df) > 0:
            self.sj_cacc_lineEdit_01.setText(df['Access_key'][0])
            self.sj_cacc_lineEdit_02.setText(df['Secret_key'][0])
            self.UpdateTexedit([ui_num['설정텍스트'], '업비트 계정 설정값 불러오기 완료'])
        else:
            QtWidgets.QMessageBox.critical(self, '오류 알림', '업비트 계정 설정값이\n존재하지 않습니다.\n')

    def ButtonClicked_21(self):
        con = sqlite3.connect(DB_SETTING)
        df = pd.read_sql('SELECT * FROM telegram', con)
        df = df.set_index('index')
        con.close()
        if len(df) > 0:
            self.sj_tele_lineEdit_01.setText(df['str_bot'][0])
            self.sj_tele_lineEdit_02.setText(str(df['int_id'][0]))
            self.UpdateTexedit([ui_num['설정텍스트'], '텔레그램 봇토큰 및 사용자 아이디 설정값 불러오기 완료'])
        else:
            QtWidgets.QMessageBox.critical(self, '오류 알림', '텔레그램 봇토큰 및 사용자 아이디\n설정값이 존재하지 않습니다.\n')

    def ButtonClicked_22(self):
        con = sqlite3.connect(DB_SETTING)
        df = pd.read_sql('SELECT * FROM stock', con)
        df = df.set_index('index')
        con.close()
        if len(df) > 0:
            self.sj_stock_checkBox_01.setChecked(True) if df['모의투자'][0] else self.sj_stock_checkBox_01.setChecked(False)
            self.sj_stock_checkBox_02.setChecked(True) if df['알림소리'][0] else self.sj_stock_checkBox_02.setChecked(False)
            self.sj_stock_lineEdit_01.setText(str(df['콜렉터'][0]))
            self.sj_stock_lineEdit_02.setText(str(df['트레이더'][0]))
            self.sj_stock_lineEdit_03.setText(str(df['잔고청산'][0]))
            self.sj_stock_lineEdit_04.setText(str(df['체결강도차이'][0]))
            self.sj_stock_lineEdit_05.setText(str(df['평균시간'][0]))
            self.sj_stock_lineEdit_06.setText(str(df['거래대금차이'][0]))
            self.sj_stock_lineEdit_07.setText(str(df['체결강도하한'][0]))
            self.sj_stock_lineEdit_08.setText(str(df['누적거래대금하한'][0]))
            self.sj_stock_lineEdit_09.setText(str(df['등락율하한'][0]))
            self.sj_stock_lineEdit_10.setText(str(df['등락율상한'][0]))
            self.sj_stock_lineEdit_11.setText(str(df['청산수익률'][0]))
            self.sj_stock_lineEdit_12.setText(str(df['최대매수종목수'][0]))
            self.UpdateTexedit([ui_num['설정텍스트'], '주식 전략 설정값 불러오기 완료'])
        else:
            QtWidgets.QMessageBox.critical(self, '오류 알림', '주식 전략 설정값이\n존재하지 않습니다.\n')

    def ButtonClicked_23(self):
        con = sqlite3.connect(DB_SETTING)
        df = pd.read_sql('SELECT * FROM coin', con)
        df = df.set_index('index')
        con.close()
        if len(df) > 0:
            self.sj_coin_checkBox_01.setChecked(True) if df['모의투자'][0] else self.sj_coin_checkBox_01.setChecked(False)
            self.sj_coin_checkBox_02.setChecked(True) if df['알림소리'][0] else self.sj_coin_checkBox_02.setChecked(False)
            self.sj_coin_lineEdit_01.setText(str(df['체결강도차이'][0]))
            self.sj_coin_lineEdit_02.setText(str(df['평균시간'][0]))
            self.sj_coin_lineEdit_03.setText(str(df['거래대금차이'][0]))
            self.sj_coin_lineEdit_04.setText(str(df['체결강도하한'][0]))
            self.sj_coin_lineEdit_05.setText(str(df['누적거래대금하한'][0]))
            self.sj_coin_lineEdit_06.setText(str(df['등락율하한'][0]))
            self.sj_coin_lineEdit_07.setText(str(df['등락율상한'][0]))
            self.sj_coin_lineEdit_08.setText(str(df['청산수익률'][0]))
            self.sj_coin_lineEdit_09.setText(str(df['최대매수종목수'][0]))
            self.UpdateTexedit([ui_num['설정텍스트'], '코인 전략 설정값 불러오기 완료'])
        else:
            QtWidgets.QMessageBox.critical(self, '오류 알림', '코인 전략 설정값이\n존재하지 않습니다.\n')

    def ButtonClicked_24(self):
        kc = 1 if self.sj_main_checkBox_01.isChecked() else 0
        kt = 1 if self.sj_main_checkBox_02.isChecked() else 0
        cc = 1 if self.sj_main_checkBox_03.isChecked() else 0
        ct = 1 if self.sj_main_checkBox_04.isChecked() else 0
        bt = 1 if self.sj_main_checkBox_05.isChecked() else 0
        t = self.sj_main_lineEdit_01.text()
        if t == '':
            t = 0
        df = pd.DataFrame([[kc, kt, cc, ct, bt, int(t)]], columns=columns_sm, index=[0])
        query1Q.put([1, df, 'main', 'replace'])
        self.UpdateTexedit([ui_num['설정텍스트'], '시스템 기본 설정값 저장하기 완료'])

        # noinspection PyGlobalUndefined
        global DICT_SET
        DICT_SET['키움콜렉터'] = kc
        DICT_SET['키움트레이더'] = kt
        DICT_SET['업비트콜렉터'] = cc
        DICT_SET['업비트트레이더'] = ct
        DICT_SET['백테스터'] = bt
        DICT_SET['백테스터시작시간'] = int(t)

    def ButtonClicked_25(self):
        id1 = self.sj_sacc_lineEdit_01.text()
        ps1 = self.sj_sacc_lineEdit_02.text()
        cp1 = self.sj_sacc_lineEdit_03.text()
        ap1 = self.sj_sacc_lineEdit_04.text()
        id2 = self.sj_sacc_lineEdit_05.text()
        ps2 = self.sj_sacc_lineEdit_06.text()
        cp2 = self.sj_sacc_lineEdit_07.text()
        ap2 = self.sj_sacc_lineEdit_08.text()
        if id1 == '' or ps1 == '' or cp1 == '' or ap1 == '' or id2 == '' or ps2 == '' or cp2 == '' or ap2 == '':
            QtWidgets.QMessageBox.critical(self, '오류 알림', '일부 설정값이 입력되지 않았습니다.\n')
        else:
            df = pd.DataFrame([[id1, ps1, cp1, ap1, id2, ps2, cp2, ap2]], columns=columns_sk, index=[0])
            query1Q.put([1, df, 'kiwoom', 'replace'])
            self.UpdateTexedit([ui_num['설정텍스트'], '키움증권 계정 설정값 저장하기 완료'])

            # noinspection PyGlobalUndefined
            global DICT_SET
            DICT_SET['아이디1'] = id1
            DICT_SET['비밀번호1'] = ps1
            DICT_SET['인증서비밀번호1'] = cp1
            DICT_SET['계좌비밀번호1'] = ap1
            DICT_SET['아이디2'] = id2
            DICT_SET['비밀번호2'] = ps2
            DICT_SET['인증서비밀번호2'] = cp2
            DICT_SET['계좌비밀번호2'] = ap2

    def ButtonClicked_26(self):
        access_key = self.sj_cacc_lineEdit_01.text()
        secret_key = self.sj_cacc_lineEdit_02.text()
        if access_key == '' or secret_key == '':
            QtWidgets.QMessageBox.critical(self, '오류 알림', '일부 설정값이 입력되지 않았습니다.\n')
        else:
            df = pd.DataFrame([[access_key, secret_key]], columns=columns_su, index=[0])
            query1Q.put([1, df, 'upbit', 'replace'])
            self.UpdateTexedit([ui_num['설정텍스트'], '업비트 계정 설정값 저장하기 완료'])

            # noinspection PyGlobalUndefined
            global DICT_SET
            DICT_SET['Access_key'] = access_key
            DICT_SET['Secret_key'] = secret_key

    def ButtonClicked_27(self):
        str_bot = self.sj_tele_lineEdit_01.text()
        int_id = self.sj_tele_lineEdit_02.text()
        if str_bot == '' or int_id == '':
            QtWidgets.QMessageBox.critical(self, '오류 알림', '일부 설정값이 입력되지 않았습니다.\n')
        else:
            df = pd.DataFrame([[str_bot, int(int_id)]], columns=columns_st, index=[0])
            query1Q.put([1, df, 'telegram', 'replace'])
            self.UpdateTexedit([ui_num['설정텍스트'], '텔레그램 봇토큰 및 사용자 아이디 설정값 저장하기 완료'])

            # noinspection PyGlobalUndefined
            global DICT_SET
            DICT_SET['텔레그램봇토큰'] = str_bot
            DICT_SET['텔레그램사용자아이디'] = int(int_id)

    def ButtonClicked_28(self):
        me = 1 if self.sj_stock_checkBox_01.isChecked() else 0
        sd = 1 if self.sj_stock_checkBox_02.isChecked() else 0
        cl = int(self.sj_stock_lineEdit_01.text())
        tr = int(self.sj_stock_lineEdit_02.text())
        cs = int(self.sj_stock_lineEdit_03.text())
        gapch = float(self.sj_stock_lineEdit_04.text())
        avgtime = int(self.sj_stock_lineEdit_05.text())
        gapsm = int(self.sj_stock_lineEdit_06.text())
        chlow = float(self.sj_stock_lineEdit_07.text())
        dmlow = int(self.sj_stock_lineEdit_08.text())
        plow = float(self.sj_stock_lineEdit_09.text())
        phigh = float(self.sj_stock_lineEdit_10.text())
        csper = float(self.sj_stock_lineEdit_11.text())
        buyc = int(self.sj_stock_lineEdit_12.text())
        if cl == '' or tr == '' or cs == '' or gapch == '' or avgtime == '' or gapsm == '' or chlow == '' or \
                dmlow == '' or plow == '' or phigh == '' or csper == '' or buyc == '':
            QtWidgets.QMessageBox.critical(self, '오류 알림', '일부 변수값이 입력되지 않았습니다.\n')
        else:
            query = f"UPDATE stock SET 모의투자 = {me}, 알림소리 = {sd}, 콜렉터 = {cl}, 트레이더 = {tr}, 잔고청산 = {cs}," \
                    f"체결강도차이 = {gapch}, 평균시간 = {avgtime}, 거래대금차이 = {gapsm}, 체결강도하한 = {chlow}, " \
                    f"누적거래대금하한 = {dmlow}, 등락율하한 = {plow}, 등락율상한 = {phigh}, 청산수익률 = {csper}, " \
                    f"최대매수종목수 = {buyc}"
            query1Q.put([1, query])
            self.UpdateTexedit([ui_num['설정텍스트'], '주식 전략 설정값 저장하기 완료'])

            # noinspection PyGlobalUndefined
            global DICT_SET
            DICT_SET['모의투자1'] = me
            DICT_SET['알림소리1'] = sd
            DICT_SET['콜렉터'] = cl
            DICT_SET['트레이더'] = tr
            DICT_SET['잔고청산'] = cs
            DICT_SET['체결강도차이1'] = gapch
            DICT_SET['평균시간1'] = avgtime
            DICT_SET['거래대금차이1'] = gapsm
            DICT_SET['체결강도하한1'] = chlow
            DICT_SET['누적거래대금하한1'] = dmlow
            DICT_SET['등락율하한1'] = plow
            DICT_SET['등락율상한1'] = phigh
            DICT_SET['청산수익률1'] = csper
            DICT_SET['최대매수종목수1'] = buyc

    def ButtonClicked_29(self):
        me = 1 if self.sj_coin_checkBox_01.isChecked() else 0
        sd = 1 if self.sj_coin_checkBox_02.isChecked() else 0
        gapch = float(self.sj_coin_lineEdit_01.text())
        avgtime = int(self.sj_coin_lineEdit_02.text())
        gapsm = int(self.sj_coin_lineEdit_03.text())
        chlow = float(self.sj_coin_lineEdit_04.text())
        dmlow = int(self.sj_coin_lineEdit_05.text())
        plow = float(self.sj_coin_lineEdit_06.text())
        phigh = float(self.sj_coin_lineEdit_07.text())
        csper = float(self.sj_coin_lineEdit_08.text())
        buyc = int(self.sj_coin_lineEdit_09.text())
        if gapch == '' or avgtime == '' or gapsm == '' or chlow == '' or \
                dmlow == '' or plow == '' or phigh == '' or csper == '' or buyc == '':
            QtWidgets.QMessageBox.critical(self, '오류 알림', '일부 변수값이 입력되지 않았습니다.\n')
        else:
            query = f"UPDATE coin SET 모의투자 = {me}, 알림소리 = {sd}, 체결강도차이 = {gapch}, 평균시간 = {avgtime}," \
                    f"거래대금차이 = {gapsm}, 체결강도하한 = {chlow}, 누적거래대금하한 = {dmlow}, 등락율하한 = {plow}," \
                    f"등락율상한 = {phigh}, 청산수익률 = {csper}, 최대매수종목수 = {buyc}"
            query1Q.put([1, query])
            self.UpdateTexedit([ui_num['설정텍스트'], '코인 전략 설정값 저장하기 완료'])

            # noinspection PyGlobalUndefined
            global DICT_SET
            DICT_SET['모의투자2'] = me
            DICT_SET['알림소리2'] = sd
            DICT_SET['체결강도차이2'] = gapch
            DICT_SET['평균시간2'] = avgtime
            DICT_SET['거래대금차이2'] = gapsm
            DICT_SET['체결강도하한2'] = chlow
            DICT_SET['누적거래대금하한2'] = dmlow
            DICT_SET['등락율하한2'] = plow
            DICT_SET['등락율상한2'] = phigh
            DICT_SET['청산수익률2'] = csper
            DICT_SET['최대매수종목수2'] = buyc

    def UpdateTexedit(self, data):
        text = f'[{now()}] {data[1]}'
        if data[0] == ui_num['설정텍스트']:
            self.sj_textEdit.append(text)
        elif data[0] == ui_num['S로그텍스트']:
            self.st_textEdit.append(text)
            self.log1.info(text)
        elif data[0] == ui_num['S단순텍스트']:
            self.sc_textEdit.append(text)
        elif data[0] == ui_num['C로그텍스트']:
            self.ct_textEdit.append(text)
            self.log2.info(text)
        elif data[0] == ui_num['C단순텍스트']:
            self.cc_textEdit.append(text)
        elif data[0] == ui_num['S종목명딕셔너리']:
            self.dict_name = data[1]

    def UpdateTablewidget(self, data):
        gubun = data[0]
        df = data[1]

        tableWidget = None
        if gubun == ui_num['S실현손익']:
            tableWidget = self.stt_tableWidget
        elif gubun == ui_num['S거래목록']:
            tableWidget = self.std_tableWidget
        elif gubun == ui_num['S잔고평가']:
            tableWidget = self.stj_tableWidget
        elif gubun == ui_num['S잔고목록']:
            tableWidget = self.sjg_tableWidget
        elif gubun == ui_num['S체결목록']:
            tableWidget = self.scj_tableWidget
        elif gubun == ui_num['S당일합계']:
            tableWidget = self.sdt_tableWidget
        elif gubun == ui_num['S당일상세']:
            tableWidget = self.sds_tableWidget
        elif gubun == ui_num['S누적합계']:
            tableWidget = self.snt_tableWidget
        elif gubun == ui_num['S누적상세']:
            tableWidget = self.sns_tableWidget
        if gubun == ui_num['C실현손익']:
            tableWidget = self.ctt_tableWidget
        elif gubun == ui_num['C거래목록']:
            tableWidget = self.ctd_tableWidget
        elif gubun == ui_num['C잔고평가']:
            tableWidget = self.ctj_tableWidget
        elif gubun == ui_num['C잔고목록']:
            tableWidget = self.cjg_tableWidget
        elif gubun == ui_num['C체결목록']:
            tableWidget = self.ccj_tableWidget
        elif gubun == ui_num['C당일합계']:
            tableWidget = self.cdt_tableWidget
        elif gubun == ui_num['C당일상세']:
            tableWidget = self.cds_tableWidget
        elif gubun == ui_num['C누적합계']:
            tableWidget = self.cnt_tableWidget
        elif gubun == ui_num['C누적상세']:
            tableWidget = self.cns_tableWidget
        if tableWidget is None:
            return

        if len(df) == 0:
            tableWidget.clearContents()
            return

        tableWidget.setRowCount(len(df))
        for j, index in enumerate(df.index):
            for i, column in enumerate(df.columns):
                if column == '체결시간':
                    cgtime = str(df[column][index])
                    cgtime = f'{cgtime[8:10]}:{cgtime[10:12]}:{cgtime[12:14]}'
                    item = QtWidgets.QTableWidgetItem(cgtime)
                elif column in ['거래일자', '일자']:
                    day = df[column][index]
                    if '.' not in day:
                        day = day[:4] + '.' + day[4:6] + '.' + day[6:]
                    item = QtWidgets.QTableWidgetItem(day)
                elif column in ['종목명', '주문구분', '기간']:
                    item = QtWidgets.QTableWidgetItem(str(df[column][index]))
                elif (gubun == ui_num['C잔고목록'] and column == '보유수량') or \
                        (gubun == ui_num['C체결목록'] and column == '주문수량') or \
                        (gubun == ui_num['C거래목록'] and column == '주문수량'):
                    item = QtWidgets.QTableWidgetItem(changeFormat(df[column][index], dotdown8=True))
                elif (gubun == ui_num['C잔고목록'] and column in ['매입가', '현재가']) or \
                        (gubun == ui_num['C체결목록'] and column in ['체결가', '주문가격']):
                    item = QtWidgets.QTableWidgetItem(changeFormat(df[column][index]))
                elif column not in ['수익률', '등락율', '고저평균대비등락율', '체결강도', '최고체결강도']:
                    item = QtWidgets.QTableWidgetItem(changeFormat(df[column][index], dotdowndel=True))
                else:
                    item = QtWidgets.QTableWidgetItem(changeFormat(df[column][index]))

                if column == '종목명':
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                elif column in ['거래횟수', '추정예탁자산', '추정예수금', '보유종목수',
                                '주문구분', '체결시간', '거래일자', '기간', '일자']:
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignCenter)
                else:
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)

                if '수익률' in df.columns:
                    if df['수익률'][index] >= 0:
                        item.setForeground(color_fg_bt)
                    else:
                        item.setForeground(color_fg_dk)
                elif gubun in [ui_num['S체결목록'], ui_num['C체결목록']]:
                    if df['주문구분'][index] == '매수':
                        item.setForeground(color_fg_bt)
                    elif df['주문구분'][index] == '매도':
                        item.setForeground(color_fg_dk)
                    elif df['주문구분'][index] in ['매도취소', '매수취소']:
                        item.setForeground(color_fg_bc)
                tableWidget.setItem(j, i, item)

        if len(df) < 13 and gubun in [ui_num['S거래목록'], ui_num['S잔고목록'], ui_num['C거래목록'], ui_num['C잔고목록']]:
            tableWidget.setRowCount(13)
        elif len(df) < 15 and gubun in [ui_num['S체결목록'], ui_num['C체결목록']]:
            tableWidget.setRowCount(15)
        elif len(df) < 19 and gubun in [ui_num['S당일상세'], ui_num['C당일상세']]:
            tableWidget.setRowCount(19)
        elif len(df) < 28 and gubun in [ui_num['S누적상세'], ui_num['C누적상세']]:
            tableWidget.setRowCount(28)

    def UpdateGaonsimJongmok(self, data):
        gubun = data[0]
        dict_df = data[1]

        if gubun == ui_num['S관심종목']:
            tn = 1
            gj_tableWidget = self.sgj_tableWidget
        else:
            tn = 2
            gj_tableWidget = self.cgj_tableWidget

        if len(dict_df) == 0:
            gj_tableWidget.clearContents()
            return

        gj_tableWidget.setRowCount(len(dict_df))
        for j, code in enumerate(list(dict_df.keys())):
            try:
                item = QtWidgets.QTableWidgetItem(self.dict_name[code])
            except KeyError:
                item = QtWidgets.QTableWidgetItem(code)
            item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            gj_tableWidget.setItem(j, 0, item)

            smavg = dict_df[code]['거래대금'][DICT_SET[f'평균시간{tn}'] + 1]
            item = QtWidgets.QTableWidgetItem(changeFormat(smavg).split('.')[0])
            item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
            gj_tableWidget.setItem(j, columns_gj3.index('smavg'), item)

            chavg = dict_df[code]['체결강도'][DICT_SET[f'평균시간{tn}'] + 1]
            item = QtWidgets.QTableWidgetItem(changeFormat(chavg))
            item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
            gj_tableWidget.setItem(j, columns_gj3.index('chavg'), item)

            chhigh = dict_df[code]['최고체결강도'][DICT_SET[f'평균시간{tn}'] + 1]
            item = QtWidgets.QTableWidgetItem(changeFormat(chhigh))
            item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
            gj_tableWidget.setItem(j, columns_gj3.index('chhigh'), item)

            for i, column in enumerate(columns_gj2):
                if column in ['거래대금', '누적거래대금']:
                    item = QtWidgets.QTableWidgetItem(changeFormat(dict_df[code][column][0], dotdowndel=True))
                else:
                    item = QtWidgets.QTableWidgetItem(changeFormat(dict_df[code][column][0]))
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
                if column == '등락율':
                    if DICT_SET[f'등락율하한{tn}'] <= dict_df[code][column][0] <= \
                            DICT_SET[f'등락율상한{tn}']:
                        item.setForeground(color_fg_bt)
                    else:
                        item.setForeground(color_fg_dk)
                elif column == '고저평균대비등락율':
                    if dict_df[code][column][0] >= 0:
                        item.setForeground(color_fg_bt)
                    else:
                        item.setForeground(color_fg_dk)
                elif column == '거래대금':
                    if dict_df[code][column][0] >= smavg + DICT_SET[f'거래대금차이{tn}']:
                        item.setForeground(color_fg_bt)
                    else:
                        item.setForeground(color_fg_dk)
                elif column == '누적거래대금':
                    if dict_df[code][column][0] >= DICT_SET[f'누적거래대금하한{tn}']:
                        item.setForeground(color_fg_bt)
                    else:
                        item.setForeground(color_fg_dk)
                elif column == '체결강도':
                    if dict_df[code][column][0] >= DICT_SET[f'체결강도하한{tn}'] and \
                            dict_df[code][column][0] >= chavg + DICT_SET[f'체결강도차이{tn}']:
                        item.setForeground(color_fg_bt)
                    else:
                        item.setForeground(color_fg_dk)
                gj_tableWidget.setItem(j, i + 1, item)

        if len(dict_df) < 15:
            gj_tableWidget.setRowCount(15)

    def CalendarClicked(self, gubun):
        if gubun == 'S':
            table = 's_tradelist'
            searchday = self.s_calendarWidget.selectedDate().toString('yyyyMMdd')
        else:
            table = 'c_tradelist'
            searchday = self.c_calendarWidget.selectedDate().toString('yyyyMMdd')
        con = sqlite3.connect(DB_TRADELIST)
        df = pd.read_sql(f"SELECT * FROM {table} WHERE 체결시간 LIKE '{searchday}%'", con)
        con.close()
        if len(df) > 0:
            df = df.set_index('index')
            df.sort_values(by=['체결시간'], ascending=True, inplace=True)
            df = df[['체결시간', '종목명', '매수금액', '매도금액', '주문수량', '수익률', '수익금']].copy()
            nbg, nsg = df['매수금액'].sum(), df['매도금액'].sum()
            sp = round((nsg / nbg - 1) * 100, 2)
            npg, nmg, nsig = df[df['수익금'] > 0]['수익금'].sum(), df[df['수익금'] < 0]['수익금'].sum(), df['수익금'].sum()
            df2 = pd.DataFrame(columns=columns_dt)
            df2.at[0] = searchday, nbg, nsg, npg, nmg, sp, nsig
        else:
            df = pd.DataFrame(columns=columns_dt)
            df2 = pd.DataFrame(columns=columns_dd)
        self.UpdateTablewidget([ui_num[f'{gubun}당일합계'], df2])
        self.UpdateTablewidget([ui_num[f'{gubun}당일상세'], df])

    def closeEvent(self, a):
        buttonReply = QtWidgets.QMessageBox.question(
            self, "프로그램 종료", "프로그램을 종료합니다.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No
        )
        if buttonReply == QtWidgets.QMessageBox.Yes:
            sound_proc.kill()
            query_proc1.kill()
            query_proc2.kill()
            tele_proc.kill()
            if self.qtimer1.isActive():
                self.qtimer1.stop()
            if self.qtimer2.isActive():
                self.qtimer2.stop()
            if self.qtimer3.isActive():
                self.qtimer3.stop()
            if self.writer.isRunning():
                self.writer.terminate()
            if self.trader_stock_proc.is_alive():
                self.trader_stock_proc.kill()
            if self.strategy_coin_proc.is_alive():
                self.strategy_coin_proc.kill()
            if self.strategy_stock_proc.is_alive():
                self.strategy_stock_proc.kill()
            if self.collector_coin_proc.is_alive():
                self.collector_coin_proc.kill()
            if self.collector_stock_proc1.is_alive():
                self.collector_stock_proc1.kill()
            if self.collector_stock_proc2.is_alive():
                self.collector_stock_proc2.kill()
            if self.collector_stock_proc3.is_alive():
                self.collector_stock_proc3.kill()
            if self.collector_stock_proc4.is_alive():
                self.collector_stock_proc4.kill()
            if self.receiver_stock_proc.is_alive():
                self.receiver_stock_proc.kill()
            if self.receiver_coin_thread1.isRunning():
                self.receiver_coin_thread1.websQ_ticker.terminate()
                self.receiver_coin_thread1.terminate()
            if self.receiver_coin_thread2.isRunning():
                self.receiver_coin_thread2.websQ_order.terminate()
                self.receiver_coin_thread2.terminate()
            if self.trader_coin_thread.isRunning():
                self.trader_coin_thread.websocketQ.terminate()
                self.trader_coin_thread.terminate()
            a.accept()
        else:
            a.ignore()


class Writer(QtCore.QThread):
    data1 = QtCore.pyqtSignal(list)
    data2 = QtCore.pyqtSignal(list)
    data3 = QtCore.pyqtSignal(list)

    def __init__(self):
        super().__init__()

    def run(self):
        while True:
            data = windowQ.get()
            if data[0] <= 5:
                self.data1.emit(data)
            elif data[0] < 20:
                self.data2.emit(data)
            elif data[0] == 20:
                self.data3.emit(data)
            elif data[0] < 30:
                self.data2.emit(data)
            elif data[0] == 30:
                self.data3.emit(data)


if __name__ == '__main__':
    windowQ, soundQ, query1Q, query2Q, teleQ, receivQ, stockQ, coinQ, sstgQ, cstgQ, tick1Q, tick2Q, tick3Q,\
        tick4Q, tick5Q = Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), \
        Queue(), Queue(), Queue(), Queue(), Queue()
    qlist = [windowQ, soundQ, query1Q, query2Q, teleQ, receivQ, stockQ, coinQ, sstgQ, cstgQ,
             tick1Q, tick2Q, tick3Q, tick4Q, tick5Q]

    sound_proc = Process(target=Sound, args=(qlist,), daemon=True)
    query_proc1 = Process(target=Query, args=(qlist,), daemon=True)
    query_proc2 = Process(target=QueryTick, args=(qlist,), daemon=True)
    tele_proc = Process(target=TelegramMsg, args=(qlist,), daemon=True)
    sound_proc.start()
    query_proc1.start()
    query_proc2.start()
    tele_proc.start()

    app = QtWidgets.QApplication(sys.argv)
    app.setStyle(ProxyStyle())
    app.setStyle('fusion')
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.Window, color_bg_bc)
    palette.setColor(QtGui.QPalette.Background, color_bg_bc)
    palette.setColor(QtGui.QPalette.WindowText, color_fg_bc)
    palette.setColor(QtGui.QPalette.Base, color_bg_bc)
    palette.setColor(QtGui.QPalette.AlternateBase, color_bg_dk)
    palette.setColor(QtGui.QPalette.Text, color_fg_bc)
    palette.setColor(QtGui.QPalette.Button, color_bg_bc)
    palette.setColor(QtGui.QPalette.ButtonText, color_fg_bc)
    palette.setColor(QtGui.QPalette.Link, color_fg_bk)
    palette.setColor(QtGui.QPalette.Highlight, color_fg_bk)
    palette.setColor(QtGui.QPalette.HighlightedText, color_bg_bk)
    app.setPalette(palette)
    window = Window()
    window.show()
    app.exec_()
