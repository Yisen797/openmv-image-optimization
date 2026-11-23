"""
OpenMV H7 Plus + OV5640 高清拍照
=================================
倒计时 → 拍照 → 双边去噪+自然锐化 → 冻结显示
"""

import sensor, image, time
from pyb import LED

# ============================================================
# 参数
# ============================================================

LENS_STRENGTH = 1.8
LENS_ZOOM     = 1.0

# ============================================================
# 初始化 (不写OV5640寄存器, 保留出厂校准)
# ============================================================

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.VGA)
sensor.set_auto_exposure(True)
sensor.set_auto_gain(True)
sensor.set_auto_whitebal(True)
sensor.skip_frames(30)

red   = LED(1)
green = LED(2)
blue  = LED(3)

def all_off():
    red.off()
    green.off()
    blue.off()

def yellow():
    red.on()
    green.on()
    blue.off()

def flash(led, count=2, delay=150):
    for _ in range(count):
        led.on()
        time.sleep_ms(delay)
        led.off()
        time.sleep_ms(delay)

# ============================================================
# 倒计时
# ============================================================

all_off()
print("高清拍照  lens=%.1f  VGA" % LENS_STRENGTH)

for s in [3, 2, 1]:
    deadline = time.ticks_add(time.ticks_ms(), 1000)

    if s == 3:
        green.on()
    elif s == 2:
        yellow()
    elif s == 1:
        green.off()
        red.on()

    while time.ticks_diff(deadline, time.ticks_ms()) > 0:
        img = sensor.snapshot()
        img.lens_corr(strength=LENS_STRENGTH, zoom=LENS_ZOOM)
        img.draw_string(5, 5, "%d" % s, scale=5, mono_space=False)

# ============================================================
# 拍照 + 软件处理 (不碰传感器寄存器)
# ============================================================

all_off()
time.sleep_ms(100)

print("拍照处理中...")
img = sensor.snapshot()
img.lens_corr(strength=LENS_STRENGTH, zoom=LENS_ZOOM)
img.bilateral(3, color_sigma=0.1, space_sigma=2)
img.gaussian(1, unsharp=True)

flash(green, 2, 200)
red.on()

# 画标识 (必须在sleep之前)
img.draw_rectangle(0, 0, img.width(), img.height(),
                   color=(0, 255, 0), thickness=4)
img.draw_string(10, 10, "PHOTO", scale=3, mono_space=False)

# 存到G盘 (SD卡优先, 内部Flash备选)
saved = False

# 1. 先试SD卡 (插了卡G盘就是SD卡)
try:
    img.save("/sd/capture.jpg")
    print("已保存: SD卡 capture.jpg")
    saved = True
except:
    pass

# 2. 再试内部Flash
if not saved:
    try:
        img.save("/flash/capture.jpg")
        print("已保存: 内部Flash capture.jpg")
        saved = True
    except:
        pass

# 3. 当前目录
if not saved:
    try:
        img.save("capture.jpg")
        print("已保存: capture.jpg")
        saved = True
    except:
        pass

if not saved:
    print("保存失败, 右键IDE保存")

try:
    sensor.sleep(True)
except:
    pass

print("完成")

# ============================================================
# 冻结显示
# ============================================================

while True:
    time.sleep_ms(500)
