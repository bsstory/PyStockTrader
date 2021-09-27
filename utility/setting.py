import sqlite3
import pandas as pd
from PyQt5.QtGui import QFont, QColor

OPENAPI_PATH = 'D:/OpenAPI'
SYSTEM_PATH = 'D:/PythonProjects/PyStockTrader'
GRAPH_PATH = f'{SYSTEM_PATH}/backtester/graph'
DB_SETTING = f'{SYSTEM_PATH}/database/setting.db'
DB_BACKTEST = f'{SYSTEM_PATH}/database/backtest.db'
DB_TRADELIST = f'{SYSTEM_PATH}/database/tradelist.db'
DB_STOCK_TICK = f'{SYSTEM_PATH}/database/stock_tick.db'
DB_COIN_TICK = f'{SYSTEM_PATH}/database/coin_tick.db'

conn = sqlite3.connect(DB_SETTING)
df_m = pd.read_sql('SELECT * FROM main', conn).set_index('index')
df_s = pd.read_sql('SELECT * FROM stock', conn).set_index('index')
df_c = pd.read_sql('SELECT * FROM coin', conn).set_index('index')
df_k = pd.read_sql('SELECT * FROM kiwoom', conn).set_index('index')
df_u = pd.read_sql('SELECT * FROM upbit', conn).set_index('index')
df_t = pd.read_sql('SELECT * FROM telegram', conn).set_index('index')
conn.close()

DICT_SET = {
    '키움콜렉터': df_m['키움콜렉터'][0],
    '키움트레이더': df_m['키움트레이더'][0],
    '업비트콜렉터': df_m['업비트콜렉터'][0],
    '업비트트레이더': df_m['업비트트레이더'][0],
    '백테스터': df_m['백테스터'][0],
    '백테스터시작시간': df_m['시작시간'][0],

    '아이디1': df_k['아이디1'][0] if len(df_k) > 0 and df_k['아이디1'][0] != '' else None,
    '비밀번호1': df_k['비밀번호1'][0] if len(df_k) > 0 and df_k['비밀번호1'][0] != '' else None,
    '인증서비밀번호1': df_k['인증서비밀번호1'][0] if len(df_k) > 0 and df_k['인증서비밀번호1'][0] != '' else None,
    '계좌비밀번호1': df_k['계좌비밀번호1'][0] if len(df_k) > 0 and df_k['계좌비밀번호1'][0] != '' else None,
    '아이디2': df_k['아이디2'][0] if len(df_k) > 0 and df_k['아이디2'][0] != '' else None,
    '비밀번호2': df_k['비밀번호2'][0] if len(df_k) > 0 and df_k['비밀번호2'][0] != '' else None,
    '인증서비밀번호2': df_k['인증서비밀번호2'][0] if len(df_k) > 0 and df_k['인증서비밀번호2'][0] != '' else None,
    '계좌비밀번호2': df_k['계좌비밀번호2'][0] if len(df_k) > 0 and df_k['계좌비밀번호2'][0] != '' else None,

    'Access_key': df_u['Access_key'][0] if len(df_u) > 0 and df_u['Access_key'][0] != '' else None,
    'Secret_key': df_u['Secret_key'][0] if len(df_u) > 0 and df_u['Secret_key'][0] != '' else None,

    '텔레그램봇토큰': df_t['str_bot'][0] if len(df_t) > 0 and df_t['str_bot'][0] != '' else None,
    '텔레그램사용자아이디': df_t['int_id'][0] if len(df_t) > 0 and df_t['int_id'][0] != '' else None,

    '모의투자1': df_s['모의투자'][0],
    '알림소리1': df_s['알림소리'][0],
    '버전업': df_s['버전업'][0],
    '자동로그인2': df_s['자동로그인2'][0],
    '콜렉터': df_s['콜렉터'][0],
    '자동로그인1': df_s['자동로그인1'][0],
    '트레이더': df_s['트레이더'][0],
    '전략시작': df_s['전략시작'][0],
    '잔고청산': df_s['잔고청산'][0],
    '전략종료': df_s['전략종료'][0],
    '체결강도차이1': df_s['체결강도차이'][0],
    '평균시간1': df_s['평균시간'][0],
    '거래대금차이1': df_s['거래대금차이'][0],
    '체결강도하한1': df_s['체결강도하한'][0],
    '누적거래대금하한1': df_s['누적거래대금하한'][0],
    '등락율하한1': df_s['등락율하한'][0],
    '등락율상한1': df_s['등락율상한'][0],
    '청산수익률1': df_s['청산수익률'][0],
    '최대매수종목수1': df_s['최대매수종목수'][0],

    '모의투자2': df_c['모의투자'][0],
    '알림소리2': df_c['알림소리'][0],
    '체결강도차이2': df_c['체결강도차이'][0],
    '평균시간2': df_c['평균시간'][0],
    '거래대금차이2': df_c['거래대금차이'][0],
    '체결강도하한2': df_c['체결강도하한'][0],
    '누적거래대금하한2': df_c['누적거래대금하한'][0],
    '등락율하한2': df_c['등락율하한'][0],
    '등락율상한2': df_c['등락율상한'][0],
    '청산수익률2': df_c['청산수익률'][0],
    '최대매수종목수2': df_c['최대매수종목수'][0]
}

qfont = QFont()
qfont.setFamily('나눔고딕')
qfont.setPixelSize(12)

