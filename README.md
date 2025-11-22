# Squeeze Momentum Indicator - Python实现

基于LazyBear的Squeeze Momentum指标的Python实现，结合RSI确认和ATR跟踪止损功能。

## 功能特点

### 1. Squeeze Momentum核心指标
- **Squeeze检测**: 使用布林带(Bollinger Bands)和肯特纳通道(Keltner Channels)
  - Squeeze状态: BB在KC内部 → 市场处于低波动挤压状态
  - Squeeze释放: BB突破KC → 市场波动性增加，可能产生趋势

- **Momentum计算**: 基于线性回归的动量指标
  - 使用价格的线性回归值计算动量
  - 正动量表示上升趋势，负动量表示下降趋势

### 2. RSI确认
- 买入信号需要RSI < 超买阈值(默认70)
- 卖出信号需要RSI > 超卖阈值(默认30)
- 避免在超买/超卖极端区域进场

### 3. ATR跟踪止损
- 使用ATR(Average True Range)动态调整止损位
- 多头止损只能上移，空头止损只能下移
- 默认使用2倍ATR作为止损距离

## 安装

```bash
pip install -r requirements.txt
```

## 使用方法

### 基本使用

```python
import pandas as pd
from squeeze_momentum import SqueezeMomentumIndicator

# 准备数据 (需要high, low, close)
data = pd.DataFrame({
    'high': [...],
    'low': [...],
    'close': [...]
})

# 创建指标实例
indicator = SqueezeMomentumIndicator(
    bb_length=20,        # 布林带周期
    bb_mult=2.0,         # 布林带标准差倍数
    kc_length=20,        # 肯特纳通道周期
    kc_mult=1.5,         # 肯特纳通道ATR倍数
    rsi_length=14,       # RSI周期
    rsi_overbought=70,   # RSI超买阈值
    rsi_oversold=30,     # RSI超卖阈值
    atr_length=14,       # ATR周期
    atr_mult=2.0         # ATR止损倍数
)

# 生成信号
signals = indicator.generate_signals(
    data['high'],
    data['low'],
    data['close']
)

# 查看结果
print(signals[['squeeze', 'momentum', 'rsi', 'signal', 'stop_loss']])
```

### 回测示例

```python
from backtest_example import SqueezeBacktester

# 创建回测器
backtester = SqueezeBacktester(
    initial_capital=10000,  # 初始资金
    commission=0.001,       # 手续费 0.1%
    slippage=0.0005        # 滑点 0.05%
)

# 运行回测
results, trades = backtester.run_backtest(data, signals)

# 计算指标
metrics = backtester.calculate_metrics(results, trades)

print(f"总收益率: {metrics['total_return']:.2f}%")
print(f"最大回撤: {metrics['max_drawdown']:.2f}%")
print(f"胜率: {metrics['win_rate']:.2f}%")
print(f"Sharpe比率: {metrics['sharpe_ratio']:.2f}")
```

### 运行示例

```bash
# 运行指标示例
python squeeze_momentum.py

# 运行回测示例
python backtest_example.py
```

## 信号说明

### 返回的DataFrame包含以下列：

- `squeeze`: 布尔值，True表示市场处于squeeze状态
- `momentum`: 动量值，正值看涨，负值看跌
- `rsi`: RSI指标值 (0-100)
- `atr`: ATR值，用于止损计算
- `signal`: 交易信号
  - `1`: 买入信号 (Squeeze释放 + 正动量 + RSI未超买)
  - `-1`: 卖出信号 (Squeeze释放 + 负动量 + RSI未超卖)
  - `0`: 无信号
- `stop_loss`: 当前止损价格
- `bb_upper`, `bb_lower`: 布林带上下轨
- `kc_upper`, `kc_lower`: 肯特纳通道上下轨

## 交易逻辑

### 买入条件
1. Squeeze状态释放 (前一周期为squeeze，当前周期不是)
2. Momentum > 0 (上升动量)
3. RSI < 超买阈值 (避免追高)

