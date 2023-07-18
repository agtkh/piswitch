#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proconクラスの定義

"""

import math
import time
from .procon_base import ProconBase


def combine_12bit_values(val1: int, val2: int) -> int:
    """
    2つの12bitの値から3byteの値を生成する
    val1: 12bitの値1
    val2: 12bitの値2
    Return: 生成した3byteの値
    """
    data = bytearray(3)
    data[0] = val1 & 0xff
    data[1] = ((val2 << 4) & 0xf0) | ((val1 >> 8) & 0x0f)
    data[2] = (val2 >> 4) & 0xff
    return data


class Procon(ProconBase):

    def __init__(self, body_color="ff0000", button_color="ffff00", left_grip_color="00ff00", right_grip_color="0000ff"):
        super().__init__()

        # ボタン名をより一般的な名前に変換する辞書
        self.btn_key_dict = {
            "x": "button_x",
            "y": "button_y",
            "b": "button_b",
            "h": "button_home",
            "c": "button_capture",
            "": "button_a",
            " ": "button_b",
            "\x1b": "button_home",
            "\x1b[C": "dpad_right",
            "\x1b[D": "dpad_left",
            "\x1b[A": "dpad_up",
            "\x1b[B": "dpad_down",
            "d": "dpad_right",
            "a": "dpad_left",
            "w": "dpad_up",
            "s": "dpad_down",
            "-": "button_minus",
            "=": "button_plus",
            "+": "button_plus",
        }

        # ROMを書き換えてコントローラの色をカスタム
        self.spi_rom[0x60][0x50:0x53] = bytes.fromhex(body_color)  # body color
        self.spi_rom[0x60][0x53:0x56] = bytes.fromhex(button_color)  # button color
        self.spi_rom[0x60][0x56:0x59] = bytes.fromhex(left_grip_color)  # left grip color
        self.spi_rom[0x60][0x59:0x5c] = bytes.fromhex(right_grip_color)  # right grip color

    

    def set_button_state(self, btn_key: str, value: bool):
        """
        ボタンの状態の変更する関数
        btn_key: ボタン名
        value: True | False
        """
        # ボタン名を変換
        btn_key = self.btn_key_dict.get(btn_key, btn_key).lower()

        if getattr(self.control, btn_key, None) != None:
            setattr(self.control, btn_key, 1 if value else 0)
        else:
            print("Invalid button key: " + btn_key)


    def move_stick(self, stick: str, angle: float, radius: float):
        """
        左右のJoyスティックを動かす
        stick: "l" | "r"
        angle: 角度(0~360)
        radius: 半径(0~1.0)
        """
        x = round((1.0 + radius * math.cos(math.radians(angle))) * 2047.5)
        y = round((1.0 + radius * math.sin(math.radians(angle))) * 2047.5)
        analog = combine_12bit_values(x, y)
        if stick == "l":
            self.control.analog[0] = analog[0]
            self.control.analog[1] = analog[1]
            self.control.analog[2] = analog[2]
        elif stick == "r":
            self.control.analog[3] = analog[0]
            self.control.analog[4] = analog[1]
            self.control.analog[5] = analog[2]

    def move_left_stick(self, angle: float, radius: float):
        """
        左Joyスティックを動かす
        angle: 角度(0~360)
        radius: 半径(0~1.0)
        """
        self.move_stick("l", angle, radius)

    def move_right_stick(self, angle: float, radius: float):
        """
        右Joyスティックを動かす
        angle: 角度(0~360)
        radius: 半径(0~1.0)
        """
        self.move_stick("r", angle, radius)

    def push_button(self, btn_key, hold_time=0.15, delay_time=0.15, repeat_count=1):
        """
        ボタンを押す
        btn_key: ボタン名
        hold_time: ボタンを押している時間
        delay_time: ボタンを離してから次のボタンを押すまでの時間
        repeat_count: ボタンを押す回数
        """
        self.control.charging_grip = 1
        self.set_button_state(btn_key, True)
        time.sleep(hold_time)
        self.set_button_state(btn_key, False)
        time.sleep(delay_time)

        if repeat_count > 1:
            # 残りの回数を再帰的に呼び出す
            self.push(btn_key, hold_time, delay_time, repeat_count - 1)
