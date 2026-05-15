# UPscaledEV 项目：预测方法详解

> 本文档面向**首次接触本项目的研究人员或汇报对象**，用通俗的语言解释代码中每一种预测（Forecast）方法的工作原理、优缺点和适用场景。

---

## 目录

1. [背景：为什么需要预测？](#1-背景为什么需要预测)
2. [预测对象一览](#2-预测对象一览)
3. [方法一：Perfect Forecast（完美预测）](#3-方法一perfect-forecast完美预测)
4. [方法二：Persistence Forecast（持续性预测）](#4-方法二persistence-forecast持续性预测)
5. [方法三：ML at Arrival Forecast（到达时刻机器学习预测）](#5-方法三ml-at-arrival-forecast到达时刻机器学习预测)
6. [方法组合与实际使用建议](#6-方法组合与实际使用建议)
7. [快速对比表](#7-快速对比表)

---

## 1. 背景：为什么需要预测？

本项目的核心是**在一天开始之前（Day-Ahead，DA）或实时滚动（Real-Time，RT）** 制定 EV 充电 + BESS 储能 + 批发市场投标的联合优化方案。

优化器需要知道**明天会发生什么**才能做出最佳决策，例如：

- 明天有多少辆 EV 会来充电？
- 每辆车需要充多少电？
- 每辆车什么时候到达、什么时候离开？
- 建筑的用电负荷是多少？
- 光伏（PV）能发多少电？

但在现实世界中，我们**不可能提前 100% 准确知道**这些信息。因此，我们需要**预测（Forecast）**。

代码中提供了多种预测方法，从"理想情况"到"更贴近现实"逐级过渡，帮助研究人员：

- 评估**理论上界**（Perfect Forecast）
- 评估**现实可行方案**（Persistence / ML Forecast）
- 量化**预测误差带来的经济损失**

---

## 2. 预测对象一览

代码中通过以下全局变量控制预测模式：

| 变量 | 预测对象 | 可选值 |
|------|---------|--------|
| `Fc_SessionkWh` | 每辆 EV 的充电需求量（kWh） | `'PerfectSessionkWh'` / `'PersistenceSessionkWh'` |
| `Fc_NumbEV` | 每天到达的 EV 数量 | `'PerfectNumbEV'` / `'PersistenceNumbEV'` |
| `Fc_AtArrival` | 每辆 EV 的到达时间和停留时长 | `'PerfectatArrival'` / `'MLatArrival'` |
| `Fc_building` | 建筑电力负荷 | `'Perfect'` / `'Persistence'` |
| `Fc_PV` | 光伏发电功率 | `'Perfect'` / `'Persistence'` |

---

## 3. 方法一：Perfect Forecast（完美预测）

### 3.1 通俗解释

> **"我有一台时间机器，已经看到了明天发生的一切。"**

Perfect Forecast 直接**使用目标日（Day 0）的真实数据**作为 DA 优化的输入。这意味着优化器在制定计划时，已经"知道"明天实际会发生什么。

### 3.2 代码中的具体实现

对于 Day-Ahead（DA）优化：

```python
if Fc_SessionkWh == 'PerfectSessionkWh':
    # 使用 Day 0（目标日本身）的真实数据
    Baseline_Opt_fc[i] = np.array(Baseline_Opt_avg[0][i])
    SessionkWh_table_fc = SessionkWh_table_TheDates_[0]  # Day 0 真实数据
```

对于 Real-Time（RT）优化：

```python
if Fc_SessionkWh == 'PerfectSessionkWh':
    # 同样使用 Day 0 的真实数据作为"预测"
    i_ = 0  # 指向 Day 0
```

### 3.3 优点

- **优化结果是最优上界**：任何实际预测方法都不可能超过 Perfect Forecast 的表现
- **适合作为基准线（Benchmark）**：用于衡量其他预测方法的好坏
- **排除了预测误差的干扰**：当你想研究市场机制本身（而非预测问题）时非常有用

### 3.4 缺点

- **完全不现实**：实际运营中不可能提前知道明天的 EV 到达情况
- **不能直接用于实际部署**

### 3.5 适用场景

- 学术论文中的 **"理论最优"基准线**
- 验证优化模型本身是否正确
- 评估预测误差带来的经济损失（对比 Perfect vs Persistence）

---

## 4. 方法二：Persistence Forecast（持续性预测）

### 4.1 通俗解释

> **"明天会和昨天差不多，我用昨天的数据来预测明天。"**

Persistence Forecast 使用**前一个相似日（Day-1 或 Day-2）的数据**作为目标日（Day 0）的预测输入。

这是电力负荷预测中最简单、最经典的基准方法。它的假设是：**相邻的同类日（工作日/周末）行为高度相似**。

### 4.2 代码中的具体实现

对于 Day-Ahead（DA）优化：

```python
elif Fc_SessionkWh == 'PersistenceSessionkWh':
    # DA 优化使用 Day-2（前两天）的数据
    if i == 2:  # DA case
        i_ = 2  # 指向 Day-2
    # RT 优化使用 Day-1（前一天）的数据
    elif (i == 0) | (i == 1):  # RT cases
        i_ = 1  # 指向 Day-1
    Baseline_Opt_fc[i] = np.array(Baseline_Opt_avg[i_][i])
```

对于 EV 数量预测：

```python
elif Fc_NumbEV == 'PersistenceNumbEV':
    # 直接使用前一天（Day-1）的 EV 到达数据
    for j in [1, 2]:  # Tesla, Non-Tesla
        SessionkWh_table_fc_fix[j][i] = SessionkWh_table_fc[j][i].copy()
        Car_table_fc_fix[j][i] = Car_table_fc[j][i].copy()
```

如果前一个相似日没有任何 EV 到达（例如周末没人上班），代码会自动回退到 Perfect Forecast：

```python
elif len(Car_table_fc[j][i]) == 0:
    # 前一天没有车 → 回退使用 Day 0 真实数据
    SessionkWh_table_fc_fix[j][i] = SessionkWh_table_real[j][i].copy()
```

如果预测的 EV 数量不够，代码会复制已有的 EV 数据来凑数：

```python
elif len(Car_table_fc[j][i].columns) < len(Car_table_real[j][i].columns):
    n1 = len(Car_table_real[j][i].columns) // len(Car_table_fc[j][i].columns)
    # 重复 Day-1 的数据 n1 次，凑够真实 EV 数量
    SessionkWh_table_fc_fix[j][i] = pd.concat([SessionkWh_table_fc[j][i]]*n1, axis=1)
```

### 4.3 优点

- **简单直观**，计算成本极低
- **不需要任何历史数据训练**
- **作为经典基准方法**，在许多实际应用中表现不差
- **可解释性强**：预测结果 = 昨天的情况

### 4.4 缺点

- **无法捕捉趋势变化**（例如学期开始/结束、节假日前后）
- **对异常日表现差**（例如极端天气、特殊活动）
- **完全依赖"昨天"**，如果昨天是异常日，预测也会跟着错

### 4.5 适用场景

- 实际部署中的**基础预测方案**
- 评估更复杂预测模型的**提升空间**
- 稳定性要求高的场景（Persistence 不会产生离谱的预测）

---

## 5. 方法三：ML at Arrival Forecast（到达时刻机器学习预测）

### 5.1 通俗解释

> **"我在每辆车到达的瞬间，根据这辆车的历史充电记录，预测它这次会充多少电、停多久。"**

与 Perfect 和 Persistence 不同，**ML at Arrival 只在每辆 EV 到达时才触发预测**，而不是在一天开始时就预测所有车。

这是最贴近实际运营场景的方法：充电站运营商在车主插上充电枪的瞬间，根据该车/该用户的历史充电行为，预测本次充电会话的参数。

### 5.2 代码中的具体实现

当 `Fc_AtArrival == 'MLatArrival'` 时，代码在 RT 优化的每个时间步（每 15 分钟）检查是否有新车到达：

```python
if Fc_AtArrival == 'MLatArrival':
    if i == 0:  # 只对 100% 服务水平的 Base case 运行一次
        SessInfo_ThisUser = All_Sess[All_Sess['Car']==car_i]
        ThisUser = int(SessInfo_ThisUser['User'])
        
        if ThisUser in list(User_known):
            # 已知用户：使用个人历史数据预测
            ThisUser_PD_ED = KnownUser(ThisUser, SessInfo_ThisUser[['Session start', 'Arrival Hour']])
        else:
            # 未知用户：使用群体统计特征预测
            ThisUser_PD_ED = UnKnownUser(SessInfo_ThisUser[['Session start','Arrival Hour', 'Battery (kWh)','Weekday', 'Max Charging Power']])
```

#### 5.2.1 KnownUser（已知用户预测）

对于**历史充电次数 ≥ 10 次**的"老用户"，系统会：

1. 读取该用户的个人历史充电数据文件（`Sessions_Data/Sessions_Data_<user_id>.csv`）
2. 根据**到达时刻**和**历史行为模式**，预测：
   - **停留时长**（Predicted Duration, PD）
   - **充电需求量**（Expected Demand, ED）

预测逻辑基于该用户**历史相同到达时段的平均行为**。

#### 5.2.2 UnKnownUser（未知用户预测）

对于**历史充电次数 < 10 次**的"新用户"，系统会：

1. 使用该用户提供的有限信息：
   - 到达时刻（Session start）
   - 到达小时（Arrival Hour）
   - 电池容量（Battery kWh）
   - 星期几（Weekday）
   - 最大充电功率（Max Charging Power）
2. 基于**全体用户的统计规律**进行预测

### 5.3 预测的用途

ML 预测的结果直接用于：

- **更新该车可用的充电窗口**：`IntervalkWh_max_RT[j][i][:, car_col] = ThisUser_Interval`
- **更新该车的充电需求**：`SessionkWh_RT[j][i][:, car_col] = ThisUser_PD_ED[1]`
- **决定是否允许服务水平降低**：如果充电窗口与 event hour 不重叠，则保持 100% 服务水平

### 5.4 优点

- **最贴近实际运营**：在车主到达时才做预测，符合真实场景
- **利用了个体历史行为**（KnownUser），比群体平均更准确
- **对新用户也有兜底方案**（UnKnownUser），不会"冷启动"失败

### 5.5 缺点

- **需要维护历史数据**（每个用户的充电记录）
- **计算开销比 Persistence 大**（每个到达事件都要调用预测函数）
- **预测精度依赖历史数据质量**
- **不适用于 DA 优化**（只能在 RT 阶段逐车触发）

### 5.6 适用场景

- 实际充电站部署运营
- 需求响应（DR）场景中判断是否可降低服务水平
- 研究预测误差对实时调度的影响

---

## 6. 方法组合与实际使用建议

代码支持这些预测方法的**任意组合**。例如：

| 组合 | 含义 | 适用场景 |
|------|------|---------|
| `PerfectSessionkWh` + `PerfectNumbEV` + `PerfectatArrival` | 全部完美预测 | 理论上界评估 |
| `PersistenceSessionkWh` + `PersistenceNumbEV` + `PerfectatArrival` | 电量/数量用持续性，到达时间完美 | 基础现实方案 |
| `PersistenceSessionkWh` + `PerfectNumbEV` + `MLatArrival` | 电量用持续性，数量完美，到达时 ML 预测 | 侧重实际到达行为预测 |
| `PersistenceSessionkWh` + `PersistenceNumbEV` + `MLatArrival` | 全部使用实际可行方法 | 最贴近真实部署 |

### 推荐的实验设计

1. **首先运行 Perfect 一切**，获得理论上界
2. **再运行 Persistence 一切**，获得最简单的现实方案
3. **逐步替换单一项为 ML**，观察各项预测误差的单独影响
4. **最终对比所有组合**，确定哪种预测改进最有价值

---

## 7. 快速对比表

| 特性 | Perfect | Persistence | ML at Arrival |
|------|---------|-------------|---------------|
| **出发逻辑** | "我已经知道明天" | "明天和昨天一样" | "这辆车的历史告诉我" |
| **预测时机** | 一天开始前 | 一天开始前 | 每辆车到达时 |
| **数据需求** | 目标日真实数据（不可得） | 前一日同类数据 | 用户历史充电记录 |
| **计算开销** | 零 | 几乎为零 | 中等（每个到达事件触发） |
| **是否现实** | ❌ 不现实 | ✅ 可行 | ✅ 最现实 |
| **精度** | 100%（上界） | 中等 | 中高（取决于历史数据量） |
| **适用优化层级** | DA + RT | DA + RT | 仅 RT |
| **EV 数量预测** | ✅ | ✅ | ❌（不影响数量） |
| **充电量预测** | ✅ | ✅ | ✅ |
| **到达时间预测** | ✅ | ✅ | ✅ |
| **停留时长预测** | — | — | ✅ |

---

## 附录：代码中的关键变量速查

```python
# 在 Cell 3（参数设置）中定义
Fc_SessionkWh = 'PersistenceSessionkWh'  # 充电量预测方法
Fc_NumbEV = 'PersistenceNumbEV'          # EV 数量预测方法
Fc_AtArrival = 'PerfectatArrival'        # 到达时间预测方法
Fc_building = 'Perfect'                  # 建筑负荷预测方法
Fc_PV = 'Perfect'                        # 光伏预测方法
```

这些变量控制着主循环（Cell 11）中的数据选择逻辑，影响 DA 优化和 RT/MPC 优化的输入。

---

*文档版本：v1.0 | 最后更新：2025-05-14 | 作者：Yizhan Gu*