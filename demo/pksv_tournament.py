#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2023 K.Agata
# SPDX-License-Identifier: GPL-3.0
"""
ポケモンSVでAボタン連打することで学校最強大会を周回して金策する。
30分ごとSlackにスクリーンショットを送って敗退していないか見る。
"""

import sys
import os
import time
import threading
from datetime import datetime
import logging

from Common import Capture, send_img_to_slack

DIR_NAME = os.path.dirname(__file__)
BASE_NAME = os.path.basename(__file__)

# piswitchパッケージをインポート
sys.path.append(os.path.join(DIR_NAME, '..'))
import piswitch

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.WARNING)
_logger.addHandler(logging.StreamHandler())
_logger.addHandler(logging.FileHandler(os.path.join(DIR_NAME, f"{BASE_NAME}.log")))

def screen_shot_loop():
    cb = Capture()
    while True:
        try:
            if cb.save_screenshot('ss.jpg'):
                date_str = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
                send_img_to_slack(date_str, 'ss.jpg')
        except Exception:
            _logger.exception('スクリーンショット時の不明なのエラー')
        time.sleep(60 * 30)  # 30 mins


if __name__ == '__main__':
    _logger.info('start')
    try:
        con = piswitch.Procon()
        con.start()

        # 定期的にスクリーンショットを送る
        threading.Thread(target=screen_shot_loop, daemon=True).start()

        while True:
            # マクロループ開始
            con.push('button_a', delay=0.2)

    except KeyboardInterrupt as e:
        print("\nCtrl-Cなどで終了")
    except Exception as e:
        _logger.exception('不明なエラー')

    con.close()
    _logger.info('end')
