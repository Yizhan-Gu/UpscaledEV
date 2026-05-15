# upscaledev_imp.ipynb 缓存摘要

> **最后更新：2026-05-14** | 基于 notebook 当前实际代码状态

## 1. Notebook 的核心目标

这个 notebook 是 **UPscaledEV 项目的主实现版优化代码**。它的目标是构建一个包含以下资源的联合优化框架：

- 建筑负荷 / 电网购电（Grid Import）
- EV 充电负荷
- BESS（储能电池）
- 批发市场（Wholesale Market, WM）参与
- 需求响应 / baseline 事件逻辑

它解决的是一个 **value stacking（多价值叠加）** 问题：

- 一边通过 TOU 电价、Demand Charge 降低零售电费
- 一边通过 CAISO 的 DA/RT 能量与辅助服务产品获取市场收益
- 同时保证 EV 充电服务水平

---

## 2. 总体结构

Notebook 主要分成 **8 个 code cell**（实际可执行单元）：

| Cell | 功能 |
|------|------|
| Cell 1 | 项目说明 / README (markdown) |
| Cell 2 | 环境与包导入 |
| Cell 3 | 参数设置（含 `TARGET_SAVE`、`RUN_MAIN_LOOP_DIRECT` 等开关） |
| Cell 4-8 | 数据读取与预处理 |
| Cell 9 | **`plot_daily_solver_choice_figures()`** 绘图与结果导出函数 |
| Cell 10 | Baseline / event hour 预处理逻辑 |
| Cell 11 | **主循环（DA + RT/MPC 优化）** |
| Cell 12 | **批量运行器**（用 `nbformat` 动态执行 Cell 11） |
| Cell 13 | **财务后处理**（WM profit / TOU / 2x5 表汇总） |
| Cell 14 | **月度汇总 + 多图输出**（time-series、stacked bar、delta 图等） |

### 关键架构决策
- **DA vs RT 切换**：通过全局变量 `TARGET_SAVE` 控制（`'DA'` 或 `'RT'`），当前默认值为 `'RT'`
- **批量运行**：Cell 12 读取 Cell 11 源码，通过 `nbformat` + `exec()` 循环不同 `WM_Mode`
- **主循环开关**：`RUN_MAIN_LOOP_DIRECT = False`（默认不运行），Cell 12 将其替换为 `True` 后执行

---

## 3. 关键输入数据

### EV 数据
- `2025Data/EV_data/UCSD_AllSites_Merge_PostProcessedSession_QC.csv`

用途：
- 构造车辆到达/离开时间
- Session kWh
- 每个 15min interval 的真实充电功率
- 区分 Tesla / NonTesla

### Baseline / 历史 dispatch
- `Results/Dispatch/2025_<forecast tags>_baseline.csv`

用途：
- 给 implementation notebook 提供初始 baseline
- 用于 event hour 判定和后续 rolling baseline 更新

### LMP 数据
- `2025Data/LMP/2025/DA/*.csv`
- `2025Data/LMP/2025/FM/*.csv`

用途：DA LMP / RT LMP

### Ancillary Service 数据
- `2025Data/AS_DAM/AS_price_2025_clear.csv`
- `2025Data/AS_RTM/AS_price_2025_clear.csv`

用途：RegUp / RegDown / Spin / NonSpin 的 DA / RT 价格

### 可选 ML 到达预测相关
- `Driver_Table.csv`
- `Sessions_Data/Sessions_Data_<user>.csv`
- 外部 battery lookup 表

用途：当 `Fc_AtArrival == 'MLatArrival'` 时，对用户到达后的 session / 停留时长进行预测

---

## 4. 关键全局参数

### 时间分辨率
- `dt_m_EV = 15`
- `dt_h = 0.25`
- 每天 96 个时间步

### DA/RT 切换开关（新增）
- `TARGET_SAVE = 'RT'` — **控制所有图/表/文件夹的后缀**，支持 `'DA'` | `'RT'`
- 影响范围：
  - 绘图保存路径：`Results/Plots/Solver_{TARGET_SAVE}_Choices/...`
  - 文件名前缀：`{TARGET_SAVE}_WM_profit_breakdown_...`
  - 财务表文件夹：`{TARGET_SAVE}_financial_tables/...`
  - 6-panel 图标题和数据源选择

### BESS 参数
- `SOC_BESS_min = 0.05`
- `SOC_BESS_max = 0.95`
- `P_BESS_max = 250 kW`
- `C_BESS = 332 kWh`
- `gamma = 0.9`
- 每天 throughput 被限制为：
  `dt_h * sum(p_ch + p_dch) <= 2 * C_BESS * (SOCmax - SOCmin)`

