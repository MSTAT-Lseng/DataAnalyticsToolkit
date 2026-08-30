# DataAnalyticsToolkit

一个面向中文文本与表格数据的轻量级 Web 数据分析工作台。用户可以直接在浏览器中输入文本或上传 CSV / Excel 文件，完成数据清洗、分词统计、词云生成、情感分析、关系网络、回归、相关性热力图和文本聚类，并将结果导出为 Excel。

项目采用 Flask 应用工厂与 Blueprint 分模块路由，整个应用不依赖数据库，适合本地运行、课程实验和小规模数据分析。

## 功能概览

| 模块 | 能力 |
| --- | --- |
| 数据清洗 | 上传 CSV / XLS / XLSX；预览数据；按列删除空值、去重和过滤最小字数；导出清洗结果与统计信息 |
| 分词统计 | 支持文本和表格列；中英文分词；内置或自定义停用词；自定义词典；高频词图表；导出完整词频表 |
| 词云制作 | 根据文本或词频表生成词云；支持最大词数、配色方案和背景色设置 |
| 情感分析 | 使用 SnowNLP 分析文本情感；支持逐句分析、表格列批量分析、自定义情感词微调和 Excel 导出 |
| 社会网络关系图 | 根据文本或表格列统计词语共现；可导入分词统计导出的词频表作为分词规则；生成可交互关系图和关系明细 |
| 回归分析 | 从表格中选择至少两列 1 到 10 的数值列；按选择顺序执行所有两两一元线性回归；展示散点图、回归线、方程、R² 和 MSE |
| 热力分析 | 选择至少两列 1 到 10 的数值列；计算 Pearson 相关系数矩阵；使用 Plotly 绘制带数值标注的热力图 |
| 聚类分析 | 支持按句子或表格列聚类；使用 TF-IDF 提取文本特征和 K-Means 分组；展示聚类关键词、二维样本分布、中心距离和样本归属；支持导出 |

## 界面与数据流

- 中文工作台界面，提供统一的工具侧栏和响应式布局。
- 使用白色画布、黑色主操作、细灰色边线和胶囊形控件，页面风格保持简洁克制。
- 上传文件通过 Ajax / `FormData` 发送到 Flask API，服务器读取后在临时文件上下文中处理。
- 结果在浏览器中实时展示，词频、情感、清洗和聚类等结果支持 Excel 下载。
- 图表由 Plotly.js 在浏览器端渲染；基础模板从 Plotly CDN 加载脚本。

## 技术栈

- **后端**：Python、Flask、Blueprint、pandas、NumPy
- **文本处理**：jieba、NLTK、SnowNLP
- **机器学习**：scikit-learn，包括 Linear Regression、TF-IDF 和 K-Means
- **可视化**：Plotly.js、WordCloud、Matplotlib
- **文件处理**：openpyxl、xlrd，支持 CSV / XLS / XLSX
- **测试**：Python `unittest`

## 快速开始

建议使用 Python 3.10 或更高版本。

```bash
git clone https://github.com/MSTAT-Lseng/DataAnalyticsToolkit.git
cd DataAnalyticsToolkit

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python app.py
```

启动后访问：<http://127.0.0.1:5000>

Windows PowerShell 激活虚拟环境可以使用：

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

应用默认监听 `127.0.0.1:5000`，开发模式由 `app.py` 启动。生产环境请使用经过配置的 WSGI Server，并根据实际部署环境修改密钥、监听地址和日志配置。

## 使用流程

1. 打开首页，从左侧工具列表选择分析模块。
2. 根据模块要求输入文本，或上传 CSV / XLS / XLSX 文件。
3. 在预览结果中选择列并配置分析参数。
4. 点击分析按钮查看统计结果和图表。
5. 使用页面提供的导出按钮下载 Excel 或词频结果。

### 数据要求

- 表格文件需要包含第一行标题，单个文件大小默认不超过 16 MB。
- 回归和热力分析只接受标题下所有数据均为 1 到 10 的数值列，包含边界值并支持小数。
- 回归和热力分析至少需要选择两列。
- 聚类至少需要两条有效文本，聚类数量至少为 2 且不能超过有效样本数。
- 分词、词云、情感和聚类会使用 `utils/stopwords.txt` 中的内置停用词；部分模块支持额外停用词配置。
- 中文词云生成依赖系统中可用的中文字体。若部署环境没有中文字体，词云中的中文可能无法正常显示。

## 页面路由

