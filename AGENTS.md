# 网页版 Python 数据处理平台设计方案

## 一、整体架构概述

本平台是一个面向中文文本的数据分析 Web 应用，提供**分词统计**、**词云图制作**、**文本的情感分析**、**回归分析**及**可视化制作**等功能，由于仅单用户本地使用，采用 前后端不分离但融合交互 的简化架构。Flask 负责路由与业务逻辑，前端进行交互和可视化，核心数据处理封装在独立工具模块中。
根据你的需求，我将设计一个基于 **Flask** 的轻量级数据处理平台，专为单用户本地运行优化。以下从整体架构、技术栈、项目目录三个维度给出详细方案。

**数据流**：
1. 用户在网页表单中提交文本 / Excel 文件。
2. Flask 接收请求，调用相应工具模块（分词、情感分析、回归等）进行处理。
3. 工具模块返回处理结果（词频列表、情感分数、回归系数、图表数据等）。
4. Flask 将结果渲染到 HTML 模板，或通过 Ajax 返回 JSON 供前端动态绘图。
5. 用户看到结果（表格、图片、交互图表）。

**架构示意图**：
```
用户浏览器 <-> Flask (路由+视图) <-> Utils (分词/情感/回归/词云)
                |
                +--> templates (HTML页面)
                +--> static (JS/CSS)
                +--> uploads (临时文件)
```

---

## 二、技术栈

### 后端
| 类别 | 库 | 用途 |
|------|----|------|
| Web 框架 | Flask | 处理 HTTP 请求、路由、模板渲染 |
| 中文分词 | jieba | 中文文本分词与关键词提取 |
| 英文分词 | nltk | 英文分词的支持 |
| 情感分析 | SnowNLP | 简单易用，中文情感倾向评分 |
| 词云生成 | wordcloud + matplotlib | 生成词云图片 |
| 回归分析 | scikit-learn + statsmodels | 线性回归建模、统计摘要 |
| 数据处理 | pandas + numpy | CSV 读取、数据清洗、数组计算 |
| 可视化（后端辅助） | matplotlib | 仅用于生成词云图片（无 GUI 后端） |
| 文件上传 | Flask 原生 `request.files` | 处理 Excel 上传 |

### 前端
| 类别 | 库 | 用途 |
|------|----|------|
| UI 框架 | 工程中的 DESIGN.md | 美观简洁的网站设计 |
| 图表渲染 | Plotly.js | 交互式回归散点图、词频柱状图 |
| 动态交互 | 原生 JavaScript (或 Vue 3) | 处理 Ajax 请求、更新图表 |
| 词云展示 | 后端生成图片 + `<img>` | 简单可靠 |

> 为什么不完全用前端做图？<br>
> 词云生成依赖 Python 的 `wordcloud` 库，无法在前端完成；回归图使用 Plotly.js 可完全前端绘制（只需后端传输 X/Y 数据），减轻后端压力。

### 其他工具
- **matplotlib 后端**：设置为 `Agg`，避免在无桌面环境报错。
- **临时文件管理**：`tempfile` 模块处理用户上传的 CSV，用完即删。
- **日志**：使用 Python `logging` 记录关键操作（便于调试）。

---

## 三、项目目录结构

```
DataAnalyticsToolkit/
│
├── app.py                      # Flask 应用入口，注册路由
├── config.py                   # 配置项（如上传目录、允许后缀等）
├── requirements.txt            # 依赖列表
│
├── templates/                  # HTML 模板
│   ├── base.html               # 基础模板（导航栏、公共样式）
│   ├── index.html              # 首页（功能导航卡片）
│   ├── segmentation.html       # 分词统计页面
│   ├── wordcloud.html          # 词云生成页面
│   ├── sentiment.html          # 情感分析页面
│   └── regression.html         # 回归分析页面
│
├── static/                     # 静态资源
│   ├── css/
│   │   └── style.css           # 自定义样式
│   ├── js/
│   │   ├── segmentation.js     # 分词页面的交互（Ajax 请求，Plotly 柱状图）
│   │   ├── regression.js       # 回归页面的绘图逻辑（Plotly）
│   │   └── common.js           # 公共函数（如文件预览）
│   └── images/                 # 占位图片或图标
│
├── utils/                      # 核心处理模块（所有业务逻辑）
│   ├── __init__.py
│   ├── segmentation.py         # 分词 + 词频统计，返回 Counter 对象
│   ├── wordcloud_gen.py        # 生成词云图片，返回图片的 base64 或保存路径
│   ├── sentiment_analysis.py   # 情感分析，返回得分和极性
│   └── regression.py           # 线性回归分析，返回系数、R²、预测值、绘图数据
│
├── uploads/                    # 临时上传文件夹（git ignored）
│   └── .gitkeep
│
├── logs/                       # 日志文件夹（可选）
│   └── app.log
│
└── run.py                      # 启动脚本（方便设置环境变量，可选）
```