### 零售电价 / 成本
- Non-coincident demand charge: `c_NCD = 15.38`
- Peak demand charge: `c_PD`（按季节切换）
- TOU 电价数组：`c_e_TOU_AL`，长度 96

### 预测模式开关
- `Fc_SessionkWh`：`'PerfectSessionkWh'` | `'PersistenceSessionkWh'` | `'ForecastSessionkWh'`
- `Fc_NumbEV`：`'PerfectNumbEV'` | `'PersistenceNumbEV'` | `'ForecastNumbEV'`
- `Fc_AtArrival`：`'PerfectatArrival'` | `'MLatArrival'`
- `Fc_building`：`'Perfectbuilding'` | `'Persistencebuilding'`
- `Fc_PV`：`'PerfectPV'` | `'PersistencePV'`

当前 notebook 默认使用：
- `PerfectSessionkWh`
- `PerfectNumbEV`
- `PerfectatArrival`

### 市场模式开关
- `WM_Mode = 'full' | 'wm_only' | 'retail_only'`
- 注意有两处定义：
  - Cell 3 顶部：`Enable_WM = (WM_Mode in ['full', 'retail_only'])`（可疑——`retail_only` 不应启用 WM）
  - Cell 12 批量运行器：`Enable_WM = (WM_Mode in ['full'])`（正确覆盖）

### Case 设置
- `Cases = ['Base', 'Case1']`
  - `Base`：100% 服务水平
  - `Case1`：允许 service level reduction（Eta_min）

### 主循环运行开关
- `RUN_MAIN_LOOP_DIRECT = False` — 防止在 notebook 中误触直接运行
- `run_days = [1, 2]` — 默认运行天数（Cell 12 中 `RUN_DAYS_CONFIG` 覆盖）

---

## 5. 数据预处理在做什么

### 5.1 节假日 / 工作日分类
构建：
- `Y_WeekendsWH`：周末 + 节假日
- `Y_WeekdaysWOH`：工作日（不含节假日）

用于 baseline days 的筛选。

### 5.2 EV 数据清洗与时间列转换
- 转换 interval/session 的开始结束时间为 `datetime`
- 转换 demand 列为数值
- 生成年份、日期范围、站点数量、充电桩数量等统计

### 5.3 读取历史 baseline dispatch
把之前 baseline notebook 生成的 dispatch 读进来，作为 implementation 的基础输入。

---

## 6. 主要辅助函数

### 6.1 `plot_daily_solver_choice_figures(...)`（Cell 9）
作用：
- 生成每天的 6-panel 图（a-f）
- Panel a：价格信号（LMP、AS、TOU）
- Panel b：容量产品 bid
- Panel c：Capacity products — AS bid bar chart（当前无 p_up/p_down 边界线）
- Panel d：BESS 功率拆分（WM vs NWM）
- Panel e：SOC 曲线
- Panel f：系统总功率关系（EV/Baseline/BESS/GI），含 demand charge threshold dashes

所有 6 个 panel 均**无 grid lines**。

函数签名：
```python
def plot_daily_solver_choice_figures(
    TheDate_Day0, dt_h, Solver_Outputs,
    c_e_TOU_AL, Bid_Pr_DA, Bid_Pr_RT,
    AS_Pr_RU_DA, AS_Pr_RU_RT, AS_Pr_RD_DA, AS_Pr_RD_RT,
    AS_Pr_SP_DA, AS_Pr_SP_RT, AS_Pr_NSP_DA, AS_Pr_NSP_RT,
    alpha_RU, alpha_RD, alpha_SP, alpha_NSP,
    run_tag, M_Th_NCD, M_Th_PD,
    P_BESS_max, P_EV_max,
)
```

### 6.2 `save_old_stairplot_beautified(...)`
作用：生成传统 stair plot，比较 V0G / V1G / DA / RT implementation / baseline 等曲线。

当前 notebook 中**调用被注释掉了**（Cell 11 末尾 `''' ... '''` 块），没有实际输出。

---

## 7. 主体优化逻辑：它到底在做什么

Notebook 的核心其实是 **两层优化 + 一个实施层**：

### 第一层：DA / Offline 优化
针对一天 96 个时间步，做一次日内整体优化，决定：

- EV 充电计划
- BESS 充放电
- DA / RT 能量 bid
- AS capacity（RU / RD / SP / NSP）

目标函数包含：
- Demand Charge（NCD + PD）
- TOU 电能成本
- EV service revenue
- Wholesale market revenue
- BESS terminal SOC penalty（最后一天强制回 50%）