### 卖出条件
1. Squeeze状态释放
2. Momentum < 0 (下降动量)
3. RSI > 超卖阈值 (避免杀跌)

### 止损条件
- 多头: 价格跌破止损线 (入场价 - ATR × 倍数)
- 空头: 价格突破止损线 (入场价 + ATR × 倍数)
- 止损线动态跟踪价格移动

## 参数调优建议

### 保守策略
```python
indicator = SqueezeMomentumIndicator(
    bb_mult=2.5,          # 更宽的布林带
    kc_mult=2.0,          # 更宽的KC
    rsi_overbought=65,    # 更严格的超买标准
    rsi_oversold=35,      # 更严格的超卖标准
    atr_mult=2.5          # 更宽的止损
)
```

### 激进策略
```python
indicator = SqueezeMomentumIndicator(
    bb_mult=1.5,          # 更窄的布林带
    kc_mult=1.0,          # 更窄的KC
    rsi_overbought=75,    # 更宽松的超买标准
    rsi_oversold=25,      # 更宽松的超卖标准
    atr_mult=1.5          # 更紧的止损
)
```

### 短线交易
```python
indicator = SqueezeMomentumIndicator(
    bb_length=10,         # 更短的周期
    kc_length=10,
    rsi_length=7,
    atr_length=7
)
```

### 长线交易
```python
indicator = SqueezeMomentumIndicator(
    bb_length=50,         # 更长的周期
    kc_length=50,
    rsi_length=21,
    atr_length=21
)
```

## 注意事项

1. **数据要求**: 需要足够的历史数据来计算指标（至少50-100根K线）
2. **市场环境**: Squeeze指标在趋势市场中表现更好，在震荡市可能产生较多假信号
3. **参数优化**: 建议根据具体市场和交易品种进行参数优化
4. **风险管理**: 始终使用止损，控制单笔交易风险
5. **组合使用**: 可以结合其他指标（如成交量、MACD等）进一步确认信号

## 模型验证和防止过拟合

### 完整验证流程

本项目包含严格的模型验证系统，防止过拟合：

```bash
# 生成测试数据
python generate_sample_data.py

# 运行完整验证（包含参数优化和Walk-Forward分析）
python model_validation.py
```

验证流程包括：
1. **数据分割**：训练集(70%) / 验证集(15%) / 测试集(15%)
2. **参数优化**：在训练集上进行网格搜索
3. **验证集测试**：验证参数的泛化能力
4. **测试集评估**：最终的out-of-sample测试
5. **过拟合检测**：比较训练集和测试集性能
6. **Walk-Forward分析**：时间序列交叉验证

详细说明请参考 [VALIDATION_GUIDE.md](VALIDATION_GUIDE.md)

### 从币安获取真实数据

```python
from binance_data_fetcher import BinanceDataFetcher

fetcher = BinanceDataFetcher()
data = fetcher.get_historical_klines(
    symbol='BTCUSDT',
    interval='4h',
    start_date='2023-01-01'
)
fetcher.save_to_csv(data, 'btc_4h_data.csv')
```

## 文件说明

### 核心指标
- `squeeze_momentum.py`: Squeeze Momentum指标实现
- `backtest_example.py`: 基础回测系统和示例

### 数据获取
- `binance_data_fetcher.py`: 币安API数据获取器
- `generate_sample_data.py`: 生成真实市场特征的模拟数据

### 模型验证
- `model_validation.py`: 完整的模型验证系统（防止过拟合）
- `VALIDATION_GUIDE.md`: 模型验证详细指南

### 其他
- `README.md`: 本说明文档
- `requirements.txt`: Python依赖包

## 重要提示

⚠️ **关于过拟合**：
- 本项目的验证系统检测到训练集和测试集存在性能差异
- 这是正常现象，说明验证系统正确工作
- 使用Walk-Forward分析获得更可靠的性能评估
- 在实盘前务必进行充分的模拟交易测试

⚠️ **风险警告**：
- 历史表现不代表未来收益
- 加密货币交易存在高风险
- 仅用于教育和研究目的
- 实盘交易前请充分测试并做好风险管理

## License

MIT License
