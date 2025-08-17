#!/usr/bin/python
# coding:utf-8

# @FileName:    main_cmd.py
# @Time:        2024/1/2 22:27
# @Author:      bubu
# @Project:     douyinLiveWebFetcher

from liveMan import DouyinLiveWebFetcher

if __name__ == '__main__':
    live_id = '688562299427'
    print(f"【启动】开始监听直播间: {live_id}")
    print("【提示】按 Ctrl+C 可以停止程序并保存Excel文件")

    # 命令行模式下不传入ui_mode参数，默认为False，可以使用信号处理器
    room = DouyinLiveWebFetcher(live_id)
    room.get_room_status()

    try:
        room.start()
    except KeyboardInterrupt:
        print("\n【!】用户手动停止程序")
    except Exception as e:
        print(f"【X】程序异常: {e}")
    finally:
        room.stop()
