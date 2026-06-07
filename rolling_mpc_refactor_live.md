# Rolling MPC 重构实时记录

## 目标
- 将当前 shrinking-horizon MPC 改为固定 24 小时（96 个 15 分钟时段）的 rolling MPC。
- 保留全部 EV 手动预处理与预测分支逻辑。
- 在不破坏原始业务语义的前提下，提供可直接运行且可迭代优化的 notebook 版本。

## 约束
- 不删除 EV 数据处理与预测逻辑。
- 尽量保持现有输出口径（Dispatch、daily summary、财务后处理）兼容。
- 每次结构性改动后先做 2 天短测，再考虑长周期。

## 当前方案
- rolling 运行器已内联到 notebook 的执行单元中（无外部 `.py` 依赖）。
- 通过运行时源码变换，将 shrinking 逻辑转为 rolling：
  - 统一使用固定 horizon（`H=96`）；
  - 把 `i_t:` 截断切片替换为滚动切片并做尾部补齐；
  - 保留原 EV 预处理和预测流程，只改输入窗口组织；
  - 放松 shrinking 专用的末日 SOC 严格退出检查（避免 rolling 模式误判失败）。

## 已做性能优化
- 关闭循环内高频调试 CSV 写盘（`Results/Dispatch/0_*`、`1_*`）。
- 默认关闭每日大图生成（`ENABLE_DAILY_PLOTS=False`）。
- Gurobi 参数优化（在 rolling 运行器内统一注入）：
  - `warm_start=True`
  - `MIPGap=5e-3`
  - `Presolve=2`
  - `MIPFocus=1`
  - `Heuristics=0.2`
  - `Cuts=1`
  - `Threads=SOLVER_THREADS`（按机器核数自动设置）

## 基线测试结果（2026-05-28）
- Notebook：`upscaledev_imp_rollingMPC.ipynb`
- 模式：`retail_only`、`full`
- 天数：`[1, 2]`
- 状态：成功
- 耗时：
  - `retail_only`：`67.73 s`
  - `full`：`235.27 s`
  - 合计：`303.08 s`

## 第二轮加速尝试（2026-05-28）
- 试验内容：`warm_start + MIPFocus + Heuristics + Cuts + MIPGap=5e-3`
- 结果：`full` 模式明显变慢（2 天约 `490.52 s`），判定为负优化，已回退。

## 当前稳定版本复测（回退后）
- 模式：`retail_only`、`full`
- 天数：`[1, 2]`
- 耗时：
  - `retail_only`：`68.57 s`
  - `full`：`235.41 s`
  - 合计：`304.06 s`

结论：
- 对当前问题结构，激进 Gurobi 参数并不一定更快；
- 当前保留的有效优化是：rolling 固定窗口、关闭循环内调试写盘、默认关闭每日大图。

## 第三轮加速（显著缩短）
- 目标：优先压缩 `full` 模式运行时间（2 天短测口径一致）。
- 调整：
  - 允许 `status in ['optimal', 'optimal_inaccurate', 'user_limit']`，避免严格 `optimal` 导致过度求解；
  - 在每次 MIP 求解加入：`TimeLimit` 与更宽松 `MIPGap`；
  - 保持 `Threads=SOLVER_THREADS`、关闭高频调试写盘、关闭每日大图。

### 加速结果（full 模式，2 天）
- 旧稳定版：`235.41 s`
- 方案 A（`MIPGap=1e-2`, `TimeLimit=0.8`）：`167.25 s`
- 方案 B（`MIPGap=2e-2`, `TimeLimit=0.6`）：`152.46 s`

### 结论
- 已实现显著缩短：`235.41 -> 152.46 s`，约 **35.2%** 提升。
- 当前 notebook 默认采用方案 B 作为快速配置。

## 告警修复（inaccurate solution）
- 用户反馈：出现 `warning inaccurate solution`。
- 根因：快速配置中引入了 `TimeLimit`，并放宽了状态判定（接受 `optimal_inaccurate` / `user_limit`），会触发精度相关告警。

### 修复动作
- 回退为精度优先配置：
  - 移除 `TimeLimit`；
  - 恢复 `MIPGap=1e-3`；
  - 状态检查恢复为仅接受 `optimal`。

### 修复后复测（full 模式，2 天）
- 耗时：`234.91 s`（与历史稳定值 `~235 s` 基本一致）
- 结论：
  - 告警风险显著降低；
  - 速度与精度存在明确 trade-off：无告警稳态约 `235 s`，激进加速约 `152 s` 但可能出现精度告警。

## 新增：每个 timestep 预测刷新（仅 Perfect/Persistence）
- 范围：先不改 ML forecast 路径（`Fc_AtArrival='MLatArrival'` 直接跳过）。
- 实现方式：在 RT 每个 `i_t` 开始处，新增 step-wise forecast refresh：
  - 对“未到达车辆”刷新 `SessionkWh_RT` 与 `IntervalkWh_max_RT`；
  - `PerfectSessionkWh` 使用当天真实表（作为 perfect 参考）；
  - `PersistenceSessionkWh` 使用 persistence 参考表；
  - 为避免执行态冲突，不重置 `SessionkWh_nEta` 与 `UpperBound`（保持 execution 状态连续）。

### 验证结果（full 模式，2 天）
- 可执行：通过
- 主循环耗时：`242.00 s`
- 说明：该版本的重点是实现“每步刷新预测输入”，不是提速；运行时间相比稳态版略有上升，后续可继续做缓存与向量化优化。

## 仅数据结构优化（不改 solver 参数）
本轮按要求仅改主代码块中的数据结构与结果保存逻辑，不改求解器参数。

### 已改内容
- 新增开关：`SAVE_STEP_DEBUG=False`、`ENABLE_RT_TRACE_TABLE=False`，默认关闭循环内调试写盘和 trace merge。
- `append_df_to_csv` 对 `Results/Dispatch/0_*`、`1_*` 调试路径直接短路，减少高频 I/O。
- RT 阈值更新由“每步全日 max 重算”改为“当前步增量更新”。
- RT 执行阶段减少每步整表 `pd.concat`，仅在日末一次性拼接 `Dispatch[0]`。
- `EnergyDemand_Table_Opt` 每步不再整块转 DataFrame，改为 ndarray 路径取首行执行量。

### 2 天复测（full）
- 优化前（本轮前基线）：`242.00 s`
- 优化后：`239.63 s`
- 提升：约 `0.98%`

### 结论
- 本模型当前主要耗时仍在 MIP 求解本身，数据结构层优化只能带来小幅改善；
- 但本轮优化是“低风险、无语义变化”的稳态优化，已保留在主代码块中。

## 下一步
- 复测本轮参数优化后的 2 天耗时并对比基线。
- 如 `full` 仍偏慢，优先增加分段计时（preprocess / solve / postprocess）定位瓶颈。
- 再考虑“低风险”结构优化（批量写盘、结果保存裁剪、可选降采样诊断输出）。
