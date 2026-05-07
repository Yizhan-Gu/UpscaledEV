# upscaledev_imp.ipynb 缓存摘要

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

Notebook 主要分成 7 个部分：

1. **项目说明 / README**
2. **环境与包导入**
3. **参数设置**
4. **数据读取与预处理**
5. **绘图与结果导出函数**
6. **主循环（DA + RT/MPC 优化）**
7. **批量运行与财务汇总后处理**

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

用途：
- DA LMP
- RT LMP

### Ancillary Service 数据
- `2025Data/AS_DAM/AS_price_2025_clear.csv`
- `2025Data/AS_RTM/AS_price_2025_clear.csv`

用途：
- RegUp / RegDown / Spin / NonSpin 的 DA / RT 价格

### 可选 ML 到达预测相关
- `Driver_Table.csv`
- `Sessions_Data/Sessions_Data_<user>.csv`
- 外部 battery lookup 表

用途：
- 当 `Fc_AtArrival == 'MLatArrival'` 时，对用户到达后的 session / 停留时长进行预测

---

## 4. 关键全局参数

### 时间分辨率
- `dt_m_EV = 15`
- `dt_h = 0.25`
- 每天 96 个时间步

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
- `Fc_SessionkWh`
- `Fc_NumbEV`
- `Fc_AtArrival`
- `Fc_building`
- `Fc_PV`

当前 notebook 主要使用：
- `PerfectSessionkWh`
- `PerfectNumbEV`
- `PerfectatArrival`

### 市场模式开关
- `WM_Mode = 'full' | 'wm_only' | 'retail_only'`
- `Enable_WM = (WM_Mode in ['full', 'retail_only'])`
  - **注意：这里逻辑上有点可疑**，因为 `retail_only` 直觉上不应启用 WM；
    后面 runner cell 里又重新定义：`Enable_WM = (WM_Mode in ['full'])`

### Case 设置
- `Cases = ['Base', 'Case1']`
  - `Base`: 100% 服务水平
  - `Case1`: 允许 service level reduction（Eta_min）

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

## 6. 两个主要辅助函数

### 6.1 `plot_daily_solver_choice_figures(...)`
作用：
- 生成每天的 6-panel 图
- 导出 daily price table
- 导出 BESS activity table
- 输出 DA 结果可视化

图里主要展示：
- 各类价格信号（LMP、AS、TOU）
- 容量产品和能量义务
- BESS 的 WM / NWM 充放电拆分
- SOC 曲线
- EV / Baseline / BESS / GI 的整体功率关系

### 6.2 `save_old_stairplot_beautified(...)`
作用：
- 生成传统 stair plot
- 比较 V0G / V1G / DA / RT implementation / baseline 等曲线

当前 notebook 中这部分调用被注释掉了，没有实际输出。

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

这意味着 notebook 不只是“算一次”，而是形成了 **多天串联仿真**。

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
  - `p_ch_BESS_WM`
  - `p_dch_BESS_WM`
  - `p_ch_BESS_NWM`
  - `p_dch_BESS_NWM`
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

意思是：
- 不是所有卖出的容量都转化为全额能量调用
- 用 alpha 表示预期能量义务

约束里主要管三件事：

1. **容量上限**：不能超过 EV + BESS 提供能力
2. **方向一致性**：避免同一时段同时做互相冲突的动作
3. **SOC 可行性**：确保 BESS 有足够电量/空间履约

收益中同时计入：

- DA / RT 能量收益
- AS capacity 收益
- activation 对应的能量项

---

## 11. Baseline / Event Hour 逻辑

Notebook 里 baseline 不是一个固定曲线，而是会根据历史非事件日动态构造。

### baseline 的核心逻辑
- 若目标日是工作日，则从过去工作日找样本
- 若目标日是周末/节假日，则从过去周末/节假日找样本
- Base / Case1 会逐小时找“非 event hour”样本

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

### 图与价格表
- `Results/Plots/Solver_DA_Choices/...`
- `Results/Plots/Daily_Price_Tables/...`
- `Results/Plots/Imp_Stair/...`

### 财务汇总
最后一个 code cell 会：

- 汇总 DA WM profit breakdown
- 汇总 DA WM TOU breakdown
- 生成 daily 2x5 financial table

---

## 14. notebook 末尾额外两个 code cell 的作用

### 倒数第二个 cell
不是重新写主循环，而是：

- 用 `nbformat` 直接读取 notebook 自己
- 抽取 main loop cell 的 source
- 把 `RUN_MAIN_LOOP_DIRECT=False` 替换成 `True`
- 批量运行多个 `WM_Mode`

当前配置：
- `RUN_DAYS_CONFIG = [1, 2]`
- `RUN_MODES = ['retail_only', 'full']`

也就是说，这个 cell 是一个 **批量运行器**。

### 最后一个 cell
基于已经生成的结果文件，做：

- 每日 WM profit summary
- 每日 WM TOU summary
- 2x5 财务表（TOU only / Both）

这个 cell **不重新优化**，只是读取已有 CSV 做后处理。

---

## 15. 这个 notebook 的一句话总结

> 它是一个把 EV 聚合充电、BESS 调度、零售电费优化、需求响应 baseline 逻辑、以及 CAISO 批发市场参与整合到一起的 **日级 DA + 15分钟级 RT/MPC 联合优化实现 notebook**。

---

## 16. 后续改代码时最重要的上下文缓存

如果后面要改代码，优先记住下面这些：

### A. 最核心主线
- 先做 **DA 优化**
- 再做 **RT/MPC implementation**
- 最后把结果写到 `Results/Dispatch/*.csv`

### B. 三种模式
- `full`: 零售 + WM 都参与
- `wm_only`: 只保留 WM 驱动（代码里有对应约束）
- `retail_only`: 只做零售侧，但 notebook 内部有一处 `Enable_WM` 定义不完全一致，需要特别小心

### C. 两个 case
- `Base`
- `Case1`

### D. 最关键结果变量
- `Solver_Outputs_DA`
- `Solver_Outputs_RT`
- `Dispatch`
- `Baseline_96`
- `EventHour_96`
- `p_BESS_value_RT`
- `p_GI_DA`

### E. 最容易改坏的区域
- baseline/event hour 逻辑
- WM 和 BESS 的方向约束
- RT 中 arrival 更新和 `SessionkWh_nEta` / `UpperBound` 的维护
- `Enable_WM` 与 `WM_Mode` 的一致性
- notebook 中 runner cell 对 main-loop source 的正则替换

---

## 17. 建议的后续协作方式（省 token）

以后你不需要再贴整个 notebook。你可以直接引用这份缓存摘要，并告诉我：

### 用法示例 1
“按 `upscaledev_imp_cache.md` 的缓存，帮我改 RT 优化里的 BESS 约束。”

### 用法示例 2
“基于缓存摘要，检查 `retail_only` 和 `Enable_WM` 的逻辑是否一致。”

### 用法示例 3
“按缓存摘要，帮我把 notebook 的 main loop 抽成 `.py` 文件。”

这样我后续只需要：
- 读这个摘要文件
- 再读 notebook 的相关局部代码段

就不用每次重新消耗大量 token 读取整份 notebook。
