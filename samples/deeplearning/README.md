# ImageTools

**版本**: 0.1.0

基于节点的可视化图像处理工具，使用 Python/PySide6/OpenCV/NodeGraphQt 构建。

## 功能特性

- 节点化图像处理流程
- 可视化蓝图编辑器（NodeGraphQt）
- 插件化架构，自动扫描加载节点
- 支持多种图像格式（PNG/JPG/BMP/TIFF）
- 实时执行状态显示
- 输入/输出图像集查看
- ROI（感兴趣区域）系统
- 标尺测量工具
- 像素信息显示

## 系统架构

### 五层架构

```
┌─────────────────────────────────────────────────────┐
│  UI Layer (ui/)                                      │
│  MainWindow, NodeGraphWidget, NodeSelectorWindow,   │
│  ImageViewerWidget, 参数编辑器                        │
├─────────────────────────────────────────────────────┤
│  Systems Layer (systems/)                            │
│  BlueprintSystem, ImageDisplaySystem,                │
│  ExecutionEngine, RulerSystem, ImageInfoSystem       │
├─────────────────────────────────────────────────────┤
│  Node Framework (core/node_base/ + core/plugin/)     │
│  NodeBase, NodeMeta, Port, PortDefinition,           │
│  NodeRegistry, PluginScanner                         │
├─────────────────────────────────────────────────────┤
│  Core Infrastructure (core/)                         │
│  Config, Logger, Events, ImageData, ROI, Pipeline    │
├─────────────────────────────────────────────────────┤
│  Node Plugins (nodes/)                               │
│  图像源、检测、处理等节点插件                          │
└─────────────────────────────────────────────────────┘
```

### 目录结构

```
imageTool-blueprint/
├── main.py                      # 应用入口
├── requirements.txt             # 依赖列表
├── config/                      # 配置文件
│   ├── app.yaml                 # 主配置
│   ├── nodes.yaml               # 节点树配置
│   └── ui/
│       └── custom.css           # 自定义样式
├── core/                        # 核心框架
│   ├── config/                  # 配置加载器
│   ├── engine/                  # 执行引擎（Qt兼容层）
│   ├── events.py                # 事件系统
│   ├── image_data.py            # 图像数据模型
│   ├── interfaces.py            # 抽象接口
│   ├── logger.py                # 日志系统
│   ├── node_base/               # 节点基类
│   │   ├── node.py              # NodeBase, NodeMeta
│   │   ├── port.py              # Port, PortDefinition
│   │   └── registry.py          # NodeRegistry
│   ├── pipeline.py              # PipelineNodeInfo
│   ├── plugin/                  # 插件扫描器
│   ├── roi/                     # ROI 数据模型
│   └── system/                  # 系统管理器
├── systems/                     # 系统组件
│   ├── blueprint/               # 蓝图系统
│   ├── execution/               # 执行系统（纯Python）
│   └── image_display/           # 图像显示系统
├── ui/                          # UI组件
│   ├── main_window.py           # 主窗口
│   ├── node_graph_widget.py     # 节点图组件
│   ├── node_selector.py         # 节点选择器
│   ├── image_viewer.py          # 图像查看器
│   ├── execution_controller.py  # 执行控制器
│   ├── param_widgets/           # 参数控件
│   └── widgets/                 # 通用控件
├── nodes/                       # 节点插件
│   ├── image_source/            # 图像源节点
│   ├── detection/               # 检测节点
│   └── processing/              # 处理节点
└── logs/                        # 日志目录
```

## 安装指南

### 环境要求

- Python 3.10+
- Conda 环境（推荐）

### 安装步骤

1. 克隆项目
```bash
git clone <repository-url>
cd imageTool-blueprint
```

2. 创建 Conda 环境
```bash
conda create -n claude-vision python=3.10
conda activate claude-vision
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

### 依赖列表

| 包名 | 版本 | 用途 |
|---|---|---|
| PySide6 | >= 6.5.0 | Qt6 GUI 框架 |
| opencv-python | >= 4.8.0 | 图像处理 |
| NodeGraphQt | >= 0.6.0 | 可视化节点图 |
| numpy | >= 1.24.0 | 数组操作 |
| Pillow | >= 10.0.0 | 图像 I/O |
| PyYAML | >= 6.0 | YAML 配置解析 |
| Shapely | >= 2.0.0 | 几何计算（ROI） |
| ultralytics | >= 8.0.0 | YOLO 目标检测 |
| qt-material | - | Material Design 主题 |

## 使用说明

### 启动应用

```bash
python main.py
```

### 创建节点

1. **右键菜单创建**：在画布空白处右键，选择节点类型
2. **节点参数**：创建节点后自动弹出参数编辑窗口

### 连接节点

- 拖拽节点端口创建连接
- 支持多输入/多输出连接
- 支持管道交叉和切片

### 执行处理

1. 点击工具栏 "▶ 开始" 按钮
2. 或菜单 "运行" -> "开始执行"
3. 节点状态颜色变化：灰色（待执行）→ 黄色（执行中）→ 绿色（成功）/ 红色（失败）

### 查看结果

- 右侧面板显示输入/输出图像集
- 使用下拉框切换"输入显示"/"输出显示"
- 点击缩略图按钮切换图像
- 支持鼠标滚轮缩放、中键拖拽平移

## 节点系统

### 内置节点

#### 图像源

| 节点ID | 名称 | 说明 |
|---|---|---|
| `image_source/input_image_set` | 图集 | 从文件加载图像 |
| `image_source/camera` | 相机源 | 相机捕获 |

#### 检测

| 节点ID | 名称 | 说明 |
|---|---|---|
| `detection/shape_detection/circle` | 圆形检测 | 霍夫圆变换 |
| `detection/shape_detection/polygon` | 多边形检测 | 轮廓近似 |
| `detection/yolo/yolo_detect` | YOLO检测 | YOLOv8+ 目标检测 |

#### 处理

| 节点ID | 名称 | 说明 |
|---|---|---|
| `processing/color_conversion/color_filter` | 颜色过滤 | 通道值范围过滤 |
| `processing/color_conversion/convert` | 颜色转化 | 颜色空间转换 |
| `processing/image_operations/morphology` | 形态学操作 | 腐蚀、膨胀、开闭运算 |
| `processing/image_operations/mask_operations` | 掩码操作 | AND/OR/XOR/NOT 逻辑运算 |

### 节点参数类型

| 类型 | 说明 | UI控件 |
|---|---|---|
| `combo` | 下拉选择 | QComboBox |
| `int_slider` | 整数滑块 | QSlider + QSpinBox |
| `float_slider` | 浮点滑块 | QSlider + QDoubleSpinBox |
| `text` | 文本输入 | QLineEdit |
| `checkbox` | 复选框 | QCheckBox |
| `file_list` | 文件列表 | 自定义文件选择器 |
| `channel_range` | 通道范围 | 双滑块 |

### 创建自定义节点

#### 方式一：meta.json + node.py（推荐）

在 `nodes/` 目录下创建文件夹结构：

```
nodes/
  <category>/
    <subcategory>/      # 可选
      <node_name>/
        meta.json       # 节点定义
        node.py         # 节点实现
