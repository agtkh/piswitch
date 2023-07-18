#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2023 K.Agata
# SPDX-License-Identifier: GPL-3.0
"""
ポケモンSVのポケモンボックス内を画像認識し、
卵を探し、自動孵化作業を行う。
"""

import time
import sys
import cv2
import os
import numpy as np
import pyocr
from PIL import Image
import logging

# piswitchをインポート
DIR_NAME = os.path.dirname(__file__)
BASE_NAME = os.path.basename(__file__)

sys.path.append(os.path.join(DIR_NAME, '..'))
from piswitch import Procon

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.WARNING)
_logger.addHandler(logging.StreamHandler())
_logger.addHandler(logging.FileHandler(os.path.join(DIR_NAME, f"{BASE_NAME}.log")))

# for OCR
# path_tesseract = "/usr/share/tesseract-ocr/4.00/tessdata"
# if path_tesseract not in os.environ["DIR_NAME"].split(os.pathsep):
#     os.environ["DIR_NAME"] += os.pathsep + path_tesseract
tools = pyocr.get_available_tools()
if len(tools) == 0:
    _logger.error("Do not find OCR tools")
OCR_TOOL = tools[0]


def decode_fourcc(v):
    # https://amdkkj.blogspot.com/2017/06/opencv-python-for-windows-playing-videos_17.html
    v = int(v)
    return "".join([chr((v >> 8 * i) & 0xFF) for i in range(4)])


class Capture:

    def __init__(self, device_id=0):
        self.cap = cv2.VideoCapture(device_id)
        # self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
        # self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('Y', 'U', 'Y', 'V'))
        # self.cap.set(cv2.CAP_PROP_FPS, 30)
        # self.cap.set(cv2.CAP_PROP_FPS, 10)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Latency Reduction

        print(f"[{decode_fourcc(self.cap.get(cv2.CAP_PROP_FOURCC))} "
              f"{self.cap.get(cv2.CAP_PROP_FPS):.1f}fps "
              f"{self.cap.get(cv2.CAP_PROP_FRAME_WIDTH):.0f}x{self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT):.0f}]")

        if not self.cap.isOpened():
            print('Could not open device.')
            return False

    def __del__(self):
        self.cap.release()

    def get_frame(self):
        self.cap.read()  # 1フレーム読み捨て
        for i in range(64):
            ret, cv2_img = self.cap.read()
            if ret and cv2.countNonZero(cv2_img[0]) > 0:
                return cv2_img
        return None


def binarization(img, threshold=127):
    return cv2.threshold(img, threshold, 255, cv2.THRESH_BINARY)


def comp_imgs(image1, image2):
    # Compare by number of matched pixels
    return np.count_nonzero(image1 == image2) / image1.size


def party_search(box_img, poke_img, threshold=0.96):
    _, poke_img = binarization(poke_img)
    x = 171
    y0 = 133
    w = 80
    h = 80
    m = 4
    result = []
    for j in range(6):
        y = y0 + (h + m) * j
        cell_img = box_img[y:y + h, x:x + w]
        _, cell_img = binarization(cell_img)
        # cv2.imwrite(f'party/{j}.png', cell_img)
        v = comp_imgs(poke_img, cell_img)
        if v > threshold:
            result.append((-1, j))
    return result


def box_search(box_img, poke_img, threshold=0.96):
    _, poke_img = binarization(poke_img)
    w = 80
    h = 80
    m = 4
    x0 = 300
    y0 = 133
    result = []
    for j in range(5):
        for i in range(6):
            x = x0 + (w + m) * i
            y = y0 + (h + m) * j
            cell_img = box_img[y:y + h, x:x + w]
            _, cell_img = binarization(cell_img)
            # cv2.imwrite(f'box/{i}_{j}.png', cell_img)
            v = comp_imgs(poke_img, cell_img)
            if v > threshold:
                result.append((i, j))
    return result


def search_egg(box_img):
    box_egg_img = cv2.imread(f'{DIR_NAME}/img/egg.png', cv2.IMREAD_GRAYSCALE)
    egg_img = cv2.imread(f'{DIR_NAME}/img/box_egg.png', cv2.IMREAD_GRAYSCALE)
    box_r = box_search(box_img, box_egg_img)
    party_r = party_search(box_img, egg_img)
    return box_r, party_r


def search_empty(box_img):
    box_empty_img = cv2.imread(f'{DIR_NAME}/img/empty.png', cv2.IMREAD_GRAYSCALE)
    empty_img = cv2.imread(f'{DIR_NAME}/img/box_empty.png', cv2.IMREAD_GRAYSCALE)
    box_r = box_search(box_img, box_empty_img, 0.99)
    party_r = party_search(box_img, empty_img, 0.99)
    return box_r, party_r


