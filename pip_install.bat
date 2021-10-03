chcp 65001
pip install psutil pyqt5 pandas pyttsx3 matplotlib python-telegram-bot pyupbit websockets==9.1
@echo off
@echo ====================================================================================
@echo 다음 두개의 파일내에서 디렉토리 경로를 수정해야 프로그램이 올바르게 작동합니다.
@echo ====================================================================================
@echo utility/setting.py
@echo OPENAPI_PATH = 'D:/OpenAPI'
@echo SYSTEM_PATH = 'D:/PythonProjects/PyStockTrader'
@echo ====================================================================================
@echo pystocktrader.bat
@echo cd /D D:/PythonProjects/PyStockTrader
@echo ====================================================================================
pause