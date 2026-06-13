# 网页版 Python 数据处理平台设计方案

## 一、整体架构概述

本平台是一个面向中文文本的数据分析 Web 应用，提供**分词统计**、**词云图制作**、**文本的情感分析**、**回归分析**及**可视化制作**等功能，采用前后端融合交互的简化架构。Flask 负责路由与业务逻辑，前端使用原生 JavaScript + Plotly.js 进行交互和可视化，核心数据处理封装在独立工具模块中。

**视觉设计**：基于 MongoDB 设计系统（DESIGN.md），使用深色 teal (#001e2b) Hero 区域、品牌绿 (#00ed64) CTA 药丸按钮、Euclid Circular A 字体（Lexend 替代）、统一的圆角和间距体系。

**数据流**：
1. 用户在网页表单中提交文本 / Excel / CSV 文件。
2. Flask 接收请求，调用相应工具模块（分词、情感分析、回归等）进行处理。
3. 工具模块返回处理结果（词频列表、情感分数、回归系数、图表数据等）。
4. Flask 将结果渲染到 HTML 模板，或通过 Ajax 返回 JSON 供前端动态绘图。
5. 用户看到结果（表格、图片、交互图表）。

**架构示意图**：
```
用户浏览器 <-> Flask (路由+视图) <-> Utils (分词/情感/回归/词云)
                |
                +--> templates (HTML页面)
                +--> static (JS/CSS/images)
                +--> uploads (临时文件)
```

---

## 二、技术栈

### 后端
| 类别 | 库 | 用途 |
|------|----|------|
| Web 框架 | Flask | 处理 HTTP 请求、路由、模板渲染 |
| 中文分词 | jieba | 中文文本分词与关键词提取，支持自定义词典 |
| 英文分词 | nltk | 英文分词的支持 |
| 情感分析 | SnowNLP | 简单易用，中文情感倾向评分（0~1） |
| 词云生成 | wordcloud + matplotlib | 生成词云图片 |
| 回归分析 | scikit-learn | 线性回归建模、R²、MSE |
| 数据处理 | pandas + numpy | CSV/Excel 读取、数据清洗、数组计算 |
| Excel 读写 | openpyxl + xlrd | .xlsx 和 .xls 文件的读写 |
| 可视化（后端辅助） | matplotlib | 仅用于生成词云图片（Agg 后端） |
| 文件上传 | Flask 原生 `request.files` | 处理文件上传 |

### 前端
| 类别 | 库 | 用途 |
|------|----|------|
| UI 框架 | 基于 DESIGN.md (MongoDB 风格) | 颜色、字体、圆角、间距的完整设计令牌体系 |
| 图表渲染 | Plotly.js | 交互式词频柱状图、回归散点图+回归线 |
| 动态交互 | 原生 JavaScript | Ajax 请求、表单处理、Chart 更新、Tab 切换、折叠/展开 |
| 词云展示 | 后端生成 Base64 + `<img>` | 由 Python wordcloud 生成，前端直接展示 |
| 字体 | Lexend (Google Fonts) + Source Code Pro | 替代 Euclid Circular A 的几何无衬线字体 |

### 其他工具
- **matplotlib 后端**：设置为 `Agg`，避免在无桌面环境报错。
- **临时文件管理**：`tempfile` 模块处理用户上传的文件，用完即删。
- **日志**：Python `logging` 输出到控制台和 `logs/app.log`。

---

## 三、项目目录结构

```
DataAnalyticsToolkit/
│
├── app.py                      # Flask 应用入口，注册路由 + API 端点
├── config.py                   # 配置项（上传目录、允许后缀、日志等）
├── requirements.txt            # 依赖列表
├── .gitignore                  # Git 忽略规则
│
├── templates/                  # HTML 模板（Jinja2）
│   ├── base.html               # 基础模板（深色毛玻璃导航栏、页脚）
│   ├── index.html              # 首页（Hero Banner + 四功能卡片 + CTA）
│   ├── segmentation.html       # 分词统计页面（Tab 切换、面板手风琴）
│   ├── wordcloud.html          # 词云生成页面
│   ├── sentiment.html          # 情感分析页面
│   └── regression.html         # 回归分析页面（CSV/手动 Tab 切换）
│
├── static/                     # 静态资源
│   ├── css/
│   │   └── style.css           # 自定义样式（MongoDB 设计系统）
│   ├── js/
│   │   ├── segmentation.js     # 分词页交互（Text/Table Tab、预览、折叠、导出）
│   │   ├── regression.js       # 回归页绘图逻辑（Plotly 散点+回归线）
│   │   └── common.js           # 公共函数（HTML 转义、CSV 解析、文件读取）
│   └── images/
│       └── banner_background.png # Banner 背景图
│
├── utils/                      # 核心处理模块（所有业务逻辑）
│   ├── __init__.py
│   ├── segmentation.py         # 分词 + 词频统计（支持自定义停用词/词典）
│   ├── wordcloud_gen.py        # 生成词云图片，返回 Base64 字符串
│   ├── sentiment_analysis.py   # 情感分析，逐句评分+整体统计
│   ├── regression.py           # 线性回归（CSV/JSON/手动输入）
│   └── stopwords.txt           # 停用词表（含约 2300 个中英文停用词）
│
├── uploads/                    # 临时上传文件夹（git ignored）
│   └── .gitkeep
│
├── logs/                       # 日志文件夹
│   └── app.log
│
└── venv/                       # Python 虚拟环境（git ignored）
```

---

## 四、页面路由

| 路由 | 页面 | 说明 |
|------|------|------|
| `/` | index.html | 首页：Hero Banner + 四大功能导航卡片 + CTA |
| `/segmentation` | segmentation.html | 分词统计：文本输入 / 表格文件上传 |
| `/wordcloud` | wordcloud.html | 词云制作：粘贴文本即可生成 |
| `/sentiment` | sentiment.html | 情感分析：文本逐句评分 + 整体倾向 |
| `/regression` | regression.html | 回归分析：CSV 上传 / 手动输入数据 |

---

## 五、API 端点

### 分词统计
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/segmentation` | POST | 文本分词（JSON：text, top_n, remove_stopwords, extra_stopwords, extra_dict） |
| `/api/segmentation/preview` | POST | 表格文件预览（FormData：file）→ 返回列名 + 前 20 行 |
| `/api/segmentation/file` | POST | 表格列分词（FormData：file, column, top_n, remove_stopwords, extra_stopwords, extra_dict） |
| `/api/segmentation/export` | POST | 导出全部词频为 Excel（JSON，忽略 top_n 返回全部） |
| `/api/segmentation/file/export` | POST | 表格列导出全部词频为 Excel（FormData） |

### 词云制作
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/wordcloud` | POST | 生成词云（FormData：text, max_words, colormap, bg_color）→ Base64 图片 |

### 情感分析
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/sentiment` | POST | 情感分析（JSON：text）→ 得分、标签、逐句详情 |

### 回归分析
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/regression` | POST | CSV 回归分析（FormData：file, x_column, y_column） |
| `/api/regression/manual` | POST | 手动数据回归分析（JSON：data[{x,y}...]） |

---

## 六、Utils 模块接口

### segmentation.py
```python
def segment_text(
    text: str,
    top_n: int = 50,
    remove_stopwords: bool = True,
    extra_stopwords: set[str] | None = None,
    extra_dict: list[str] | None = None,
) -> Dict[str, int]
```
- `extra_stopwords`：运行时追加的停用词集合，与内置停用词合并过滤。
- `extra_dict`：自定义词典词条列表，分词前调用 `jieba.add_word()` 将每个词注册为整体。
- 返回按频次降序排列的 `{词语: 频次}` 字典。

### wordcloud_gen.py
```python
def generate_wordcloud(
    text: str | None = None,
    freq_dict: Dict[str, int] | None = None,
    width: int = 800, height: int = 500,
    background_color: str = "#ffffff",
    colormap: str = "viridis",
    max_words: int = 200,
    font_path: str | None = None,
) -> str  # Base64 编码的 PNG
```
- 自动检测系统中文字体（WQY、Noto Sans CJK、PingFang、微软雅黑等）。

### sentiment_analysis.py
```python
def analyze_sentiment(text: str) -> Dict
```
- 返回整体得分、标签（积极/中性/消极）、积极/消极/中性占比、逐句详情。
- 阈值：>0.6 积极，<0.4 消极，中间为中性。

### regression.py
```python
def linear_regression(x, y, x_label, y_label) -> Dict
def linear_regression_from_csv(filepath, x_column, y_column) -> Dict
def linear_regression_from_json(data, x_key, y_key) -> Dict
```
- 返回：coefficients, intercept, slope, r_squared, mse, equation, x_values, y_true, y_pred。

---

## 七、分词统计模块详细设计

分词统计页面是最复杂的功能模块，支持两种输入模式（Tab 切换）：

### 文本数据 Tab
- 文本输入区（textarea）+ 可选 `.txt` 文件上传（自动读取到 textarea）
- "显示前 N 个高频词"输入框 + "过滤停用词"复选框
- **自定义停用词**面板（手风琴）：手动输入（每行一个词）或上传 `.txt` 文件
- **自定义词典**面板（手风琴）：手动输入或上传文件，词条被 jieba 视为整体
- 自定义停用词和自定义词典面板**互斥展开**（手风琴行为）
- 点击"开始分词"→ Ajax 提交 → 展示结果

### 表格文件 Tab
- 文件上传（.xls / .xlsx / .csv）→ **自动解析并预览**（前 20 行）
- **点击表头选择列**：表头可点击，选中后整列高亮显示（绿色背景）
- 已选列名称实时显示在徽章中
- 同样支持自定义停用词和自定义词典面板
- 点击"对该列分词"→ 合并该列所有行文本后分词

### 结果展示（共享）
- **统计栏**：来源列/数据行数、去重词数、总词频
- **词频表**：默认显示前 20 条，超过 20 条出现"展开全部 N 条"按钮
- **导出全部词频**：按钮在词频表卡片右上角，生成包含所有词频的 Excel 文件（排名按频次降序）
- **高频词柱状图**：Plotly 交互式图表，绿色柱体

---

## 八、前端交互特性

- **导航栏**：深色毛玻璃效果（backdrop-filter: blur），sticky 吸顶
- **Hero/Banner**：深色 teal 底色叠加 banner_background.png 背景图
- **Tab 切换**：文本数据 / 表格文件，切换时自动隐藏表格预览面板
- **手风琴面板**：自定义停用词和自定义词典只能同时展开一个
- **文件输入**：自定义 `::file-selector-button` 药丸风格按钮
- **自定义复选框**：品牌绿底色 + 白色对勾（clip-path），含 hover 和 focus 状态
- **表格列选择**：点击表头选中整列，表头变绿、整列单元格变浅绿
- **折叠表格**：词频表 >20 行时默认折叠，可展开全部
- **Plotly 柱状图**：响应式，绿色柱体，词频数值标注

---

## 九、部署与运行

### 依赖安装
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 启动
```bash
source venv/bin/activate
python app.py
# 访问 http://127.0.0.1:5000
```

### requirements.txt
```
flask>=3.0, jieba>=0.42, nltk>=3.8, snownlp>=0.12, wordcloud>=1.9,
matplotlib>=3.8, pandas>=2.1, numpy>=1.26, scikit-learn>=1.3,
statsmodels>=0.14, plotly>=5.18, openpyxl>=3.1, xlrd>=2.0
```

### 配置项（config.py）
- `UPLOAD_FOLDER`: uploads/
- `MAX_CONTENT_LENGTH`: 16 MB
- `ALLOWED_EXTENSIONS`: csv, xlsx, xls, txt
- `MPL_BACKEND`: Agg（无 GUI）
- `STOPWORDS_FILE`: utils/stopwords.txt