本质上是一个 **混合整数优化问题**：
- `cvxpy`
- `GUROBI`
- 含 boolean 变量控制充放电方向与 net direction

### 第二层：RT / MPC Implementation
然后做 **receding horizon** 的实时实施：

- 每 15 分钟滚动一次
- 用实时到达的车更新问题输入
- 根据 Day-ahead 的结果加软约束，尽量跟随 DA bid
- 每一步只执行当前时刻的第一步决策

即：
- DA 是日级规划
- RT 是逐时段 MPC 落地

### 第三层：落地写回 dispatch / baseline 更新支撑
每天运行完之后会输出：
- implementation dispatch
- daily summary
- 供后续天数 baseline 使用的数据

这意味着 notebook 不只是"算一次"，而是形成了 **多天串联仿真**。

---

## 8. EV 建模在做什么

### 车辆层面
对于每天出现的每辆车，构造：
- ArrivalTime
- SessionkWh
- Eta_min
- Interval 最大可充电量
- Tesla / NonTesla 分类

### V0G / V1G
- `V0G`：按最大功率尽快充满
- `V1G_real`：真实历史充电曲线

### 优化变量
- `EnergyDemand_Table_Opt`：每辆车每个时间步的充电量
- `EnergyDemand_Step_Opt`：聚合后的总充电量
- `p_EV`：聚合 EV 功率

### Base vs Case1
- Base：必须满足完整 session energy
- Case1：允许按 `Eta_min` 服务，非 event 情况又可能被放宽回 100%

---

## 9. BESS 建模在做什么

定义了：
- 总 BESS 功率 `p_BESS`
- 充电功率 `p_ch_BESS`
- 放电功率 `p_dch_BESS`
- WM 渠道 / 非 WM 渠道拆分：
  - `p_ch_BESS_WM` / `p_dch_BESS_WM`
  - `p_ch_BESS_NWM` / `p_dch_BESS_NWM`
- SOC 动态 `soc_BESS`

它的作用有两个：
1. **零售侧削峰填谷**
2. **为批发市场容量和能量义务提供灵活性**

并且 notebook 试图区分：
- 因 TOU 驱动的充放电
- 因 WM 驱动的充放电

---

## 10. Wholesale Market 建模在做什么

定义的市场变量包括：
- 能量：`p_DA`, `p_RT`
- 辅助服务容量：
  - `c_RU_DA`, `c_RU_RT`
  - `c_RD_DA`, `c_RD_RT`
  - `c_SP_DA`, `c_SP_RT`
  - `c_NSP_DA`, `c_NSP_RT`

还定义了 activation factor：
- `alpha_RU = 0.7`
- `alpha_RD = 0.7`
- `alpha_SP = 0.2`
- `alpha_NSP = 0.2`

意思是：不是所有卖出的容量都转化为全额能量调用，用 alpha 表示预期能量义务。

约束里主要管三件事：
1. **容量上限**：`p_up = P_BESS_max + B_EV`（上调能力），`p_down = P_BESS_max - B_EV + P_EV_max`（下调能力）
2. **方向一致性**：避免同一时段同时做互相冲突的动作
3. **SOC 可行性**：确保 BESS 有足够电量/空间履约

收益中同时计入：
- DA / RT 能量收益
- AS capacity 收益
- activation 对应的能量项

### WM Revenue 列结构（wm_profit_table）

Energy products:
- `p_DA_profit`, `p_RT_profit`

Capacity products (up-side, p_up relevant):
- `c_RU_DA_profit`, `c_RU_RT_profit`
- `c_SP_DA_profit`, `c_SP_RT_profit`
- `c_NSP_DA_profit`, `c_NSP_RT_profit`

Capacity products (down-side, p_down relevant):
- `c_RD_DA_profit`, `c_RD_RT_profit`

---

## 11. Baseline / Event Hour 逻辑

Notebook 里 baseline 不是一个固定曲线，而是会根据历史非事件日动态构造。

### baseline 的核心逻辑
- 若目标日是工作日，则从过去工作日找样本
- 若目标日是周末/节假日，则从过去周末/节假日找样本
- Base / Case1 会逐小时找"非 event hour"样本

### Event hour 判定
通过：
- `Baseline_hr - Offline_hr`

如果差值 > 0，则认为该小时可视为 event hour。

这部分是 demand response / baseline settlement 的关键支撑逻辑。

---

## 12. 实时滚动（MPC）具体怎么运行

在 `for i_t in range(96)` 里，每个 15min 都会：

