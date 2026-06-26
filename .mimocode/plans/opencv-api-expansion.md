# 计划：增加API到500+ 并添加技术术语tooltip

## 当前状态
- 208个API，9个模块
- 需要增加到500+个API
- 需要为技术术语添加鼠标悬停说明

## 技术术语tooltip列表（需添加到style.css + 各HTML中）

### 颜色空间
- HSV: 色相(Hue)-饱和度(Saturation)-明度(Value)颜色空间，适合颜色分割
- HLS: 色相(Hue)-亮度(Lightness)-饱和度(Saturation)颜色空间
- Lab: 亮度(L)-红绿(a)-黄蓝(b)颜色空间，与设备无关
- Luv: 亮度(L)-色度(u,v)颜色空间，适合均匀色差
- YCrCb: 亮度(Y)-红色色度(Cr)-蓝色色度(Cb)，用于JPEG压缩
- BGR: 蓝-绿-红通道顺序，OpenCV默认格式
- RGB: 红-绿-蓝通道顺序，标准显示格式
- 灰度(Grayscale): 单通道黑白图像，像素值0-255

### 图像处理术语
- 掩码(Mask): 二值图像，用于限定操作区域(白色=有效，黑色=忽略)
- 核/卷积核(Kernel): 小矩阵，用于滤波、形态学等操作
- 锚点(Anchor): 卷积核或结构元素的参考点
- 迭代(Iterations): 操作重复执行的次数
- 轮廓(Contour): 图像中相同强度值的连续点组成的曲线
- 阈值(Threshold): 用于二值化的分界值
- 直方图(Histogram): 图像像素值分布的统计图
- 反向投影(Back Projection): 直方图匹配的逆过程
- 积分图(Integral Image): 用于快速计算区域和

### 几何变换术语
- 仿射变换(Affine): 保持平行线的线性变换(旋转、缩放、平移、剪切)
- 透视变换(Perspective): 模拟视角变化的变换，平行线可能相交
- 插值(Interpolation): 估算非整数位置的像素值
- 双线性插值(Bilinear): 使用4个相邻像素加权平均的插值方法
- 双三次插值(Bicubic): 使用16个相邻像素的高精度插值
- 重映射(Remap): 根据映射表重新排列像素位置

### 形态学术语
- 腐蚀(Erode): 缩小亮区，去除小噪点
- 膨胀(Dilate): 扩大亮区，填充小孔洞
- 开运算(Opening): 先腐蚀后膨胀，去噪点
- 闭运算(Closing): 先膨胀后腐蚀，填孔洞
- 结构元素(Structuring Element): 形态学操作的模板

### 边缘检测术语
- 梯度(Gradient): 图像亮度的变化率
- Canny: 多阶段边缘检测算法
- Sobel: 一阶微分算子，计算梯度
- Laplacian: 二阶微分算子
- 非极大值抑制(NMS): 保留局部最大值，抑制其他值

### 特征检测术语
- 角点(Corner): 两条边缘交汇处，梯度变化大的点
- 关键点(Keypoint): 图像中可重复检测的显著点
- 描述符(Descriptor): 描述关键点周围特征的向量
- 匹配(Matching): 在两幅图像间寻找对应特征

### 相机标定术语
- 内参矩阵(Camera Matrix): 焦距和主点参数
- 畸变系数(Distortion Coefficients): 描述镜头畸变的参数
- 外参(Extrinsic): 相机在世界坐标系中的位姿
- PnP: 从N个3D-2D点对应求解相机位姿
- 极线(Epipolar Line): 对极几何中的约束线
- 视差(Disparity): 立体视觉中同一点在左右图的水平位移

### 深度学习术语
- Blob: 4D张量(N,C,H,W)，DNN输入格式
- 前向推理(Forward Pass): 网络计算输出的过程
- 后端(Backend): DNN计算引擎(OpenCV/CUDA/OpenCL)
- NMS: 非极大值抑制，去除重叠检测框

## 新增API计划（按模块分配）

### imgproc.html 需新增 (~100个)
**图像变换:**
- cv2.warpPolar - 极坐标变换
- cv2.linearPolar - 线性极坐标
- cv2.logPolar - 对数极坐标
- cv2.convertMaps - 转换映射表
- cv2.getAffineTransform - 3点仿射
- cv2.convertTo - 类型转换

**滤波增强:**
- cv2.sepFilter2D - 可分离滤波
- cv2.spatialGradient - 空间梯度
- cv2.sqrBoxFilter - 平方框滤波
- cv2.GaussianBlur变体
- cv2.stackBlur - 堆叠模糊

**形态学:**
- cv2.morphologyDefaultBorderValue - 默认边框值

**直方图:**
- cv2.calcBackProject - 反向投影
- cv2.EMD - Earth Mover距离

**轮廓:**
- cv2.convexityDefects - 凸缺陷
- cv2.minEnclosingTriangle - 最小外接三角
- cv2.rotatedRectangleIntersection - 旋转矩形交集

