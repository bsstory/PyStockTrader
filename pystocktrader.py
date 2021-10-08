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

        self.counter = 0
        self.cpu_per = 0
        self.int_time = int(strf_time('%H%M%S'))
        self.dict_name = {}
        self.dict_code = {}

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
        self.trader_coin_proc = Process(target=TraderUpbit, args=(qlist,), daemon=True)

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
        if DICT_SET['업비트콜렉터']:
            self.UpbitCollectorStart()
        if DICT_SET['업비트트레이더']:
            self.UpbitTraderStart()
        if DICT_SET['주식최적화백테스터'] and self.int_time < DICT_SET['주식백테시작시간'] <= int(strf_time('%H%M%S')):
            self.StockBacktestStart()
        if DICT_SET['코인최적화백테스터'] and self.int_time < DICT_SET['코인백테시작시간'] <= int(strf_time('%H%M%S')):
            self.CoinBacktestStart()
        if self.int_time < 100 <= int(strf_time('%H%M%S')):
            self.ClearTextEdit()
        self.UpdateWindowTitle()
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
            if not self.trader_coin_proc.is_alive():
                self.trader_coin_proc.start()
                text = '코인 트레이더를 시작하였습니다.'
                soundQ.put(text)
                teleQ.put(text)
        else:
            QtWidgets.QMessageBox.critical(
                self, '오류 알림',
                '업비트 계정이 설정되지 않아\n트레이더를 시작할 수 없습니다.\n계정 설정 후 다시 시작하십시오.\n'
            )

    def StockBacktestStart(self):
        if self.backtester_proc is not None and self.backtester_proc.poll() != 0:
            QtWidgets.QMessageBox.critical(self, '오류 알림', '현재 백테스터가 실행중입니다.\n중복 실행할 수 없습니다.\n')
            return
        else:
            self.backtester_proc = subprocess.Popen(f'python {SYSTEM_PATH}/backtester/backtester_stock_vc.py')

    def CoinBacktestStart(self):
        if self.backtester_proc is not None and self.backtester_proc.poll() != 0:
            QtWidgets.QMessageBox.critical(self, '오류 알림', '현재 백테스터가 실행중입니다.\n중복 실행할 수 없습니다.\n')
            return
        else:
            self.backtester_proc = subprocess.Popen(f'python {SYSTEM_PATH}/backtester/backtester_coin_vc.py')

    def ClearTextEdit(self):
        self.st_textEdit.clear()
        self.ct_textEdit.clear()
        self.sc_textEdit.clear()
        self.cc_textEdit.clear()

    def UpdateWindowTitle(self):
        if self.showqsize:
            queryQ_size = query1Q.qsize() + query2Q.qsize()
            stocktickQ_size = tick1Q.qsize() + tick2Q.qsize() + tick3Q.qsize() + tick4Q.qsize()
            text = f'PyStockTrader                                                                   ' \
                   f'windowQ[{windowQ.qsize()}] | soundQ[{soundQ.qsize()}] | ' \
                   f'queryQ[{queryQ_size}] | teleQ[{teleQ.qsize()}] | receivQ[{sreceivQ.qsize()}] | ' \
                   f'stockQ[{stockQ.qsize()}] | coinQ[{coinQ.qsize()}] | sstgQ[{sstgQ.qsize()}] | ' \
                   f'cstgQ[{cstgQ.qsize()}] | stocktickQ[{stocktickQ_size}] | cointickQ[{tick5Q.qsize()}]'
            self.setWindowTitle(text)
        elif self.windowTitle() != 'PyStockTrader':
            self.setWindowTitle('PyStockTrader')

    def UpdateProgressBar(self):
        if self.counter > 9:
            self.counter = 0
        self.counter += 1
        self.progressBar.setValue(int(self.cpu_per))
        if self.backtester_proc is not None and self.backtester_proc.poll() != 0:
            if self.counter % 2 == 0:
                self.sb_pushButton_01.setStyleSheet(style_bc_st)
                self.sb_pushButton_02.setStyleSheet(style_bc_bt)
                self.cb_pushButton_01.setStyleSheet(style_bc_st)
                self.cb_pushButton_02.setStyleSheet(style_bc_bt)
            else:
                self.sb_pushButton_01.setStyleSheet(style_bc_bt)
                self.sb_pushButton_02.setStyleSheet(style_bc_st)
                self.cb_pushButton_01.setStyleSheet(style_bc_bt)
                self.cb_pushButton_02.setStyleSheet(style_bc_st)
        else:
            self.sb_pushButton_01.setStyleSheet(style_bc_bt)
            self.sb_pushButton_02.setStyleSheet(style_bc_bt)
            self.cb_pushButton_01.setStyleSheet(style_bc_bt)
            self.cb_pushButton_02.setStyleSheet(style_bc_bt)

    @thread_decorator
    def UpdateCpuper(self):
        self.cpu_per = psutil.cpu_percent(interval=1)

    def ShowQsize(self):
        self.showqsize = True if not self.showqsize else False

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
        code = item.text()
        oc = comma2float(self.cjg_tableWidget.item(row, columns_jg.index('보유수량')).text())
        c = comma2float(self.cjg_tableWidget.item(row, columns_jg.index('현재가')).text())
        buttonReply = QtWidgets.QMessageBox.question(
            self, '코인 시장가 매도', f'{code} {oc}개를 시장가매도합니다.\n계속하시겠습니까?\n',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No
        )
        if buttonReply == QtWidgets.QMessageBox.Yes:
            coinQ.put(['매도', code, c, oc])

    def ButtonClicked_01(self):
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
    def ButtonClicked_02(self):
        buttonReply = QtWidgets.QMessageBox.question(
            self, '주식 수동 시작', '주식 콜렉터 또는 트레이더를 시작합니다.\n계속하시겠습니까?\n',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No
        )
        if buttonReply == QtWidgets.QMessageBox.Yes:
            if DICT_SET['아이디2'] is None:
                QtWidgets.QMessageBox.critical(
                    self, '오류 알림',
                    '키움 두번째 계정이 설정되지 않아\n콜렉터를 시작할 수 없습니다.\n계정 설정 후 다시 시작하십시오.\n'
                )
            else:
                self.KiwoomCollectorStart()
                QTest.qWait(20000)
            if DICT_SET['아이디1'] is None:
                QtWidgets.QMessageBox.critical(
                    self, '오류 알림',
                    '키움 첫번째 계정이 설정되지 않아\n트레이더를 시작할 수 없습니다.\n계정 설정 후 다시 시작하십시오.\n'
                )
            else:
                self.KiwoomTraderStart()

    def ButtonClicked_03(self):
        if self.geometry().width() > 1000:
            self.setFixedSize(722, 383)
            self.zo_pushButton.setStyleSheet(style_bc_dk)
        else:
            self.setFixedSize(1403, 763)
            self.zo_pushButton.setStyleSheet(style_bc_bt)

    def ButtonClicked_04(self):
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

    def ButtonClicked_05(self):
        buttonReply = QtWidgets.QMessageBox.warning(
            self, '계정 설정 초기화', '계정 설정 항목이 모두 초기화됩니다.\n계속하시겠습니까?\n',
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No
        )
        if buttonReply == QtWidgets.QMessageBox.Yes:
            query1Q.put([1, 'DELETE FROM kiwoom'])
            query1Q.put([1, 'DELETE FROM upbit'])
            query1Q.put([1, 'DELETE FROM telegram'])
            self.sd_pushButton.setStyleSheet(style_bc_dk)

    def ButtonClicked_06(self, cmd):
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

    def Activated_01(self):
        strategy_name = self.ssi_comboBox.currentText()
        if strategy_name != '':
            con = sqlite3.connect(DB_STOCK_STRETEGY)
            df = pd.read_sql(f"SELECT * FROM init WHERE `index` = '{strategy_name}'", con).set_index('index')
            con.close()
            self.ss_textEdit_01.clear()
            self.ss_textEdit_01.append(df['전략코드'][strategy_name])

    def Activated_02(self):
        strategy_name = self.ssb_comboBox.currentText()
        if strategy_name != '':
            con = sqlite3.connect(DB_STOCK_STRETEGY)
            df = pd.read_sql(f"SELECT * FROM buy WHERE `index` = '{strategy_name}'", con).set_index('index')
            con.close()
            self.ss_textEdit_02.clear()
            self.ss_textEdit_02.append(df['전략코드'][strategy_name])

    def Activated_03(self):
        strategy_name = self.sss_comboBox.currentText()
        if strategy_name != '':
            con = sqlite3.connect(DB_STOCK_STRETEGY)
            df = pd.read_sql(f"SELECT * FROM sell WHERE `index` = '{strategy_name}'", con).set_index('index')
            con.close()
            self.ss_textEdit_03.clear()
            self.ss_textEdit_03.append(df['전략코드'][strategy_name])

    def Activated_04(self):
        strategy_name = self.csi_comboBox.currentText()
        if strategy_name != '':
            con = sqlite3.connect(DB_COIN_STRETEGY)
            df = pd.read_sql(f"SELECT * FROM init WHERE `index` = '{strategy_name}'", con).set_index('index')
            con.close()
            self.cs_textEdit_01.clear()
            self.cs_textEdit_01.append(df['전략코드'][strategy_name])

    def Activated_05(self):
        strategy_name = self.csb_comboBox.currentText()
        if strategy_name != '':
            con = sqlite3.connect(DB_COIN_STRETEGY)
            df = pd.read_sql(f"SELECT * FROM buy WHERE `index` = '{strategy_name}'", con).set_index('index')
            con.close()
            self.cs_textEdit_02.clear()
            self.cs_textEdit_02.append(df['전략코드'][strategy_name])

    def Activated_06(self):
        strategy_name = self.css_comboBox.currentText()
        if strategy_name != '':
            con = sqlite3.connect(DB_COIN_STRETEGY)
            df = pd.read_sql(f"SELECT * FROM sell WHERE `index` = '{strategy_name}'", con).set_index('index')
            con.close()
            self.cs_textEdit_03.clear()
            self.cs_textEdit_03.append(df['전략코드'][strategy_name])

    def ButtonClicked_11(self):
        con = sqlite3.connect(DB_STOCK_STRETEGY)
        df = pd.read_sql('SELECT * FROM init', con).set_index('index')
        con.close()
        if len(df) > 0:
            self.ssi_comboBox.clear()
            for index in df.index:
                self.ssi_comboBox.addItem(index)
            windowQ.put([ui_num['S전략텍스트'], '시작전략 불러오기 완료'])
            self.ssi_pushButton_04.setStyleSheet(style_bc_st)
        else:
            windowQ.put([ui_num['S전략텍스트'], '시작전략 없음'])

    def ButtonClicked_12(self):
        strategy_name = self.ssi_lineEdit.text()
        strategy = self.ss_textEdit_01.toPlainText()
        if strategy_name == '':
            QtWidgets.QMessageBox.critical(
                self, '오류 알림',
                '시작전략의 이름이 공백 상태입니다.\n이름을 입력하십시오.\n'
            )
        elif strategy == '':
            QtWidgets.QMessageBox.critical(
                self, '오류 알림',
                '시작전략의 코드가 공백 상태입니다.\n코드를 작성하십시오.\n'
            )
        else:
            query1Q.put([3, f"DELETE FROM init WHERE `index` = '{strategy_name}'"])
            df = pd.DataFrame({'전략코드': [strategy]}, index=[strategy_name])
            query1Q.put([3, df, 'init', 'append'])
            windowQ.put([ui_num['S전략텍스트'], '시작전략 저장하기 완료'])
            self.ssi_pushButton_04.setStyleSheet(style_bc_st)

    def ButtonClicked_13(self):
        buy_code = '''"""def __init__(self)"""'''
        self.ss_textEdit_01.clear()
        self.ss_textEdit_01.append(buy_code)
        windowQ.put([ui_num['S전략텍스트'], '시작변수 불러오기 완료'])
        self.ssi_pushButton_04.setStyleSheet(style_bc_st)

    def ButtonClicked_14(self):
        strategy = self.ss_textEdit_01.toPlainText()
        if strategy == '':
            QtWidgets.QMessageBox.critical(
                self, '오류 알림',
                '시작전략의 코드가 공백 상태입니다.\n'
            )
        else:
            query1Q.put([3, "DELETE FROM init WHERE `index` = '현재전략'"])
            df = pd.DataFrame({'전략코드': [strategy]}, index=['현재전략'])
            query1Q.put([3, df, 'init', 'append'])
            sstgQ.put(['시작전략', strategy])
            windowQ.put([ui_num['S전략텍스트'], '시작전략 설정하기 완료'])
            QtWidgets.QMessageBox.warning(
                self, '적용 알림', '시작전략은 프로그램을 재시작해야 적용됩니다.\n'
            )
            self.ssi_pushButton_04.setStyleSheet(style_bc_dk)

    def ButtonClicked_15(self):
        con = sqlite3.connect(DB_STOCK_STRETEGY)
        df = pd.read_sql('SELECT * FROM buy', con).set_index('index')
        con.close()
        if len(df) > 0:
            self.ssb_comboBox.clear()
            for index in df.index:
                self.ssb_comboBox.addItem(index)
            windowQ.put([ui_num['S전략텍스트'], '매수전략 불러오기 완료'])
            self.ssb_pushButton_04.setStyleSheet(style_bc_st)
        else:
            windowQ.put([ui_num['S전략텍스트'], '매수전략 없음'])

    def ButtonClicked_16(self):
        strategy_name = self.ssb_lineEdit.text()
        strategy = self.ss_textEdit_02.toPlainText()
        if strategy_name == '':
            QtWidgets.QMessageBox.critical(
                self, '오류 알림',
                '매수전략의 이름이 공백 상태입니다.\n이름을 입력하십시오.\n'
            )
        elif strategy == '':
            QtWidgets.QMessageBox.critical(
                self, '오류 알림',
                '매수전략의 코드가 공백 상태입니다.\n코드를 작성하십시오.\n'
            )
        else:
            query1Q.put([3, f"DELETE FROM buy WHERE `index` = '{strategy_name}'"])
            df = pd.DataFrame({'전략코드': [strategy]}, index=[strategy_name])
            query1Q.put([3, df, 'buy', 'append'])
            windowQ.put([ui_num['S전략텍스트'], '매수전략 저장하기 완료'])
            self.ssb_pushButton_04.setStyleSheet(style_bc_st)

    def ButtonClicked_17(self):
        buy_code = '''"""
def BuyStrategy(self, *args)
매수(True), 종목코드(str), 현재가(int), 시가(int), 고가(int), 저가(int), 등락율(float), 고저평균대비등락율(float),
당일거래대금(int), 초당거래대금(int), 초당거래대금평균(int), 체결강도(float), 체결강도평균(float), 최고체결강도(float),
VI해제시간(datetime), VI아래5호가(int), 초당매수수량(int), 초당매도수량(int), 매도총잔량(int), 매수총잔량(int),
매도호가2(int), 매도호가1(int), 매수호가1(int), 매수호가2(int), 매도잔량2(int), 매도잔량1(int), 매수잔량1(int), 매수잔량2(int)
"""'''
        self.ss_textEdit_02.clear()
        self.ss_textEdit_02.append(buy_code)
        windowQ.put([ui_num['S전략텍스트'], '매수변수 불러오기 완료'])
        self.ssb_pushButton_04.setStyleSheet(style_bc_st)

    def ButtonClicked_18(self):
        strategy = self.ss_textEdit_02.toPlainText()
        if strategy == '':
            QtWidgets.QMessageBox.critical(
                self, '오류 알림',
                '매수전략의 코드가 공백 상태입니다.\n'
            )
        else:
            query1Q.put([3, "DELETE FROM buy WHERE `index` = '현재전략'"])
            df = pd.DataFrame({'전략코드': [strategy]}, index=['현재전략'])
            query1Q.put([3, df, 'buy', 'append'])
            sstgQ.put(['매수전략', strategy])
            windowQ.put([ui_num['S전략텍스트'], '매수전략 시작하기 완료'])
            self.ssb_pushButton_04.setStyleSheet(style_bc_dk)
            self.ssb_pushButton_12.setStyleSheet(style_bc_st)

    def ButtonClicked_19(self):
        sell_code = '''if 고저평균대비등락율 < 0:\n    매수 = False'''
        self.ss_textEdit_02.append(sell_code)
        windowQ.put([ui_num['S전략텍스트'], '매수전략 모듈추가 완료'])

    def ButtonClicked_20(self):
        sell_code = '''if 체결강도 < 체결강도평균 + 5:\n    매수 = False'''
        self.ss_textEdit_02.append(sell_code)
        windowQ.put([ui_num['S전략텍스트'], '매수전략 모듈추가 완료'])

    def ButtonClicked_21(self):
        sell_code = '''if 초당거래대금 < 초당거래대금평균 + 90:\n    매수 = False'''
        self.ss_textEdit_02.append(sell_code)
        windowQ.put([ui_num['S전략텍스트'], '매수전략 모듈추가 완료'])

    def ButtonClicked_22(self):
        sell_code = '''if now() < timedelta_sec(1800, VI해제시간):\n    매수 = False'''
        self.ss_textEdit_02.append(sell_code)
        windowQ.put([ui_num['S전략텍스트'], '매수전략 모듈추가 완료'])

    def ButtonClicked_23(self):
        sell_code = '''if 매도총잔량 < 매수총잔량:\n    매수 = False'''
        self.ss_textEdit_02.append(sell_code)
        windowQ.put([ui_num['S전략텍스트'], '매수전략 모듈추가 완료'])

    def ButtonClicked_24(self):
        sell_code = '''if 매도잔량1 < 매수잔량1 * 2:\n    매수 = False'''
        self.ss_textEdit_02.append(sell_code)
        windowQ.put([ui_num['S전략텍스트'], '매수전략 모듈추가 완료'])

    def ButtonClicked_25(self):
        sell_code = '''
if 매수:
    매수수량 = int(self.int_tujagm / 현재가)
    if 매수수량 > 0:
        self.list_buy.append(종목코드)
        self.stockQ.put(['매수', 종목코드, 종목명, 현재가, 매수수량])'''
        self.ss_textEdit_02.append(sell_code)
        windowQ.put([ui_num['S전략텍스트'], '매수전략 모듈추가 완료'])

    # noinspection PyMethodMayBeStatic
    def ButtonClicked_26(self):
        sstgQ.put(['매수전략중지', ''])
        self.ssb_pushButton_12.setStyleSheet(style_bc_dk)
        self.ssb_pushButton_04.setStyleSheet(style_bc_st)

    def ButtonClicked_27(self):
        if self.backtester_proc is not None and self.backtester_proc.poll() != 0:
            QtWidgets.QMessageBox.critical(self, '오류 알림', '현재 백테스터가 실행중입니다.\n중복 실행할 수 없습니다.\n')
            return
        else:
            testperiod = self.ssb_lineEdit_01.text()
            totaltime = self.ssb_lineEdit_02.text()
            avgtime = self.ssb_lineEdit_03.text()
            starttime = self.ssb_lineEdit_04.text()
            endtime = self.ssb_lineEdit_05.text()
            multi = self.ssb_lineEdit_06.text()
            buystg = self.ssb_comboBox.currentText()
            sellstg = self.sss_comboBox.currentText()
            if buystg == '' or sellstg == '' or testperiod == '' or totaltime == '' or avgtime == '' or \
                    starttime == '' or endtime == '' or multi == '':
                QtWidgets.QMessageBox.critical(self, '오류 알림', '일부 설정값이 공백 상태입니다.\n')
                return
            self.backtester_proc = subprocess.Popen(
                    f'python {SYSTEM_PATH}/backtester/backtester_stock_stg.py '
                    f'{testperiod} {totaltime} {avgtime} {starttime} {endtime} {multi} {buystg} {sellstg}'
            )

    def ButtonClicked_28(self):
        if self.backtester_proc is None or self.backtester_proc.poll() == 0:
            buttonReply = QtWidgets.QMessageBox.question(
                self, '최적화 백테스터',
                'backtester/backtester_stock_vc.py 파일을\n본인의 전략에 맞게 수정 후 사용해야합니다.\n계속하시겠습니까?\n',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No
            )
            if buttonReply == QtWidgets.QMessageBox.Yes:
                self.backtester_proc = subprocess.Popen(f'python {SYSTEM_PATH}/backtester/backtester_stock_vc.py')

    def ButtonClicked_29(self):
        con = sqlite3.connect(DB_STOCK_STRETEGY)
        df = pd.read_sql('SELECT * FROM sell', con).set_index('index')
        con.close()
        if len(df) > 0:
            self.sss_comboBox.clear()
            for index in df.index:
                self.sss_comboBox.addItem(index)
            windowQ.put([ui_num['S전략텍스트'], '매도전략 불러오기 완료'])
            self.sss_pushButton_04.setStyleSheet(style_bc_st)
        else:
            windowQ.put([ui_num['S전략텍스트'], '매도전략 없음'])

    def ButtonClicked_30(self):
        strategy_name = self.sss_lineEdit.text()
        strategy = self.ss_textEdit_03.toPlainText()
        if strategy_name == '':
            QtWidgets.QMessageBox.critical(
                self, '오류 알림',
                '매도전략의 이름이 공백 상태입니다.\n이름을 입력하십시오.\n'
            )
        elif strategy == '':
            QtWidgets.QMessageBox.critical(
                self, '오류 알림',
                '매도전략의 코드가 공백 상태입니다.\n코드를 작성하십시오.\n'
            )
        else:
            query1Q.put([3, f"DELETE FROM sell WHERE `index` = '{strategy_name}'"])
            df = pd.DataFrame({'전략코드': [strategy]}, index=[strategy_name])
            query1Q.put([3, df, 'sell', 'append'])
            windowQ.put([ui_num['S전략텍스트'], '매도전략 저장하기 완료'])
            self.sss_pushButton_04.setStyleSheet(style_bc_st)

    def ButtonClicked_31(self):
        sell_code = '''"""
def SellStrategy(self, *args)
매도(False), 종목코드(str), 수익률(float), 보유수량(int), 매수시간(datetime), 현재가(int), 등락율(float), 고저평균대비등락율(float),
체결강도(float), 체결강도평균(float), 최고체결강도(float), 초당거래대금(int), 초당거래대금평균(int), 매도총잔량(int), 매수총잔량(int),
매도호가2(int), 매도호가1(int), 매수호가1(int), 매수호가2(int), 매도잔량2(int), 매도잔량1(int), 매수잔량1(int), 매수잔량2(int)
"""'''
        self.ss_textEdit_03.clear()
        self.ss_textEdit_03.append(sell_code)
        windowQ.put([ui_num['S전략텍스트'], '매도전략 불러오기 완료'])
        self.sss_pushButton_04.setStyleSheet(style_bc_st)

    def ButtonClicked_32(self):
        strategy = self.ss_textEdit_03.toPlainText()
        if strategy == '':
            QtWidgets.QMessageBox.critical(
                self, '오류 알림',
                '매도전략의 코드가 공백 상태입니다.\n'
            )
        else:
            query1Q.put([3, "DELETE FROM sell WHERE `index` = '현재전략'"])
            df = pd.DataFrame({'전략코드': [strategy]}, index=['현재전략'])
            query1Q.put([3, df, 'sell', 'append'])
            sstgQ.put(['매도전략', strategy])
            windowQ.put([ui_num['S전략텍스트'], '매도전략 시작하기 완료'])
            self.sss_pushButton_04.setStyleSheet(style_bc_dk)
            self.sss_pushButton_12.setStyleSheet(style_bc_st)

    def ButtonClicked_33(self):
        sell_code = '''if now() > timedelta_sec(1800, 매수시간):\n    매도 = True'''
        self.ss_textEdit_03.append(sell_code)
        windowQ.put([ui_num['S전략텍스트'], '매도전략 모듈추가 완료'])

    def ButtonClicked_34(self):
        sell_code = '''if 수익률 <= -2 :\n    매도 = True'''
        self.ss_textEdit_03.append(sell_code)
        windowQ.put([ui_num['S전략텍스트'], '매도전략 모듈추가 완료'])

    def ButtonClicked_35(self):
        sell_code = '''if 수익률 >= 3:\n    매도 = True'''
        self.ss_textEdit_03.append(sell_code)
        windowQ.put([ui_num['S전략텍스트'], '매도전략 모듈추가 완료'])

    def ButtonClicked_36(self):
        sell_code = '''if 체결강도 < 체결강도평균:\n    매도 = True'''
        self.ss_textEdit_03.append(sell_code)
        windowQ.put([ui_num['S전략텍스트'], '매도전략 모듈추가 완료'])

    def ButtonClicked_37(self):
        sell_code = '''if 매도총잔량 < 매수총잔량:\n    매도 = True'''
        self.ss_textEdit_03.append(sell_code)
        windowQ.put([ui_num['S전략텍스트'], '매도전략 모듈추가 완료'])

    def ButtonClicked_38(self):
        sell_code = '''if 현재가 > VI아래5호가 * 1.003:\n    매도 = True'''
        self.ss_textEdit_03.append(sell_code)
        windowQ.put([ui_num['S전략텍스트'], '매도전략 모듈추가 완료'])

    def ButtonClicked_39(self):
        sell_code = '''
if 매도:
    self.list_sell.append(종목코드)
    self.stockQ.put(['매도', 종목코드, 종목명, 현재가, 보유수량])'''
        self.ss_textEdit_03.append(sell_code)
        windowQ.put([ui_num['S전략텍스트'], '매도전략 모듈추가 완료'])

    # noinspection PyMethodMayBeStatic
    def ButtonClicked_40(self):
        sstgQ.put(['매도전략중지', ''])
        self.sss_pushButton_12.setStyleSheet(style_bc_dk)
        self.sss_pushButton_04.setStyleSheet(style_bc_st)

    def ButtonClicked_41(self):
        con = sqlite3.connect(DB_COIN_STRETEGY)
        df = pd.read_sql('SELECT * FROM init', con).set_index('index')
        con.close()
        if len(df) > 0:
            self.csi_comboBox.clear()
            for index in df.index:
                self.csi_comboBox.addItem(index)
            windowQ.put([ui_num['C전략텍스트'], '시작전략 불러오기 완료'])
            self.csi_pushButton_04.setStyleSheet(style_bc_st)
        else:
            windowQ.put([ui_num['C전략텍스트'], '시작전략 없음'])

    def ButtonClicked_42(self):
        strategy_name = self.csi_lineEdit.text()
        strategy = self.cs_textEdit_01.toPlainText()
        if strategy_name == '':
            QtWidgets.QMessageBox.critical(
                self, '오류 알림',
                '시작전략의 이름이 공백 상태입니다.\n이름을 입력하십시오.\n'
            )
        elif strategy == '':
            QtWidgets.QMessageBox.critical(
                self, '오류 알림',
                '시작전략의 코드가 공백 상태입니다.\n코드를 작성하십시오.\n'
            )
        else:
            query1Q.put([4, f"DELETE FROM init WHERE `index` = '{strategy_name}'"])
            df = pd.DataFrame({'전략코드': [strategy]}, index=[strategy_name])
            query1Q.put([4, df, 'init', 'append'])
            windowQ.put([ui_num['C전략텍스트'], '시작전략 저장하기 완료'])
            self.csi_pushButton_04.setStyleSheet(style_bc_st)

    def ButtonClicked_43(self):
        buy_code = '''"""def __init__(self)"""'''
        self.cs_textEdit_01.clear()
        self.cs_textEdit_01.append(buy_code)
        windowQ.put([ui_num['C전략텍스트'], '시작변수 불러오기 완료'])
        self.csi_pushButton_04.setStyleSheet(style_bc_st)

    def ButtonClicked_44(self):
        strategy = self.cs_textEdit_01.toPlainText()
        if strategy == '':
            QtWidgets.QMessageBox.critical(
                self, '오류 알림',
                '시작전략의 코드가 공백 상태입니다.\n'
            )
        else:
            query1Q.put([4, "DELETE FROM init WHERE `index` = '현재전략'"])
            df = pd.DataFrame({'전략코드': [strategy]}, index=['현재전략'])
            query1Q.put([4, df, 'init', 'append'])
            cstgQ.put(['시작전략', strategy])
            windowQ.put([ui_num['C전략텍스트'], '시작전략 설정하기 완료'])
            QtWidgets.QMessageBox.warning(
                self, '적용 알림', '시작전략은 프로그램을 재시작해야 적용됩니다.\n'
            )
            self.csi_pushButton_04.setStyleSheet(style_bc_dk)

    def ButtonClicked_45(self):
        con = sqlite3.connect(DB_COIN_STRETEGY)
        df = pd.read_sql('SELECT * FROM buy', con).set_index('index')
        con.close()
        if len(df) > 0:
            self.csb_comboBox.clear()
            for index in df.index:
                self.csb_comboBox.addItem(index)
            windowQ.put([ui_num['C전략텍스트'], '매수전략 불러오기 완료'])
            self.csb_pushButton_04.setStyleSheet(style_bc_st)
        else:
            windowQ.put([ui_num['C전략텍스트'], '매수전략 없음'])

    def ButtonClicked_46(self):
        strategy_name = self.csb_lineEdit.text()
        strategy = self.cs_textEdit_02.toPlainText()
        if strategy_name == '':
            QtWidgets.QMessageBox.critical(
                self, '오류 알림',
                '매수전략의 이름이 공백 상태입니다.\n이름을 입력하십시오.\n'
            )
        elif strategy == '':
            QtWidgets.QMessageBox.critical(
                self, '오류 알림',
                '매수전략의 코드가 공백 상태입니다.\n코드를 작성하십시오.\n'
            )
        else:
            query1Q.put([4, f"DELETE FROM buy WHERE `index` = '{strategy_name}'"])
            df = pd.DataFrame({'전략코드': [strategy]}, index=[strategy_name])
            query1Q.put([4, df, 'buy', 'append'])
            windowQ.put([ui_num['C전략텍스트'], '매수전략 저장하기 완료'])
            self.csb_pushButton_04.setStyleSheet(style_bc_st)

    def ButtonClicked_47(self):
        buy_code = '''"""
def BuyStrategy(self, *args)
매수(True), 종목명(str), 현재가(int), 시가(int), 고가(int), 저가(int), 등락율(float), 고저평균대비등락율(float), 당일거래대금(int), 초당거래대금(int),
초당거래대금평균(int), 체결강도(float), 체결강도평균(float), 최고체결강도(float), 초당매수수량(int), 초당매도수량(int), 매도총잔량(float), 매수총잔량(float),
매도호가5(float), 매도호가4(float), 매도호가3(float), 매도호가2(float), 매도호가1(float),
매수호가1(float), 매수호가2(float), 매수호가3(float), 매수호가4(float), 매수호가5(float),
매도잔량5(float), 매도잔량4(float), 매도잔량3(float), 매도잔량2(float), 매도잔량1(float),
매수잔량1(float), 매수잔량2(float), 매수잔량3(float), 매수잔량4(float), 매수잔량5(float)
"""'''
        self.cs_textEdit_02.clear()
        self.cs_textEdit_02.append(buy_code)
        windowQ.put([ui_num['C전략텍스트'], '매수변수 불러오기 완료'])
        self.csb_pushButton_04.setStyleSheet(style_bc_st)

    def ButtonClicked_48(self):
        strategy = self.cs_textEdit_02.toPlainText()
        if strategy == '':
            QtWidgets.QMessageBox.critical(
                self, '오류 알림',
                '매수전략의 코드가 공백 상태입니다.\n'
            )
        else:
            query1Q.put([4, "DELETE FROM buy WHERE `index` = '현재전략'"])
            df = pd.DataFrame({'전략코드': [strategy]}, index=['현재전략'])
            query1Q.put([4, df, 'buy', 'append'])
            cstgQ.put(['매수전략', strategy])
            windowQ.put([ui_num['C전략텍스트'], '매수전략 시작하기 완료'])
            self.csb_pushButton_04.setStyleSheet(style_bc_dk)
            self.csb_pushButton_12.setStyleSheet(style_bc_st)

    def ButtonClicked_49(self):
        sell_code = '''if 고저평균대비등락율 < 0:\n    매수 = False'''
        self.cs_textEdit_02.append(sell_code)
        windowQ.put([ui_num['C전략텍스트'], '매수전략 모듈추가 완료'])

    def ButtonClicked_50(self):
        sell_code = '''if 체결강도 < 체결강도평균 + 5:\n    매수 = False'''
        self.cs_textEdit_02.append(sell_code)
        windowQ.put([ui_num['C전략텍스트'], '매수전략 모듈추가 완료'])

    def ButtonClicked_51(self):
        sell_code = '''if 초당거래대금 < 초당거래대금평균 + 10000000:\n    매수 = False'''
        self.cs_textEdit_02.append(sell_code)
        windowQ.put([ui_num['C전략텍스트'], '매수전략 모듈추가 완료'])

    def ButtonClicked_52(self):
        sell_code = '''if 당일거래대금 < 10000000000:\n    매수 = False'''
        self.cs_textEdit_02.append(sell_code)
        windowQ.put([ui_num['C전략텍스트'], '매수전략 모듈추가 완료'])

    def ButtonClicked_53(self):
        sell_code = '''if 매도총잔량 < 매수총잔량:\n    매수 = False'''
        self.cs_textEdit_02.append(sell_code)
        windowQ.put([ui_num['C전략텍스트'], '매수전략 모듈추가 완료'])

    def ButtonClicked_54(self):
        sell_code = '''if 매도잔량1 < 매수잔량1 * 2:\n    매수 = False'''
        self.cs_textEdit_02.append(sell_code)
        windowQ.put([ui_num['S전략텍스트'], '매수전략 모듈추가 완료'])

    def ButtonClicked_55(self):
        sell_code = '''
if 매수:
    매수수량 = round(self.int_tujagm / 현재가, 8)
    if 매수수량 > 0.00000001:
        self.list_buy.append(종목명)
        self.coinQ.put(['매수', 종목명, 현재가, 매수수량])'''
        self.cs_textEdit_02.append(sell_code)
        windowQ.put([ui_num['C전략텍스트'], '매수전략 모듈추가 완료'])

    # noinspection PyMethodMayBeStatic
    def ButtonClicked_56(self):
        cstgQ.put(['매수전략중지', ''])
        self.csb_pushButton_12.setStyleSheet(style_bc_dk)
        self.csb_pushButton_04.setStyleSheet(style_bc_st)

    def ButtonClicked_57(self):
        if self.backtester_proc is not None and self.backtester_proc.poll() != 0:
            QtWidgets.QMessageBox.critical(self, '오류 알림', '현재 백테스터가 실행중입니다.\n중복 실행할 수 없습니다.\n')
            return
        else:
            testperiod = self.csb_lineEdit_01.text()
            totaltime = self.csb_lineEdit_02.text()
            avgtime = self.csb_lineEdit_03.text()
            starttime = self.csb_lineEdit_04.text()
            endtime = self.csb_lineEdit_05.text()
            multi = self.csb_lineEdit_06.text()
            buystg = self.csb_comboBox.currentText()
            sellstg = self.css_comboBox.currentText()
            if buystg == '' or sellstg == '' or testperiod == '' or totaltime == '' or avgtime == '' or \
                    starttime == '' or endtime == '' or multi == '':
                QtWidgets.QMessageBox.critical(self, '오류 알림', '일부 설정값이 공백 상태입니다.\n')
                return
            self.backtester_proc = subprocess.Popen(
                    f'python {SYSTEM_PATH}/backtester/backtester_coin_stg.py '
                    f'{testperiod} {totaltime} {avgtime} {starttime} {endtime} {multi} {buystg} {sellstg}'
            )

    def ButtonClicked_58(self):
        if self.backtester_proc is None or self.backtester_proc.poll() == 0:
            buttonReply = QtWidgets.QMessageBox.question(
                self, '최적화 백테스터',
                'backtester/backtester_coin_vc.py 파일을\n본인의 전략에 맞게 수정 후 사용해야합니다.\n계속하시겠습니까?\n',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No
            )
            if buttonReply == QtWidgets.QMessageBox.Yes:
                self.backtester_proc = subprocess.Popen(f'python {SYSTEM_PATH}/backtester/backtester_coin_vc.py')

    def ButtonClicked_59(self):
        con = sqlite3.connect(DB_COIN_STRETEGY)
        df = pd.read_sql('SELECT * FROM sell', con).set_index('index')
        con.close()
        if len(df) > 0:
            self.css_comboBox.clear()
            for index in df.index:
                self.css_comboBox.addItem(index)
            windowQ.put([ui_num['C전략텍스트'], '매도전략 불러오기 완료'])
            self.css_pushButton_04.setStyleSheet(style_bc_st)
        else:
            windowQ.put([ui_num['C전략텍스트'], '매도전략 없음'])

    def ButtonClicked_60(self):
        strategy_name = self.css_lineEdit.text()
        strategy = self.cs_textEdit_03.toPlainText()
        if strategy_name == '':
            QtWidgets.QMessageBox.critical(
                self, '오류 알림',
                '매도전략의 이름이 공백 상태입니다.\n이름을 입력하십시오.\n'
            )
        elif strategy == '':
            QtWidgets.QMessageBox.critical(
                self, '오류 알림',
                '매도전략의 코드가 공백 상태입니다.\n코드를 작성하십시오.\n'
            )
        else:
            query1Q.put([4, f"DELETE FROM sell WHERE `index` = '{strategy_name}'"])
            df = pd.DataFrame({'전략코드': [strategy]}, index=[strategy_name])
            query1Q.put([4, df, 'sell', 'append'])
            windowQ.put([ui_num['C전략텍스트'], '매도전략 저장하기 완료'])
            self.css_pushButton_04.setStyleSheet(style_bc_st)

    def ButtonClicked_61(self):
        sell_code = '''"""
def SellStrategy(self, *args)
매도(False), 종목명(str), 수익률(float), 보유수량(float), 매수시간(datetime), 현재가(float), 등락율(float), 고저평균대비등락율(float),
체결강도(float), 체결강도평균(float), 최고체결강도(float), 초당거래대금(int), 초당거래대금평균(int), 매도총잔량(float), 매수총잔량(float),
매도호가5(float), 매도호가4(float), 매도호가3(float), 매도호가2(float), 매도호가1(float),
매수호가1(float), 매수호가2(float), 매수호가3(float), 매수호가4(float), 매수호가5(float),
매도잔량5(float), 매도잔량4(float), 매도잔량3(float), 매도잔량2(float), 매도잔량1(float),
매수잔량1(float), 매수잔량2(float), 매수잔량3(float), 매수잔량4(float), 매수잔량5(float)
"""'''
        self.cs_textEdit_03.clear()
        self.cs_textEdit_03.append(sell_code)
        windowQ.put([ui_num['C전략텍스트'], '매도변수 불러오기 완료'])
        self.css_pushButton_04.setStyleSheet(style_bc_st)

    def ButtonClicked_62(self):
        strategy = self.cs_textEdit_03.toPlainText()
        if strategy == '':
            QtWidgets.QMessageBox.critical(
                self, '오류 알림',
                '매도전략의 코드가 공백 상태입니다.\n'
            )
        else:
            query1Q.put([4, "DELETE FROM sell WHERE `index` = '현재전략'"])
            df = pd.DataFrame({'전략코드': [strategy]}, index=['현재전략'])
            query1Q.put([4, df, 'sell', 'append'])
            cstgQ.put(['매도전략', strategy])
            windowQ.put([ui_num['C전략텍스트'], '매도전략 시작하기 완료'])
            self.css_pushButton_04.setStyleSheet(style_bc_dk)
            self.css_pushButton_12.setStyleSheet(style_bc_st)

    def ButtonClicked_63(self):
        sell_code = '''if now() > timedelta_sec(1800, 매수시간):\n    매도 = True'''
        self.cs_textEdit_03.append(sell_code)
        windowQ.put([ui_num['C전략텍스트'], '매도전략 모듈추가 완료'])

    def ButtonClicked_64(self):
        sell_code = '''if 수익률 <= -2 :\n    매도 = True'''
        self.cs_textEdit_03.append(sell_code)
        windowQ.put([ui_num['C전략텍스트'], '매도전략 모듈추가 완료'])

    def ButtonClicked_65(self):
        sell_code = '''if 수익률 >= 3:\n    매도 = True'''
        self.cs_textEdit_03.append(sell_code)
        windowQ.put([ui_num['C전략텍스트'], '매도전략 모듈추가 완료'])

    def ButtonClicked_66(self):
        sell_code = '''if 체결강도 < 체결강도평균 + 5:\n    매도 = True'''
        self.cs_textEdit_03.append(sell_code)
        windowQ.put([ui_num['C전략텍스트'], '매도전략 모듈추가 완료'])

    def ButtonClicked_67(self):
        sell_code = '''if 매도총잔량 < 매수총잔량:\n    매도 = True'''
        self.cs_textEdit_03.append(sell_code)
        windowQ.put([ui_num['C전략텍스트'], '매도전략 모듈추가 완료'])

    def ButtonClicked_68(self):
        sell_code = '''if 고저평균대비등락율 < 0.:\n    매도 = True'''
        self.cs_textEdit_03.append(sell_code)
        windowQ.put([ui_num['C전략텍스트'], '매도전략 모듈추가 완료'])

    def ButtonClicked_69(self):
        sell_code = '''
if 매도:
    self.list_sell.append(종목명)
    self.coinQ.put(['매도', 종목명, 현재가, 보유수량])'''
        self.cs_textEdit_03.append(sell_code)
        windowQ.put([ui_num['C전략텍스트'], '매도전략 모듈추가 완료'])

    # noinspection PyMethodMayBeStatic
    def ButtonClicked_70(self):
        cstgQ.put(['매도전략중지', ''])
        self.css_pushButton_12.setStyleSheet(style_bc_dk)
        self.css_pushButton_04.setStyleSheet(style_bc_st)

    def ButtonClicked_71(self):
        con = sqlite3.connect(DB_SETTING)
        df = pd.read_sql('SELECT * FROM main', con)
        df = df.set_index('index')
        con.close()
        if len(df) > 0:
            self.sj_main_checkBox_01.setChecked(True) if df['키움콜렉터'][0] else self.sj_main_checkBox_01.setChecked(False)
            self.sj_main_checkBox_02.setChecked(True) if df['키움트레이더'][0] else self.sj_main_checkBox_02.setChecked(False)
            self.sj_main_checkBox_03.setChecked(True) if df['업비트콜렉터'][0] else self.sj_main_checkBox_03.setChecked(False)
            self.sj_main_checkBox_04.setChecked(True) if df['업비트트레이더'][0] else self.sj_main_checkBox_04.setChecked(False)
            self.sj_main_checkBox_05.setChecked(True) if df['주식최적화백테스터'][0] else self.sj_main_checkBox_05.setChecked(False)
            self.sj_main_checkBox_06.setChecked(True) if df['코인최적화백테스터'][0] else self.sj_main_checkBox_06.setChecked(False)
            self.sj_main_lineEdit_01.setText(str(df['주식백테시작시간'][0]))
            self.sj_main_lineEdit_02.setText(str(df['코인백테시작시간'][0]))
            self.UpdateTexedit([ui_num['설정텍스트'], '시스템 기본 설정값 불러오기 완료'])
        else:
            QtWidgets.QMessageBox.critical(self, '오류 알림', '시스템 기본 설정값이\n존재하지 않습니다.\n')

    def ButtonClicked_72(self):
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

    def ButtonClicked_73(self):
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

    def ButtonClicked_74(self):
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

    def ButtonClicked_75(self):
        con = sqlite3.connect(DB_SETTING)
        df = pd.read_sql('SELECT * FROM stock', con)
        df = df.set_index('index')
        con.close()
        if len(df) > 0:
            self.sj_stock_checkBox_01.setChecked(True) if df['모의투자'][0] else self.sj_stock_checkBox_01.setChecked(False)
            self.sj_stock_checkBox_02.setChecked(True) if df['알림소리'][0] else self.sj_stock_checkBox_02.setChecked(False)
            self.sj_stock_lineEdit_01.setText(str(df['평균값계산틱수'][0]))
            self.sj_stock_lineEdit_02.setText(str(df['최대매수종목수'][0]))
            self.sj_stock_lineEdit_03.setText(str(df['콜렉터'][0]))
            self.sj_stock_lineEdit_04.setText(str(df['트레이더'][0]))
            self.sj_stock_lineEdit_05.setText(str(df['잔고청산'][0]))
            self.UpdateTexedit([ui_num['설정텍스트'], '주식 전략 설정값 불러오기 완료'])
        else:
            QtWidgets.QMessageBox.critical(self, '오류 알림', '주식 전략 설정값이\n존재하지 않습니다.\n')

    def ButtonClicked_76(self):
        con = sqlite3.connect(DB_SETTING)
        df = pd.read_sql('SELECT * FROM coin', con)
        df = df.set_index('index')
        con.close()
        if len(df) > 0:
            self.sj_coin_checkBox_01.setChecked(True) if df['모의투자'][0] else self.sj_coin_checkBox_01.setChecked(False)
            self.sj_coin_checkBox_02.setChecked(True) if df['알림소리'][0] else self.sj_coin_checkBox_02.setChecked(False)
            self.sj_coin_lineEdit_01.setText(str(df['평균값계산틱수'][0]))
            self.sj_coin_lineEdit_02.setText(str(df['최대매수종목수'][0]))
            self.UpdateTexedit([ui_num['설정텍스트'], '코인 전략 설정값 불러오기 완료'])
        else:
            QtWidgets.QMessageBox.critical(self, '오류 알림', '코인 전략 설정값이\n존재하지 않습니다.\n')

    def ButtonClicked_77(self):
        kc = 1 if self.sj_main_checkBox_01.isChecked() else 0
        kt = 1 if self.sj_main_checkBox_02.isChecked() else 0
        cc = 1 if self.sj_main_checkBox_03.isChecked() else 0
        ct = 1 if self.sj_main_checkBox_04.isChecked() else 0
        sbt = 1 if self.sj_main_checkBox_05.isChecked() else 0
        cbt = 1 if self.sj_main_checkBox_06.isChecked() else 0
        sbst = self.sj_main_lineEdit_01.text()
        if sbst == '':
            sbst = 0
        cbst = self.sj_main_lineEdit_02.text()
        if cbst == '':
            cbst = 0
        df = pd.DataFrame([[kc, kt, cc, ct, sbt, int(sbst), cbt, int(cbst)]], columns=columns_sm, index=[0])
        query1Q.put([1, df, 'main', 'replace'])
        self.UpdateTexedit([ui_num['설정텍스트'], '시스템 기본 설정값 저장하기 완료'])

        # noinspection PyGlobalUndefined
        global DICT_SET
        DICT_SET['키움콜렉터'] = kc
        DICT_SET['키움트레이더'] = kt
        DICT_SET['업비트콜렉터'] = cc
        DICT_SET['업비트트레이더'] = ct
        DICT_SET['주식최적화백테스터'] = sbt
        DICT_SET['주식백테시작시간'] = int(sbst)
        DICT_SET['코인최적화백테스터'] = cbt
        DICT_SET['코인백테시작시간'] = int(cbst)

    def ButtonClicked_78(self):
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

    def ButtonClicked_79(self):
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

    def ButtonClicked_80(self):
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

    def ButtonClicked_81(self):
        me = 1 if self.sj_stock_checkBox_01.isChecked() else 0
        sd = 1 if self.sj_stock_checkBox_02.isChecked() else 0
        avgtime = int(self.sj_stock_lineEdit_01.text())
        buyc = int(self.sj_stock_lineEdit_02.text())
        cl = int(self.sj_stock_lineEdit_03.text())
        tr = int(self.sj_stock_lineEdit_04.text())
        cs = int(self.sj_stock_lineEdit_05.text())
        if cl == '' or tr == '' or cs == '' or avgtime == '' or buyc == '':
            QtWidgets.QMessageBox.critical(self, '오류 알림', '일부 변수값이 입력되지 않았습니다.\n')
        else:
            query = f"UPDATE stock SET 모의투자 = {me}, 알림소리 = {sd}, 콜렉터 = {cl}, 트레이더 = {tr}, 잔고청산 = {cs}," \
                    f"평균값계산틱수 = {avgtime}, 최대매수종목수 = {buyc}"
            query1Q.put([1, query])
            self.UpdateTexedit([ui_num['설정텍스트'], '주식 전략 설정값 저장하기 완료'])

            # noinspection PyGlobalUndefined
            global DICT_SET
            DICT_SET['모의투자1'] = me
            DICT_SET['알림소리1'] = sd
            DICT_SET['콜렉터'] = cl
            DICT_SET['트레이더'] = tr
            DICT_SET['잔고청산'] = cs
            DICT_SET['평균값계산틱수1'] = avgtime
            DICT_SET['최대매수종목수1'] = buyc

    def ButtonClicked_82(self):
        me = 1 if self.sj_coin_checkBox_01.isChecked() else 0
        sd = 1 if self.sj_coin_checkBox_02.isChecked() else 0
        avgtime = int(self.sj_coin_lineEdit_01.text())
        buyc = int(self.sj_coin_lineEdit_02.text())
        if avgtime == '' or buyc == '':
            QtWidgets.QMessageBox.critical(self, '오류 알림', '일부 변수값이 입력되지 않았습니다.\n')
        else:
            query = f"UPDATE coin SET 모의투자 = {me}, 알림소리 = {sd}, 평균값계산틱수 = {avgtime}, 최대매수종목수 = {buyc}"
            query1Q.put([1, query])
            self.UpdateTexedit([ui_num['설정텍스트'], '코인 전략 설정값 저장하기 완료'])

            # noinspection PyGlobalUndefined
            global DICT_SET
            DICT_SET['모의투자2'] = me
            DICT_SET['알림소리2'] = sd
            DICT_SET['평균값계산틱수2'] = avgtime
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
            self.dict_code = data[2]
        elif data[0] == ui_num['S전략텍스트']:
            self.ss_textEdit_04.append(text)
        elif data[0] == ui_num['C전략텍스트']:
            self.cs_textEdit_04.append(text)

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
            if tableWidget.item(0, 0) is not None:
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
            if gj_tableWidget.item(0, 0) is not None:
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

            smavg = dict_df[code]['초당거래대금'][DICT_SET[f'평균시간{tn}'] + 1]
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
                if column in ['초당거래대금', '당일거래대금']:
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
                elif column == '초당거래대금':
                    if dict_df[code][column][0] >= smavg + DICT_SET[f'거래대금차이{tn}']:
                        item.setForeground(color_fg_bt)
                    else:
                        item.setForeground(color_fg_dk)
                elif column == '당일거래대금':
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
            if self.trader_coin_proc.is_alive():
                self.trader_coin_proc.kill()
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
            if data[0] <= 10:
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
    windowQ, soundQ, query1Q, query2Q, teleQ, sreceivQ, creceivQ, stockQ, coinQ, sstgQ, cstgQ, tick1Q, tick2Q, tick3Q, \
        tick4Q, tick5Q = Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), Queue(), \
        Queue(), Queue(), Queue(), Queue(), Queue(), Queue()
    qlist = [windowQ, soundQ, query1Q, query2Q, teleQ, sreceivQ, creceivQ, stockQ, coinQ, sstgQ, cstgQ,
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
