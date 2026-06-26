# ImageTools

**版本**: 0.1.0

基于节点的可视化图像处理工具，使用 Python/PySide6/OpenCV/NodeGraphQt 构建。

## 功能特性

- 节点化图像处理流程
- 可视化蓝图编辑器
- 插件化架构，易于扩展
- 支持多种图像格式（PNG/JPG/BMP/TIFF）
- 实时执行状态显示
- 输入/输出图像集查看

## 系统架构

### 四层架构

```
┌─────────────────────────────────────────────────────┐
│  UI Layer (ui/)                                      │
│  PySide6/Qt6 widgets: MainWindow, NodeGraphWidget,  │
│  NodeSelectorWindow, ImageViewerWidget               │
├─────────────────────────────────────────────────────┤
│  Engine Layer (core/engine/)                         │
│  ExecutionEngine + ExecutionWorker (QThread)         │
│  Topological sort, node execution, data propagation  │
├─────────────────────────────────────────────────────┤
│  Node Framework (core/node_base/ + core/plugin/)     │
│  NodeBase, NodeMeta, Port, PortDefinition,           │
│  NodeRegistry, PluginScanner                         │
├─────────────────────────────────────────────────────┤
│  Infrastructure (core/config/, core/logger.py,       │
│  core/interfaces.py)                                 │
│  ConfigLoader (YAML/JSON), RotatingFileHandler       │
│  logger, abstract interfaces                         │
└─────────────────────────────────────────────────────┘
```

### 目录结构

```
imageTools/
├── main.py                      # 应用入口
├── requirements.txt             # 依赖列表
├── config/                      # 配置文件
│   ├── app.yaml                 # 主配置
│   └── ui/
│       └── custom.css           # 自定义样式
├── core/                        # 核心框架
│   ├── interfaces.py            # 抽象接口
│   ├── logger.py                # 日志系统
│   ├── config/                  # 配置加载器
│   ├── node_base/               # 节点基类
│   ├── engine/                  # 执行引擎
│   └── plugin/                  # 插件扫描器
├── ui/                          # UI组件
│   ├── main_window.py           # 主窗口
│   ├── node_graph_widget.py     # 节点图组件
│   ├── node_selector.py         # 节点选择器
│   └── image_viewer.py          # 图像查看器
├── nodes/                       # 节点插件
│   ├── image_source/            # 图像源节点
│   └── detection/               # 检测节点
└── systems/                     # 系统组件（预留）
```

## 安装指南

### 环境要求

- Python 3.8+
- Conda 环境（推荐）

### 安装步骤

1. 克隆项目
```bash
git clone <repository-url>
cd imageTools
```

2. 创建 Conda 环境
```bash
conda create -n claude-imagetool python=3.10
conda activate claude-imagetool
```

3. 安装依赖
```bash
pip install -r requirements.txt
pip install qt-material
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
| qt-material | - | Material Design 主题 |

## 使用说明

### 启动应用

```bash
python main.py
```

### 创建节点

1. **右键菜单创建**：在画布空白处右键，选择节点类型
2. **双击创建**：双击空白节点，弹出节点选择窗口
3. **节点参数**：创建节点后自动弹出参数编辑窗口

### 连接节点

- 拖拽节点端口创建连接
- 支持多输入/多输出连接
- 支持管道交叉

### 执行处理

1. 点击工具栏 "▶ 开始" 按钮
2. 或菜单 "运行" -> "开始执行"
3. 节点状态颜色变化：灰色（待执行）→ 黄色（执行中）→ 绿色（成功）/ 红色（失败）

### 查看结果

- 右侧面板显示输入/输出图像集
- 使用下拉框切换查看输入/输出
- 点击缩略图按钮切换图像

## 节点系统

### 内置节点

#### 图像源

| 节点ID | 名称 | 说明 |
|---|---|---|
| `image_source/input_image_set` | 输入图像集 | 从文件/文件夹加载图像 |
| `image_source/camera` | 相机源 | 相机捕获（预留） |

#### 检测 > 形状检测

| 节点ID | 名称 | 说明 |
|---|---|---|
| `detection/shape_detection/polygon` | 多边形检测 | 基于轮廓的多边形检测 |
| `detection/shape_detection/circle` | 圆检测 | 基于霍夫变换的圆检测 |

### 节点参数类型

| 类型 | 说明 | UI控件 |
|---|---|---|
| `combo` | 下拉选择 | QComboBox |
| `int_slider` | 整数滑块 | QSlider + QSpinBox |
| `float_slider` | 浮点滑块 | QSlider + QDoubleSpinBox |
| `text` | 文本输入 | QLineEdit |
| `checkbox` | 复选框 | QCheckBox |
| `file_list` | 文件列表 | 自定义文件选择器 |

### 创建自定义节点

1. 在 `nodes/` 目录下创建文件夹结构：
```
nodes/
  <category>/
    <subcategory>/      # 可选
      <node_name>/
        meta.json       # 节点定义
        node.py         # 节点实现
