# 网页版 Python 数据处理平台当前说明

本文档记录 DataAnalyticsToolkit 当前工程结构、已实现进度和后续协作约束。当前版本已经从单文件路由方案演进为 **Flask 应用工厂 + Blueprint 分模块路由 + Utils 业务模块** 的结构。

---

## 一、当前定位

本平台是一个面向中文文本和表格数据的数据分析 Web 应用，提供七个已落地功能模块：

1. **数据清洗**：上传 CSV / Excel，按列配置删除空值、去重、最小字数过滤，并导出清洗结果。
2. **分词统计**：支持文本输入和表格列分词，支持停用词、自定义词典、词频图表和 Excel 导出。
3. **词云制作**：支持粘贴文本生成词云，也支持读取词频表生成词云。
4. **情感分析**：支持文本分析、表格列批量分析、自定义情感词微调和 Excel 导出。
5. **社会网络关系图**：支持文本或表格列分词，导入分词统计结果作为分词规则，并基于词语共现绘制关系图。
6. **回归分析**：支持 CSV / XLS / XLSX 上传，选择至少两列 1-10 数值列并对所有列组合执行一元线性回归，用 Plotly 绘制一张或多张回归图。
7. **热力分析**：上传 CSV / Excel，选择至少两列 1-10 数值列，计算列间 Pearson 相关系数并用 Plotly 绘制热力图。

**视觉设计**：遵循 `DESIGN.md` 中的 Ollama 风格设计系统，使用纯白画布（`#ffffff`）、纯黑主色（`#000000`）、中性灰文本与细边线，采用 SF Pro Rounded / 系统无衬线 / 系统等宽字体。交互控件使用全圆角胶囊形，卡片使用 12px 圆角，不使用渐变或装饰性阴影。

**数据流**：

```text
用户浏览器
  <-> templates + static JS/CSS
  <-> Flask app.py / routes 蓝图
  <-> utils 业务处理模块
  <-> uploads 临时文件 / logs 日志
```

---

## 二、技术栈

### 后端

| 类别 | 库 / 模块 | 用途 |
|------|-----------|------|
| Web 框架 | Flask | 应用工厂、Blueprint 路由、模板渲染、API 响应 |
| 中文分词 | jieba | 中文分词、词频统计、自定义词典 |
| 英文分词 | nltk | 英文分词支持 |
| 情感分析 | SnowNLP | 中文情感倾向评分 |
| 词云生成 | wordcloud + matplotlib | 生成 Base64 PNG 词云图 |
| 回归分析 | scikit-learn | 一元线性回归、R²、MSE |
| 数据处理 | pandas + numpy | CSV / Excel 读取、清洗、数组计算 |
| Excel 读写 | openpyxl + xlrd | `.xlsx` / `.xls` 读取和导出 |
| 文件处理 | tempfile + utils.file_helpers | 上传文件临时保存、DataFrame 读取、Excel 下载 |
| 日志 | logging | 控制台与 `logs/app.log` 输出 |

### 前端

| 类别 | 实现 | 用途 |
|------|------|------|
| UI | 原生 HTML/CSS + `static/css/style.css` | Ollama 风格页面、组件、响应式布局 |
| 图表 | Plotly.js 3.0.0 CDN | 分词柱状图、回归散点图/回归线、分析可视化 |
| 交互 | 原生 JavaScript | Ajax、Tab、表格预览、列选择、导出下载 |
| 公共脚本 | `static/js/common.js` | HTML 转义、CSV 解析、文件读取等公共函数 |
| 独立脚本 | `segmentation.js`、`regression.js`、`heat_analysis.js` | 分词、回归与热力分析页面主交互 |
| 页内脚本 | cleaning / sentiment / wordcloud 模板 | 这些页面当前主要在模板内维护交互逻辑 |

---

## 三、当前项目目录结构