| 路径 | 页面 |
| --- | --- |
| `/` | 数据分析工作台首页 |
| `/cleaning` | 数据清洗 |
| `/segmentation` | 分词统计 |
| `/wordcloud` | 词云制作 |
| `/sentiment` | 情感分析 |
| `/social-network` | 社会网络关系图 |
| `/regression` | 回归分析 |
| `/heat-analysis` | 热力分析 |
| `/clustering` | 聚类分析 |

## API 速览

所有接口均为 POST 请求，上传型接口使用 `multipart/form-data`。

| 模块 | 接口 |
| --- | --- |
| 清洗 | `/api/cleaning/preview`、`/api/cleaning/process`、`/api/cleaning/export` |
| 分词 | `/api/segmentation`、`/api/segmentation/preview`、`/api/segmentation/file`、`/api/segmentation/export`、`/api/segmentation/file/export` |
| 词云 | `/api/wordcloud`、`/api/wordcloud/preview-freq`、`/api/wordcloud/from-file` |
| 情感 | `/api/sentiment`、`/api/sentiment/preview`、`/api/sentiment/file`、`/api/sentiment/export` |
| 社会网络 | `/api/social-network/preview`、`/api/social-network/import-frequency`、`/api/social-network/prepare`、`/api/social-network/graph` |
| 回归 | `/api/regression/preview`、`/api/regression` |
| 热力 | `/api/heat-analysis/preview`、`/api/heat-analysis` |
| 聚类 | `/api/heat-analysis/clustering/preview`、`/api/heat-analysis/clustering`、`/api/heat-analysis/clustering/export` |

社会网络接口还保留 `/api/social-network` 和 `/api/social-network/analyze` 作为兼容入口。聚类 API 当前复用热力分析 Blueprint 的前缀，但页面路由独立为 `/clustering`。

## 项目结构

```text
DataAnalyticsToolkit/
├── app.py                    # Flask 应用工厂与开发启动入口
├── config.py                 # 上传、日志和 Matplotlib 配置
├── requirements.txt          # Python 依赖
├── DESIGN.md                 # 界面设计系统
├── routes/                   # 页面路由与 API Blueprint
├── templates/                # Jinja2 页面模板
├── static/                   # CSS、公共脚本和模块脚本
├── utils/                    # 文件、文本、统计和机器学习业务逻辑
├── tests/                    # 业务逻辑与 API 测试
├── uploads/                  # 临时上传目录，仅保留占位文件
└── logs/                     # 应用日志目录
```

业务代码和接口职责分离如下：

```text
浏览器
  ├── templates + static/js + static/css
  ↓ Ajax / FormData
Flask app factory
  ├── routes/*       页面与 API 参数解析、错误处理、响应
  └── utils/*        文件读取、文本处理、统计与模型计算
  ↓
临时上传文件 / Excel 响应 / logs/app.log
```

## 配置

默认配置位于 `config.py`，常用配置包括：

| 配置项 | 默认值 | 说明 |
| --- | --- | --- |
| `SECRET_KEY` | `dev-secret-key-change-in-production` | Flask 密钥；生产环境应通过环境变量覆盖 |
| `UPLOAD_FOLDER` | `uploads/` | 临时上传目录 |
| `MAX_CONTENT_LENGTH` | `16 MB` | 单次上传大小限制 |
| `ALLOWED_EXTENSIONS` | `csv, xlsx, xls, txt` | 允许的文件扩展名 |
| `MPL_BACKEND` | `Agg` | 无 GUI 环境下的 Matplotlib 后端 |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `LOG_FILE` | `logs/app.log` | 日志文件路径 |

例如设置生产密钥：

```bash
export SECRET_KEY='replace-with-a-long-random-secret'
```

上传文件只用于当前请求的读取和分析，临时文件在处理上下文退出后删除。`uploads/` 和 `logs/` 中的本地产物已加入 `.gitignore`，不要将用户数据或运行日志提交到仓库。

## 测试

在虚拟环境中运行：

```bash
python -m unittest discover -s tests -v
```

测试覆盖聚类、热力分析、回归分析的业务逻辑，以及表格预览、参数校验和 API 响应。

## 开发约定

- 新增页面放入 `routes/pages.py` 和 `templates/`，并继承 `templates/base.html`。
- 新增 API 按模块放入 `routes/<module>.py`，业务处理放入 `utils/<module>.py`。
- 表格读取、预览和 Excel 下载优先复用 `utils/file_helpers.py`。
- 上传文件使用临时文件，不要长期写入 `uploads/`。
- 图表优先使用项目已经引入的 Plotly.js；Matplotlib 保持使用 `Agg` 后端。
- 新增 Python 依赖时同步更新 `requirements.txt`。
