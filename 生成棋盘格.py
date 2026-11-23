"""
生成可打印的棋盘格标定板
========================
生成 9列×7行内角点 (10×8格子) 的棋盘格图片, 用于相机标定。

使用方法:
  python generate_checkerboard.py

输出: checkerboard_9x7.png (可直接打印在A4纸上)

可调参数:
  --cols    内角点列数 (默认8 → 9列方块)
  --rows    内角点行数 (默认6 → 7行方块)
  --square  格子边长mm (默认25, 仅用于显示, 未做A4适配)
"""

import numpy as np
import cv2
import argparse
import os

def generate_checkerboard(cols=8, rows=6, square_px=80, margin_px=60):
    """
    生成棋盘格图像

    参数:
      cols:       内角点列数
      rows:       内角点行数
      square_px:  每格像素数
      margin_px:  边距像素数
    """
    # 棋盘格方块数 = 内角点数 + 1
    board_w = cols * square_px
    board_h = rows * square_px

    # 创建棋盘格（零值 = 黑块, 交替）
    pattern = np.zeros((rows, cols), dtype=np.uint8)
    pattern[1::2, ::2] = 255
    pattern[::2, 1::2] = 255

    # 放大到实际像素
    board = cv2.resize(pattern, (board_w, board_h), interpolation=cv2.INTER_NEAREST)

    # 添加边距
    img_w = board_w + 2 * margin_px
    img_h = board_h + 2 * margin_px
    img = np.ones((img_h, img_w), dtype=np.uint8) * 255
    img[margin_px:margin_px+board_h, margin_px:margin_px+board_w] = board

    # 添加标注
    # 在左上角画标记 (小三角)
    cv2.putText(img, "TOP-LEFT", (margin_px, margin_px - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, 0, 1)

    return img

def main():
    parser = argparse.ArgumentParser(description="生成棋盘格标定板")
    parser.add_argument("--cols", type=int, default=8, help="内角点列数 (默认8)")
    parser.add_argument("--rows", type=int, default=6, help="内角点行数 (默认6)")
    parser.add_argument("--square", type=int, default=80, help="每格像素数 (默认80)")
    parser.add_argument("--margin", type=int, default=60, help="边距像素数 (默认60)")
    parser.add_argument("--dpi", type=int, default=300, help="打印DPI (默认300)")
    parser.add_argument("--output", default="checkerboard_9x7.png", help="输出文件名")
    args = parser.parse_args()

    img = generate_checkerboard(args.cols, args.rows, args.square, args.margin)

    # 保存
    cv2.imwrite(args.output, img)
    print(f"[OK] 棋盘格已保存: {args.output}")
    print(f"     内角点: {args.cols}列 × {args.rows}行")
    print(f"     方块数: {args.cols+1}列 × {args.rows+1}行")
    print(f"     图像尺寸: {img.shape[1]}×{img.shape[0]} px")
    print(f"\n标定命令:")
    print(f"  python pc_calibrate.py calibrate --input ./calib/ --cols {args.cols} --rows {args.rows} --square <格子实际mm> --fisheye")

if __name__ == "__main__":
    main()
