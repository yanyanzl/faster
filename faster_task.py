# -*- coding: utf-8 -*-
"""可取消、可显示进度的后台任务令牌（长时间扫描用）。

用法：task = Task(); 扫描循环里  if not task.tick(当前目录): break   # 被取消时返回 False，保留已有的部分结果
界面线程读取 task.text / task.count 显示进度，用户点“取消”调用 task.cancel()。
"""
import threading


class Task:
    def __init__(self):
        self._ev = threading.Event()
        self.text, self.count = "", 0

    def cancel(self):
        self._ev.set()

    @property
    def cancelled(self):
        return self._ev.is_set()

    def tick(self, text=None, n=1):
        """记一次进度；返回 True 表示继续，False 表示已被取消，应尽快结束循环"""
        self.count += n
        if text is not None:
            self.text = str(text)
        return not self._ev.is_set()