```text
DataAnalyticsToolkit/
├── app.py                         # Flask 应用入口：create_app、日志、matplotlib 后端、蓝图注册
├── config.py                      # Config：上传目录、允许后缀、日志、matplotlib 后端等
├── requirements.txt               # Python 依赖
├── DESIGN.md                      # 视觉设计系统说明
├── AGENTS.md                      # 当前工程说明与协作约束
│
├── routes/                        # Flask Blueprint 路由层
│   ├── __init__.py                # register_routes(app)
│   ├── pages.py                   # 页面路由
│   ├── cleaning.py                # 数据清洗 API
│   ├── segmentation.py            # 分词统计 API
│   ├── wordcloud.py               # 词云制作 API
│   ├── sentiment.py               # 情感分析 API
│   ├── social_network.py           # 社会网络关系图 API
│   ├── regression.py              # 回归分析 API
│   └── heat_analysis.py           # 热力分析 API
│
├── templates/                     # Jinja2 页面模板
│   ├── base.html                  # 基础模板：顶部工具栏、持久侧栏、Plotly、公共样式、页脚
│   ├── index.html                 # 工作台首页：左侧功能列表、右侧操作面板
│   ├── cleaning.html              # 数据清洗页面
│   ├── segmentation.html          # 分词统计页面
│   ├── wordcloud.html             # 词云制作页面
│   ├── sentiment.html             # 情感分析页面
│   ├── social_network.html         # 社会网络关系图页面
│   ├── regression.html            # 回归分析页面
│   └── heat_analysis.html         # 热力分析页面
│
├── static/
│   ├── css/
│   │   └── style.css              # 全局样式与设计系统落地
│   ├── js/
│   │   ├── common.js              # 公共前端工具函数
│   │   ├── segmentation.js        # 分词页交互
│   │   ├── social_network.js       # 社会网络关系图页交互
│   │   ├── regression.js          # 回归页交互
│   │   └── heat_analysis.js       # 热力分析页交互
│   └── images/
│       └── banner_background.png  # 历史资源，当前页面不再引用
│
├── utils/                         # 核心业务处理模块
│   ├── __init__.py
│   ├── file_helpers.py            # 上传表格读取、预览、Excel 响应
│   ├── cleaning.py                # 数据清洗逻辑
│   ├── segmentation.py            # 分词与词频统计
│   ├── wordcloud_gen.py           # 词云生成
│   ├── sentiment_analysis.py      # 情感分析与自定义情感词
│   ├── social_network.py            # 分词共现与关系图数据
│   ├── regression.py              # 线性回归
│   ├── heat_analysis.py           # 列间相关性热力值
│   └── stopwords.txt              # 停用词表
│
├── uploads/
│   └── .gitkeep                   # 临时上传目录占位
│
└── logs/
    └── app.log                    # 运行日志
```

---

## 四、应用入口与路由组织

`app.py` 现在使用应用工厂：

```python
def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(os.path.dirname(app.config.get("LOG_FILE", "logs/app.log")), exist_ok=True)
    matplotlib.use(app.config["MPL_BACKEND"])
    _setup_logging(app)
    from routes import register_routes
    register_routes(app)
    return app
```

所有页面和 API 均通过 `routes/__init__.py` 注册蓝图。新增功能时优先新增或扩展对应 `routes/*.py` 蓝图，不要把业务接口重新堆回 `app.py`。

---

## 五、页面路由

| 路由 | 模板 | 说明 |
|------|------|------|
| `/` | `index.html` | 面板型工作台首页：左侧工具列表、右侧操作面板 |
| `/cleaning` | `cleaning.html` | 数据清洗 |
| `/segmentation` | `segmentation.html` | 分词统计 |
| `/wordcloud` | `wordcloud.html` | 词云制作 |
| `/sentiment` | `sentiment.html` | 情感分析 |
| `/social-network` | `social_network.html` | 社会网络关系图 |
| `/regression` | `regression.html` | 回归分析 |
| `/heat-analysis` | `heat_analysis.html` | 热力分析 |

---

## 六、API 端点

