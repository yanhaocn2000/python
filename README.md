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

## 文件说明

- `squeeze_momentum.py`: 主要指标实现
- `backtest_example.py`: 回测系统和示例
- `README.md`: 本说明文档
- `requirements.txt`: Python依赖包

## License

MIT License