sn_brrq = 1000
sn_brrd = 1001
sn_cond = 1002
sn_oper = 1003
sn_jscg = 1004
sn_vijc = 1005
sn_cthg = 1006
sn_short = 1100
sn_jchj = 2000

color_fg_bt = QColor(230, 230, 235)
color_fg_bc = QColor(190, 190, 195)
color_fg_dk = QColor(150, 150, 155)
color_fg_bk = QColor(110, 110, 115)

color_bg_bt = QColor(50, 50, 55)
color_bg_bc = QColor(40, 40, 45)
color_bg_dk = QColor(30, 30, 35)
color_bg_bk = QColor(20, 20, 25)
color_bg_ld = (50, 50, 55, 150)

color_bf_bt = QColor(110, 110, 115)
color_bf_dk = QColor(70, 70, 75)

color_cifl = QColor(230, 230, 255)
color_pluss = QColor(230, 230, 235)
color_minus = QColor(120, 120, 125)

color_chuse1 = QColor(35, 35, 40)
color_chuse2 = QColor(30, 30, 35)
color_ema05 = QColor(230, 230, 235)
color_ema10 = QColor(200, 200, 205)
color_ema20 = QColor(170, 170, 175)
color_ema40 = QColor(140, 140, 145)
color_ema60 = QColor(110, 110, 115)
color_ema120 = QColor(80, 80, 85)
color_ema240 = QColor(70, 70, 75)
color_ema480 = QColor(60, 60, 65)

style_fc_bt = 'color: rgb(230, 230, 235);'
style_fc_dk = 'color: rgb(150, 150, 155);'
style_bc_bt = 'background-color: rgb(50, 50, 55);'
style_bc_md = 'background-color: rgb(40, 40, 45);'
style_bc_dk = 'background-color: rgb(30, 30, 35);'

ui_num = {'설정텍스트': 0, 'S단순텍스트': 1, 'S로그텍스트': 2, 'S종목명딕셔너리': 3, 'C단순텍스트': 4, 'C로그텍스트': 5,
          'S실현손익': 11, 'S거래목록': 12, 'S잔고평가': 13, 'S잔고목록': 14, 'S체결목록': 15,
          'S당일합계': 16, 'S당일상세': 17, 'S누적합계': 18, 'S누적상세': 19, 'S관심종목': 20,
          'C실현손익': 21, 'C거래목록': 22, 'C잔고평가': 23, 'C잔고목록': 24, 'C체결목록': 25,
          'C당일합계': 26, 'C당일상세': 27, 'C누적합계': 28, 'C누적상세': 29, 'C관심종목': 30}

columns_tt = ['거래횟수', '총매수금액', '총매도금액', '총수익금액', '총손실금액', '수익률', '수익금합계']
columns_td = ['종목명', '매수금액', '매도금액', '주문수량', '수익률', '수익금', '체결시간']
columns_tj = ['추정예탁자산', '추정예수금', '보유종목수', '수익률', '총평가손익', '총매입금액', '총평가금액']
columns_jg = ['종목명', '매입가', '현재가', '수익률', '평가손익', '매입금액', '평가금액', '보유수량']
columns_cj = ['종목명', '주문구분', '주문수량', '미체결수량', '주문가격', '체결가', '체결시간']
columns_gj1 = ['등락율', '고저평균대비등락율', '거래대금', '누적거래대금', '체결강도', '최고체결강도']
columns_gj2 = ['등락율', '고저평균대비등락율', '거래대금', '누적거래대금', '체결강도']
columns_gj3 = ['종목명', 'per', 'hmlper', 'smoney', 'dmoney', 'ch', 'smavg', 'chavg', 'chhigh']

columns_dt = ['거래일자', '누적매수금액', '누적매도금액', '누적수익금액', '누적손실금액', '수익률', '누적수익금']
columns_dd = ['체결시간', '종목명', '매수금액', '매도금액', '주문수량', '수익률', '수익금']
columns_nt = ['기간', '누적매수금액', '누적매도금액', '누적수익금액', '누적손실금액', '수익률', '누적수익금']
columns_nd = ['일자', '총매수금액', '총매도금액', '총수익금액', '총손실금액', '수익률', '수익금합계']

columns_sm = ['키움콜렉터', '키움트레이더', '업비트콜렉터', '업비트트레이더', '백테스터', '시작시간']
columns_sk = ['아이디1', '비밀번호1', '인증서비밀번호1', '계좌비밀번호1', '아이디2', '비밀번호2', '인증서비밀번호2', '계좌비밀번호2']
columns_ss = ['모의투자', '알림소리', '버전업', '자동로그인2', '콜렉터', '자동로그인1', '트레이더', '전략시작', '전략종료',
              '종목당투자금', '백테스팅기간', '백테스팅시간', '시작시간', '종료시간', '체결강도차이', '평균시간', '거래대금차이',
              '체결강도하한', '누적거래대금하한', '등락율하한', '등락율상한', '청산수익률', '멀티프로세스']
columns_sc = ['모의투자', '알림소리', '종목당투자금', '백테스팅기간', '백테스팅시간', '시작시간', '종료시간', '체결강도차이',
              '평균시간', '거래대금차이', '체결강도하한', '누적거래대금하한', '등락율하한', '등락율상한', '청산수익률', '멀티프로세스']
columns_su = ['Access_key', 'Secret_key']
columns_st = ['str_bot', 'int_id']