def is_shiny(image):
    """
    Determine if the currently displayed Pokemon is the shiny color.
    """
    shiny_img = cv2.imread(f'{DIR_NAME}/img/shiny.png', cv2.IMREAD_GRAYSCALE)
    _, shiny_img = binarization(shiny_img)
    x = 1126
    y = 61
    w = 29
    h = 27
    cap_img = image[y:y + h, x:x + w]
    _, cap_img = binarization(cap_img)
    return comp_imgs(shiny_img, cap_img) > 0.95


def ocr(cv2_img):

    pil_image = Image.fromarray(cv2_img)
    # TextBuilder  文字列を認識
    # WordBoxBuilder  単語単位で文字認識 + BoundingBox
    # LineBoxBuilder  行単位で文字認識 + BoundingBox
    # DigitBuilder  数字 / 記号を認識
    # DigitLineBoxBuilder  数字 / 記号を認識 + BoundingBox
    return OCR_TOOL.image_to_string(pil_image, lang="jpn", builder=pyocr.builders.TextBuilder(tesseract_layout=6))


def held_money(cap_img):
    x = 1111
    y = 16
    w = 120
    h = 24
    cap_img = cap_img[y:y + h, x:x + w]
    _, cap_img = binarization(cap_img, 200)
    cv2.imwrite('money.png', cap_img)
    try:
        return int(ocr(cap_img))
    except ValueError:
        return None
    except:
        _logger.exception('head_money Error')
        return None


def get_goods_name(cap_img):
    x = 360
    y = 550
    w = 220
    h = 32
    cap_img = cap_img[y:y + h, x:x + w]
    _, cap_img = binarization(cap_img, 55)
    cv2.imwrite('goods_name.png', cap_img)
    return ocr(cap_img).split(' ')[0]


def save_game_data(con: Procon):
    print("ゲームデータのセーブ中...")
    con.push_button('b', n=2)
    con.push_button('x', delay=1.0)
    con.push_button('r', delay=0.5)
    con.push_button('a', delay=3.0)


def cheange_date_setting(con: Procon):
    print("日付設定の変更中...")
    con.push_dpad('down')
    con.push_dpad('right', n=5)
    con.push_button('a', delay=1.0)  # open setting
    con.push_dpad('down', hold=0.05, delay=0.05, n=16)  # 本体
    con.push_dpad('right')
    con.push_dpad('down', hold=0.3, n=6)
    con.push_button('a')  # 日付と時刻
    con.push_dpad('down', n=2)
    con.push_button('a', delay=0.5)  # 日付と時刻の設定
    con.push_dpad('right', n=2)
    con.push_dpad('up')
    con.push_dpad('right', n=2)
    con.push_button('a', n=2)
    con.push_button('home', delay=1.5)


def launch_sv(con: Procon):
    print("ゲーム起動中...")
    con.push_button('a', delay=1.0, n=2)
    for _ in range(16):
        con.push_button('a', delay=1.0)
        con.push_button('b', delay=0.5, n=2)
    print("ゲーム起動完了")
    time.sleep(1.0)


def exit_game(con: Procon):
    con.push_button('home', delay=1.5)
    con.push_button('x')
    con.push_button('a', delay=4.0)


if __name__ == '__main__':
    con = Procon()
    con.start()
    con.push_button('b', n=4)
    cap = Capture()

    print("周回の準備")
    if input("この商品は欲しいですか(y/n)") != 'y':
        save_game_data(con)
        exit_game(con)
        cheange_date_setting(con)
        launch_sv(con)

    while True:

        # 競りの画面かどうか
        cap_img = cap.get_frame()
        cap_img = cv2.cvtColor(cap_img, cv2.COLOR_BGR2GRAY)
        money_n = held_money(cap_img)
        if money_n is None:
            con.push_button('a', delay=1.0)

            # 競りの画面かどうか
            cap_img = cap.get_frame()
            cap_img = cv2.cvtColor(cap_img, cv2.COLOR_BGR2GRAY)
            money_n = held_money(cap_img)
            if money_n is None:
                print("商品が売り切れだから、セーブして日付を変更")
                save_game_data(con)
                exit_game(con)
                cheange_date_setting(con)
                launch_sv(con)
                continue

        goods_name = get_goods_name(cap_img)
        print("所持金:", money_n)
        print('商品名:', goods_name)

        # 後方一致
        if goods_name.endswith('のハネ') or goods_name.endswith('の八ネ') or goods_name.endswith('のみ') or goods_name.endswith('ボール'):
            _logger.info(f"目的の商品({goods_name})だから、競りを開始")
            if money_n < 100000:
                _logger.warning()("所持金が足りないため、プログラムを停止")
                break

            fin_flag = 0
            while True:
                con.push_button('a', n=10)
                # 競りの画面かどうか
                cap_img = cap.get_frame()
                cap_img = cv2.cvtColor(cap_img, cv2.COLOR_BGR2GRAY)
                money_n = held_money(cap_img)
                if money_n is None:
                    fin_flag += 1
                    if fin_flag >= 3:
                        print("競りが終了")
                        break
            continue

        print("違う商品だから、リセット")
        exit_game(con)
        launch_sv(con)
        continue
