#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Proconの基本クラス
"""
import logging
import threading
import time
from ctypes import LittleEndianStructure, c_uint8

from .procon_usb_gadget import ProconUsbGadget

# DEBUG, INFO, WARNING, ERROR, CRITICAL
_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)
_logger.addHandler(logging.StreamHandler())
# _logger.propagate = True

class ProconControlStruct(LittleEndianStructure):
    # コントロールデータ構造体 (11bytes)
    _fields_ = [("connection_info", c_uint8, 4), ("battery_level", c_uint8, 4), ("button_y", c_uint8, 1), ("button_x", c_uint8, 1), ("button_b", c_uint8, 1),
                ("button_a", c_uint8, 1), ("button_right_sr", c_uint8, 1), ("button_right_sl", c_uint8, 1), ("button_r", c_uint8, 1), ("button_zr", c_uint8, 1),
                ("button_minus", c_uint8, 1), ("button_plus", c_uint8, 1), ("button_thumb_r", c_uint8, 1), ("button_thumb_l", c_uint8, 1),
                ("button_home", c_uint8, 1), ("button_capture", c_uint8, 1), ("dummy", c_uint8, 1), ("charging_grip", c_uint8, 1), ("dpad_down", c_uint8, 1),
                ("dpad_up", c_uint8, 1), ("dpad_right", c_uint8, 1), ("dpad_left", c_uint8, 1), ("button_left_sr", c_uint8, 1), ("button_left_sl", c_uint8, 1),
                ("button_l", c_uint8, 1), ("button_zl", c_uint8, 1), ("analog", c_uint8 * 6), ("vibrator_input_report", c_uint8)]


class ProconBase:

    def __init__(self, mac_addr="00005e00535f"):
        self.mac_addr = mac_addr

        self.control_data = bytearray.fromhex("810000000008800008800c")
        self.control = ProconControlStruct.from_buffer(self.control_data)
        self.counter = 0
        self.player_lights = 0

        self.input_looping = False
        self.close_req_flag = False
        self.gadget = ProconUsbGadget("procon")

        self.spi_rom = {
            0x60:
                bytearray.fromhex("ffff ffff ffff ffff ffff ffff ffff ffff"
                                  "ffff ffff ffff ffff ffff ff02 ffff ffff"
                                  "ffff ffff ffff ffff ffff ffff ffff ffff"
                                  "ffff ffff ffff ffff ffff ffff fff9 255f"
                                  "b217 7903 665f 8357 7201 3661 0e56 66ff"
                                  "2c2c c3d1 1515 0e62 27c1 c32c ffff ffff"
                                  "ffff ffff ffff ffff ffff ffff ffff ffff"
                                  "ffff ffff ffff ffff ffff ffff ffff ffff"
                                  "50fd 0000 c60f 0f30 61ae 90d9 d414 5441"
                                  "1554 c779 9c33 3663 0f30 61ae 90d9 d414"
                                  "5441 1554 c779 9c33 3663"),
            0x80:
                bytearray.fromhex("ffff ffff ffff ffff ffff ffff ffff ffff"
                                  "ffff ffff ffff ffff ffff ffff ffff ffff"
                                  "ffff ffff ffff b2a1 aeff e7ff ec01 0040"
                                  "0040 0040 eaff 0f00 0700 e73b e73b e73b")
        }

    def start(self):
        """プロコンを起動"""
        self.gadget.open()

        # self.reset_magic_packet()

        threading.Thread(target=self.countup_loop, daemon=True).start()
        threading.Thread(target=self.interact_loop, daemon=True).start()

        st = False
        for _ in range(100):
            if self.input_looping:
                st = True
                break
            # 通信が始まるまで待機
            time.sleep(0.1)
        return st

    def close(self):
        """プロコンを停止する"""
        self.input_looping = False
        self.close_req_flag = True
        time.sleep(0.5)
        self.gadget.close()

    def send_usb(self, send_buf: bytearray, max_packet_size: int) -> bool:
        """
        USBパケットの送信
        """
        data_len = len(send_buf)
        if data_len > max_packet_size:
            return False

        send_buf.extend(bytearray(max_packet_size - data_len))

        # 送信
        return self.gadget.send(send_buf)

    def send_hid(self, report_id: int, cmd: int, data: bytes):
        """
        HID送信
        report_id:
            0x21: コントローラー入力 + UART応答
            0x30: コントローラー入力のみ
        """
        send_buf = bytearray([report_id, cmd])
        send_buf.extend(data)
        return self.send_usb(send_buf, 64)

    def send_uart(self, code, subcmd, data):
        """
        UART送信
        """
        send_buf = self.control_data.copy()
        send_buf.extend([code, subcmd])
        send_buf.extend(data)
        # 0x21: コントローラー入力+UART応答
        self.send_hid(0x21, self.counter, send_buf)

    def send_spi(self, addr: bytes, data):
        """
        SPI送信
        """
        send_buf = bytearray(addr)
        send_buf.extend([0x00, 0x00, len(data)])
        send_buf.extend(data)
        self.send_uart(0x90, 0x10, send_buf)

    def reset_magic_packet(self):
        # reset magic packet
        self.send_hid(0x81, 0x03, bytes([]))
        time.sleep(0.05)
        self.send_hid(0x81, 0x01, bytes([0x00, 0x03]))
        time.sleep(0.05)

    def countup_loop(self):
        """
        カウンターをインクリメントする関数。
        実際のプロコンは約80Hzで動作しているが、
        今回は軽量化のため約40Hzで動作させている。
        """
        while not self.close_req_flag:
            self.counter = (self.counter + 2) % 256
            time.sleep(1 / 40)

    def send_input_loop(self):
        while self.input_looping and not self.close_req_flag:
            buf = self.control_data
            # 0x30: コントローラー入力のみ
            self.send_hid(0x30, self.counter, buf)
            time.sleep(1 / 40)

    def read_spi_rom(self, spi_addr: bytes, data_len):
        """SPIでのROMの読み込み"""
        try:
            addr1 = spi_addr[1]
            addr2 = spi_addr[0]
            return self.spi_rom[addr1][addr2:addr2 + data_len]
        except IndexError:
            _logger.error(f"{spi_addr}({data_len}) is not found")
            return None

    def player_lights_str(self):
        return f"{self.player_lights:04b}"[::-1].replace("0", "□ ").replace("1", "■ ")[:-1]

    def uart_interact(self, subcmd, data):
        """
        UARTでの対話
        """
        if subcmd == 0x01:
            _logger.info(f">>> [UART] Bluetooth manual pairing: {data.hex()}")
            self.send_uart(0x81, subcmd, [0x03, 0x01])
        elif subcmd == 0x02:
            _logger.info(f">>> [UART] Request device info")
            self.send_uart(0x82, subcmd, bytes.fromhex("0421 03 02" + self.mac_addr[::-1] + "03 02"))
        elif subcmd == 0x30:
            # Set player lights
            self.player_lights = data[0]
            _logger.info(f">>> [UART] Set player lights: {self.player_lights_str()}")
            self.send_uart(0x80, subcmd, [])
        elif subcmd == 0x03:
            _logger.info(f">>> [UART] Set input report mode: {data[0]}")
            self.send_uart(0x80, subcmd, [])
        elif subcmd == 0x08:
            _logger.info(f">>> [UART] Set shipment low power state: {data[0]}")
            self.send_uart(0x80, subcmd, [])
        elif subcmd == 0x38:
            _logger.info(f">>> [UART] 0x38: {data.hex()}")
            self.send_uart(0x80, subcmd, [])
        elif subcmd == 0x40:
            _logger.info(f">>> [UART] Enable IMU: {data.hex()}")
            self.send_uart(0x80, subcmd, [])
        elif subcmd == 0x48:
            _logger.info(f">>> [UART] Enable vibration: {data[0]}")
            self.send_uart(0x80, subcmd, [])
        elif subcmd == 0x04:
            # Trigger buttons elapsed time
            self.send_uart(0x83, subcmd, [])
        elif subcmd == 0x21:
            # Set NFC/IR MCU configuration
            self.send_uart(0xA0, subcmd, bytes.fromhex("0100ff0003000501"))
        elif subcmd == 0x10:
            # SPI flash read
            spi_addr = data[:2]
            data_len = data[4]
            rom_data = self.read_spi_rom(spi_addr, data_len)
            if rom_data != None:
                self.send_spi(spi_addr, rom_data)
        else:
            _logger.debug(">>> [UART]", subcmd, data.hex())

    def interact_loop(self):
        """
        対話の繰り返し
        """
        while not self.close_req_flag:
            try:
                data = self.gadget.recv(128)
                if data[0] == 0x80:
                    if data[1] == 0x01:
                        _logger.info(f">>> Requested MAC addr")
                        self.send_hid(0x81, data[1], bytes.fromhex("0003" + self.mac_addr))
                    elif data[1] == 0x02:
                        _logger.info(f">>> Handshake")
                        self.send_hid(0x81, data[1], [])
                    elif data[1] == 0x03:
                        _logger.info(f">>> baudrate setting {data[2:].hex()}")
                    elif data[1] == 0x04:
                        _logger.info(f">>> Enable USB HID Joystick report")
                        self.input_looping = True
                        threading.Thread(target=self.send_input_loop, daemon=True).start()
                    elif data[1] == 0x05:
                        _logger.info(f">>> Disable USB HID Joystick report")
                        self.input_looping = False
                        self.reset_magic_packet()
                    else:
                        _logger.info(f">>> {data.hex()}")
                elif data[0] == 0x01 and len(data) > 16:  # UARTで届いた
                    subcmd = data[10]
                    self.uart_interact(subcmd, data[11:])
                elif data[0] == 0x10 and len(data) == 10:
                    pass
                else:
                    _logger.info(f">>> {data.hex()}")
            except BlockingIOError as e:
                # print("except5:", e)
                pass
            # except Exception as e:
            #     print("except2:", e)
            #     os._exit(1)