```

2. 编写 `meta.json`：
```json
{
  "id": "category/node_name",
  "name": "节点名称",
  "category": "分类",
  "subcategory": "子分类",
  "description": "节点描述",
  "inputs": [
    {"name": "images", "type": "image", "label": "图像"}
  ],
  "outputs": [
    {"name": "images", "type": "image", "label": "图像"}
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

3. 编写 `node.py`：
```python
from core.node_base import NodeBase, NodeState

class MyNode(NodeBase):
    def execute(self) -> bool:
        try:
            # 获取参数
            param1 = self.params.get("param1", 100)
            
            # 获取输入图像
            images = self._get_input_images("images")
            
            # 处理图像
            results = []
            for img in images:
                # 图像处理逻辑
                processed = img.copy()
                results.append(processed)
            
            # 设置输出
            self._set_output_images("images", results)
            return True
        except Exception as e:
            self._set_error(str(e))
            return False
```

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

engine:
  max_workers: 4
  timeout_seconds: 300

ui:
  window_title: "ImageTools - 图像处理工具"
  window_width: 1600
  window_height: 900
  left_panel_ratio: 0.55
  right_panel_ratio: 0.45
  theme: "dark_teal.xml"
  extra:
    font_family: "Segoe UI"
    font_size: "10px"
    density_scale: "0"
```

### custom.css

自定义 Qt 样式表，覆盖默认主题样式。支持 `{QTMATERIAL_*}` 模板变量。

## 开发指南

### 项目结构

- `core/`: 核心框架，包含节点基类、执行引擎、配置加载器
- `ui/`: UI 组件，使用 PySide6 构建
- `nodes/`: 节点插件，自动扫描加载
- `config/`: 配置文件
- `systems/`: 系统组件（预留）

### 添加新节点

1. 在 `nodes/` 下创建目录和文件
2. 编写 `meta.json` 定义节点元数据
3. 编写 `node.py` 实现节点逻辑
4. 重启应用，节点自动注册

### 扩展 UI

- 修改 `config/ui/custom.css` 自定义样式
- 修改 `config/app.yaml` 调整配置
- 在 `ui/` 目录下添加新组件

### 调试

- 查看 `logs/app.log` 日志文件
- 日志级别：DEBUG/INFO/WARNING/ERROR
- 日志文件自动轮转（5MB，保留3个备份）

## 计划功能

### ROI系统（Region of Interest）
- 区域选择和标记
- ROI 区域内的图像处理
- ROI 数据传递给下游节点

### 测量工具
- 距离测量
- 角度测量
- 面积计算
- 标尺和单位系统

### 相机支持
- 实时相机捕获（已预留 CameraSourceNode）
- 相机参数配置
- 多相机支持

### 标定功能
- 相机标定
- 图像畸变校正
- 坐标系转换

### 数学/逻辑系统
- 图像算术运算
- 逻辑运算节点
- 数学函数节点

### 视频支持
- 视频文件读取
- 视频流处理
- 帧提取和处理

### 蓝图导入/导出
- 保存节点图配置
- 加载已有配置
- 配置文件格式

### 其他计划功能
- 预览系统（已预留 PreviewProvider 接口）
- 保存/加载功能（已预留 SaveLoadProvider 接口）
- 插件系统扩展（已预留 PluginBase 接口）

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request。
