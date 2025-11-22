# Squeeze Momentum策略验证指南

本指南介绍如何使用完整的模型验证系统来避免过拟合并评估策略的真实性能。

## 概述

本项目实现了严格的模型验证流程，包括：
- **数据分割**：训练集/验证集/测试集分离
- **参数优化**：网格搜索寻找最优参数
- **Walk-Forward分析**：时间序列交叉验证
- **过拟合检测**：比较训练集和测试集性能

## 快速开始

### 1. 生成或获取数据

#### 选项A：使用模拟数据（推荐用于测试）

```bash
python generate_sample_data.py
```

这会生成具有真实市场特征的BTC 4H模拟数据，包括：
- 牛市、熊市、震荡等不同市场状态
- 真实的价格波动特征
- 约3000个数据点（约1.5年的4小时数据）

#### 选项B：从币安获取真实数据

如果币安API可访问：

```python
from binance_data_fetcher import BinanceDataFetcher
from datetime import datetime, timedelta

fetcher = BinanceDataFetcher()
start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')

data = fetcher.get_historical_klines(
    symbol='BTCUSDT',
    interval='4h',
    start_date=start_date
)

fetcher.save_to_csv(data, 'btc_4h_data.csv')
```

#### 选项C：使用CSV文件

如果您有自己的数据，确保CSV格式如下：
```
timestamp,open,high,low,close,volume
2023-01-01 00:00:00,16500.0,16550.0,16450.0,16520.0,1234.5
...
```

### 2. 运行完整验证

```bash
python model_validation.py
```

这个脚本会自动执行以下步骤：

## 详细验证流程

### 步骤1：数据分割

数据被分为三个部分：
- **训练集（70%）**：用于参数优化
- **验证集（15%）**：用于参数选择和调优
- **测试集（15%）**：用于最终性能评估（从未在优化中使用）

```python
from model_validation import ModelValidator

validator = ModelValidator()
splits = validator.split_data(data, method='simple')
```

### 步骤2：参数优化

在训练集上进行网格搜索：

```python
param_grid = {
    'bb_length': [15, 20, 25],      # 布林带周期
    'bb_mult': [1.5, 2.0, 2.5],     # 布林带倍数
    'kc_length': [15, 20, 25],      # KC周期
    'kc_mult': [1.0, 1.5, 2.0],     # KC倍数
    'rsi_length': [14],              # RSI周期
    'atr_mult': [2.0]                # ATR止损倍数
}

best_params, results = validator.optimize_parameters(
    splits['train'],
    param_grid
)
```

优化目标：最大化Sharpe比率

### 步骤3：验证集测试

使用最优参数在验证集上测试：

```python
val_metrics = validator.validate_model(
    splits['validation'],
    best_params,
    "验证集"
)
```

### 步骤4：测试集评估

最终在完全独立的测试集上评估：

```python
test_metrics = validator.validate_model(
    splits['test'],
    best_params,
    "测试集"
)
```

### 步骤5：过拟合检测

比较训练集和测试集性能：

```python
overfitting = validator.detect_overfitting(
    train_metrics,
    test_metrics,
    threshold=0.3  # 30%性能下降阈值
)
```

**判断标准**：
- 如果测试集性能下降 > 30%，可能存在过拟合
- Sharpe比率、收益率、胜率都会被检查

### 步骤6：Walk-Forward分析

最强的防过拟合方法，模拟真实交易：

```python
wf_results = validator.walk_forward_analysis(
    data,
    param_grid,
    n_splits=5
)
```

**工作原理**：
1. 将数据分成5个时间段
2. 每个时间段：
   - 在前面的数据上优化参数
   - 在后面的数据上测试
3. 所有时间段的测试结果都是out-of-sample

这模拟了真实交易中定期重新优化参数的情况。

## 结果解读

### 性能指标

- **总收益率**：策略的总盈亏百分比
- **最大回撤**：从峰值到谷值的最大跌幅
- **Sharpe比率**：风险调整后收益（> 1.0 为好，> 2.0 为优秀）
- **胜率**：盈利交易占比
- **盈亏比**：平均盈利 / 平均亏损

### 过拟合信号

⚠️ **警告信号**：
- 训练集Sharpe > 3.0，测试集Sharpe < 1.0
- 训练集收益率 >> 测试集收益率（差异 > 50%）
- 胜率在测试集大幅下降
- Walk-Forward结果方差很大

