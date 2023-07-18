#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USB Gadget API for Linuxを使って、USBデバイスを作成する
Raspberry Pi 4B での動作を想定している。
"""

import logging
import os

from . import treecreater

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.WARNING)
_logger.addHandler(logging.StreamHandler())


class UsbGadget:

    def __init__(self, name: str, config_tree: dict):
        dir_path = "/sys/kernel/config/usb_gadget"
        self.name = name
        self.base_path = os.path.join(dir_path, name)
        self.conn_sock_file = None

        # Create gadget directory
        if not os.path.exists(self.base_path):
            treecreater.create_tree(config_tree, self.base_path)

    def open(self):
        """
        USBデバイスを開いて、有効化する
        """

        # 再接続
        self.disabled()
        self.enabled()

        try:
            self.conn_sock_file = os.open("/dev/hidg0", os.O_RDWR | os.O_NONBLOCK)
        except (FileNotFoundError, PermissionError):
            _logger.error("Could not access USB Gadget device.")
            self.conn_sock_file = None

    def close(self):
        """
        USBデバイスを閉じて、無効化する
        """
        if self.conn_sock_file is not None:
            os.close(self.conn_sock_file)
            self.conn_sock_file = None

        self.disabled()

    def send(self, data) -> bool:
        """
        データを送信する
        成功時: True
        失敗時: False
        """
        try:
            os.write(self.conn_sock_file, data)
        except BlockingIOError as e:
            # バッファが一杯
            return False
        except BrokenPipeError as e:
            return False

        return True

    def recv(self, max_len=128):
        """
        データを受信する
        """
        try:
            d = os.read(self.conn_sock_file, max_len)
        except Exception as e:
            d = b""
            raise e
        return d

    def write_to_udc(self, lst: list) -> bool:
        """
        UDCファイルに書き込む
        成功時: True
        失敗時: False
        """
        udc_file_path = os.path.join(self.base_path, "UDC")
        d = "\n".join(lst) + "\n"
        try:
            fd = os.open(udc_file_path, os.O_RDWR)
            os.write(fd, d.encode())
            os.close(fd)
        except PermissionError:
            _logger.error("Permission error")
            return False
        except OSError as e:
            if e.errno == 19:
                # すでに有効化されていた場合のエラーを無視する
                pass
            else:
                # 不明なエラー
                raise e
        return True
    
    def enabled(self) ->bool:
        """
        USBデバイスを有効化する
        成功時: True
        失敗時: False
        """
        return self.write_to_udc(os.listdir("/sys/class/udc"))

    def disabled(self) ->bool:
        """
        USBデバイスを無効化する
        成功時: True
        失敗時: False
        """
        return self.write_to_udc([])
