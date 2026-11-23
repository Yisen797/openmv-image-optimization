"""
OpenMV H7 Plus 标定图像采集脚本
================================
采集棋盘格标定图像, 供PC端计算畸变系数。

使用方法:
  1. 打印棋盘格, 贴在平整表面
  2. 烧录此脚本到 OpenMV H7 Plus
  3. 插入SD卡
  4. 棋盘格放摄像头前不同角度/位置
  5. 按P0拍摄, 共拍15-25张
  6. 图片存于SD卡 /calib/ 目录
  7. 拷贝到PC, 运行 PC端标定校正.py 计算系数
"""

import sensor, image, time, os
from pyb import LED, Pin

# ============================================================
# 配置
# ============================================================

SAVE_DIR = "/sd/calib"
btn = Pin('P0', Pin.IN, Pin.PULL_UP)

red_led   = LED(1)
green_led = LED(2)
blue_led  = LED(3)

# ============================================================
# 初始化
# ============================================================

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.VGA)
sensor.set_auto_gain(True)
sensor.set_auto_whitebal(True)
sensor.set_auto_exposure(True)
sensor.skip_frames(30)

try:
    os.mkdir(SAVE_DIR)
    print("[OK] 创建目录: %s" % SAVE_DIR)
except OSError:
    print("[OK] 目录已存在: %s" % SAVE_DIR)

clock = time.clock()
count = 0

def check_button():
    if btn.value() == 1:
        return False
    press_start = time.ticks_ms()
    while btn.value() == 0:
        time.sleep_ms(10)
    duration = time.ticks_diff(time.ticks_ms(), press_start)
    return 50 < duration < 800

print("\n" + "=" * 50)
print("棋盘格标定采集")
print("将棋盘格放在摄像头前, 按P0拍摄")
print("目标: 15-25张, 覆盖不同角度和位置")
print("=" * 50 + "\n")

while True:
    clock.tick()
    img = sensor.snapshot()

    rects = img.find_rects(threshold=8000)

    fps = clock.fps()
    img.draw_string(10, 10, "Calib | FPS:%.1f" % fps, scale=1.2)
    img.draw_string(10, 30, "Captured: %d" % count, scale=1.2)
    img.draw_string(10, 50, "Rects: %d" % len(rects), scale=1.2)
    img.draw_string(10, 70, "Press P0 to capture", scale=1.2)

    for r in rects:
        img.draw_rectangle(r.rect(), color=(0, 255, 0))

    if check_button():
        count += 1
        filename = "%s/calib_%04d.jpg" % (SAVE_DIR, count)
        img.save(filename)
        print("[%d] SAVED: %s" % (count, filename))

        green_led.on()
        time.sleep_ms(100)
        green_led.off()

        if count >= 25:
            print("\n>>> 已采集 %d 张, 足够标定!" % count)
        elif count >= 15:
            print("\n>>> 已采集 %d 张, 基本够用" % count)

    if count >= 15:
        blue_led.on()
    else:
        blue_led.off()