✓ **健康信号**：
- 训练集和测试集性能接近
- Walk-Forward所有fold都有正收益
- Sharpe比率稳定在1.0-2.0之间
- 胜率在50%-60%之间且稳定

### 输出文件

运行后会生成两个CSV文件：

1. **optimization_results.csv**
   - 所有参数组合的结果
   - 可用于分析参数敏感性

2. **walk_forward_results.csv**
   - 每个fold的out-of-sample结果
   - 最重要的性能指标

## 进阶使用

### 自定义参数网格

```python
# 更精细的搜索
param_grid = {
    'bb_length': [10, 15, 20, 25, 30],
    'bb_mult': [1.5, 2.0, 2.5, 3.0],
    'kc_length': [10, 15, 20, 25, 30],
    'kc_mult': [1.0, 1.5, 2.0, 2.5],
    'rsi_overbought': [65, 70, 75],
    'rsi_oversold': [25, 30, 35],
    'atr_mult': [1.5, 2.0, 2.5, 3.0]
}
```

### 调整数据分割比例

```python
validator = ModelValidator()
validator.train_ratio = 0.6
validator.validation_ratio = 0.2
validator.test_ratio = 0.2
```

### 更多Walk-Forward折数

```python
wf_results = validator.walk_forward_analysis(
    data,
    param_grid,
    n_splits=10  # 更多的fold，更严格的测试
)
```

## 避免过拟合的最佳实践

### 1. 使用足够的数据
- 最少1-2年的历史数据
- 确保包含不同市场状态（牛市、熊市、震荡）

### 2. 保持模型简单
- 不要使用太多参数
- 避免过度优化单个参数

### 3. 使用稳健的指标
- 优先考虑Sharpe比率而不是纯收益率
- 关注风险指标（最大回撤、胜率）

### 4. 进行时间序列验证
- 始终使用Walk-Forward分析
- 不要随机打乱时间序列数据

### 5. 合理的性能预期
- 真实交易中Sharpe > 1.0就很好
- 年化收益30%-50%是合理的
- 如果回测收益率 > 1000%，很可能过拟合

### 6. 考虑交易成本
- 包含手续费和滑点
- 高频交易策略对成本更敏感

### 7. 样本外测试
- 测试集绝对不能用于任何优化
- 可以保留一部分最新数据作为"真正的"未来数据

## 示例结果解读

### 案例1：健康的策略

```
数据集     收益率    最大回撤   Sharpe   胜率
训练集     45.2%    -15.3%     1.85    55.2%
验证集     38.7%    -18.1%     1.62    52.8%
测试集     41.3%    -16.5%     1.73    54.1%

过拟合风险评估: ✓ 低风险 - 模型泛化性能良好
```

**分析**：性能稳定，各数据集表现接近，可以谨慎使用。

### 案例2：过拟合的策略

```
数据集     收益率    最大回撤   Sharpe   胜率
训练集    523.8%    -45.2%     3.45    72.3%
验证集     12.3%    -35.6%     0.42    48.1%
测试集     -5.7%    -42.3%    -0.15    45.2%

过拟合风险评估: ⚠️ 高风险 - 模型可能存在过拟合
```

**分析**：明显过拟合，训练集表现异常好，但测试集失败。不应使用此策略。

## 常见问题

### Q: Walk-Forward分析需要多长时间？
A: 取决于参数网格大小和数据量。通常5-30分钟。可以先用小网格测试。

### Q: 多少条数据才够？
A: 建议至少1000-2000个数据点。4小时K线的话，约半年到一年的数据。

### Q: 测试集表现比训练集好，是什么原因？
A: 可能是：1) 测试期市场环境更适合策略 2) 随机波动 3) 数据量不够。需要更多测试。

### Q: 如何处理策略在某些市场失效？
A: 1) 添加市场状态过滤 2) 使用多个策略组合 3) 动态调整参数。

### Q: Sharpe比率多少算好？
A: > 1.0 可接受，> 1.5 良好，> 2.0 优秀，> 3.0 需要警惕（可能过拟合）。

## 下一步

1. 运行完整验证，检查结果
2. 如果发现过拟合，调整参数范围或简化模型
3. 在模拟账户上实盘测试
4. 小资金实盘验证
5. 逐步扩大规模

## 警告

⚠️ **重要提示**：
- 历史表现不代表未来收益
- 即使通过所有验证，实盘仍可能亏损
- 始终使用风险管理和止损
- 不要投入超过你能承受损失的资金
