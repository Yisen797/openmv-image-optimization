"""
PC端相机标定 & 畸变校正工具
============================
运行环境: PC (需要 opencv-python, numpy)

功能1 - 标定 (calibrate):
  从OpenMV采集的棋盘格图片计算相机内参和畸变系数

功能2 - 校正 (correct):
  用标定结果对高清照片进行畸变校正

=== 安装依赖 ===
  pip install opencv-python numpy

=== 使用方法 ===

1. 标定:
   python pc_calibrate.py calibrate --input ./calib_images/ --rows 6 --cols 8 --square 25

   参数说明:
   --input   棋盘格图片所在目录
   --rows    棋盘格内角点行数 (9x7棋盘格就是 6 行)
   --cols    棋盘格内角点列数 (9x7棋盘格就是 8 列)
   --square  每个格子的实际边长(mm), 用于计算物理焦距
   --fisheye 使用鱼眼模型 (OV5640广角镜头推荐)
   --save    输出文件保存路径 (默认: ./calib_result.npz)

2. 校正照片:
   python pc_calibrate.py correct --calib ./calib_result.npz --input ./photo.jpg --output ./corrected.jpg

   参数说明:
   --calib   标定结果文件 (.npz)
   --input   待校正的照片 (或目录, 批量处理)
   --output  输出路径
   --fisheye 使用鱼眼模型校正
   --crop    是否裁剪黑边 (默认True)
   --alpha   校正后保留区域比例 (0=最大裁剪, 1=保留全部含黑边)
"""

import numpy as np
import cv2
import glob
import os
import argparse
import sys

# ============================================================
# 棋盘格检测 & 标定
# ============================================================

