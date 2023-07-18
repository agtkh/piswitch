#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2023 K.Agata
# SPDX-License-Identifier: GPL-3.0

"""
ポケモンSVの競りを自動化する。
商品のリセットを行うために本体設定を自動で変更する。
OCRを用いて、商品の区別を行う。
"""
import time
import sys
import os
import cv2
import logging

from Common import Capture, ocr, img_cmp, img_binarization, send_img_to_slack, send_msg_to_slack

DIR_NAME = os.path.dirname(__file__)
BASE_NAME = os.path.basename(__file__)

# piswitchをインポートする
sys.path.append(os.path.join(DIR_NAME, '..'))
import piswitch

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.WARNING)
_logger.addHandler(logging.StreamHandler())
_logger.addHandler(logging.FileHandler(os.path.join(DIR_NAME, f"{BASE_NAME}.log")))


def party_search(box_img, poke_img, threshold=0.96):
    _, poke_img = img_binarization(poke_img)
    x = 171
    y0 = 133
    w = 80
    h = 80
    m = 4
    result = []
    for j in range(6):
        y = y0 + (h + m) * j
        cell_img = box_img[y:y + h, x:x + w]
        _, cell_img = img_binarization(cell_img)
        # cv2.imwrite(f'party/{j}.png', cell_img)
        v = img_cmp(poke_img, cell_img)
        if v > threshold:
            result.append((-1, j))
    return result


def box_search(box_img, poke_img, threshold=0.96):
    _, poke_img = img_binarization(poke_img)
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
            _, cell_img = img_binarization(cell_img)
            # cv2.imwrite(f'box/{i}_{j}.png', cell_img)
            v = img_cmp(poke_img, cell_img)
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
    _, shiny_img = img_binarization(shiny_img)
    x = 1126
    y = 61
    w = 29
    h = 27
    cap_img = image[y:y + h, x:x + w]
    _, cap_img = img_binarization(cap_img)
    return img_cmp(shiny_img, cap_img) > 0.95


def held_money(cap_img):
    x = 1111
    y = 16
    w = 120
    h = 24
    cap_img = cap_img[y:y + h, x:x + w]
    _, cap_img = img_binarization(cap_img, 250)
    cv2.imwrite(f'{DIR_NAME}/money.png', cap_img)
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
    _, cap_img = img_binarization(cap_img, 40)
    cv2.imwrite(f'{DIR_NAME}/goods_name.png', cap_img)
    return ocr(cap_img).split(' ')[0]


def save_game_data(con: piswitch.Procon):
    print("ゲームデータをセーブ中")
    con.push_button('b', n=3)
    con.push_button('x', delay=1.0)
    con.push_button('r', delay=0.5)
    con.push_button('a', delay=3.0)


def cheange_date_setting(con: piswitch.Procon):
    print("本体日付設定を変更中")
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


def launch_sv(con: piswitch.Procon):
    print("ゲーム起動中")
    con.push_button('a', delay=1.0, n=2)
    for _ in range(20):
        con.push_button('a', delay=1.0)
        con.push_button('b', n=3)
    print("ゲーム起動完了")
    time.sleep(0.5)


def exit_game(con: piswitch.Procon):
    con.push_button('home', delay=1.5)
    con.push_button('x')
    con.push_button('a', delay=4.0)


if __name__ == '__main__':
    con = piswitch.Procon()
    con.start()
    cap = Capture()
    time.sleep(1.0)

    # 店員さんにお辞儀
    con.push_button('b', n=4)

    save_game_data(con)
    exit_game(con)
    cheange_date_setting(con)
    launch_sv(con)

    while True:
        # 競りの画面かどうか
        cap_img = cap.get_screenshot(gray=True)
        money_n = held_money(cap_img)
        if money_n is None:
            con.push_button('a', delay=1.3)

            # 競りの画面かどうか
            cap_img = cap.get_screenshot(gray=True)
            money_n = held_money(cap_img)
            if money_n is None:
                print("商品の売り切れ。")
                save_game_data(con)
                exit_game(con)
                cheange_date_setting(con)
                launch_sv(con)
                continue

        # 所持金が1000000円以下の場合は終了
        if money_n < 1000000:
            _logger.warning(f"所持金が足りない。({money_n}円)")
            send_msg_to_slack(f"所持金が{money_n}円ため、プログラムを停止。")
            break

        # 商品名の取得
        goods_name = get_goods_name(cap_img)

        # 目的の商品の場合は競りを開始
        if goods_name.endswith('のハネ') or goods_name.endswith('の八ネ') or goods_name.endswith('のハネネ') or goods_name.endswith('の八ネネ') or goods_name.endswith(
                'のみ') or goods_name.endswith('ボール'):

            _logger.info(f"「{goods_name}」の競りを開始。所持金は{money_n}円")

            fin_flag = 0
            while True:
                con.push_button('a', n=10)
                # 競りの画面かどうか
                cap_img = cap.get_screenshot(gray=True)
                is_auction = held_money(cap_img)
                if is_auction is None:
                    fin_flag += 1
                    if fin_flag >= 4:
                        print("競りが終了")
                        send_msg_to_slack(f"「{goods_name}」を落札。\n所持金は{money_n}円。")
                        break
                else:
                    fin_flag = 0
        else:
            _logger.info(f"目的外「{goods_name}」のため、リセット。")
            exit_game(con)
            launch_sv(con)
