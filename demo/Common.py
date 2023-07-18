# SPDX-FileCopyrightText: 2023 K.Agata
# SPDX-License-Identifier: GPL-3.0

import cv2
import os
import numpy as np
import slack_sdk
import pyocr
from threading import Thread
from PIL import Image
from logging import getLogger, FileHandler, StreamHandler, DEBUG

SLACK_TOKEN = os.getenv('SLACK_API_TOKEN')
SLACK_CHANNEL = os.getenv('SLACK_CHANNEL_ID')

logger = getLogger(__name__)
logger.setLevel(DEBUG)
# logger.addHandler(StreamHandler())
logger.addHandler(FileHandler(f'{os.path.dirname(__file__)}/Common.log'))

# for OCR
# path_tesseract = "/usr/share/tesseract-ocr/4.00/tessdata"
# if path_tesseract not in os.environ["PATH"].split(os.pathsep):
#     os.environ["PATH"] += os.pathsep + path_tesseract
tools = pyocr.get_available_tools()
if len(tools) == 0:
    logger.error("Do not find OCR tools")
OCR_TOOL = tools[0]


def _send_msg_to_slack(msg_text):
    try:
        slack_cl = slack_sdk.WebClient(token=SLACK_TOKEN)
        slack_cl.chat_postMessage(text=msg_text, channel=SLACK_CHANNEL)
    except slack_sdk.errors.SlackApiError as e:
        logger.exception('Slack APIのエラー')

def send_msg_to_slack(msg_text):
    Thread(target=_send_msg_to_slack, args=(msg_text,)).start()

def _send_img_to_slack(msg_text, file_path):
    try:
        slack_cl = slack_sdk.WebClient(token=SLACK_TOKEN)
        slack_cl.files_upload(channels=SLACK_CHANNEL,
                              file=file_path,
                              initial_comment=msg_text)
    except slack_sdk.errors.SlackApiError as e:
        logger.exception('Slack APIのエラー')

def send_img_to_slack(msg_text, file_path='ss.jpg'):
    Thread(target=_send_img_to_slack, args=(msg_text, file_path)).start()

def decode_fourcc(v):
    v = int(v)
    return "".join([chr((v >> 8 * i) & 0xFF) for i in range(4)])


def img_binarization(img, threshold=127):
    return cv2.threshold(img, threshold, 255, cv2.THRESH_BINARY)


def img_cmp(image1, image2):
    # Compare by number of matched pixels
    return np.count_nonzero(image1 == image2) / image1.size


def ocr(cv2_img):
    pil_image = Image.fromarray(cv2_img)
    return OCR_TOOL.image_to_string(
        pil_image,
        lang="jpn",
        builder=pyocr.builders.TextBuilder(tesseract_layout=6))


class Capture:

    def __init__(self, device_id=0):
        self.cap = cv2.VideoCapture(device_id)
        # self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
        self.cap.set(cv2.CAP_PROP_FOURCC,
                     cv2.VideoWriter_fourcc('Y', 'U', 'Y', 'V'))
        # self.cap.set(cv2.CAP_PROP_FPS, 30)
        # self.cap.set(cv2.CAP_PROP_FPS, 10)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Latency Reduction

        # print(
        #     f"[{decode_fourcc(self.cap.get(cv2.CAP_PROP_FOURCC))} "
        #     f"{self.cap.get(cv2.CAP_PROP_FPS):.1f}fps "
        #     f"{self.cap.get(cv2.CAP_PROP_FRAME_WIDTH):.0f}x{self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT):.0f}]"
        # )

        if not self.cap.isOpened():
            logger.error('Could not open device.')

    def __del__(self):
        self.cap.release()

    def get_screenshot(self, gray=False):
        self.cap.read()  # 1フレーム読み捨て
        for i in range(64):
            ret, cv2_img = self.cap.read()
            if ret and cv2.countNonZero(cv2_img[0]) > 0:
                if gray:
                    return cv2.cvtColor(cv2_img, cv2.COLOR_BGR2GRAY)
                return cv2_img
        return None

    def save_screenshot(self, save_path='ss.jpg'):
        cv2_img = self.get_screenshot()
        if cv2_img is None:
            return False

        # リサイズ
        height = cv2_img.shape[0]
        width = cv2_img.shape[1]
        cv2_img = cv2.resize(cv2_img, (int(width * 0.5), int(height * 0.5)))

        # 保存
        cv2.imwrite(save_path, cv2_img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])

        return True
