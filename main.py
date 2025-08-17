#!/usr/bin/python
# coding:utf-8

# @FileName:    main.py
# @Time:        2024/1/2 22:27
# @Author:      bubu
# @Project:     douyinLiveWebFetcher

from ui_main import LiveStreamUI

if __name__ == '__main__':
    print("【启动】抖音直播间弹幕采集工具 UI版本")
    app = LiveStreamUI()
    app.run()

