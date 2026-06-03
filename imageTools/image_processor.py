# -*- coding: utf-8 -*-
"""图像处理模块 —— 提供常见图像处理方法，支持参数调节。

功能分类:
  - 增强: 亮度/对比度、伽马校正、直方图均衡化、CLAHE
  - 去噪: 高斯模糊、中值滤波、双边滤波、非局部均值、连通性过滤
  - 形态学: 腐蚀、膨胀、开运算、闭运算
  - 阈值化: 自适应阈值、Otsu
  - 检测: 边缘检测(canny/sobel/laplacian)、形状检测(矩形/圆形/多边形)、文字检测、条码检测
  - 形状检测: 矩形、圆形、多边形
  - 颜色处理: 颜色转换(灰度/HSV/RGB/LAB)、颜色过滤、自适应分割
  - 文字检测: 双引擎 —— EasyOCR GPU(主) + PaddleOCR CPU(辅) + 形态学(回退)
    * EasyOCR: PyTorch CUDA 加速，CRAFT 检测器，速度快
    * PaddleOCR: DB++ 检测器，弧形文字精度更高，CPU 兜底
    * 形态学: 纯 OpenCV，无任何依赖时的最后回退
"""
import math
import cv2
import numpy as np

# ══════════════════════════════════════════════════════════════════════
# 双引擎文字检测初始化（按优先级：GPU → CPU → 形态学）
# ══════════════════════════════════════════════════════════════════════

# 引擎 1: EasyOCR (PyTorch CUDA) — 快速 GPU 检测
try:
    import easyocr
    _EASYOCR_READER = easyocr.Reader(['en'], gpu=True, verbose=False)
    HAS_EASYOCR = True
except Exception:
    _EASYOCR_READER = None
    HAS_EASYOCR = False

# 引擎 2: PaddleOCR (DB++) — 弧形文字精度最高
try:
    from paddleocr import PaddleOCR
    _PADDLE_OCR = PaddleOCR(lang='en', use_angle_cls=False, show_log=False,
                            det_db_thresh=0.3, det_db_box_thresh=0.4,
                            det_limit_side_len=640, use_gpu=False)
    HAS_PADDLE = True
except Exception:
    _PADDLE_OCR = None
    HAS_PADDLE = False