### 数据清洗

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/cleaning/preview` | POST | 表格文件预览，返回列名、前 20 行、总行数 |
| `/api/cleaning/process` | POST | 表格文件 + `strategies` JSON，返回清洗后预览和统计 |
| `/api/cleaning/export` | POST | 表格文件 + `strategies` JSON，导出清洗后 Excel |

`strategies` 格式：

```json
{
  "列名": {
    "remove_null": true,
    "remove_duplicates": "first",
    "min_length": 5
  }
}
```

### 分词统计

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/segmentation` | POST | 文本分词，JSON：`text, top_n, remove_stopwords, extra_stopwords, extra_dict` |
| `/api/segmentation/preview` | POST | 表格文件预览，FormData：`file` |
| `/api/segmentation/file` | POST | 表格列分词，FormData：`file, column, top_n, remove_stopwords, extra_stopwords, extra_dict` |
| `/api/segmentation/export` | POST | 文本分词结果导出 Excel |
| `/api/segmentation/file/export` | POST | 表格列分词结果导出 Excel |

### 词云制作

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/wordcloud` | POST | 文本生成词云，FormData：`text, max_words, colormap, bg_color` |
| `/api/wordcloud/preview-freq` | POST | 词频表预览，自动识别词列和频次列 |
| `/api/wordcloud/from-file` | POST | 从词频表生成词云，FormData：`file, max_words, colormap, bg_color` |

### 情感分析

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/sentiment` | POST | 文本情感分析，JSON：`text, custom_sentiment?` |
| `/api/sentiment/preview` | POST | 表格文件预览，FormData：`file` |
| `/api/sentiment/file` | POST | 表格列批量情感分析，FormData：`file, column, custom_sentiment?` |
| `/api/sentiment/export` | POST | 导出文本或批量情感分析结果 Excel |

### 回归分析

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/regression/preview` | POST | 表格预览并识别可用数值列，FormData：`file` |
| `/api/regression` | POST | 多列两两回归，FormData：`file, columns`，其中 `columns` 为列名 JSON 数组 |

### 热力分析

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/heat-analysis/preview` | POST | 表格预览并识别可用数值列，FormData：`file` |
| `/api/heat-analysis` | POST | 计算所选列的 Pearson 相关系数矩阵，FormData：`file, columns`，其中 `columns` 为列名 JSON 数组 |

### 社会网络关系图

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/social-network/preview` | POST | 表格来源预览，返回列名和前 20 行 |
| `/api/social-network/import-frequency` | POST | 导入分词统计导出的词频表，最多返回前 4000 个分词规则 |
| `/api/social-network/prepare` | POST | 文本/表格列分词，应用导入的分词规则并返回摘要 |
| `/api/social-network/graph` | POST | 基于词语窗口共现关系返回节点和连线数据 |

`/api/social-network` 和 `/api/social-network/analyze` 是关系图接口的兼容别名。

`prepare` 和 `graph` 使用 FormData：`mode, text? / file+column?, segmentation_words, window_size, min_frequency, max_nodes, max_edges`。

---

## 七、Utils 模块接口

### `utils.file_helpers`

```python
def uploaded_dataframe(file, allowed_extensions: Optional[set[str]] = None)
def dataframe_preview(df: pd.DataFrame, max_rows: int = 20) -> dict
def send_excel(workbook, filename: str = "export.xlsx") -> Response
```

- 支持 `.csv`、`.xlsx`、`.xls` 表格文件。
- 读取上传文件时使用临时文件，并在上下文退出后删除。
- 新增表格型 API 时优先复用这些函数。

### `utils.cleaning`

```python
def clean_dataframe(
    df: pd.DataFrame,
    strategies: Dict[str, Dict[str, Any]],
) -> tuple[pd.DataFrame, Dict[str, Any]]
```

- 支持删除空值、按列去重（保留首行/末行）、最小字数过滤。
- 返回清洗后的 DataFrame 和清洗统计。

### `utils.segmentation`

```python
def segment_text(
    text: str,
    top_n: int = 50,
    remove_stopwords: bool = True,
    extra_stopwords: set[str] | None = None,
    extra_dict: list[str] | None = None,
) -> Dict[str, int]
```

- `extra_stopwords` 与内置停用词合并过滤。
- `extra_dict` 会通过 `jieba.add_word()` 注册为整体词。
- `top_n=0` 表示返回全部词频，用于导出。

### `utils.wordcloud_gen`

```python
def generate_wordcloud(
    text: str | None = None,
    freq_dict: Dict[str, int] | None = None,
    width: int = 800,
    height: int = 500,
    background_color: str = "#ffffff",
    colormap: str = "viridis",
    max_words: int = 200,
    font_path: str | None = None,
) -> str
```

- 返回 Base64 编码 PNG。
- 自动检测常见系统中文字体。
- 支持从原始文本或词频字典生成。

### `utils.sentiment_analysis`

```python
def analyze_sentiment(
    text: str,
    custom_sentiment: Optional[Dict[str, float]] = None,
    custom_weight: float = 0.6,
) -> Dict