```

**meta.json 示例**：

```json
{
  "id": "category/node_name",
  "name": "节点名称",
  "category": "分类",
  "subcategory": "子分类",
  "description": "节点描述",
  "inputs": [
    {"name": "images", "type": "image", "label": "图像输入"}
  ],
  "outputs": [
    {"name": "images", "type": "image", "label": "图像输出"}
  ],
  "optional_ports": [
    {"name": "roi", "label": "ROI 输入", "port_type": "roi", "direction": "input", "default": false, "group": "input"}
  ],
  "params": [
    {
      "name": "param1",
      "type": "int_slider",
      "label": "参数1",
      "default": 100,
      "min": 0,
      "max": 1000,
      "step": 1
    }
  ]
}
```

**node.py 示例**：

```python
from core.node_base.node import NodeBase, NodeState

class MyNode(NodeBase):
    NODE_ID = "category/node_name"
    NODE_NAME = "节点名称"

    def execute(self) -> bool:
        images = self._get_input_images("images")
        if not images:
            self.set_state(NodeState.ERROR)
            return False

        results = []
        for img in images:
            processed = img.copy()
            results.append(processed)

        self._set_output_images("images", results)
        self.set_state(NodeState.SUCCESS)
        return True
```

#### 方式二：纯类属性（无 meta.json）

```python
from core.node_base.node import NodeBase, NodeState

class MyNode(NodeBase):
    NODE_ID = "category/node_name"
    NODE_NAME = "节点名称"
    NODE_CATEGORY = "分类"
    NODE_INPUTS = [
        {"name": "images", "type": "image", "label": "图像输入"},
    ]
    NODE_OUTPUTS = [
        {"name": "images", "type": "image", "label": "图像输出"},
    ]
    NODE_PARAMS = [
        {"name": "param1", "type": "int_slider", "label": "参数1", "default": 100, "min": 0, "max": 1000, "step": 1},
    ]

    def execute(self) -> bool:
        # ...
```

**注意**：如果同时存在 meta.json 和类属性，以 meta.json 为准。

### 检测节点基类

检测节点继承 `DetectionBase`，只需实现两个方法：

```python
from nodes.detection.detection_base import DetectionBase

class MyDetectionNode(DetectionBase):
    NODE_ID = "detection/my_detection"

    def _get_detection_params(self) -> dict:
        return {"param1": self.params.get("param1", 100)}

    def _detect(self, img, color_space, **params):
        # 返回 (标注图像, ROI列表)
        annotated = img.copy()
        rois = []
        # ... 检测逻辑 ...
        return annotated, rois
```

`DetectionBase` 自动处理：
- 可选端口管理（ROI 输入、禁止区域、标注图像输出）
- 标注图像输出控制（通过 `_opt_annotated` 参数）
- ROI 输出
- 输入图像读取和类型转换

## 配置说明

### app.yaml

```yaml
app:
  name: "ImageTools"
  version: "0.1.0"

paths:
  nodes_dir: "nodes"
  config_dir: "config"
  logs_dir: "logs"

logging:
  level: "INFO"
  max_file_size_mb: 5
  backup_count: 3

ui:
  theme: "dark_teal.xml"
  extra:
    font_family: "Segoe UI"
    font_size: "13px"
    density_scale: "0"
```

## 开发指南

### 项目结构

- `core/`: 核心框架，包含节点基类、配置加载器、事件系统
- `systems/`: 系统组件，包含蓝图、执行、图像显示系统
- `ui/`: UI 组件，使用 PySide6 构建
- `nodes/`: 节点插件，自动扫描加载
- `config/`: 配置文件

### 添加新节点

1. 在 `nodes/` 下创建目录和文件
2. 编写 `meta.json` 定义节点元数据
3. 编写 `node.py` 实现节点逻辑
4. 重启应用，节点自动注册

### 调试

- 查看 `logs/` 目录下的日志文件
- 日志级别：DEBUG/INFO/WARNING/ERROR
- 日志文件按日期自动轮转

## 许可证

MIT License