1. 更新当前滚动优化窗口 `H = 96 - i_t`
2. 检查上一时间步新到的车辆
3. 若开启 `MLatArrival`，对新到车做 Session 预测
4. 更新可用的 session energy / upper bound
5. 重新求解 RT 优化问题
6. 执行当前时刻一格 dispatch
7. 扣减剩余 session energy
8. 更新 demand threshold 与 BESS throughput

这是 notebook 最耗时、也最容易出 bug 的核心部分。

---

## 13. 输出文件有哪些

### Dispatch 主输出
- `Results/Dispatch/2025_<tags>_<WM_Mode>_implementation.csv`
- `Results/Dispatch/2025_<tags>_<WM_Mode>_daily_summary.csv`

### 中间 debug / 追踪输出
- `Results/Dispatch/0_*.csv`
- `Results/Dispatch/1_*.csv`

### 图与价格表（路径由 `TARGET_SAVE` 控制）
- `Results/Plots/Solver_{TARGET_SAVE}_Choices/.../`
  - 每日 6-panel 图
  - `{TARGET_SAVE}_WM_profit_breakdown_{mode}.csv`
  - `{TARGET_SAVE}_WM_TOU_breakdown_{mode}.csv`

### 财务汇总（Cell 13）
Cell 13 会生成：
- 每日产品拆分 CSV：`{TARGET_SAVE}_WM_profit_breakdown_summary_YYYYMMDD.csv`
- 每日 TOU 拆分 CSV：`{TARGET_SAVE}_WM_TOU_breakdown_summary_YYYYMMDD.csv`
- 每日 2x5 财务表：`{TARGET_SAVE}_financial_tables/{TARGET_SAVE}_financial_table_YYYYMMDD.csv`
  - 列：`Case / US$`, `Total Revenue`, `WM Revenue`, `TOU Cost`, `PD Cost`, `NCD Cost`, `EV Revenue`
  - ⚠️ 注意：Demand Cost 拆分为独立的 `PD Cost` 和 `NCD Cost` 两列，**没有**合并的 `Demand Cost (PD+NCD)` 列

### 月度汇总 + 多图（Cell 14）
保存至 `Results/Plots/Cost/2025_{Fc tags}/`：
- `monthly_financial_summary.csv`
- `daily_financial_detail.csv`
- `daily_financial_metrics_all.png` — 时间序列折线图（5 个指标 × 2 cases）
- `daily_financial_metrics_hbar.png` — 水平条形图对比
- `daily_value_stack_comparison.png` — 2x1 stacked bar（Retail only / Both）
- `daily_wm_delta.png` — Δ(Both − Retail only) 增量图
- `monthly_summary_grouped_bar.png` — 月度汇总分组柱状图

---

## 14. 各 Cell 详细说明

### Cell 12（批量运行器）
**不是重新写主循环**，而是：
- 用 `nbformat` 直接读取 notebook 自己
- 抽取 main loop cell (Cell 11) 的 source
- 把 `RUN_MAIN_LOOP_DIRECT=False` 替换成 `True`
- 把 `run_days = [1, 2]` 替换为 `run_days = list(RUN_DAYS_CONFIG)`
- 批量运行多个 `WM_Mode`

当前配置：
- `TARGET_SAVE = 'RT'`
- `RUN_DAYS_CONFIG = list(range(1, 32))`
- `RUN_MODES = ['retail_only', 'full']`

关键细节：`Enable_WM = (WM_Mode in ['full'])` —— 在批量运行器中正确定义，覆盖了 Cell 3 中的可疑定义。

### Cell 13（财务后处理）
基于已经生成的结果文件，做：
- 每日 WM profit summary
- 每日 WM TOU summary
- 2x5 财务表（TOU only / Both）
- **不做** WM Revenue 的 EV vs BESS 拆分分析（该功能在当前版本中不存在）

### Cell 14（月度汇总 + 多图）
- 月度汇总表 + 每日各指标趋势图
- 5 组图：时间序列、水平条形、stacked bar、delta 图、分组柱状图
- 保存至 `Results/Plots/Cost/`

---

## 15. TARGET_SAVE 机制（DA/RT 切换）

当前 notebook 已实现 `TARGET_SAVE` 全局变量来统一控制 DA vs RT 输出：

```python
TARGET_SAVE = 'RT'  # 当前默认值，可选 'DA' | 'RT'
```

