#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USB Gadget API for Linuxを使って、Nintendo Switch Pro Controllerを作成する
Raspberry Pi 4Bでの動作を想定している。
"""

from .usb_gadget import UsbGadget
from . import treecreater


class ProconUsbGadget(UsbGadget):

    def __init__(self, name):
        config_tree = {
            "idVendor": "0x057e",  # Nintendo Co., Ltd
            "idProduct": "0x2009",  # Pro Controller
            "bcdDevice": "0x0200",
            "bcdUSB": "0x0200",
            "bDeviceClass": "0x00",
            "bDeviceSubClass": "0x00",
            "bDeviceProtocol": "0x00",
            "bMaxPacketSize0": "0x40",
            "strings/0x409": {
                "serialnumber": "000000000001",
                "manufacturer": "Nintendo Co., Ltd.",
                "product": "Pro Controller",
            },
            "configs/c.1": {
                "MaxPower": "500",
                "bmAttributes": "0xa0",
                "strings/0x409": {
                    "configuration": "Nintendo Switch Pro Controller",
                }
            },
            "functions/hid.usb0": {
                "protocol":
                    "0",
                "subclass":
                    "0",
                "no_out_endpoint":
                    "0",
                "report_length":
                    "64",
                "report_desc":
                    bytes.fromhex(
                        "050115000904a1018530050105091901290a150025017501950a5500650081020509190b290e150025017501950481027501950281030b01000100a1000b300001000b310001000b320001000b35000100150027ffff0000751095048102c00b39000100150025073500463b0165147504950181020509190f2912150025017501950481027508953481030600ff852109017508953f8103858109027508953f8103850109037508953f9183851009047508953f9183858009057508953f9183858209067508953f9183c0"
                    ),
            },
            "configs/c.1/hid.usb0": treecreater.SymbolicLink("functions/hid.usb0")
        }
        super().__init__(name, config_tree)
