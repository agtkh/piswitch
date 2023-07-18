# SPDX-FileCopyrightText: 2023 K.Agata
# SPDX-License-Identifier: GPL-3.0
"""
This is free software.
"""

import sys, os

# piswitchパッケージをインポート
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from piswitch import Procon

if __name__ == "__main__":
    mode = 0
    # 0: 方向キーを操作
    # 1: 右スティックを操作
    # 2: 左スティックを操作
    try:
        con = Procon()

        if not con.start():
            print("Failed to start")
            sys.exit()

        while True:
            btn = input(f"[{mode}] Press button (q: quit, m: mode change): ")
            if btn == "q":
                break
            elif btn == "m":
                mode = (mode + 1) % 3
            else:
                con.push(btn, delay=0.2)

    except KeyboardInterrupt as e:
        print("\nExiting with keyboard interrupt")

    # except Exception as e:
    #     print(f"Unknown exception: ({e.__class__.__name__}) {e}")

    con.close()
    print("Done")