**影响范围**：
1. **Cell 9 绘图函数**：`plot_daily_solver_choice_figures()` 内部使用 `TARGET_SAVE` 决定保存路径和标题
2. **Cell 11 主循环**：每日结束时的保存逻辑根据 `TARGET_SAVE` 选择数据源
   ```python
   if TARGET_SAVE == 'DA':
       Solver_Outputs_target = Solver_Outputs_DA
       P_EV_max_for_plot = 6.6 * Car_table_RT[0][2].shape[1]
   else:
       Solver_Outputs_target = Solver_Outputs_RT_Base
       P_EV_max_for_plot = 6.6 * Car_table_RT[0][0].shape[1]
   ```
3. **Cell 12 批量运行器**：顶部 `TARGET_SAVE = 'RT'` 定义
4. **Cell 13/Cell 14 后处理**：所有文件路径使用 `{TARGET_SAVE}_` 前缀

### 注意事项
- `TARGET_SAVE` 在 Cell 9 函数内部通过 `global TARGET_SAVE` 引用
- Cell 12 单独定义了 `TARGET_SAVE`，批量运行时所有模式共用同一个值
- Cell 13 和 Cell 14 通过 `global TARGET_SAVE` 引用 notebook 全局变量
- 变量命名：notebook 中使用 `Solver_Outputs_RT_Base`（首字母大写驼峰）和 `Solver_Outputs_DA`

---

## 16. 当前已知问题 / Bugs

### Bug 1：Cell 14 中 `Demand Cost (PD+NCD)` 列不存在
- **位置**：Cell 14 约第 3576 行
- **代码**：`demand_cost = float(row.get('Demand Cost (PD+NCD)', 0.0))`
- **问题**：Cell 13 的 2x5 表保存的是独立的 `PD Cost` 和 `NCD Cost` 两列，**没有**合并的 `Demand Cost (PD+NCD)` 列
- **后果**：`demand_cost` 始终为 0.0，影响月度汇总中的 demand cost 计算
- **修复**：改为 `demand_cost = pd_cost_day + ncd_cost_day` 或从已有两列求和

### Bug 2：Cell 3 中 `Enable_WM` 定义可疑
- **位置**：Cell 3 参数设置区域
- **代码**：`Enable_WM = (WM_Mode in ['full', 'retail_only'])`
- **问题**：`retail_only` 直觉上不应启用 WM
- **现状**：Cell 12 批量运行器用 `Enable_WM = (WM_Mode in ['full'])` 正确覆盖
- **影响**：只在手动运行 Cell 11（不通过 Cell 12）时可能错误

### Bug 3：`monthly_summary_grouped_bar` 标签使用 'Net'
- **位置**：Cell 14 约第 3919 行
- **代码**：`('Total Revenue', '#222222', 'Net')`
- **问题**：x 轴标签显示为 'Net'，可能与 'Total Revenue' 语义不一致
- **建议**：改为 `'Total'`

### Bug 4：Cell 9 Panel c 标题
- **当前**：panel c 显示 Capacity products 相关信息
- **可能的改进点**：标题可能需要改为 'Bids'（待确认具体需求）

---

## 17. 后续协作方式（省 token）

以后你不需要再贴整个 notebook。你可以直接引用这份缓存摘要，并告诉我：

### 用法示例 1
"按 `upscaledev_imp_cache.md` 的缓存，帮我改 RT 优化里的 BESS 约束。"

### 用法示例 2
"基于缓存摘要，检查 `retail_only` 和 `Enable_WM` 的逻辑是否一致。"

### 用法示例 3
"按缓存摘要，帮我把 notebook 的 main loop 抽成 `.py` 文件。"

### 用法示例 4
"按缓存 Bug 1，修复 Cell 14 的 Demand Cost (PD+NCD) 列为两列求和。"

这样我后续只需要：
- 读这个摘要文件
- 再读 notebook 的相关局部代码段

就不用每次重新消耗大量 token 读取整份 notebook。

注意：Cline 读取或修改 Notebook 之前，先手动执行 "Clear All Outputs" 并保存。

---

## 18. 与旧版缓存的主要差异（2026-05-14 更新）

旧版缓存（Section 16）记录了 4 个"已完成修改"：
1. Cell 11 新增 `DA_WM_cap_bids_{WM_Mode}.csv` 输出
2. Cell 9 Panel c 添加 p_up/p_down 边界线
3. Cell 14 WM Revenue Breakdown 改为 interval 级精确分析
4. Cell 14 额外输出 `WM_Revenue_Breakdown_Interval_Detail.csv`

**这些修改在当前 notebook 中均不存在**。当前版本可能是从不同基准版本衍生而来，或这些修改已被回退。如需恢复，请参考旧版缓存的 Section 16 重新实施。

当前 notebook 的核心新特性是 **`TARGET_SAVE` 机制**（支持 DA/RT 统一切换），这是旧版缓存中没有记录的功能。