class ImageProcessor:
    """图像处理器 —— 封装各种图像处理算法。"""

    # ------------------------------------------------------------------
    # 增强函数
    # ------------------------------------------------------------------
    @staticmethod
    def adjust_brightness_contrast(img: np.ndarray, brightness: int = 0,
                                    contrast: int = 0) -> np.ndarray:
        """调整亮度和对比度。

        Args:
            img: 输入图像 (BGR 或灰度)
            brightness: 亮度调节 [-100, 100]，0 为原始
            contrast: 对比度调节 [-100, 100]，0 为原始

        Returns:
            处理后的图像
        """
        if img is None:
            return img

        # 亮度
        if brightness != 0:
            if brightness > 0:
                shadow = brightness
                highlight = 255
            else:
                shadow = 0
                highlight = 255 + brightness
            alpha = (highlight - shadow) / 255
            gamma = shadow
            img = cv2.addWeighted(img, alpha, img, 0, gamma)

        # 对比度
        if contrast != 0:
            f = 131 * (contrast + 127) / (127 * (131 - contrast))
            img = cv2.addWeighted(img, f, img, 0, 127 * (1 - f))

        return np.clip(img, 0, 255).astype(np.uint8)

    @staticmethod
    def gamma_correction(img: np.ndarray, gamma: float = 1.0) -> np.ndarray:
        """伽马校正。

        Args:
            img: 输入图像
            gamma: 伽马值 (0.1-3.0)，<1 提亮，>1 变暗

        Returns:
            处理后的图像
        """
        if img is None or gamma == 1.0:
            return img

        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255
                          for i in range(256)]).astype(np.uint8)
        return cv2.LUT(img, table)

    @staticmethod
    def histogram_equalization(img: np.ndarray) -> np.ndarray:
        """直方图均衡化 (仅适用于灰度图)。"""
        if img is None:
            return img

        if len(img.shape) == 3:
            # 转换到 YUV 空间，只对 Y 通道均衡化
            yuv = cv2.cvtColor(img, cv2.COLOR_BGR2YUV)
            yuv[:, :, 0] = cv2.equalizeHist(yuv[:, :, 0])
            return cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)
        else:
            return cv2.equalizeHist(img)

    @staticmethod
    def clahe(img: np.ndarray, clip_limit: float = 2.0,
              grid_size: int = 8) -> np.ndarray:
        """自适应直方图均衡化 (CLAHE)。

        Args:
            img: 输入图像
            clip_limit: 对比度限制 (1.0-10.0)
            grid_size: 网格大小 (4-16)

        Returns:
            处理后的图像
        """
        if img is None:
            return img

        clahe = cv2.createCLAHE(clipLimit=clip_limit,
                                 tileGridSize=(grid_size, grid_size))

        if len(img.shape) == 3:
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            lab[:, :, 0] = clahe.apply(lab[:, :, 0])
            return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        else:
            return clahe.apply(img)

    # ------------------------------------------------------------------
    # 去噪函数
    # ------------------------------------------------------------------
    @staticmethod
    def gaussian_blur(img: np.ndarray, kernel_size: int = 5,
                      sigma: float = 0) -> np.ndarray:
        """高斯模糊。

        Args:
            img: 输入图像
            kernel_size: 核大小 (必须为奇数，3-31)
            sigma: 高斯标准差，0 表示自动计算

        Returns:
            处理后的图像
        """
        if img is None:
            return img
        kernel_size = max(3, kernel_size | 1)  # 确保为奇数
        return cv2.GaussianBlur(img, (kernel_size, kernel_size), sigma)

    @staticmethod
    def median_blur(img: np.ndarray, kernel_size: int = 5) -> np.ndarray:
        """中值滤波 (椒盐噪声去除效果好)。

        Args:
            img: 输入图像
            kernel_size: 核大小 (必须为奇数，3-31)

        Returns:
            处理后的图像
        """
        if img is None:
            return img
        kernel_size = max(3, kernel_size | 1)
        return cv2.medianBlur(img, kernel_size)

    @staticmethod
    def bilateral_filter(img: np.ndarray, d: int = 9,
                          sigma_color: float = 75,
                          sigma_space: float = 75) -> np.ndarray:
        """双边滤波 (保边去噪)。

        Args:
            img: 输入图像
            d: 滤波直径 (5-15)
            sigma_color: 颜色空间滤波器 sigma
            sigma_space: 坐标空间滤波器 sigma

        Returns:
            处理后的图像
        """
        if img is None:
            return img
        return cv2.bilateralFilter(img, d, sigma_color, sigma_space)

    @staticmethod
    def nlm_denoise(img: np.ndarray, h: float = 10,
                     template_window: int = 7,
                     search_window: int = 21) -> np.ndarray:
        """非局部均值去噪 (效果最好但较慢)。

        Args:
            img: 输入图像
            h: 滤波强度 (5-30)
            template_window: 模板窗口大小 (7)
            search_window: 搜索窗口大小 (21)

        Returns:
            处理后的图像
        """
        if img is None:
            return img

        if len(img.shape) == 3:
            return cv2.fastNlMeansDenoisingColored(img, None, h, h,
                                                     template_window,
                                                     search_window)
        else:
            return cv2.fastNlMeansDenoising(img, None, h,
                                            template_window,
                                            search_window)

    # ------------------------------------------------------------------
    # 边缘检测
    # ------------------------------------------------------------------
    @staticmethod
    def canny_edge(img: np.ndarray, threshold1: int = 50,
                   threshold2: int = 150, aperture_size: int = 3) -> np.ndarray:
        """Canny 边缘检测。

        Args:
            img: 输入图像
            threshold1: 低阈值 (0-255)
            threshold2: 高阈值 (0-255)
            aperture_size: Sobel 核大小 (3, 5, 7)

        Returns:
            边缘图像
        """
        if img is None:
            return img

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        return cv2.Canny(gray, threshold1, threshold2,
                         apertureSize=aperture_size)

    @staticmethod
    def sobel_edge(img: np.ndarray, dx: int = 1, dy: int = 1,
                   ksize: int = 3) -> np.ndarray:
        """Sobel 边缘检测。

        Args:
            img: 输入图像
            dx: X 方向导数阶数
            dy: Y 方向导数阶数
            ksize: 核大小 (1, 3, 5, 7)

        Returns:
            边缘图像
        """
        if img is None:
            return img

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, dx, 0, ksize=ksize)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, dy, ksize=ksize)
        magnitude = np.sqrt(sobel_x ** 2 + sobel_y ** 2)
        return np.clip(magnitude, 0, 255).astype(np.uint8)

    @staticmethod
    def laplacian_edge(img: np.ndarray, ksize: int = 3) -> np.ndarray:
        """Laplacian 边缘检测。

        Args:
            img: 输入图像
            ksize: 核大小 (1, 3, 5, 7)

        Returns:
            边缘图像
        """
        if img is None:
            return img

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        laplacian = cv2.Laplacian(gray, cv2.CV_64F, ksize=ksize)
        return np.clip(np.abs(laplacian), 0, 255).astype(np.uint8)

    # ------------------------------------------------------------------
    # 形态学操作
    # ------------------------------------------------------------------
    @staticmethod
    def morphological(img: np.ndarray, operation: str = "dilate",
                      kernel_size: int = 5, iterations: int = 1) -> np.ndarray:
        """形态学操作。

        Args:
            img: 输入图像
            operation: 操作类型 ('erode', 'dilate', 'open', 'close', 'gradient')
            kernel_size: 核大小 (3-21)
            iterations: 迭代次数 (1-10)

        Returns:
            处理后的图像
        """
        if img is None:
            return img

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT,
                                            (kernel_size, kernel_size))

        ops = {
            "erode": cv2.MORPH_ERODE,
            "dilate": cv2.MORPH_DILATE,
            "open": cv2.MORPH_OPEN,
            "close": cv2.MORPH_CLOSE,
            "gradient": cv2.MORPH_GRADIENT,
        }

        op = ops.get(operation, cv2.MORPH_DILATE)
        return cv2.morphologyEx(img, op, kernel, iterations=iterations)

    # ------------------------------------------------------------------
    # 阈值化
    # ------------------------------------------------------------------
    @staticmethod
    def threshold(img: np.ndarray, method: str = "binary",
                  thresh: int = 127, max_val: int = 255,
                  block_size: int = 11, C: int = 2) -> np.ndarray:
        """阈值化处理。

        Args:
            img: 输入图像
            method: 方法 ('binary', 'adaptive_mean', 'adaptive_gaussian', 'otsu')
            thresh: 阈值 (0-255)，用于 binary 和 otsu
            max_val: 最大值 (用于 binary)
            block_size: 自适应阈值块大小 (3-31，奇数)
            C: 自适应阈值常数

        Returns:
            处理后的图像
        """
        if img is None:
            return img

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

        if method == "binary":
            _, result = cv2.threshold(gray, thresh, max_val,
                                       cv2.THRESH_BINARY)
        elif method == "adaptive_mean":
            block_size = max(3, block_size | 1)
            result = cv2.adaptiveThreshold(gray, max_val,
                                            cv2.ADAPTIVE_THRESH_MEAN_C,
                                            cv2.THRESH_BINARY,
                                            block_size, C)
        elif method == "adaptive_gaussian":
            block_size = max(3, block_size | 1)
            result = cv2.adaptiveThreshold(gray, max_val,
                                            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                            cv2.THRESH_BINARY,
                                            block_size, C)
        elif method == "otsu":
            _, result = cv2.threshold(gray, 0, max_val,
                                       cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        else:
            result = gray

        return result

    # ------------------------------------------------------------------
    # 连通性过滤
    # ------------------------------------------------------------------
    @staticmethod
    def connectivity_filter(img: np.ndarray,
                            min_area: int = 100,
                            thresh: int = 127,
                            keep_white: int = 1) -> np.ndarray:
        """连通性过滤 —— 去除面积小于阈值的连通色块。

        使用 connectedComponentsWithStats 分析连通域，
        保留面积 >= min_area 的色块，去除其余。

        Args:
            img: 输入图像
            min_area: 最小保留面积（像素数），小于此值的色块被去除
            thresh: 二值化阈值 (0-255)
            keep_white: 1=保留白色色块，0=保留黑色色块

        Returns:
            过滤后的图像
        """
        if img is None:
            return img

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

        # 二值化
        if keep_white:
            _, binary = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY)
        else:
            _, binary = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY_INV)

        # 连通域分析
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
            binary, connectivity=8)

        # 创建掩码：保留面积 >= min_area 的连通域
        mask = np.zeros_like(gray)
        for i in range(1, num_labels):  # 跳过背景 (label 0)
            area = stats[i, cv2.CC_STAT_AREA]
            if area >= min_area:
                mask[labels == i] = 255

        # 应用掩码
        if len(img.shape) == 3:
            result = cv2.bitwise_and(img, img, mask=mask)
        else:
            result = cv2.bitwise_and(gray, gray, mask=mask)

        return result

    # ------------------------------------------------------------------
    # 矩形检测
    # ------------------------------------------------------------------
    @staticmethod
    def detect_rectangles(img: np.ndarray, min_area: int = 1000,
                          max_area: int = 0, threshold1: int = 50,
                          threshold2: int = 150,
                          roi_type: int = 0,
                          roi_cx: int = 0, roi_cy: int = 0,
                          roi_radius: int = 100,
                          roi_x: int = 0, roi_y: int = 0,
                          roi_w: int = 100, roi_h: int = 100) -> np.ndarray:
        """矩形检测 —— 使用最小外接矩形检测图像中的矩形并标注。

        使用 cv2.minAreaRect 获取轮廓的最小外接旋转矩形，
        可检测任意方向的矩形目标。
        使用层次轮廓检测和孔洞填充来处理有孔洞的矩形。

        Args:
            img: 输入图像 (BGR 或灰度)
            min_area: 最小矩形面积 (100-100000)
            max_area: 最大矩形面积 (0 表示不限制，100-500000)
            threshold1: Canny 低阈值 (0-255)
            threshold2: Canny 高阈值 (0-255)
            roi_type: ROI 类型 (0=无, 1=圆形, 2=矩形)
            roi_cx, roi_cy, roi_radius: 圆形 ROI 参数
            roi_x, roi_y, roi_w, roi_h: 矩形 ROI 参数

        Returns:
            标注了矩形的图像
        """
        if img is None:
            return img

        # 应用 ROI
        img = ImageProcessor._apply_roi(img, roi_type, roi_cx, roi_cy,
                                         roi_radius, roi_x, roi_y,
                                         roi_w, roi_h)

        # 保存原始图像用于绘制
        if len(img.shape) == 3:
            original = img.copy()
        else:
            original = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        # 标准边缘检测
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()
        # Canny 边缘检测
        edges = cv2.Canny(gray, threshold1, threshold2)


        # 使用层次轮廓检测（区分外轮廓和内轮廓）
        contours, hierarchy = cv2.findContours(edges, cv2.RETR_TREE,
                                                cv2.CHAIN_APPROX_SIMPLE)

        # 结果图像
        result = original.copy()
        rect_count = 0
        rect_info = []

        for i, contour in enumerate(contours):
            # 只处理外轮廓（父轮廓为-1的轮廓）
            if hierarchy[0][i][3] != -1:
                continue

            area = cv2.contourArea(contour)

            # 面积过滤
            if area < min_area:
                continue
            if max_area > 0 and area > max_area:
                continue

            # 获取最小外接矩形
            rot_rect = cv2.minAreaRect(contour)
            box = cv2.boxPoints(rot_rect)
            box = box.astype(np.int32)

            # 获取矩形尺寸
            center_x, center_y = rot_rect[0]
            width, height = rot_rect[1]
            angle = rot_rect[2]

            # 确定长边和短边
            length = max(width, height)
            breadth = min(width, height)

            rect_count += 1

            # 绘制绿色旋转矩形框
            cv2.drawContours(result, [box], 0, (0, 255, 0), 2)

            # 收集矩形信息
            rect_info.append({
                "id": rect_count,
                "center": (int(center_x), int(center_y)),
                "size": (round(length, 1), round(breadth, 1)),
                "angle": round(angle, 1),
                "area": int(area),
                "box_points": box.tolist()
            })

        # 在左上角绘制检测结果信息
        if rect_count > 0:
            # 绿色文字 - 检测到矩形
            info_text = f"Detected: {rect_count} rect(s)"
            cv2.putText(result, info_text, (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # 显示每个矩形的信息
            for i, info in enumerate(rect_info[:5]):  # 最多显示5个
                text = f"#{info['id']}: {info['size'][0]}x{info['size'][1]} angle={info['angle']}"
                cv2.putText(result, text, (10, 50 + i * 22),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            if rect_count > 5:
                cv2.putText(result, f"... and {rect_count - 5} more", (10, 50 + 5 * 22),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        else:
            # 红色文字 - 未检测到矩形
            cv2.putText(result, "No rectangle detected", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        return result

    # ------------------------------------------------------------------
    # 圆形检测
    # ------------------------------------------------------------------
    @staticmethod
    def detect_circles(img: np.ndarray, min_radius: int = 10,
                       max_radius: int = 200, min_dist: int = 50,
                       param1: int = 50, param2: int = 30,
                       circularity_threshold: float = 0.50,
                       roi_type: int = 0,
                       roi_cx: int = 0, roi_cy: int = 0,
                       roi_radius: int = 100,
                       roi_x: int = 0, roi_y: int = 0,
                       roi_w: int = 100, roi_h: int = 100) -> np.ndarray:
        """圆形检测 —— 使用霍夫圆变换 + 边缘采样验证，过滤误检。

        HoughCircles 基于梯度方向投票，容易把非圆形也检测为圆。
        本方法先用 HoughCircles 获取候选，再用边缘采样验证圆周完整性，
        只有真正接近圆形的候选才会保留。

        Args:
            img: 输入图像 (BGR 或灰度)
            min_radius: 最小半径 (1-500)
            max_radius: 最大半径 (1-500)
            min_dist: 圆心最小距离 (10-500)
            param1: Canny高阈值 (10-300)
            param2: 累加器阈值 (10-100)，越小检测越多候选（但也会被验证过滤）
            circularity_threshold: 圆形度最低分数 (0.0-1.0)，0 表示跳过验证
            roi_type: ROI 类型 (0=无, 1=圆形, 2=矩形)
            roi_cx, roi_cy, roi_radius: 圆形 ROI 参数
            roi_x, roi_y, roi_w, roi_h: 矩形 ROI 参数

        Returns:
            标注了圆形的图像
        """
        if img is None:
            return img

        # 应用 ROI
        img = ImageProcessor._apply_roi(img, roi_type, roi_cx, roi_cy,
                                         roi_radius, roi_x, roi_y,
                                         roi_w, roi_h)

        # 保存原始图像用于绘制
        if len(img.shape) == 3:
            original = img.copy()
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            original = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            gray = img.copy()

        # 高斯模糊去噪
        blurred = cv2.GaussianBlur(gray, (9, 9), 2)

        # 霍夫圆变换
        circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT,
                                    dp=1, minDist=min_dist,
                                    param1=param1, param2=param2,
                                    minRadius=min_radius, maxRadius=max_radius)

        result = original.copy()
        circle_count = 0
        circle_info = []

        if circles is not None:
            circles = np.uint16(np.around(circles))
            for i, circle in enumerate(circles[0]):
                cx, cy, r = int(circle[0]), int(circle[1]), int(circle[2])

                # ── 圆形度验证：过滤非圆形误检 ──
                if circularity_threshold > 0 and r >= 5:
                    score, passed = ImageProcessor._validate_circle_circularity(
                        gray, cx, cy, r, min_score=circularity_threshold)
                    if not passed:
                        continue  # 非圆形，跳过

                circle_count += 1

                # 绘制圆形和圆心
                cv2.circle(result, (cx, cy), r, (0, 255, 0), 2)
                cv2.circle(result, (cx, cy), 2, (0, 0, 255), 3)

                # 收集圆形信息
                circle_info.append({
                    "id": circle_count,
                    "center": (cx, cy),
                    "radius": r,
                    "area": round(3.14159 * r * r, 1)
                })

        # 绘制检测结果信息
        if circle_count > 0:
            info_text = f"Detected: {circle_count} circle(s)"
            cv2.putText(result, info_text, (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            for i, info in enumerate(circle_info[:5]):
                text = f"#{info['id']}: r={info['radius']} @ ({info['center'][0]},{info['center'][1]})"
                cv2.putText(result, text, (10, 50 + i * 22),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        else:
            cv2.putText(result, "No circle detected", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        return result

    # ------------------------------------------------------------------
    # 多边形检测
    # ------------------------------------------------------------------
    @staticmethod
    def detect_polygons(img: np.ndarray, min_area: int = 1000,
                        max_area: int = 0, threshold1: int = 50,
                        threshold2: int = 150,
                        approx_epsilon: float = 0.02,
                        min_sides: int = 3,
                        max_sides: int = 8,
                        roi_type: int = 0,
                        roi_cx: int = 0, roi_cy: int = 0,
                        roi_radius: int = 100,
                        roi_x: int = 0, roi_y: int = 0,
                        roi_w: int = 100, roi_h: int = 100) -> np.ndarray:
        """多边形检测 —— 检测图像中的多边形并标注。

        使用多边形近似检测不同边数的多边形（三角形、四边形、五边形等）。

        Args:
            img: 输入图像 (BGR 或灰度)
            min_area: 最小面积 (100-100000)
            max_area: 最大面积 (0 表示不限制)
            threshold1: Canny 低阈值 (0-255)
            threshold2: Canny 高阈值 (0-255)
            approx_epsilon: 多边形逼近精度 (0.01-0.1)
            min_sides: 最小边数 (3-20)
            max_sides: 最大边数 (3-20)
            roi_type: ROI 类型 (0=无, 1=圆形, 2=矩形)
            roi_cx, roi_cy, roi_radius: 圆形 ROI 参数
            roi_x, roi_y, roi_w, roi_h: 矩形 ROI 参数

        Returns:
            标注了多边形的图像
        """
        if img is None:
            return img

        # 应用 ROI
        img = ImageProcessor._apply_roi(img, roi_type, roi_cx, roi_cy,
                                         roi_radius, roi_x, roi_y,
                                         roi_w, roi_h)

        # 保存原始图像
        if len(img.shape) == 3:
            original = img.copy()
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            original = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            gray = img.copy()

        # 边缘检测
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, threshold1, threshold2)

        # 形态学操作
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        edges = cv2.dilate(edges, kernel, iterations=1)

        # 查找轮廓
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)

        result = original.copy()
        poly_count = 0
        poly_info = []

        # 不同边数的颜色
        colors = {
            3: (255, 0, 0),    # 三角形 - 蓝色
            4: (0, 255, 0),    # 四边形 - 绿色
            5: (0, 0, 255),    # 五边形 - 红色
            6: (255, 255, 0),  # 六边形 - 青色
        }
        default_color = (255, 0, 255)  # 其他 - 品红

        for contour in contours:
            area = cv2.contourArea(contour)

            if area < min_area:
                continue
            if max_area > 0 and area > max_area:
                continue

            # 多边形近似
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, approx_epsilon * peri, True)

            # 获取顶点数
            vertices = len(approx)

            # 只检测指定边数范围的多边形
            if min_sides <= vertices <= max_sides:
                poly_count += 1
                color = colors.get(vertices, default_color)

                # 绘制多边形
                cv2.drawContours(result, [approx], 0, color, 2)

                # 获取边界框
                x, y, w, h = cv2.boundingRect(approx)
                cx, cy = x + w // 2, y + h // 2

                # 收集信息
                poly_info.append({
                    "id": poly_count,
                    "vertices": vertices,
                    "area": int(area),
                    "center": (cx, cy),
                    "size": (w, h)
                })

                # 标注边数
                label = f"{vertices}-gon"
                cv2.putText(result, label, (cx - 20, cy - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # 绘制检测结果信息
        if poly_count > 0:
            info_text = f"Detected: {poly_count} polygon(s)"
            cv2.putText(result, info_text, (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # 统计各边数
            vertex_counts = {}
            for info in poly_info:
                v = info["vertices"]
                vertex_counts[v] = vertex_counts.get(v, 0) + 1

            y_offset = 50
            for v, count in sorted(vertex_counts.items()):
                text = f"{v}-gon: {count}"
                cv2.putText(result, text, (10, y_offset),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                y_offset += 22
        else:
            cv2.putText(result, "No polygon detected", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        return result

    # ------------------------------------------------------------------
    # 二维码检测
    # ------------------------------------------------------------------
    @staticmethod
    def detect_qrcode(img: np.ndarray,
                      roi_type: int = 0,
                      roi_cx: int = 0, roi_cy: int = 0,
                      roi_radius: int = 100,
                      roi_x: int = 0, roi_y: int = 0,
                      roi_w: int = 100, roi_h: int = 100) -> np.ndarray:
        """二维码/条形码检测 —— 检测并解码图像中的二维码和条形码。

        优先使用 pyzbar（解码能力更强），备选 OpenCV QRCodeDetector。

        Args:
            img: 输入图像 (BGR 或灰度)
            roi_type: ROI 类型 (0=无, 1=圆形, 2=矩形)
            roi_cx, roi_cy, roi_radius: 圆形 ROI 参数
            roi_x, roi_y, roi_w, roi_h: 矩形 ROI 参数

        Returns:
            标注了二维码的图像
        """
        if img is None:
            return img

        # 应用 ROI
        img = ImageProcessor._apply_roi(img, roi_type, roi_cx, roi_cy,
                                         roi_radius, roi_x, roi_y,
                                         roi_w, roi_h)

        # 保存原始图像
        if len(img.shape) == 3:
            original = img.copy()
        else:
            original = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        result = original.copy()
        qr_count = 0
        qr_info = []

        # 使用 OpenCV QRCodeDetector
        detector = cv2.QRCodeDetector()
        decoded_info, points, _ = detector.detectAndDecode(img)
        print("OpenCV QRCodeDetector decoded info:", decoded_info)
        if points is not None:
            if len(points.shape) == 2:
                points = [points]
                decoded_info = [decoded_info]

            for i in range(len(points)):
                pts = points[i].astype(np.int32)
                if len(pts) < 4:
                    continue

                cv2.polylines(result, [pts], True, (0, 255, 0), 3)
                cx = int(np.mean(pts[:, 0]))
                cy = int(np.mean(pts[:, 1]))
                info = decoded_info[i] if i < len(decoded_info) else ""

                qr_count += 1
                qr_info.append({
                    "id": qr_count,
                    "center": (cx, cy),
                    "decoded": info,
                    "type": "QR"
                })

                if info:
                    display_text = info[:30]
                    text_size = cv2.getTextSize(display_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                    cv2.rectangle(result, (cx - text_size[0]//2 - 5, cy - 25),
                                  (cx + text_size[0]//2 + 5, cy - 3), (0, 0, 0), -1)
                    cv2.putText(result, display_text, (cx - text_size[0]//2, cy - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # 绘制检测结果信息
        if qr_count > 0:
            info_text = f"Detected: {qr_count} code(s)"
            cv2.putText(result, info_text, (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            y_offset = 50
            for i, info in enumerate(qr_info[:5]):
                text = f"#{info['id']} [{info['type']}]: {info['decoded'][:35]}"
                cv2.putText(result, text, (10, y_offset),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                y_offset += 22
        else:
            cv2.putText(result, "No QR/barcode detected", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        return result

    # ------------------------------------------------------------------
    # 文字检测
    # ------------------------------------------------------------------
    @staticmethod
    def detect_text(img: np.ndarray, min_area: int = 100,
                    max_area: int = 0, ocr_lang: str = "en",
                    roi_type: int = 0,
                    roi_cx: int = 0, roi_cy: int = 0,
                    roi_radius: int = 100,
                    inner_ratio: float = 0.5,
                    start_angle: float = 0.0, end_angle: float = 360.0,
                    roi_x: int = 0, roi_y: int = 0,
                    roi_w: int = 100, roi_h: int = 100) -> np.ndarray:
        """文字检测 —— 检测图像中的文字区域并识别内容。

        使用形态学操作检测文字区域。支持圆环展开模式 (roi_type=1)，
        将圆形环带展开为矩形条带后检测文字，适用于仪表盘、旋钮等圆环文字。
        ROI 参数通过手动画图设置，不支持手动输入坐标。内圈半径默认为外圈半径的 0.5。

        Args:
            img: 输入图像 (BGR 或灰度)
            min_area: 最小面积 (10-10000)
            max_area: 最大面积 (0 表示不限制)
            ocr_lang: OCR语言 ('eng', 'chi_sim', 'chi_tra')
            roi_type: ROI 类型 (0=无, 1=圆形圆环展开, 2=矩形) — 由绘图设置
            roi_cx, roi_cy, roi_radius: 圆形 ROI 参数 — 由绘图设置
            inner_ratio: 内圆半径比例 (0.1-0.95)，默认 0.5 保留较宽环带
            start_angle, end_angle: 扇形角度范围 (0-360)，默认展开整圈
            roi_x, roi_y, roi_w, roi_h: 矩形 ROI 参数 — 由绘图设置

        Returns:
            标注了文字区域和识别内容的图像
        """
        if img is None:
            return img

        # 保存原始图像
        if len(img.shape) == 3:
            original = img.copy()
        else:
            original = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        result = original.copy()
        text_info = []
        unwrapped_panel = None  # 圆环展开图（用于旁侧显示）

        # 判断是否使用圆形 ROI（用于圆环展开）
        use_circle_unwrap = (roi_type == 1 and roi_radius > 10)

        if use_circle_unwrap:
            # ── 圆环文字模式: PaddleOCR 直检(原生支持弧形) → 回退 warpPolar+形态学 ──
            cx, cy, r = int(roi_cx), int(roi_cy), int(roi_radius)
            inner_ratio = max(0.1, min(0.95, inner_ratio))
            r_inner = int(r * inner_ratio)
            band = r - r_inner
            if band < 5:
                return result

            h_img, w_img = original.shape[:2]

            # 创建环形 ROI 掩膜
            ring_mask = np.zeros((h_img, w_img), dtype=np.uint8)
            cv2.circle(ring_mask, (cx, cy), r, 255, -1)
            cv2.circle(ring_mask, (cx, cy), r_inner, 0, -1)

            # 扇形裁剪（非整圈时）
            sa = start_angle if start_angle is not None else 0.0
            ea = end_angle if end_angle is not None else 360.0
            if ea <= sa:
                ea = sa + 360.0
            if ea - sa < 359.5:
                # 用扇形掩膜裁剪
                sector_mask = np.zeros((h_img, w_img), dtype=np.uint8)
                cv2.ellipse(sector_mask, (cx, cy), (r, r), 0,
                           -sa, -ea, 255, -1)  # OpenCV: 顺时针为正
                ring_mask = cv2.bitwise_and(ring_mask, sector_mask)

            # ── 双引擎文字检测：裁切 ROI 加速 GPU 推理 ──
            if HAS_EASYOCR or HAS_PADDLE:
                pad = int(r * 0.1)
                x1 = max(0, cx - r - pad)
                y1 = max(0, cy - r - pad)
                x2 = min(w_img, cx + r + pad)
                y2 = min(h_img, cy + r + pad)

                crop = original[y1:y2, x1:x2]
                crop_h, crop_w = crop.shape[:2]
                crop_mask = np.zeros((crop_h, crop_w), dtype=np.uint8)
                cv2.circle(crop_mask, (cx - x1, cy - y1), r, 255, -1)
                cv2.circle(crop_mask, (cx - x1, cy - y1), r_inner, 0, -1)
                # 扇形裁剪（如有）
                if ea - sa < 359.5:
                    sector_crop = np.zeros((crop_h, crop_w), dtype=np.uint8)
                    cv2.ellipse(sector_crop, (cx - x1, cy - y1), (r, r), 0,
                               -sa, -ea, 255, -1)
                    crop_mask = cv2.bitwise_and(crop_mask, sector_crop)

                regions = ImageProcessor._detect_text_engine(crop, crop_mask)
                # 偏移回原图坐标
                for region in regions:
                    bx, by, bw, bh = region["bbox"]
                    region["bbox"] = (bx + x1, by + y1, bw, bh)
                    poly = region.get("polygon")
                    if poly is not None:
                        region["polygon"] = poly + [x1, y1]
                    region["center"] = (bx + x1 + bw // 2, by + y1 + bh // 2)
                    region["polygon_orig"] = region.get("polygon", None)
                    region["bbox_orig"] = region["bbox"]
                    text_info.append(region)

                engine_name = regions[0].get("engine", "OCR") if regions else "OCR"
                unwrapped_panel = np.full((60, 300, 3), (40, 40, 40), dtype=np.uint8)
                cv2.putText(unwrapped_panel, f"{engine_name} (native arc)",
                           (5, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 100), 1)
                cv2.putText(unwrapped_panel, f"{len(regions)} region(s) detected",
                           (5, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 100), 1)
            else:
                # ── 回退: warpPolar + 形态学 ──
                max_radius = max(r, 1)
                polar_h = band * 4
                full_polar_w = max(int(2 * np.pi * max_radius), 200)
                if full_polar_w < 50:
                    full_polar_w = 50

                full_polar = cv2.warpPolar(original, (full_polar_w, polar_h),
                                           (cx, cy), max_radius,
                                           cv2.WARP_POLAR_LINEAR)
                scale_y = polar_h / max_radius
                crop_y = int(r_inner * scale_y)
                if crop_y < polar_h:
                    full_polar = full_polar[crop_y:, :]

                angle_span = ea - sa
                is_full_circle = (angle_span >= 359.5)
                if not is_full_circle:
                    x_start = int(sa / 360.0 * full_polar_w) % full_polar_w
                    x_end = int(ea / 360.0 * full_polar_w)
                    if x_end <= x_start:
                        x_end = full_polar_w
                    if x_end - x_start < 10:
                        x_start, x_end = 0, full_polar_w
                    polar = full_polar[:, x_start:x_end].copy()
                    polar_w_used = x_end - x_start
                    angle_offset = sa
                else:
                    polar = full_polar
                    polar_w_used = full_polar_w
                    angle_offset = 0.0

                if polar.size == 0:
                    return result

                unwrapped_panel = polar.copy()
                polar_gray = cv2.cvtColor(polar, cv2.COLOR_BGR2GRAY) if len(polar.shape) == 3 else polar
                regions = ImageProcessor._detect_text_regions_morph(polar_gray, min_area, max_area)

                for region in regions:
                    bx, by, bw, bh = region["bbox"]
                    cv2.rectangle(unwrapped_panel, (bx, by), (bx+bw, by+bh),
                                  (0, 255, 0), 2)
                    pts_orig = []
                    for corner in [(bx, by), (bx+bw, by), (bx+bw, by+bh), (bx, by+bh)]:
                        px_u, py_u = corner
                        actual_y = py_u + crop_y
                        rr = actual_y / scale_y
                        theta = 2.0 * np.pi * (px_u / polar_w_used * angle_span / 360.0
                                               + angle_offset / 360.0)
                        ox = int(cx + rr * np.cos(theta))
                        oy = int(cy + rr * np.sin(theta))
                        pts_orig.append([ox, oy])
                    region["polygon_orig"] = np.array(pts_orig, dtype=np.int32).reshape(-1, 1, 2)
                    region["bbox_orig"] = cv2.boundingRect(region["polygon_orig"])
                    text_info.append(region)

        else:
            # ── 普通模式: PaddleOCR → 回退形态学 ──
            if HAS_EASYOCR or HAS_PADDLE:
                # 创建 ROI 掩膜 (如有)
                roi_mask = None
                if roi_type == 1:
                    h_i, w_i = original.shape[:2]
                    roi_mask = np.zeros((h_i, w_i), dtype=np.uint8)
                    cv2.circle(roi_mask, (int(roi_cx), int(roi_cy)),
                               int(roi_radius), 255, -1)
                elif roi_type == 2:
                    h_i, w_i = original.shape[:2]
                    roi_mask = np.zeros((h_i, w_i), dtype=np.uint8)
                    x1, y1 = max(0, roi_x), max(0, roi_y)
                    x2, y2 = min(w_i, roi_x + roi_w), min(h_i, roi_y + roi_h)
                    roi_mask[y1:y2, x1:x2] = 255

                regions = ImageProcessor._detect_text_engine(original, roi_mask)
                for region in regions:
                    region["polygon_orig"] = region.get("polygon", None)
                    region["bbox_orig"] = region["bbox"]
                    text_info.append(region)
            else:
                img_roi = ImageProcessor._apply_roi(
                    img, roi_type, roi_cx, roi_cy,
                    roi_radius, roi_x, roi_y, roi_w, roi_h)
                gray = cv2.cvtColor(img_roi, cv2.COLOR_BGR2GRAY) if len(img_roi.shape) == 3 else img_roi
                regions = ImageProcessor._detect_text_regions_morph(gray, min_area, max_area)
                for region in regions:
                    region["polygon_orig"] = None
                    region["bbox_orig"] = region["bbox"]
                    text_info.append(region)
        print(text_info)
        # ── 绘制检测结果 ──
        for info in text_info:
            bbox = info.get("bbox_orig", info["bbox"])
            pts = info.get("polygon_orig")

            if pts is not None:
                cv2.polylines(result, [pts], isClosed=True,
                              color=(0, 255, 0), thickness=2)
            else:
                x, y, w, h = bbox
                cv2.rectangle(result, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # 汇总信息
        text_count = len(text_info)
        if text_count > 0:
            mode_tag = " [圆环展开]" if use_circle_unwrap else ""
            info_text = f"Detected: {text_count} text region(s){mode_tag}"
            cv2.putText(result, info_text, (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        else:
            cv2.putText(result, "No text detected", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # ── 圆环展开图拼接到右侧 ──
        if unwrapped_panel is not None and unwrapped_panel.size > 0:
            h_main = result.shape[0]
            panel = unwrapped_panel.copy()
            # 缩放面板高度与主图一致
            ph, pw = panel.shape[:2]
            if ph > 0 and pw > 0:
                scale = h_main / ph
                panel = cv2.resize(panel, (int(pw * scale), h_main))
                # 添加分隔线和标题
                cv2.putText(panel, "Unwrapped", (5, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
                # 拼接
                sep = np.full((h_main, 3, 3), (200, 200, 200), dtype=np.uint8)
                result = np.hstack([result, sep, panel])

        return result

    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # 圆检测 + 圆环展开文字检测
    # ------------------------------------------------------------------
    @staticmethod
    def detect_text_on_circles(img: np.ndarray,
                               min_radius: int = 30,
                               max_radius: int = 0,
                               min_dist: int = 80,
                               param1: int = 80,
                               param2: int = 25,
                               dp: float = 1.2,
                               circularity_threshold: float = 0.45,
                               inner_ratio: float = 0.5,
                               unwrap_method: str = "remap",
                               output_width: int = 1080,
                               ocr_engine: str = "auto") -> np.ndarray:
        """自动检测圆 → 边缘验证 → 圆环展开 → 文字区域检测。

        流程:
          1. HoughCircles 获取候选圆
          2. 边缘采样验证圆周完整性，过滤非圆形误检
          3. 对每个通过验证的圆做圆环展开（remap 或 warpPolar）
          4. 在展开图上做 OCR 文字检测（EasyOCR / PaddleOCR / 形态学）
          5. 绿色标注圆边界，展开面板放在圆右侧旁

        Args:
            img: 输入图像 (BGR 或灰度)
            min_radius: 最小圆半径 (默认 30，降低以检测更小的圆)
            max_radius: 最大圆半径 (0 表示自动 = min(w,h)//3)
            min_dist: 圆心最小距离 (默认 80)
            param1: Canny 高阈值，越小检测越多候选圆 (默认 80)
            param2: 累加器阈值，越小检测越多候选 (默认 25)
            dp: 累加器分辨率反比，越小精度越高 (默认 1.2)
            circularity_threshold: 圆形度最低分数 (0.0-1.0)，默认 0.45
            inner_ratio: 内圆半径比例，0.5 表示内圈半径=外圈半径的 50%
            unwrap_method: 圆环展开方式 ("remap"=极坐标remap+自动角度, "warp_polar"=OpenCV warpPolar)
            output_width: remap 展开方式的输出宽度（对应360°），默认 1080
            ocr_engine: OCR 引擎选择 ("auto"=EasyOCR→PaddleOCR→形态学, "easyocr", "paddle", "morph")

        Returns:
            标注了检测结果的图像（展开图放在对应圆右侧）
        """
        if img is None:
            return img

        if len(img.shape) == 3:
            original = img.copy()
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            original = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            gray = img.copy()

        result = original.copy()
        h_img, w_img = gray.shape[:2]

        # 自动设置 max_radius
        if max_radius <= 0:
            max_radius = min(h_img, w_img) // 3

        # 模糊以减少噪声
        blurred = cv2.GaussianBlur(gray, (9, 9), 2)

        # HoughCircles 检测
        circles = cv2.HoughCircles(
            blurred, cv2.HOUGH_GRADIENT, dp=dp,
            minDist=min_dist,
            param1=param1, param2=param2,
            minRadius=min_radius, maxRadius=max_radius)

        # 收集每个圆的展开面板及其放置位置
        panel_placements = []  # [(panel, x, y, w, h), ...]
        total_text = 0

        if circles is not None:
            circles = np.uint16(np.around(circles))
            for idx, c in enumerate(circles[0]):
                cx, cy, r = int(c[0]), int(c[1]), int(c[2])
                r_inner = int(r * inner_ratio)
                band = r - r_inner
                if band < 5:
                    continue

                # ── 圆形度验证：边缘采样过滤非圆形误检 ──
                if circularity_threshold > 0 and r >= 5:
                    score, passed = ImageProcessor._validate_circle_circularity(
                        gray, cx, cy, r, min_score=circularity_threshold)
                    if not passed:
                        continue

                # ── 绿色标注检测到的圆（外圆 + 内圆 + 圆心）──
                cv2.circle(result, (cx, cy), r, (0, 255, 0), 2)
                cv2.circle(result, (cx, cy), r_inner, (0, 200, 0), 1)
                cv2.circle(result, (cx, cy), 3, (0, 0, 255), -1)

                # ── 圆环展开 ──
                if unwrap_method == "remap":
                    # remap 极坐标展开（自动起始角度，文字拉直为一行）
                    unwrapped = ImageProcessor.ring_unwrap(
                        original, cx, cy, r,
                        inner_ratio=inner_ratio,
                        output_width=output_width,
                        auto_angle=True)
                    panel = unwrapped.copy()
                else:
                    # warpPolar 展开（OpenCV 内置）
                    max_r = max(r, 1)
                    polar_h = max(band * 4, 40)
                    polar_w = max(int(2 * np.pi * max_r), 100)

                    unwrapped = cv2.warpPolar(original, (polar_w, polar_h),
                                              (cx, cy), max_r,
                                              cv2.WARP_POLAR_LINEAR)
                    scale_y = polar_h / max_r
                    crop_y = int(r_inner * scale_y)
                    if crop_y < polar_h:
                        unwrapped = unwrapped[crop_y:, :]
                    panel = unwrapped.copy()

                if unwrapped.size == 0:
                    continue

                # ── 文字检测（按 ocr_engine 选择引擎）──
                crop_regions = []
                engine_name = "morph"

                if ocr_engine == "morph":
                    # 强制使用形态学
                    unwrapped_gray = cv2.cvtColor(unwrapped, cv2.COLOR_BGR2GRAY) if len(unwrapped.shape) == 3 else unwrapped
                    crop_regions = ImageProcessor._detect_text_regions_morph(unwrapped_gray)
                    engine_name = "Morphology"
                else:
                    # OCR 引擎检测（auto / easyocr / paddle）
                    use_easyocr = (ocr_engine in ("auto", "easyocr")) and HAS_EASYOCR and _EASYOCR_READER is not None
                    use_paddle = (ocr_engine in ("auto", "paddle")) and HAS_PADDLE and _PADDLE_OCR is not None

                    if use_easyocr:
                        try:
                            raw = _EASYOCR_READER.readtext(unwrapped, detail=1)
                            if raw:
                                for i, item in enumerate(raw):
                                    pts = np.array(item[0], dtype=np.int32)
                                    x, y, bw, bh = cv2.boundingRect(pts)
                                    if bw < 3 or bh < 3:
                                        continue
                                    crop_regions.append({
                                        "id": i + 1,
                                        "bbox": (x, y, bw, bh),
                                        "polygon": pts,
                                        "center": (x + bw // 2, y + bh // 2),
                                        "text": item[1] if len(item) > 1 else "",
                                        "engine": "EasyOCR",
                                    })
                                engine_name = "EasyOCR"
                        except Exception:
                            pass

                    if not crop_regions and use_paddle:
                        try:
                            results = _PADDLE_OCR.ocr(unwrapped, det=True, rec=False, cls=False)
                            if results and results[0]:
                                for i, box_info in enumerate(results[0]):
                                    if box_info is None:
                                        continue
                                    box = np.array(box_info, dtype=np.int32)
                                    x, y, bw, bh = cv2.boundingRect(box)
                                    if bw < 3 or bh < 3:
                                        continue
                                    crop_regions.append({
                                        "id": i + 1,
                                        "bbox": (x, y, bw, bh),
                                        "polygon": box,
                                        "center": (x + bw // 2, y + bh // 2),
                                        "text": "",
                                        "engine": "PaddleOCR",
                                    })
                                engine_name = "PaddleOCR"
                        except Exception:
                            pass

                    # OCR 均无结果时回退形态学
                    if not crop_regions:
                        unwrapped_gray = cv2.cvtColor(unwrapped, cv2.COLOR_BGR2GRAY) if len(unwrapped.shape) == 3 else unwrapped
                        crop_regions = ImageProcessor._detect_text_regions_morph(unwrapped_gray)
                        engine_name = "Morphology(fallback)"

                total_text += len(crop_regions)

                # 在展开图上绘制检测框
                for region in crop_regions:
                    bx, by, bw, bh = region["bbox"]
                    cv2.rectangle(panel, (bx, by), (bx+bw, by+bh),
                                  (0, 255, 0), 2)

                # 展开面板信息
                panel_h = max(2 * r, 60)
                panel_w = max(int(panel_h * 3.0), 150)
                info_panel = np.full((panel_h, panel_w, 3), (40, 40, 40), dtype=np.uint8)
                cv2.putText(info_panel, engine_name, (5, 18),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 100), 1)
                cv2.putText(info_panel, f"{len(crop_regions)} text(s) on ring",
                            (5, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 100), 1)

                # 在原图上绘制检测区域（映射回原图坐标）
                if unwrap_method == "remap":
                    # remap 展开：角度→原图坐标映射
                    for region in crop_regions:
                        bx, by, bw, bh = region["bbox"]
                        pts_orig = []
                        for corner in [(bx, by), (bx+bw, by), (bx+bw, by+bh), (bx, by+bh)]:
                            px_u, py_u = corner
                            frac = px_u / output_width
                            angle = 2.0 * math.pi * frac
                            rr = r - py_u
                            ox = int(cx + rr * math.cos(angle))
                            oy = int(cy + rr * math.sin(angle))
                            pts_orig.append([ox, oy])
                        poly_orig = np.array(pts_orig, dtype=np.int32).reshape(-1, 1, 2)
                        cv2.polylines(result, [poly_orig], True, (0, 255, 0), 2)
                else:
                    # warpPolar 展开：原有映射逻辑
                    for region in crop_regions:
                        bx, by, bw, bh = region["bbox"]
                        pts_orig = []
                        for corner in [(bx, by), (bx+bw, by), (bx+bw, by+bh), (bx, by+bh)]:
                            px_u, py_u = corner
                            actual_y = py_u + crop_y
                            rr = actual_y / scale_y
                            theta = 2.0 * np.pi * px_u / polar_w
                            ox = int(cx + rr * np.cos(theta))
                            oy = int(cy + rr * np.sin(theta))
                            pts_orig.append([ox, oy])
                        poly_orig = np.array(pts_orig, dtype=np.int32).reshape(-1, 1, 2)
                        cv2.polylines(result, [poly_orig], True, (0, 255, 0), 2)

                # 标注圆编号
                cv2.putText(result, f"#{idx+1}", (cx - 10, cy - r - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

                # ── 缩放展开面板：高度=圆的直径 ──
                panel_h, panel_w = panel.shape[:2]
                target_h = max(2 * r, 30)
                panel_scale = target_h / panel_h if panel_h > 0 else 1.0
                target_w = max(int(panel_w * panel_scale), 40)
                panel_scaled = cv2.resize(panel, (target_w, target_h))

                # ── 放置到圆右侧 ──
                panel_x = min(cx + r + 8, w_img - target_w)  # 圆右侧，不超出原图右边界
                panel_x = max(panel_x, cx + r + 2)
                panel_y = max(0, cy - target_h // 2)
                panel_y = min(panel_y, h_img - target_h)

                panel_placements.append((panel_scaled, panel_x, panel_y, target_w, target_h))

        # ── 确定最终画布大小（可能需要向右扩展以容纳展开面板）──
        n_circles = len(panel_placements)
        canvas_w = w_img
        for _, px, _, pw, _ in panel_placements:
            right_edge = px + pw + 4
            if right_edge > canvas_w:
                canvas_w = right_edge

        # 若需要扩展画布，在右侧填充背景
        if canvas_w > w_img:
            bg_color = (60, 60, 60)
            extended = np.full((h_img, canvas_w, 3), bg_color, dtype=np.uint8)
            extended[:, :w_img] = result
            result = extended

        # ── 将展开面板贴到对应圆旁 ──
        for panel, px, py, pw, ph in panel_placements:
            # 边框区分
            cv2.rectangle(result, (px - 2, py - 2),
                          (px + pw + 2, py + ph + 2),
                          (0, 200, 255), 1)
            cv2.putText(result, "unwrapped", (px + 2, py + 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 200, 255), 1)
            # 贴面板（clip 安全）
            y1, y2 = py, py + ph
            x1, x2 = px, px + pw
            if y2 > result.shape[0]:
                y2 = result.shape[0]
                ph = y2 - y1
            if x2 > result.shape[1]:
                x2 = result.shape[1]
                pw = x2 - x1
            if ph > 0 and pw > 0:
                result[y1:y2, x1:x2] = panel[:ph, :pw]

        # 汇总信息
        if n_circles > 0:
            info = f"Circles: {n_circles}, Text regions: {total_text}"
            cv2.putText(result, info, (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        else:
            cv2.putText(result, "No circles detected", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        return result

    # ------------------------------------------------------------------
    # 圆环展开（极坐标变换）
    # ------------------------------------------------------------------
    @staticmethod
    def polar_unwrap(img: np.ndarray,
                     roi_cx: int = 0, roi_cy: int = 0,
                     roi_radius: int = 100,
                     inner_ratio: float = 0.5,
                     start_angle: float = 0.0,
                     end_angle: float = 360.0) -> np.ndarray:
        """圆环展开 —— 将圆形环形区域通过极坐标变换展开为矩形条带。

        将圆环上的弧线文字展开成水平排列的矩形图像，
        可作为文字检测的预处理步骤，大幅提升圆环文字的检出率。

        原理: 使用 cv2.warpPolar 将圆形环带从极坐标变换为笛卡尔坐标，
        使原本沿圆弧排列的文字变为水平排列，便于后续形态学文字检测。

        ROI 参数（圆心、半径）通过手动画图设置。
        扇形角度（start_angle, end_angle）支持只展开圆环的一部分。

        Args:
            img: 输入图像 (BGR 或灰度)
            roi_cx, roi_cy: 圆心坐标 — 由绘图设置
            roi_radius: 外圆半径 — 由绘图设置
            inner_ratio: 内圆半径比例 (0.1-0.95)，默认 0.5 保留较宽环带
            start_angle: 扇形起始角度 (0-360)，默认 0
            end_angle: 扇形终止角度 (0-360)，默认 360（整圈）

        Returns:
            展开后的矩形条带图像 (BGR)
        """
        if img is None:
            return img

        h, w = img.shape[:2]

        # 自动填充默认值
        cx = roi_cx if roi_cx > 0 else w // 2
        cy = roi_cy if roi_cy > 0 else h // 2
        r_outer = roi_radius if roi_radius > 0 else min(h, w) // 3

        inner_ratio = max(0.1, min(0.95, inner_ratio))
        r_inner = int(r_outer * inner_ratio)
        band = r_outer - r_inner

        if band < 3:
            return img

        # 扇形角度处理
        sa = start_angle if start_angle is not None else 0.0
        ea = end_angle if end_angle is not None else 360.0
        if ea <= sa:
            ea = sa + 360.0
        is_full_circle = (ea - sa >= 359.5)

        # 统一为 BGR 供 warpPolar 使用
        if len(img.shape) == 2:
            img_bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        else:
            img_bgr = img.copy()

        # 极坐标展开参数
        max_radius = max(r_outer, 1)
        # 展开图尺寸: 宽度=外圆周长, 高度=环带宽度×3 保证文字不变形
        polar_h = max(band * 3, 60)
        full_polar_w = max(int(2 * np.pi * max_radius), 200)

        # warpPolar 线性展开（先展开整圈）
        full_polar = cv2.warpPolar(img_bgr, (full_polar_w, polar_h),
                                   (cx, cy), max_radius,
                                   cv2.WARP_POLAR_LINEAR)

        # 裁掉内圆以内的区域，只保留环形带
        scale_y = polar_h / max_radius
        crop_y = max(0, int(r_inner * scale_y))
        if crop_y < polar_h:
            full_polar = full_polar[crop_y:, :]

        # 裁剪到扇形角度范围
        if not is_full_circle:
            x_start = int(sa / 360.0 * full_polar_w) % full_polar_w
            x_end = int(ea / 360.0 * full_polar_w)
            if x_end <= x_start:
                x_end = full_polar_w
            if x_end - x_start < 10:
                x_start, x_end = 0, full_polar_w
            polar = full_polar[:, x_start:x_end].copy()
        else:
            polar = full_polar

        if polar.size == 0 or polar.shape[0] < 4 or polar.shape[1] < 10:
            return img

        return polar

    # ------------------------------------------------------------------
    # 圆环展开（remap 极坐标 + 自动起始角度）
    # ------------------------------------------------------------------
    @staticmethod
    def _find_longest_white_block(gray, cx, cy, r, ratio=0.6, samples=360):
        """采样各角度的圆环亮度，找到最长连续白色区段的中心作为起始角度。

        在圆环中间半径处采样一圈像素，按阈值二值化后找最长连续高亮段，
        返回其中心角度。这样文字（暗色）会被完整聚集，不会分散在左右两端。

        Args:
            gray: 灰度图
            cx, cy: 圆心坐标
            r: 圆半径
            ratio: 圆环内径比例
            samples: 采样角度数

        Returns:
            float: 最佳起始角度（弧度）
        """
        r_inner = int(r * ratio)
        r_mid = (r + r_inner) // 2

        brightness = []
        for i in range(samples):
            angle = 2.0 * math.pi * i / samples
            vals = []
            for dr in range(-3, 4):
                px = int(cx + (r_mid + dr) * math.cos(angle))
                py = int(cy + (r_mid + dr) * math.sin(angle))
                if 0 <= px < gray.shape[1] and 0 <= py < gray.shape[0]:
                    vals.append(int(gray[py, px]))
            brightness.append(np.mean(vals) if vals else 0)

        threshold = np.mean(brightness)
        is_white = [b > threshold for b in brightness]

        best_start, best_len = 0, 0
        cur_start, cur_len = -1, 0

        for i in range(samples * 2):
            idx = i % samples
            if is_white[idx]:
                if cur_len == 0:
                    cur_start = idx
                cur_len += 1
                if cur_len > best_len:
                    best_len = cur_len
                    best_start = cur_start
            else:
                cur_len = 0

        best_len = min(best_len, samples)
        center_idx = (best_start + best_len // 2) % samples
        best_angle = 2.0 * math.pi * center_idx / samples

        return best_angle

    @staticmethod
    def ring_unwrap(img: np.ndarray,
                    roi_cx: int = 0, roi_cy: int = 0,
                    roi_radius: int = 100,
                    inner_ratio: float = 0.6,
                    output_width: int = 1080,
                    auto_angle: bool = True,
                    start_angle_deg: float = 0.0) -> np.ndarray:
        """圆环展开（remap 极坐标变换 + 自动起始角度）。

        与 polar_unwrap 不同，本方法使用 cv2.remap 逐像素映射，
        配合自动寻找最佳起始角度，将圆环上的文字拉直为水平一行，
        更适合后续 OCR 识别。

        特点:
          - 自动检测最长连续白色区段，以其为中心展开，文字不被切断
          - 展开宽度可自定义（默认 1080px，对应 360°）
          - 内外径比例可调（默认 0.6）

        Args:
            img: 输入图像 (BGR 或灰度)
            roi_cx, roi_cy: 圆心坐标 — 由绘图设置
            roi_radius: 外圆半径 — 由绘图设置
            inner_ratio: 内圆半径比例 (0.1-0.95)，默认 0.6
            output_width: 展开后矩形宽度（对应 360°），默认 1080
            auto_angle: 是否自动寻找最佳起始角度，默认 True
            start_angle_deg: 手动指定起始角度（度），auto_angle=False 时生效

        Returns:
            展开后的矩形 BGR 图像
        """
        if img is None:
            return img

        h, w = img.shape[:2]
        cx = roi_cx if roi_cx > 0 else w // 2
        cy = roi_cy if roi_cy > 0 else h // 2
        r = roi_radius if roi_radius > 0 else min(h, w) // 3

        inner_ratio = max(0.1, min(0.95, inner_ratio))
        r_inner = int(r * inner_ratio)
        r_outer = r
        ring_width = r_outer - r_inner

        if ring_width < 3:
            return img

        # 统一为 BGR
        if len(img.shape) == 2:
            img_bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        else:
            img_bgr = img

        # 确定起始角度
        if auto_angle:
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            start_angle = ImageProcessor._find_longest_white_block(
                gray, cx, cy, r, inner_ratio)
        else:
            start_angle = math.radians(start_angle_deg)

        # 构建极坐标映射表
        n_cols = output_width
        n_rows = ring_width

        map_x = np.zeros((n_rows, n_cols), dtype=np.float32)
        map_y = np.zeros((n_rows, n_cols), dtype=np.float32)

        for col in range(n_cols):
            angle = start_angle + 2.0 * math.pi * col / n_cols
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)

            for row in range(n_rows):
                radius = r_outer - row
                map_x[row, col] = cx + radius * cos_a
                map_y[row, col] = cy + radius * sin_a

        unwrapped = cv2.remap(img_bgr, map_x, map_y, cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_WRAP)
        return unwrapped

    # ------------------------------------------------------------------
    # 圆形验证 —— 边缘采样 + 圆形度评分，过滤 HoughCircles 误检
    # ------------------------------------------------------------------
    @staticmethod
    def _validate_circle_circularity(gray, cx, cy, r,
                                      edge_low=50, edge_high=150,
                                      sample_count=60, radial_tolerance=0.15,
                                      min_score=0.50):
        """用边缘采样验证候选圆是否真的是圆形。

        HoughCircles 基于梯度投票，容易把矩形角、弧形段等非圆形区域误检为圆。
        本方法沿候选圆周等距采样，检查每个采样点是否有边缘像素支撑，
        只有足够比例的圆周点命中边缘才通过验证，大幅降低误检率。

        Args:
            gray: 灰度图像
            cx, cy: 圆心
            r: 半径
            edge_low, edge_high: Canny 阈值
            sample_count: 圆周采样点数（默认60）
            radial_tolerance: 径向容差比例（默认±15%半径范围）
            min_score: 最低通过分数（0.0-1.0），越高越严格

        Returns:
            float: 圆周命中分数 (0.0-1.0)，同时返回是否通过
        """
        if gray is None or r < 3:
            return 0.0, False

        h, w = gray.shape[:2]
        # 边界检查
        if cx - r < 0 or cx + r >= w or cy - r < 0 or cy + r >= h:
            return 0.0, False

        # 用 Canny 提取边缘
        edges = cv2.Canny(gray, edge_low, edge_high)

        # 沿圆周等距采样
        delta_r = max(2, int(r * radial_tolerance))
        hits = 0
        for i in range(sample_count):
            theta = 2.0 * np.pi * i / sample_count
            # 检查径向条带内是否有边缘像素
            for dr in range(-delta_r, delta_r + 1, 2):
                rr = r + dr
                if rr < 1:
                    continue
                ex = int(cx + rr * np.cos(theta))
                ey = int(cy + rr * np.sin(theta))
                if 0 <= ex < w and 0 <= ey < h:
                    if edges[ey, ex] > 0:
                        hits += 1
                        break  # 该角度命中，跳到下一个采样点

        score = hits / sample_count
        return score, score >= min_score

    # ------------------------------------------------------------------
    # 形态学文字区域检测（纯 OpenCV，极快）
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # 双引擎文字检测 —— EasyOCR GPU(主) → PaddleOCR CPU(辅)
    # ------------------------------------------------------------------
    @staticmethod
    def _detect_text_engine(img_bgr, roi_mask=None):
        """双引擎文字区域检测。

        优先使用 EasyOCR GPU (CRAFT 检测器, PyTorch CUDA 加速)，
        失败或无 GPU 时回退到 PaddleOCR CPU (DB++ 检测器)，
        两者都不可用时返回空列表（外层会回退到形态学）。

        Args:
            img_bgr: BGR 图像
            roi_mask: 可选 ROI 掩膜

        Returns:
            list[dict]: 每个区域 {bbox, polygon, center} 或空列表
        """
        regions = []

        # ── 引擎 1: EasyOCR GPU ──
        if HAS_EASYOCR and _EASYOCR_READER is not None:
            try:
                # 准备检测图像（如有掩膜则只在掩膜区域检测）
                if roi_mask is not None:
                    img_detect = cv2.bitwise_and(img_bgr, img_bgr, mask=roi_mask)
                else:
                    img_detect = img_bgr

                # EasyOCR detect+recognize; 我们只取检测框
                raw = _EASYOCR_READER.readtext(img_detect, detail=1)
                if raw:
                    for i, item in enumerate(raw):
                        pts = np.array(item[0], dtype=np.int32)
                        x, y, bw, bh = cv2.boundingRect(pts)
                        if bw < 3 or bh < 3:
                            continue
                        # ROI 掩膜校验
                        if roi_mask is not None:
                            cp = (x + bw // 2, y + bh // 2)
                            h_m, w_m = roi_mask.shape[:2]
                            if 0 <= cp[0] < w_m and 0 <= cp[1] < h_m:
                                if roi_mask[cp[1], cp[0]] == 0:
                                    continue
                        regions.append({
                            "id": i + 1,
                            "bbox": (x, y, bw, bh),
                            "polygon": pts,
                            "center": (x + bw // 2, y + bh // 2),
                            "text": item[1] if len(item) > 1 else "",
                            "engine": "EasyOCR",
                        })
                    if regions:
                        return regions
            except Exception:
                pass  # EasyOCR 失败 → 尝试下一个引擎

        # ── 引擎 2: PaddleOCR CPU (弧形文字精度更高) ──
        if HAS_PADDLE and _PADDLE_OCR is not None:
            try:
                if roi_mask is not None:
                    img_detect = cv2.bitwise_and(img_bgr, img_bgr, mask=roi_mask)
                else:
                    img_detect = img_bgr

                results = _PADDLE_OCR.ocr(img_detect, det=True, rec=False, cls=False)
                if results and results[0]:
                    h_m, w_m = img_bgr.shape[:2]
                    for i, box_info in enumerate(results[0]):
                        if box_info is None:
                            continue
                        box = np.array(box_info, dtype=np.int32)
                        x, y, bw, bh = cv2.boundingRect(box)
                        if bw < 3 or bh < 3:
                            continue
                        if roi_mask is not None:
                            cp = (x + bw // 2, y + bh // 2)
                            if 0 <= cp[0] < w_m and 0 <= cp[1] < h_m:
                                if roi_mask[cp[1], cp[0]] == 0:
                                    continue
                        regions.append({
                            "id": i + 1,
                            "bbox": (x, y, bw, bh),
                            "polygon": box,
                            "center": (x + bw // 2, y + bh // 2),
                            "text": "",
                            "engine": "PaddleOCR",
                        })
            except Exception:
                pass

        return regions

    @staticmethod
    def _detect_text_regions_morph(gray, min_area=100, max_area=0):
        """用形态学操作快速检测文字区域。

        增强策略:
          1. CLAHE 对比度增强 → 提升低对比度文字区域
          2. 自适应二值化 → 分离文字与背景
          3. 横向闭运算 → 连接同行字符
          4. 连通域分析 → 提取文字区域候选
        """
        text_info = []
        if gray is None or gray.size == 0:
            return text_info

        h_img, w_img = gray.shape[:2]

        # ── 1. CLAHE 对比度增强 ──
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # ── 2. 自适应二值化 (双策略) ──
        # 策略 A: 高斯自适应阈值 — 适合大多数场景
        block_size = max(11, min(31, (w_img // 40) | 1))  # 自适应块大小
        binary_a = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, block_size, 6)

        # 策略 B: 均值自适应阈值 — 互补检测
        binary_b = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY_INV, block_size, 4)

        # 合并两个策略的结果
        binary = cv2.bitwise_or(binary_a, binary_b)

        # ── 3. 横向闭运算连接同行字符 ──
        h_kern = max(15, w_img // 40)
        v_kern = max(2, h_img // 200)
        kern_h = cv2.getStructuringElement(cv2.MORPH_RECT, (h_kern, v_kern))
        closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kern_h)

        # 小膨胀填充字符间小间隙
        kern_d = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        dilated = cv2.dilate(closed, kern_d, iterations=1)

        # ── 4. 连通域分析 ──
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area:
                continue
            if max_area > 0 and area > max_area:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            # 宽高比过滤：排除过长或过窄的噪点区域
            aspect = w / h if h > 0 else 0
            if aspect > 35 or aspect < 0.03:
                continue
            # 尺寸过滤
            if w < 6 or h < 3:
                continue
            # 填充率过滤：文字区域内部像素占比通常在 15%-85%
            roi = binary[y:y + h, x:x + w]
            fill_ratio = np.count_nonzero(roi) / (w * h) if w * h > 0 else 0
            if fill_ratio < 0.05 or fill_ratio > 0.95:
                continue

            text_info.append({
                "id": len(text_info) + 1,
                "bbox": (x, y, w, h),
                "center": (x + w // 2, y + h // 2),
            })

        return text_info

    # ------------------------------------------------------------------
    # 自适应颜色分割（K-means K=2，自动取上值）
    # ------------------------------------------------------------------
    @staticmethod
    def adaptive_color_segment(img: np.ndarray, color_space: str = "gray",
                               channel: int = 0, invert: bool = False) -> np.ndarray:
        """自适应颜色分割 —— K-means 自动聚类为 2 簇，取上值。

        不需要手动输入阈值，算法自动根据图像像素分布找到最佳分割点。
        适用于将前景/背景区分、亮区/暗区分离等场景。

        Args:
            img: 输入图像 (BGR 或灰度)
            color_space: 颜色空间 ('gray', 'hsv', 'rgb')
            channel: 用于聚类的通道索引 (0/1/2)
                - gray: 无效（始终用灰度值）
                - hsv: 0=H, 1=S, 2=V
                - rgb: 0=R, 1=G, 2=B
            invert: False=取上值（较大簇），True=取下值（较小簇）

        Returns:
            分割后的图像（只保留目标簇的像素，其余为黑）
        """
        if img is None:
            return img

        # 转换颜色空间并取目标通道
        if color_space == "gray" or len(img.shape) == 2:
            gray = img if len(img.shape) == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            data = gray.reshape(-1, 1).astype(np.float32)
            src_img = gray
        elif color_space == "hsv":
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            ch_idx = min(max(channel, 0), 2)
            data = hsv[:, :, ch_idx].reshape(-1, 1).astype(np.float32)
            src_img = hsv[:, :, ch_idx]
        elif color_space == "rgb":
            # OpenCV BGR: channel 0=R→B, 1=G→G, 2=B→R
            bgr_map = [2, 1, 0]
            ch_idx = bgr_map[min(max(channel, 0), 2)]
            data = img[:, :, ch_idx].reshape(-1, 1).astype(np.float32)
            src_img = img[:, :, ch_idx]
        else:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
            data = gray.reshape(-1, 1).astype(np.float32)
            src_img = gray

        # K-means 聚类 (K=2)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.5)
        _, labels, centers = cv2.kmeans(data, 2, None, criteria, 3,
                                         cv2.KMEANS_PP_CENTERS)

        # 确定哪个簇是"上值"
        c0, c1 = float(centers[0][0]), float(centers[1][0])
        upper_label = 0 if c0 >= c1 else 1
        if invert:
            upper_label = 1 - upper_label

        # 生成 mask
        mask = (labels.reshape(src_img.shape) == upper_label).astype(np.uint8) * 255

        # 形态学平滑：去除噪点、填充孔洞
        kern = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kern, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kern, iterations=1)

        # 应用 mask 到原图
        if len(img.shape) == 3:
            return cv2.bitwise_and(img, img, mask=mask)
        else:
            return cv2.bitwise_and(src_img, src_img, mask=mask)

    # ROI 掩膜辅助（供检测函数内部使用）
    # ------------------------------------------------------------------
    @staticmethod
    def _apply_roi(img: np.ndarray, roi_type: int = 0,
                   roi_cx: int = 0, roi_cy: int = 0, roi_radius: int = 100,
                   roi_x: int = 0, roi_y: int = 0,
                   roi_w: int = 100, roi_h: int = 100) -> np.ndarray:
        """应用 ROI 掩膜（内部辅助方法）。

        Args:
            img: 输入图像
            roi_type: ROI 类型 (0=无, 1=圆形, 2=矩形)
            roi_cx, roi_cy, roi_radius: 圆形 ROI 参数
            roi_x, roi_y, roi_w, roi_h: 矩形 ROI 参数

        Returns:
            应用 ROI 后的图像，roi_type=0 时返回原图
        """
        if img is None or roi_type == 0:
            return img

        h, w = img.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)

        if roi_type == 1:  # 圆形
            cv2.circle(mask, (int(roi_cx), int(roi_cy)),
                       int(roi_radius), 255, -1)
        elif roi_type == 2:  # 矩形
            x1 = max(0, int(roi_x))
            y1 = max(0, int(roi_y))
            x2 = min(w, int(roi_x) + int(roi_w))
            y2 = min(h, int(roi_y) + int(roi_h))
            cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)
        else:
            return img

        return cv2.bitwise_and(img, img, mask=mask)

    @staticmethod
    def compute_adaptive_threshold(img: np.ndarray, color_space: str = "hsv",
                                   channel: int = 0) -> dict:
        """自适应阈值计算 —— 使用 Otsu 方法自动计算通道的上下限。

        分析图像指定通道的直方图分布，利用 Otsu 算法自动找到最优分割阈值，
        将图像分为两个区域。返回的上下限可用于 color_filter 的参数填充。

        Args:
            img: 输入图像 (BGR 或灰度)
            color_space: 颜色空间 ('hsv', 'rgb', 'gray')
            channel: 目标通道 (1/2/3)，0 表示计算全部三个通道。
                     灰度图忽略此参数，始终返回通道1

        Returns:
            dict: 指定通道的 {chX_min, chX_max}，channel=0 时返回全部三个通道
        """
        if img is None:
            return {}

        result = {}

        # ── 灰度图：只有通道1 ──
        if color_space == "gray" or len(img.shape) == 2:
            gray = img if len(img.shape) == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            thresh, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            # 取亮区：min=阈值, max=255
            result["ch1_min"] = int(thresh)
            result["ch1_max"] = 255
            return result

        # ── 确定颜色空间和通道范围 ──
        if color_space == "hsv":
            converted = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            max_vals = [180, 255, 255]  # H, S, V 各自的范围上限
            ch_names = ["H", "S", "V"]
        elif color_space == "rgb":
            converted = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            max_vals = [255, 255, 255]
            ch_names = ["R", "G", "B"]
        else:
            return result

        # ── 单通道模式 ──
        if channel in (1, 2, 3):
            i = channel - 1
            ch = converted[:, :, i]
            thresh, _ = cv2.threshold(ch, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            result[f"ch{channel}_min"] = int(thresh)
            result[f"ch{channel}_max"] = max_vals[i]
            return result

        # ── 全通道模式 ──
        for i in range(3):
            ch = converted[:, :, i]
            thresh, _ = cv2.threshold(ch, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            # 取亮区：min=Otsu阈值, max=通道最大值
            result[f"ch{i+1}_min"] = int(thresh)
            result[f"ch{i+1}_max"] = max_vals[i]

        return result

    @staticmethod
    def compute_kmeans_threshold(img: np.ndarray, color_space: str = "hsv") -> dict:
        """K-means 自动阈值 —— 对每个通道做 K=2 聚类，返回各通道 min/max。

        Args:
            img: 输入图像 (BGR 或灰度)
            color_space: 颜色空间 ('hsv', 'rgb', 'gray')

        Returns:
            dict: {ch1_min, ch1_max, ch2_min, ch2_max, ch3_min, ch3_max}
        """
        if img is None:
            return {}

        result = {}
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.5)

        # ── 灰度 ──
        if color_space == "gray" or len(img.shape) == 2:
            gray = img if len(img.shape) == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            data = gray.reshape(-1, 1).astype(np.float32)
            _, _, centers = cv2.kmeans(data, 2, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
            c0, c1 = float(centers[0][0]), float(centers[1][0])
            result["ch1_min"] = int(min(c0, c1))
            result["ch1_max"] = int(max(c0, c1))
            return result

        # ── 颜色空间转换 ──
        if color_space == "hsv":
            converted = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            max_vals = [180, 255, 255]
        elif color_space == "rgb":
            converted = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            max_vals = [255, 255, 255]
        else:
            return result

        # ── 每个通道 K-means ──
        for i in range(3):
            ch = converted[:, :, i]
            data = ch.reshape(-1, 1).astype(np.float32)
            _, _, centers = cv2.kmeans(data, 2, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
            c0, c1 = float(centers[0][0]), float(centers[1][0])
            result[f"ch{i+1}_min"] = int(min(c0, c1))
            result[f"ch{i+1}_max"] = int(max(c0, c1))

        return result

    @staticmethod
    def color_filter(img: np.ndarray, color_space: str = "hsv",
                     ch1_min: int = 0, ch1_max: int = 255,
                     ch2_min: int = 0, ch2_max: int = 255,
                     ch3_min: int = 0, ch3_max: int = 255) -> np.ndarray:
        """颜色过滤 —— 在指定颜色空间中过滤像素范围。

        Args:
            img: 输入图像 (BGR 或灰度)
            color_space: 颜色空间 ('hsv', 'rgb', 'gray')
                - hsv: ch1=H(0-180), ch2=S(0-255), ch3=V(0-255)
                - rgb: ch1=R(0-255), ch2=G(0-255), ch3=B(0-255)
                - gray: ch1=灰度值(0-255), ch2/ch3无效
            ch1_min: 通道1最小值
            ch1_max: 通道1最大值
            ch2_min: 通道2最小值
            ch2_max: 通道2最大值
            ch3_min: 通道3最小值
            ch3_max: 通道3最大值

        Returns:
            过滤后的图像（只保留符合范围的像素）
        """
        if img is None:
            return img

        # 灰度图处理
        if color_space == "gray" or len(img.shape) == 2:
            gray = img if len(img.shape) == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            mask = cv2.inRange(gray, ch1_min, ch1_max)
            result = cv2.bitwise_and(gray, gray, mask=mask)
            return result

        # RGB颜色空间
        if color_space == "rgb":
            # OpenCV使用BGR顺序
            lower = np.array([ch3_min, ch2_min, ch1_min])  # B, G, R
            upper = np.array([ch3_max, ch2_max, ch1_max])
            mask = cv2.inRange(img, lower, upper)
            result = cv2.bitwise_and(img, img, mask=mask)
            return result

        # HSV颜色空间
        if color_space == "hsv":
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            lower = np.array([ch1_min, ch2_min, ch3_min])  # H, S, V
            upper = np.array([ch1_max, ch2_max, ch3_max])
            mask = cv2.inRange(hsv, lower, upper)
            result = cv2.bitwise_and(img, img, mask=mask)
            return result

        return img

    # ------------------------------------------------------------------
    # 颜色空间转换
    # ------------------------------------------------------------------
    @staticmethod
    def convert_color(img: np.ndarray, conversion: str = "gray") -> np.ndarray:
        """颜色空间转换。

        所有输出统一为 BGR 格式（灰度图转为 3 通道 BGR），
        保证下游 display 管线能正确显示。

        Args:
            img: 输入图像 (BGR)
            conversion: 转换类型 ('gray', 'hsv', 'lab', 'rgb')

        Returns:
            转换后的 BGR 图像
        """
        if img is None:
            return img

        if conversion == "gray":
            if len(img.shape) == 3:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif conversion == "hsv":
            if len(img.shape) == 3:
                hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
            return img
        elif conversion == "lab":
            if len(img.shape) == 3:
                lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
                return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            return img
        elif conversion == "rgb":
            if len(img.shape) == 3:
                rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            return img
        else:
            return img


# 预设参数配置
PROCESS_PRESETS = {
    "增强": {
        "亮度对比度": {"func": "adjust_brightness_contrast",
                      "params": {"brightness": 0, "contrast": 0}},
        "伽马校正": {"func": "gamma_correction",
                    "params": {"gamma": 1.0}},
        "直方图均衡化": {"func": "histogram_equalization",
                       "params": {}},
        "CLAHE": {"func": "clahe",
                  "params": {"clip_limit": 2.0, "grid_size": 8}},
    },
    "去噪": {
        "高斯模糊": {"func": "gaussian_blur",
                    "params": {"kernel_size": 5, "sigma": 0}},
        "中值滤波": {"func": "median_blur",
                    "params": {"kernel_size": 5}},
        "双边滤波": {"func": "bilateral_filter",
                    "params": {"d": 9, "sigma_color": 75, "sigma_space": 75}},
        "非局部均值": {"func": "nlm_denoise",
                     "params": {"h": 10, "template_window": 7, "search_window": 21}},
        "连通性过滤": {"func": "connectivity_filter",
                    "params": {"min_area": 100, "thresh": 127, "keep_white": 1}},
    },
    "形态学": {
        "腐蚀": {"func": "morphological",
                "params": {"operation": "erode", "kernel_size": 5, "iterations": 1}},
        "膨胀": {"func": "morphological",
                "params": {"operation": "dilate", "kernel_size": 5, "iterations": 1}},
        "开运算": {"func": "morphological",
                  "params": {"operation": "open", "kernel_size": 5, "iterations": 1}},
        "闭运算": {"func": "morphological",
                  "params": {"operation": "close", "kernel_size": 5, "iterations": 1}},
        "梯度": {"func": "morphological",
                "params": {"operation": "gradient", "kernel_size": 5, "iterations": 1}},
    },
    "阈值化": {
        "自适应均值": {"func": "threshold",
                     "params": {"method": "adaptive_mean", "max_val": 255,
                                "block_size": 11, "C": 2}},
        "自适应高斯": {"func": "threshold",
                     "params": {"method": "adaptive_gaussian", "max_val": 255,
                                "block_size": 11, "C": 2}},
        "Otsu": {"func": "threshold",
                 "params": {"method": "otsu", "max_val": 255}},
    },
    "检测": {
        "边缘检测": {
            "Canny": {"func": "canny_edge",
                      "params": {"threshold1": 50, "threshold2": 150}},
            "Sobel": {"func": "sobel_edge",
                      "params": {"dx": 1, "dy": 1, "ksize": 3}},
            "Laplacian": {"func": "laplacian_edge",
                          "params": {"ksize": 3}},
        },
        "形状检测": {
            "矩形": {"func": "detect_rectangles",
                     "params": {"min_area": 1000, "max_area": 0,
                                "threshold1": 50, "threshold2": 150}},
            "圆形": {"func": "detect_circles",
                     "params": {"min_radius": 10, "max_radius": 200,
                                "min_dist": 50, "param1": 50, "param2": 30,
                                "circularity_threshold": 0.50}},
            "多边形": {"func": "detect_polygons",
                      "params": {"min_area": 1000, "max_area": 0,
                                 "threshold1": 50, "threshold2": 150,
                                 "approx_epsilon": 0.02,
                                 "min_sides": 3, "max_sides": 8}},
        },
        "文字检测": {"func": "detect_text",
                   "params": {"min_area": 100, "max_area": 0,
                              "ocr_lang": "eng",
                              "inner_ratio": 0.5}},
        "条码检测": {"func": "detect_qrcode",
                    "params": {}},
    },
    "颜色处理": {
        "颜色转换": {
            "灰度": {"func": "convert_color",
                     "params": {"conversion": "gray"}},
            "HSV": {"func": "convert_color",
                    "params": {"conversion": "hsv"}},
            "RGB": {"func": "convert_color",
                    "params": {"conversion": "rgb"}},
            "LAB": {"func": "convert_color",
                    "params": {"conversion": "lab"}},
        },
        "颜色过滤": {
            "HSV 过滤": {"func": "color_filter",
                         "params": {"color_space": "hsv",
                                    "ch1_min": 0, "ch1_max": 180,
                                    "ch2_min": 0, "ch2_max": 255,
                                    "ch3_min": 0, "ch3_max": 255}},
            "RGB 过滤": {"func": "color_filter",
                         "params": {"color_space": "rgb",
                                    "ch1_min": 0, "ch1_max": 255,
                                    "ch2_min": 0, "ch2_max": 255,
                                    "ch3_min": 0, "ch3_max": 255}},
            "灰度过滤": {"func": "color_filter",
                         "params": {"color_space": "gray",
                                    "ch1_min": 0, "ch1_max": 255}},
        },
        "自适应分割": {"func": "adaptive_color_segment",
                      "params": {"color_space": "gray", "channel": 0,
                                 "invert": 0}},
    },
}

# 参数范围定义 (用于滑块)
PARAM_RANGES = {
    "brightness": {"min": -100, "max": 100, "default": 0, "label": "亮度"},
    "contrast": {"min": -100, "max": 100, "default": 0, "label": "对比度"},
    "gamma": {"min": 0.1, "max": 3.0, "default": 1.0, "label": "伽马", "resolution": 0.1},
    "clip_limit": {"min": 1.0, "max": 10.0, "default": 2.0, "label": "CLAHE限制", "resolution": 0.5},
    "grid_size": {"min": 4, "max": 16, "default": 8, "label": "网格大小", "step": 2},
    "kernel_size": {"min": 3, "max": 31, "default": 5, "label": "核大小", "step": 2},
    "sigma": {"min": 0, "max": 20, "default": 0, "label": "Sigma"},
    "d": {"min": 5, "max": 15, "default": 9, "label": "滤波直径"},
    "sigma_color": {"min": 1, "max": 150, "default": 75, "label": "颜色Sigma"},
    "sigma_space": {"min": 1, "max": 150, "default": 75, "label": "空间Sigma"},
    "h": {"min": 1, "max": 30, "default": 10, "label": "去噪强度"},
    "template_window": {"min": 3, "max": 15, "default": 7, "label": "模板窗口", "step": 2},
    "search_window": {"min": 11, "max": 35, "default": 21, "label": "搜索窗口", "step": 2},
    "threshold1": {"min": 0, "max": 255, "default": 50, "label": "低阈值"},
    "threshold2": {"min": 0, "max": 255, "default": 150, "label": "高阈值"},
    "aperture_size": {"min": 3, "max": 7, "default": 3, "label": "Sobel核", "step": 2},
    "ksize": {"min": 1, "max": 7, "default": 3, "label": "核大小", "step": 2},
    "dx": {"min": 0, "max": 2, "default": 1, "label": "X阶数"},
    "dy": {"min": 0, "max": 2, "default": 1, "label": "Y阶数"},
    "iterations": {"min": 1, "max": 10, "default": 1, "label": "迭代次数"},
    "thresh": {"min": 0, "max": 255, "default": 127, "label": "阈值"},
    "max_val": {"min": 0, "max": 255, "default": 255, "label": "最大值"},
    "block_size": {"min": 3, "max": 31, "default": 11, "label": "块大小", "step": 2},
    "C": {"min": -10, "max": 10, "default": 2, "label": "常数C"},
    "min_area": {"min": 100, "max": 100000, "default": 1000, "label": "最小面积"},
    "max_area": {"min": 0, "max": 500000, "default": 0, "label": "最大面积(0不限)"},
    "min_radius": {"min": 1, "max": 500, "default": 10, "label": "最小半径"},
    "max_radius": {"min": 1, "max": 500, "default": 200, "label": "最大半径"},
    "min_dist": {"min": 10, "max": 500, "default": 50, "label": "最小距离"},
    "param1": {"min": 10, "max": 300, "default": 50, "label": "参数1"},
    "param2": {"min": 10, "max": 100, "default": 30, "label": "参数2"},
    "dp": {"min": 1.0, "max": 2.5, "default": 1.2, "label": "DP精度", "resolution": 0.1},
    "circularity_threshold": {"min": 0.0, "max": 0.95, "default": 0.50, "label": "圆形度阈值(0=不验证)", "resolution": 0.05},
    "approx_epsilon": {"min": 0.01, "max": 0.1, "default": 0.02, "label": "逼近精度", "resolution": 0.01},
    "min_sides": {"min": 3, "max": 20, "default": 3, "label": "最小边数"},
    "max_sides": {"min": 3, "max": 20, "default": 8, "label": "最大边数"},
    "ch1_min": {"min": 0, "max": 255, "default": 0, "label": "通道1最小"},
    "ch1_max": {"min": 0, "max": 255, "default": 255, "label": "通道1最大"},
    "ch2_min": {"min": 0, "max": 255, "default": 0, "label": "通道2最小"},
    "ch2_max": {"min": 0, "max": 255, "default": 255, "label": "通道2最大"},
    "ch3_min": {"min": 0, "max": 255, "default": 0, "label": "通道3最小"},
    "ch3_max": {"min": 0, "max": 255, "default": 255, "label": "通道3最大"},
    "inner_ratio": {"min": 0.1, "max": 0.95, "default": 0.5, "label": "内圆比例(环带宽)", "resolution": 0.05},
    "output_width": {"min": 360, "max": 2160, "default": 1080, "label": "展开宽度(px)", "step": 60},
    "start_angle": {"min": 0.0, "max": 360.0, "default": 0.0, "label": "起始角度", "resolution": 1.0},
    "end_angle": {"min": 0.0, "max": 360.0, "default": 360.0, "label": "终止角度", "resolution": 1.0},
    "channel": {"min": 0, "max": 2, "default": 0, "label": "通道(0/1/2)"},
    "invert": {"min": 0, "max": 1, "default": 0, "label": "反转(0=上值,1=下值)"},
    "color_space": {"options": ["gray", "hsv", "rgb"], "label": "颜色空间"},
    "keep_white": {"options": ["1", "0"], "label": "保留(1=白,0=黑)"},
}