def calibrate(input_dir, pattern_rows, pattern_cols, square_mm, use_fisheye=False, save_path="calib_result.npz"):
    """
    检测棋盘格角点, 计算相机内参和畸变系数

    参数:
      input_dir:      棋盘格图片目录
      pattern_rows:   内角点行数 (如 9x7棋盘格 → 6行)
      pattern_cols:   内角点列数 (如 9x7棋盘格 → 8列)
      square_mm:      格子实际边长(mm)
      use_fisheye:    True = 使用鱼眼模型(推荐OV5640广角)
      save_path:      结果保存路径
    """
    pattern_size = (pattern_cols, pattern_rows)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

    # 准备3D世界坐标点 (z=0平面)
    objp = np.zeros((pattern_rows * pattern_cols, 3), np.float32)
    objp[:, :2] = np.mgrid[0:pattern_cols, 0:pattern_rows].T.reshape(-1, 2)
    objp *= square_mm  # 缩放到实际尺寸(mm)

    # 收集角点
    obj_points = []   # 3D 世界坐标
    img_points = []   # 2D 图像坐标
    img_shape = None
    found_files = []

    image_files = sorted(glob.glob(os.path.join(input_dir, "*.[jJ][pP][gG]"))
                         + glob.glob(os.path.join(input_dir, "*.[pP][nN][gG]"))
                         + glob.glob(os.path.join(input_dir, "*.[bB][mM][pP]")))

    if not image_files:
        print(f"[ERROR] 在 {input_dir} 中没有找到图片文件")
        return None

    print(f"找到 {len(image_files)} 张图片, 开始检测棋盘格...")

    for fname in image_files:
        img = cv2.imread(fname)
        if img is None:
            print(f"  [SKIP] 无法读取: {fname}")
            continue

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img_shape = gray.shape[::-1]  # (width, height)

        # 检测棋盘格角点
        ret, corners = cv2.findChessboardCorners(gray, pattern_size, None)

        if ret:
            # 亚像素细化
            corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
            obj_points.append(objp)
            img_points.append(corners2)
            found_files.append(os.path.basename(fname))
            print(f"  [OK] {os.path.basename(fname)} → 检测到 {len(corners2)} 个角点")
        else:
            print(f"  [FAIL] {os.path.basename(fname)} → 未检测到棋盘格")

    if len(obj_points) < 10:
        print(f"\n[ERROR] 只检测到 {len(obj_points)} 张有效图片, 至少需要10张")
        print("请确保:")
        print("  1. 棋盘格平整无弯曲")
        print("  2. 棋盘格占画面 30%-70%")
        print("  3. 覆盖不同角度和位置")
        print("  4. 光照均匀, 无强烈反光")
        return None

    print(f"\n有效图片: {len(obj_points)}/{len(image_files)}")

    # 标定
    img_w, img_h = img_shape
    print(f"图像分辨率: {img_w}x{img_h}")
    print(f"标定模型: {'鱼眼 (fisheye)' if use_fisheye else '针孔 (pinhole)'}")

    if use_fisheye:
        # 鱼眼模型标定
        K = np.zeros((3, 3), np.float32)
        D = np.zeros((4, 1), np.float32)

        calib_flags = (cv2.fisheye.CALIB_RECOMPUTE_EXTRINSIC
                       + cv2.fisheye.CALIB_CHECK_COND
                       + cv2.fisheye.CALIB_FIX_SKEW)

        rms, K, D, rvecs, tvecs = cv2.fisheye.calibrate(
            obj_points, img_points,
            (img_w, img_h), K, D,
            flags=calib_flags,
            criteria=(cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 1e-6)
        )
    else:
        # 标准针孔模型标定
        rms, K, D, rvecs, tvecs = cv2.calibrateCamera(
            obj_points, img_points,
            (img_w, img_h),
            None, None
        )

    # 计算有效焦距 (mm)
    fx = K[0, 0]
    fy = K[1, 1]

    # OV5640 像素尺寸约 1.4μm
    pixel_size_um = 1.4
    focal_length_mm = fx * pixel_size_um / 1000.0

    print(f"\n{'='*50}")
    print(f"标定结果 (RMS重投影误差: {rms:.3f})")
    print(f"{'='*50}")
    print(f"\n相机矩阵 K:")
    print(f"  fx={K[0,0]:.1f}  fy={K[1,1]:.1f}")
    print(f"  cx={K[0,2]:.1f}  cy={K[1,2]:.1f}")
    print(f"  估算焦距: {focal_length_mm:.1f} mm (像素尺寸 {pixel_size_um}μm)")
    print(f"\n畸变系数 D:")
    print(f"  {D.ravel()}")

    # 保存结果
    np.savez(save_path,
             K=K, D=D,
             img_size=np.array([img_w, img_h]),
             rms=rms,
             use_fisheye=use_fisheye,
             pattern_size=pattern_size,
             square_mm=square_mm,
             pixel_size_um=pixel_size_um)
    print(f"\n[OK] 标定结果已保存到: {save_path}")
    print(f"\n=== OpenMV 使用建议 ===")
    print(f"你可以在 OpenMV IDE 中手动调节 lens_corr() 参数,")
    print(f"或者使用下面的校正脚本处理高清照片。")

    return K, D, img_shape


# ============================================================
# 图像校正
# ============================================================

