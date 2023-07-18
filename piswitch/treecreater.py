#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
与えられたディレクトリツリーから、ディレクトリやファイルを作成するプログラム
"""

import os


class SymbolicLink:
    """シンボリックリンクを表すクラス"""

    def __init__(self, src):
        self.src = src


def create_tree(tree, path):
    """ディレクトリツリーからディレクトリやファイルを作成する"""
    os.makedirs(path, exist_ok=True)
    for name, content in tree.items():
        dst_path = os.path.join(path, name)
        if isinstance(content, dict):
            # dict = directory
            create_tree(content, dst_path)

        elif isinstance(content, SymbolicLink):
            # SymbolicLink = symbolic link
            os.symlink(os.path.join(path, content.src), dst_path)

        elif isinstance(content, bytes):
            # bytes = binary file
            with open(dst_path, 'wb+') as f:
                f.write(content)

        elif isinstance(content, str):
            with open(dst_path, 'w+') as f:
                f.write(content + '\n')
                
        else:
            raise ValueError(f"Unknown type: {type(content)}")