def analyze_batch(
    texts: List[str],
    custom_sentiment: Optional[Dict[str, float]] = None,
    custom_weight: float = 0.6,
) -> List[Dict]

def parse_custom_sentiment(raw: str) -> Optional[Dict[str, float]]
```

- SnowNLP 得分范围为 0 到 1。
- 标签阈值：`> 0.6` 积极，`< 0.4` 消极，中间为中性。
- 自定义情感词支持 `词:0.9`、`词=0.9`、`词 0.9`。

### `utils.regression`

```python
def regression_column_details(df) -> list[dict]
def eligible_regression_columns(df) -> list[str]
def pairwise_regression(df, columns) -> list[Dict]
def linear_regression(x, y, x_label="X", y_label="Y") -> Dict
```

- 回归列必须有标题、至少 2 行数据，且每个数据行都是 1-10（含边界）的数字，支持小数。
- `pairwise_regression` 按选择顺序将每两列生成一个结果，返回截距、斜率、R²、MSE、方程、原始点、预测点、样本数等字段。

### `utils.heat_analysis`

```python
def heatmap_values(
    df: pd.DataFrame,
    columns: list[str],
) -> dict[str, Any]
```

- 复用回归分析的列校验规则，只允许标题下全部为 1-10（含边界）数值的列。
- 返回所选列、样本数、Pearson 相关系数矩阵和矩阵最小/最大值。
- 常量列导致的未定义交叉相关值以 0 展示，对角线固定为 1。

---

## 八、当前前端实现进度

- `base.html` 已包含顶部工具栏、持久化分析工具侧栏、页脚、Plotly CDN 和全局 CSS。
- 侧栏在首页和七个功能页面中都会显示；当前页面对应的工具通过 `request.endpoint` 自动高亮，桌面端使用粘性定位，移动端折叠为顶部列表。
- `index.html` 是面板型工作台首页，不再使用 Hero、功能介绍卡片或 CTA 横幅；左侧展示七个工具，右侧展示当前默认的数据清洗操作面板和快速入口。
- `segmentation.html` 使用 `common.js` + `segmentation.js`。
- `regression.html` 使用 `common.js` + `regression.js`。
- `cleaning.html`、`sentiment.html`、`wordcloud.html` 当前主要使用页内脚本，并复用 `common.js`。
- 所有上传型页面都采用 Ajax/FormData 与后端 API 交互。
- 词频、情感、清洗相关结果支持 Excel 下载。
- `static/js/segmentation.js`、`static/js/regression.js`、`static/js/heat_analysis.js` 的 Plotly 图表使用黑白中性色；情感分析结果使用绿色表示积极、蓝色表示中性、珊瑚色表示消极。
- 六个非首页功能页的右侧操作区域使用模块强调色：分词统计为蓝色、词云制作为紫色、情感分析为珊瑚色、社会网络关系图为靛紫色、回归分析为青绿色、热力分析为金色；首页操作面板保留独立的暖黄色/青绿色按钮。

后续如果继续扩展前端交互，优先将页面内过长脚本拆入 `static/js/<module>.js`，但不要在没有必要时做大规模重构。

---

## 九、分模块当前说明

### 数据清洗

- 支持 CSV / XLS / XLSX 文件上传和前 20 行预览。
- 用户按列配置清洗策略。
- 清洗结果返回统计摘要、清洗步骤和预览行。
- 导出 Excel 包含“清洗统计”和“清洗后数据”两个 Sheet。

### 分词统计

- 支持文本和表格列两种输入模式。
- 支持额外停用词、自定义词典、过滤停用词开关。
- 表格模式支持预览、选择列、合并该列文本后分词。
- 结果包含词频列表、去重词数、总词频、来源列/行数。
- 支持导出全部词频 Excel。

### 词云制作

- 支持直接输入文本生成词云。
- 支持上传词频表生成词云，自动识别“词语/word/term”和“频次/count/freq/frequency”等列。
- 返回 Base64 图片用于页面展示。

### 情感分析

- 支持文本整体分析和逐句分析。
- 支持表格列批量分析。
- 支持自定义情感词微调 SnowNLP 得分。
- 支持导出摘要和详细结果 Excel。

### 社会网络关系图

- 支持文本模式直接分词，以及表格模式上传文件后选择文本列分词。
- 分词规则通过单个“分词统计”导出的词频 Excel 获取，不在本页面重复维护停用词和词典输入控件。
- 导入词频 Excel 时按原始顺序最多保留前 4000 个分词规则。
- 按文本句子或表格行统计窗口内的词语共现关系，Plotly 展示节点、连线和关系明细。

### 回归分析

- 支持 CSV / XLS / XLSX 文件上传、前 20 行预览和可用数值列识别。
- 用户至少选择 2 列；每个组合以前一列为自变量、后一列为因变量，生成一张 Plotly 散点图和回归线。
- 列选择严格限制为标题下全部为 1-10（含边界）数值的列，支持小数。

### 热力分析

- 支持 CSV / XLS / XLSX 文件上传、前 20 行预览和可用数值列识别。
- 用户至少选择 2 列；每个交叉单元格表示对应两列的 Pearson 相关系数。
- 结果使用 Plotly 绘制带数值标注的相关性热力图，色阶范围固定为 -1 到 1。

---

## 十、配置与运行

### 安装依赖

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 启动服务

```bash
source venv/bin/activate
python app.py
# 访问 http://127.0.0.1:5000
```

### `config.py` 当前配置

- `SECRET_KEY`: 默认开发密钥，可通过环境变量覆盖。
- `UPLOAD_FOLDER`: `uploads/`
- `MAX_CONTENT_LENGTH`: 16 MB
- `ALLOWED_EXTENSIONS`: `csv, xlsx, xls, txt`
- `MPL_BACKEND`: `Agg`
- `STOPWORDS_FILE`: `utils/stopwords.txt`
- `LOG_LEVEL`: `INFO`
- `LOG_FILE`: `logs/app.log`

### `requirements.txt` 当前依赖

```text
flask>=3.0
jieba>=0.42
nltk>=3.8
snownlp>=0.12
wordcloud>=1.9
matplotlib>=3.8
pandas>=2.1
numpy>=1.26
scikit-learn>=1.3
statsmodels>=0.14
plotly>=5.18
openpyxl>=3.1
xlrd>=2.0
```

---

## 十一、协作与后续开发约束

- 后端页面路由放在 `routes/pages.py`。
- 后端 API 按功能模块放在 `routes/<module>.py`，并在 `routes/__init__.py` 注册。
- 业务逻辑放在 `utils/<module>.py`，路由层只负责参数解析、错误处理、日志和响应格式。
- 表格上传、DataFrame 预览、Excel 下载优先复用 `utils.file_helpers`。
- 上传文件应使用临时文件，用完删除，不要长期保存在 `uploads/`。
- Matplotlib 必须使用 `Agg` 后端。
- 前端继续复用 `DESIGN.md` 和 `static/css/style.css` 的 Ollama 风格设计系统：白色画布、黑色主操作、细灰边线、全圆角控件、无渐变和无装饰性阴影。
- 新增页面应继承 `templates/base.html`。
- 新增页面应继续使用公共侧栏；侧栏工具项需要根据当前 Blueprint endpoint 保持正确的 active 状态。
- 桌面端公共侧栏保持粘性定位，移动端改为页面顶部的响应式工具列表。
- 功能页操作按钮的模块配色通过 `body` 上的 Blueprint endpoint 类名和 `static/css/style.css` 统一维护，新增功能页需要补充对应强调色。
- 新增图表优先使用已引入的 Plotly.js。
- 不要把新依赖加入代码后忘记同步 `requirements.txt`。
- 不要提交 `venv/`、临时上传文件、运行日志等本地产物。