**图像修复:**
- cv2.inpaint - 图像修复
- cv2.fastNlMeansDenoising - 非局部均值去噪
- cv2.fastNlMeansDenoisingColored - 彩色去噪
- cv2.detailEnhance - 细节增强
- cv2.pencilSketch - 素描效果
- cv2.stylization - 风格化
- cv2.edgePreservingFilter - 边缘保持滤波
- cv2.decolor - 去色

**图像金字塔:**
- cv2.buildPyramid - 构建金字塔
- cv2.pyrMeanShiftFiltering - 均值漂移滤波

**连通组件:**
- cv2.connectedComponents - 连通组件
- cv2.connectedComponentsWithStats - 带统计的连通组件

**其他:**
- cv2.moments - 图像矩
- cv2.HuMoments - Hu不变矩
- cv2.floodFill - 洪水填充
- cv2.integral - 积分图
- cv2.integral3 - 三通道积分图
- cv2.rotate (更多选项)
- cv2.getGaussianKernel - 高斯核
- cv2.getDerivKernels - 导数核
- cv2.getGaborKernel - Gabor核

### core模块需新增 (~30个) → 放入imgproc或新建core.html
- cv2.split, cv2.merge (已在)
- cv2.add, subtract, multiply, divide (已在)
- cv2.addWeighted (已在)
- cv2.absdiff (已在)
- cv2.bitwise_and/or/xor/not (已在)
- cv2.sqrt, cv2.pow, cv2.exp, cv2.log
- cv2.magnitude, cv2.phase
- cv2.polarToCart, cv2.cartToPolar
- cv2.compare
- cv2.min, cv2.max
- cv2.sum, cv2.mean, cv2.meanStdDev (已在)
- cv2.countNonZero (已在)
- cv2.normalize (已在)
- cv2.LUT (已在)
- cv2.PSNR (已在)
- cv2.getRotationMatrix2D (已在)
- cv2.getPerspectiveTransform (已在)
- cv2.getAffineTransform (已在)
- cv2.invertAffineTransform (已在)
- cv2.convertTo
- cv2.reshape
- cv2.copyTo
- cv2.setRNGSeed
- cv2.RNG
- cv2.getNumThreads, cv2.setNumThreads
- cv2.format
- cv2.borderInterpolate
- cv2.patchNaNs

### highgui模块需新增 (~10个) → 放入新建highgui.html
- cv2.imshow
- cv2.waitKey
- cv2.waitKeyEx
- cv2.namedWindow
- cv2.destroyWindow
- cv2.destroyAllWindows
- cv2.moveWindow
- cv2.resizeWindow
- cv2.createTrackbar
- cv2.getTrackbarPos
- cv2.setMouseCallback
- cv2.selectROI
- cv2.selectROIs

### video模块需新增 (~10个)
- cv2.VideoCapture属性完整列表
- cv2.VideoWriter属性
- cv2.getBackendName
- cv2.getBackends

### calib3d模块需新增 (~15个)
- cv2.findHomography
- cv2.estimateAffine2D
- cv2.estimateAffinePartial2D
- cv2.decomposeHomographyMat
- cv2.solvePnP变体 (SOLVEPNP_IPPE等)
- cv2.solveP3P
- cv2.solvePxP
- cv2.calibrateCameraExtended
- cv2.stereoCalibrateExtended

### photo模块需新增 (~15个) → 放入新建photo.html
- cv2.inpaint
- cv2.fastNlMeansDenoising
- cv2.fastNlMeansDenoisingColored
- cv2.fastNlMeansDenoisingColoredMulti
- cv2.fastNlMeansDenoisingMulti
- cv2.detailEnhance
- cv2.pencilSketch
- cv2.stylization
- cv2.edgePreservingFilter
- cv2.decolor
- cv2.colorChange
- cv2.illuminationChange
- cv2.textureFlattening
- cv2.seamlessClone
- cv2.illuminationChange

## 实施步骤

### Step 1: 添加技术术语tooltip系统
- 更新style.css添加.term-tooltip样式
- 创建一个全局的术语tooltip JS函数
- 在各HTML文件的描述文本中为术语添加span

### Step 2: 增加imgproc.html API (~100个)
- 分批添加，每批20-30个
- 保持现有代码风格

### Step 3: 新建highgui.html (~15个API)
- imshow, waitKey, namedWindow等

### Step 4: 新建photo.html (~15个API)
- inpaint, denoising, enhancement等

### Step 5: 扩展calib3d, video, dnn, ml等模块

### Step 6: 最终验证
- 运行检查脚本
- 验证500+ API
- 验证tooltip工作正常

## 预计工作量
- Step 1: 1小时
- Step 2: 3小时 (最大工作量)
- Step 3: 30分钟
- Step 4: 30分钟
- Step 5: 1小时
- Step 6: 30分钟
- 总计: ~6.5小时
