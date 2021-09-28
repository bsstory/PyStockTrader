import time
import pythoncom
import pywintypes
from manuallogin import *
from PyQt5 import QtWidgets
from multiprocessing import Process
from PyQt5.QAxContainer import QAxWidget
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from utility.setting import OPENAPI_PATH


class Window(QtWidgets.QMainWindow):
    app = QtWidgets.QApplication(sys.argv)

    def __init__(self):
        super().__init__()
        self.bool_connected = False
        self.ocx = QAxWidget('KHOPENAPI.KHOpenAPICtrl.1')
        self.ocx.OnEventConnect.connect(self.OnEventConnect)
        self.CommConnect()

    def CommConnect(self):
        self.ocx.dynamicCall('CommConnect()')
        while not self.bool_connected:
            pythoncom.PumpWaitingMessages()
        self.EventLoop()

    # noinspection PyMethodMayBeStatic
    def EventLoop(self):
        while True:
            time.sleep(1)

    def OnEventConnect(self, err_code):
        if err_code == 0:
            self.bool_connected = True


if __name__ == '__main__':
    login_info = f'{OPENAPI_PATH}/system/Autologin.dat'
    if os.path.isfile(login_info):
        os.remove(f'{OPENAPI_PATH}/system/Autologin.dat')
    print('\n 자동 로그인 설정 파일 삭제 완료\n')

    proc = Process(target=Window)
    proc.start()
    print(' 버전처리용 로그인 프로세스 시작\n')
    while find_window('Open API login') == 0:
        print(' 로그인창 열림 대기 중 ...\n')
        time.sleep(1)
    print(' 아이디 및 패스워드 입력 대기 중 ...\n')
    time.sleep(5)
    manual_login(4)
    print(' 아이디 및 패스워드 입력 완료\n')

    update = False
    while find_window('Open API login') != 0:
        hwnd = find_window('opstarter')
        if hwnd != 0:
            try:
                static_hwnd = win32gui.GetDlgItem(hwnd, 0xFFFF)
                text = win32gui.GetWindowText(static_hwnd)
                if '버전처리' in text:
                    proc.kill()
                    print(' 버전처리용 로그인 프로세스 종료\n')
                    click_button(win32gui.GetDlgItem(hwnd, 0x2))
                    update = True
                    print(' 버전 업그레이드 완료\n')
            except pywintypes.error:
                pass
        print(' 버전처리 및 로그인창 닫힘 대기 중 ...\n')
        time.sleep(1)
    if update:
        time.sleep(5)
        hwnd = find_window('업그레이드 확인')
        if hwnd != 0:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        print(' 버전 업그레이드 확인 완료\n')
    else:
        proc.kill()
        print(' 버전처리용 로그인 프로세스 종료\n')
