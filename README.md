# 表面肌电（sEMG）数据处理与分析流程

## 项目结构

```
SEMG_ANSYS/
├── data_raw/                    # 原始数据（无扩展名的 CSV 格式）
│   ├── 01luochunmei/           # 受试者：罗春梅
│   │   ├── 01chunmei最大收缩测试  # MVC 测试
│   │   ├── 02chunmei装饰传统      # 装饰传统工艺
│   │   ├── 03chunmei装饰优化      # 装饰优化工艺
│   │   ├── 04chunmei打磨传统      # 打磨传统工艺
│   │   └── 05chunmei打磨优化      # 打磨优化工艺
│   └── 02lfm/                  # 受试者：LFM
│       ├── 01lfm最大收缩测试
│       ├── 02lfm装饰优化
│       ├── 03lfm装饰传统
│       ├── 04lfm打磨优化
│       └── 05lfm打磨传统
│
├── data_processed/              # 预处理后的数据（自动生成）
│   └── (与 data_raw 层级结构一致)
│
├── figures/                     # 可视化对比图（自动生成）
│   ├── 01luochunmei_装饰_对比.png
│   ├── 01luochunmei_打磨_对比.png
│   ├── 02lfm_装饰_对比.png
│   ├── 02lfm_打磨_对比.png
│   ├── 所有受试者_装饰_对比.png
│   └── 所有受试者_打磨_对比.png
│
├── batch_preprocess.py          # 步骤1：原始数据预处理
├── extract_mvc.py               # 步骤2：MVC 极大值提取
├── analyze_rms_mvc.py           # 步骤3：RMS %MVC 统计分析
├── visualize_comparison.py      # 步骤4：可视化对比
│
├── MVC_values.csv               # MVC 提取结果
├── analysis_results.xlsx        # %MVC 统计分析结果
├── 1.py                         # 初始测试脚本（非流程文件）
└── 受试者信息收集表.xlsx
```

## 数据处理流水线

### 步骤1：原始数据预处理