def correct_image(img, K, D, use_fisheye=False, alpha=0.0, crop=True):
    """
    对单张图片进行畸变校正

    参数:
      img:         输入图像 (BGR numpy array)
      K:           相机矩阵
      D:           畸变系数
      use_fisheye: 是否鱼眼模型
      alpha:       保留区域比例 (0=无黑边裁剪, 1=全部保留)
      crop:        是否自动裁剪黑边

    返回: 校正后的图像
    """
    h, w = img.shape[:2]

    if use_fisheye:
        # 鱼眼校正
        new_K = cv2.fisheye.estimateNewCameraMatrixForUndistortRectify(
            K, D, (w, h), np.eye(3), balance=1.0 - alpha, new_size=(w, h)
        )
        map1, map2 = cv2.fisheye.initUndistortRectifyMap(
            K, D, np.eye(3), new_K, (w, h), cv2.CV_16SC2
        )
        corrected = cv2.remap(img, map1, map2, interpolation=cv2.INTER_LANCZOS4)
    else:
        # 标准校正
        new_K, roi = cv2.getOptimalNewCameraMatrix(
            K, D, (w, h), alpha, (w, h)
        )
        corrected = cv2.undistort(img, K, D, None, new_K)

    # 自动裁剪黑边
    if crop and alpha < 1.0:
        gray = cv2.cvtColor(corrected, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 1, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            x, y, w_rect, h_rect = cv2.boundingRect(np.vstack(contours))
            corrected = corrected[y:y+h_rect, x:x+w_rect]

    return corrected


def batch_correct(calib_path, input_path, output_path, use_fisheye=None, alpha=0.0, crop=True):
    """
    批量校正图片

    calib_path: 标定文件路径 (.npz)
    input_path: 输入图片或目录
    output_path: 输出图片或目录
    """
    # 加载标定数据
    data = np.load(calib_path, allow_pickle=True)
    K = data['K']
    D = data['D']

    if use_fisheye is None:
        use_fisheye = bool(data.get('use_fisheye', False))

    print(f"加载标定数据: {calib_path}")
    print(f"标定模型: {'鱼眼' if use_fisheye else '针孔'}")
    print(f"RMS重投影误差: {data.get('rms', 'N/A')}")
    print(f"图像尺寸: {data['img_size']}")

    # 收集待处理文件
    if os.path.isdir(input_path):
        image_files = sorted(
            glob.glob(os.path.join(input_path, "*.[jJ][pP][gG]"))
            + glob.glob(os.path.join(input_path, "*.[pP][nN][gG]"))
            + glob.glob(os.path.join(input_path, "*.[bB][mM][pP]"))
        )
        if not image_files:
            print(f"[ERROR] {input_path} 中没有找到图片")
            return
        single_file = False
    else:
        image_files = [input_path]
        single_file = True

    # 处理
    os.makedirs(output_path, exist_ok=True) if not single_file else os.makedirs(
        os.path.dirname(output_path) or '.', exist_ok=True)

    print(f"\n处理 {len(image_files)} 张图片...")

    for i, fname in enumerate(image_files):
        img = cv2.imread(fname)
        if img is None:
            print(f"  [{i+1}/{len(image_files)}] SKIP: {fname} (无法读取)")
            continue

        corrected = correct_image(img, K, D, use_fisheye, alpha, crop)

        if single_file:
            out_name = output_path
        else:
            out_name = os.path.join(output_path, os.path.basename(fname))

        cv2.imwrite(out_name, corrected, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print(f"  [{i+1}/{len(image_files)}] {os.path.basename(fname)} "
              f"→ {os.path.basename(out_name)} "
              f"({img.shape[1]}x{img.shape[0]} → {corrected.shape[1]}x{corrected.shape[0]})")

    print(f"\n[OK] 处理完成! 输出: {output_path if single_file else output_path + '/**'}")


# ============================================================
# 命令行接口
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="相机标定 & 畸变校正工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # ---- calibrate ----
    calib_parser = subparsers.add_parser("calibrate", help="从棋盘格图片标定相机")
    calib_parser.add_argument("--input", required=True, help="棋盘格图片目录")
    calib_parser.add_argument("--rows", type=int, default=6, help="内角点行数 (默认: 6)")
    calib_parser.add_argument("--cols", type=int, default=8, help="内角点列数 (默认: 8)")
    calib_parser.add_argument("--square", type=float, default=25.0, help="格子边长mm (默认: 25)")
    calib_parser.add_argument("--fisheye", action="store_true", help="使用鱼眼模型")
    calib_parser.add_argument("--save", default="calib_result.npz", help="输出文件路径")

    # ---- correct ----
    correct_parser = subparsers.add_parser("correct", help="校正图片")
    correct_parser.add_argument("--calib", required=True, help="标定文件 (.npz)")
    correct_parser.add_argument("--input", required=True, help="输入图片/目录")
    correct_parser.add_argument("--output", required=True, help="输出路径")
    correct_parser.add_argument("--fisheye", action="store_true", default=None, help="强制鱼眼模型")
    correct_parser.add_argument("--alpha", type=float, default=0.0,
                                help="保留区域 (0=裁剪黑边, 1=全部保留)")
    correct_parser.add_argument("--no-crop", action="store_true", help="不自动裁剪黑边")

    args = parser.parse_args()

    if args.command == "calibrate":
        calibrate(
            input_dir=args.input,
            pattern_rows=args.rows,
            pattern_cols=args.cols,
            square_mm=args.square,
            use_fisheye=args.fisheye,
            save_path=args.save
        )

    elif args.command == "correct":
        batch_correct(
            calib_path=args.calib,
            input_path=args.input,
            output_path=args.output,
            use_fisheye=args.fisheye,
            alpha=args.alpha,
            crop=not args.no_crop
        )

    else:
        parser.print_help()