### 目录说明

- **`app.py`**：创建 Flask 实例，注册蓝图（若需要）或直接定义路由。每个路由对应一个功能页面（如 `/segmentation`）及处理表单提交的接口（如 `/api/segmentation`）。
- **`utils/segmentation.py`**：提供 `segment_text(text)` 函数，返回 `{word: freq, ...}` 及用于绘图的词频列表（前 20 个）。
- **`utils/wordcloud_gen.py`**：接收文本或词频字典，生成词云并返回图片的 Base64 字符串（便于直接嵌入 HTML），或保存到 static 临时文件并返回 URL。
- **`utils/sentiment_analysis.py`**：调用 SnowNLP 返回情感分数（0~1，>0.5 为积极）。
- **`utils/regression.py`**：读取 CSV 或接收 JSON 数据，使用 sklearn 做线性回归，返回：
  ```python
  {
      'coefficients': [b0, b1],
      'r_squared': 0.95,
      'x_values': [...],
      'y_true': [...],
      'y_pred': [...]
  }
  ```
- **`templates/`**：每个页面通过表单或 Ajax 与后端交互。为了用户体验，分词和回归页面建议使用 Ajax 无刷新更新图表（因为 Plotly 需要前端重建），词云和情感分析可直接刷新页面或 Ajax 替换图片区域。
- **`static/js/regression.js`**：监听表单提交（或文件上传），发送文件/数据到 `/api/regression`，获取 JSON 后调用 Plotly.newPlot() 绘制散点图和回归线。
- **`uploads/`**：存放用户上传的 CSV 文件（处理后立即删除或定期清理）。

---

## 四、关键设计细节

### 1. 分词统计模块
- 支持中英文混合文本（jieba 对英文按空格分割即可）。
- 去除停用词（提供一个 `stopwords.txt` 文件，用户可自定义）。
- 结果展示：高频词表格 + 柱状图（Plotly 绘制）。
- 前端实现无刷新：用户粘贴文本 -> Ajax 发送到后端 -> 返回 JSON 词频 -> 前端渲染表格和柱状图。

### 2. 词云制作模块
- 可复用分词模块的切词结果，也可单独处理新文本。
- 生成词云时支持自定义形状、颜色、背景色（简单版可先不做高级配置）。
- 由于词云图片由 Python 生成，后端返回图片 URL（保存到 static/temp/ 下）或 Base64 直接展示。
- 注意清理临时图片：可使用 Flask 的 `after_this_request` 钩子删除。

### 3. 情感分析模块
- 使用 SnowNLP（轻量）或调用百度 API（需联网，不推荐本场景）。
- 可对长文本按句子拆分，返回整体情感倾向分布（积极/消极占比）。
- 结果展示：情感得分进度条 + 积极/消极标签 + 可选饼图（前端 Chart.js 即可）。

### 4. 回归分析及可视化
- 支持 CSV 上传（两列：X, Y）或手动输入 X,Y 列表。
- 后端计算线性回归模型（必要时支持多项式回归的简单选项）。
- 返回数据后前端绘制散点图+回归线，并显示方程、R²。
- 另外可提供残差图（可选）。

### 5. 部署与运行
- 所有依赖写入 `requirements.txt`：`flask, jieba, snownlp, wordcloud, matplotlib, pandas, numpy, scikit-learn, plotly`
- 启动命令：`python app.py`，默认监听 `http://127.0.0.1:5000`
- 注意设置环境变量 `FLASK_ENV=development` 以启用调试模式。
