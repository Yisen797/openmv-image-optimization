"""
OpenMV H7 Plus + OV5640 实时预览
=================================
HVGA 480x320 | 传感器出厂校准 | 仅畸变校正
"""

import sensor, image, time

# ============================================================
# 参数
# ============================================================

LENS_STRENGTH = 1.8
LENS_ZOOM     = 1.0

# ============================================================
# 初始化 (不写任何OV5640寄存器, 保留出厂校准)
# ============================================================

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.HVGA)

sensor.set_auto_exposure(True)
sensor.set_auto_gain(True)
sensor.set_auto_whitebal(True)

sensor.skip_frames(30)
print("就绪 | HVGA | 传感器出厂校准 | 仅畸变校正")

# ============================================================
# 主循环
# ============================================================

clock = time.clock()

while True:
    clock.tick()
    img = sensor.snapshot()

    img.lens_corr(strength=LENS_STRENGTH, zoom=LENS_ZOOM)

    fps = clock.fps()
    img.draw_string(5, 5, "%.1f fps" % fps, scale=1.3, mono_space=False)