**脚本**：[batch_preprocess.py](file:///e:/Coding_projects/SEMG_ANSYS/batch_preprocess.py)

**功能**：读取 `data_raw` 中所有受试者、所有动作文件，对通道 1-4 进行预处理，输出至 `data_processed`。

**预处理流程**（`preprocess_semg` 函数）：

```
原始信号 → 去直流（减去均值）
         → 20-450Hz 带通滤波（4 阶 Butterworth）
         → 50Hz 陷波滤波（工频干扰抑制）
         → 全波整流
         → 预处理后信号
```

**通道-肌肉对应关系**：

| 通道 | 肌肉 |
|------|------|
| Channel 1 | 三角肌前束 |
| Channel 2 | 胸锁乳突肌 |
| Channel 3 | 斜方肌 |
| Channel 4 | 竖脊肌 |

**输入**：`data_raw/` 下的无扩展名 CSV 文件（含 `timestamp, Channel 1~6` 列）

**输出**：`data_processed/` 下同层级结构，每文件包含 `timestamp`、`Channel 1_三角肌前束`、`Channel 2_胸锁乳突肌`、`Channel 3_斜方肌`、`Channel 4_竖脊肌` 列。

---

### 步骤2：MVC 极大值提取

**脚本**：[extract_mvc.py](file:///e:/Coding_projects/SEMG_ANSYS/extract_mvc.py)

**功能**：从 `data_processed` 中查找各受试者的"最大收缩测试"文件，对每个通道使用 1 秒滑动窗口做移动平均，取全局最大值作为 MVC 参考值。

**核心算法**（`extract_mvc_max` 函数）：

```
整流后信号 → 1 秒滑动窗口均值（np.convolve）→ 取最大值 → MVC_max
```

**输入**：`data_processed/` 下的 `*最大收缩测试*` 文件

**输出**：[MVC_values.csv](file:///e:/Coding_projects/SEMG_ANSYS/MVC_values.csv)

| 列名 | 说明 |
|------|------|
| 受试者 | 受试者目录名 |
| 动作文件 | 对应的 MVC 测试文件名 |
| 通道_肌肉 | 通道与肌肉名称 |
| MVC_极大值 | 提取的 MVC 参考值 |

---

### 步骤3：RMS %MVC 统计分析

**脚本**：[analyze_rms_mvc.py](file:///e:/Coding_projects/SEMG_ANSYS/analyze_rms_mvc.py)

**功能**：对"装饰"和"打磨"工序的任务数据，截取 **10s–160s** 时间范围，计算滑动 RMS、归一化为 %MVC，再提取 4 个论文统计分析指标。

**核心算法**：

```
整流后信号 → 平方 → 1 秒滑动窗口均值 → 开方 → RMS_作业(t)
          → ÷ MVC_max × 100% → %MVC(t)
          → 统计 → Mean %MVC / APDF 10% / APDF 50% / APDF 90%
```

**统计指标含义**：

| 指标 | 含义 | 论文用途 |
|------|------|----------|
| Mean %MVC | 平均 %MVC | 平均肌肉负荷 |
| APDF 10% | 第 10 百分位 | 静态负荷水平 |
| APDF 50% | 第 50 百分位（中位数） | 中值负荷水平 |
| APDF 90% | 第 90 百分位 | 峰值负荷水平 |

**输入**：`data_processed/` 下的装饰/打磨任务文件 + [MVC_values.csv](file:///e:/Coding_projects/SEMG_ANSYS/MVC_values.csv)

**输出**：[analysis_results.xlsx](file:///e:/Coding_projects/SEMG_ANSYS/analysis_results.xlsx)

| Sheet | 内容 |
|-------|------|
| 汇总 | 全部 32 条记录（2 受试者 × 4 任务 × 4 通道） |
| 01luochunmei | 罗春梅 16 条记录 |
| 02lfm | LFM 16 条记录 |

---

### 步骤4：可视化对比分析

**脚本**：[visualize_comparison.py](file:///e:/Coding_projects/SEMG_ANSYS/visualize_comparison.py)

**功能**：读取 [analysis_results.xlsx](file:///e:/Coding_projects/SEMG_ANSYS/analysis_results.xlsx)，生成传统 vs 优化的对比柱状图。

**输出图表**（`figures/` 目录，共 6 张）：

| 图表 | 内容 |
|------|------|
| `01luochunmei_装饰_对比.png` | 罗春梅 · 装饰传统 vs 装饰优化 |
| `01luochunmei_打磨_对比.png` | 罗春梅 · 打磨传统 vs 打磨优化 |
| `02lfm_装饰_对比.png` | LFM · 装饰传统 vs 装饰优化 |
| `02lfm_打磨_对比.png` | LFM · 打磨传统 vs 打磨优化 |
| `差值_vs_桌高差_装饰.png` | 装饰工序 %MVC 差值 vs 桌高差值关系分析 |
| `差值_vs_桌高差_打磨.png` | 打磨工序 %MVC 差值 vs 桌高差值关系分析 |

每张图表包含 4 个子图（Mean %MVC、APDF 10%、APDF 50%、APDF 90%），以分组柱状图展示 4 块肌肉的传统与优化数据对比。

**差值 vs 桌高差关系分析**：结合 [受试者信息收集表](file:///e:/Coding_projects/SEMG_ANSYS/受试者信息收集表.xlsx)，分析优化桌高 - 传统桌高的差值，与 %MVC 变化（优化 − 传统）之间的关系。每张图 2×2 子图（4 个指标），每个子图中 4 条不同颜色的线分别代表 4 块肌肉，横轴为桌高差值（mm），纵轴为 %MVC 差值，每个受试者为一个数据点并标注受试者名。

## 运行方式

### 增量处理（推荐）
已有受试者会自动跳过，只处理新增的：
```bash
python run_all.py
```

### 强制重新处理
从头运行全部流程（会删除已有输出重新生成）：
```bash
python run_all.py --force
```

### 分步运行

```bash
# 1. 预处理原始数据
python batch_preprocess.py

# 2. 提取 MVC 参考值
python extract_mvc.py

# 3. RMS %MVC 统计分析
python analyze_rms_mvc.py

# 4. 生成可视化对比图
python visualize_comparison.py
```

## 依赖库

- `numpy` — 数值计算
- `scipy` — 信号处理（滤波）
- `openpyxl` — Excel 读写
- `matplotlib` — 可视化