"""
Squeeze Momentum Indicator (LazyBear) - Python Implementation
结合RSI确认和ATR跟踪止损

Squeeze Momentum指标原理:
1. Squeeze检测: 使用布林带(BB)和肯特纳通道(KC)判断市场挤压状态
2. Momentum: 使用线性回归计算动量
3. 信号: squeeze释放时结合momentum方向产生交易信号
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional


class SqueezeMomentumIndicator:
    """Squeeze Momentum指标实现"""

    def __init__(
        self,
        bb_length: int = 20,
        bb_mult: float = 2.0,
        kc_length: int = 20,
        kc_mult: float = 1.5,
        rsi_length: int = 14,
        rsi_overbought: float = 70,
        rsi_oversold: float = 30,
        atr_length: int = 14,
        atr_mult: float = 2.0
    ):
        """
        参数:
            bb_length: 布林带周期
            bb_mult: 布林带标准差倍数
            kc_length: 肯特纳通道周期
            kc_mult: 肯特纳通道ATR倍数
            rsi_length: RSI周期
            rsi_overbought: RSI超买阈值
            rsi_oversold: RSI超卖阈值
            atr_length: ATR周期
            atr_mult: ATR止损倍数
        """
        # 确保整数参数是整数类型
        self.bb_length = int(bb_length)
        self.bb_mult = float(bb_mult)
        self.kc_length = int(kc_length)
        self.kc_mult = float(kc_mult)
        self.rsi_length = int(rsi_length)
        self.rsi_overbought = float(rsi_overbought)
        self.rsi_oversold = float(rsi_oversold)
        self.atr_length = int(atr_length)
        self.atr_mult = float(atr_mult)

    def calculate_bollinger_bands(self, data: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算布林带"""
        basis = data.rolling(window=self.bb_length).mean()
        dev = data.rolling(window=self.bb_length).std()
        upper = basis + self.bb_mult * dev
        lower = basis - self.bb_mult * dev
        return upper, basis, lower

    def calculate_keltner_channels(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算肯特纳通道"""
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # ATR
        atr = tr.rolling(window=self.kc_length).mean()

        # KC
        basis = close.rolling(window=self.kc_length).mean()
        upper = basis + self.kc_mult * atr
        lower = basis - self.kc_mult * atr

        return upper, basis, lower

    def linear_regression(self, data: pd.Series, length: int) -> pd.Series:
        """计算线性回归值"""
        result = pd.Series(index=data.index, dtype=float)

        for i in range(length - 1, len(data)):
            y = data.iloc[i - length + 1:i + 1].values
            x = np.arange(length)

            # 线性回归: y = a + b*x
            x_mean = x.mean()
            y_mean = y.mean()

            b = np.sum((x - x_mean) * (y - y_mean)) / np.sum((x - x_mean) ** 2)
            a = y_mean - b * x_mean

            # 预测当前值
            result.iloc[i] = a + b * (length - 1)

        return result

    def calculate_momentum(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        length: int = 20
    ) -> pd.Series:
        """计算Squeeze Momentum值"""
        # 使用最高价和最低价的平均值
        hl_avg = (high + low) / 2

        # 线性回归
        linreg = self.linear_regression(close - hl_avg, length)

        # Momentum = 当前值 - 移动平均
        momentum = linreg - linreg.rolling(window=length).mean()

        return momentum

    def calculate_rsi(self, close: pd.Series) -> pd.Series:
        """计算RSI指标"""
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_length).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_length).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def calculate_atr(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series
    ) -> pd.Series:
        """计算ATR指标"""
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr = tr.rolling(window=self.atr_length).mean()

        return atr

    def calculate_trailing_stop(
        self,
        close: pd.Series,
        atr: pd.Series,
        signal: pd.Series
    ) -> pd.Series:
        """计算ATR跟踪止损"""
        stop_loss = pd.Series(index=close.index, dtype=float)
        current_stop = None
        position = 0  # 0: 无仓位, 1: 多头, -1: 空头

        for i in range(len(close)):
            if pd.isna(signal.iloc[i]):
                stop_loss.iloc[i] = np.nan
                continue

            # 多头信号
            if signal.iloc[i] == 1:
                position = 1
                current_stop = close.iloc[i] - self.atr_mult * atr.iloc[i]
            # 空头信号
            elif signal.iloc[i] == -1:
                position = -1
                current_stop = close.iloc[i] + self.atr_mult * atr.iloc[i]
            # 无新信号，更新止损
            elif position == 1:
                # 多头止损只能上移
                new_stop = close.iloc[i] - self.atr_mult * atr.iloc[i]
                if current_stop is not None:
                    current_stop = max(current_stop, new_stop)
                else:
                    current_stop = new_stop

                # 检查是否触及止损
                if close.iloc[i] < current_stop:
                    position = 0
                    current_stop = None
            elif position == -1:
                # 空头止损只能下移
                new_stop = close.iloc[i] + self.atr_mult * atr.iloc[i]
                if current_stop is not None:
                    current_stop = min(current_stop, new_stop)
                else:
                    current_stop = new_stop

                # 检查是否触及止损
                if close.iloc[i] > current_stop:
                    position = 0
                    current_stop = None

            stop_loss.iloc[i] = current_stop if current_stop is not None else np.nan

        return stop_loss

    def generate_signals(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series
    ) -> pd.DataFrame:
        """
        生成交易信号

        返回:
            DataFrame包含:
            - squeeze: squeeze状态 (True/False)
            - momentum: 动量值
            - rsi: RSI值
            - signal: 交易信号 (1: 买入, -1: 卖出, 0: 无信号)
            - atr: ATR值
            - stop_loss: 跟踪止损价格
        """
        # 计算布林带
        bb_upper, bb_basis, bb_lower = self.calculate_bollinger_bands(close)

        # 计算肯特纳通道
        kc_upper, kc_basis, kc_lower = self.calculate_keltner_channels(high, low, close)

        # Squeeze状态: BB在KC内部
        squeeze = (bb_lower > kc_lower) & (bb_upper < kc_upper)

        # 计算Momentum
        momentum = self.calculate_momentum(high, low, close, length=20)

        # 计算RSI
        rsi = self.calculate_rsi(close)

        # 计算ATR
        atr = self.calculate_atr(high, low, close)

        # 生成信号
        signal = pd.Series(0, index=close.index)

        # Squeeze释放检测
        squeeze_release = squeeze.shift(1) & ~squeeze

        for i in range(1, len(close)):
            if squeeze_release.iloc[i]:
                # Squeeze释放 + Momentum方向 + RSI确认
                if momentum.iloc[i] > 0 and rsi.iloc[i] < self.rsi_overbought:
                    # 多头信号: momentum向上且RSI未超买
                    signal.iloc[i] = 1
                elif momentum.iloc[i] < 0 and rsi.iloc[i] > self.rsi_oversold:
                    # 空头信号: momentum向下且RSI未超卖
                    signal.iloc[i] = -1

        # 计算跟踪止损
        stop_loss = self.calculate_trailing_stop(close, atr, signal)

        # 组合结果
        result = pd.DataFrame({
            'squeeze': squeeze,
            'momentum': momentum,
            'rsi': rsi,
            'atr': atr,
            'signal': signal,
            'stop_loss': stop_loss,
            'bb_upper': bb_upper,
            'bb_lower': bb_lower,
            'kc_upper': kc_upper,
            'kc_lower': kc_lower
        })

        return result


def example_usage():
    """示例使用"""
    # 生成示例数据
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=200, freq='D')

    # 模拟价格数据
    close = pd.Series(100 + np.cumsum(np.random.randn(200) * 2), index=dates)
    high = close + np.random.rand(200) * 2
    low = close - np.random.rand(200) * 2

    # 创建指标实例
    indicator = SqueezeMomentumIndicator(
        bb_length=20,
        bb_mult=2.0,
        kc_length=20,
        kc_mult=1.5,
        rsi_length=14,
        rsi_overbought=70,
        rsi_oversold=30,
        atr_length=14,
        atr_mult=2.0
    )

    # 生成信号
    signals = indicator.generate_signals(high, low, close)

    # 打印结果
    print("Squeeze Momentum Indicator Results:")
    print("=" * 80)
    print(signals.tail(20))

    # 统计信号
    buy_signals = (signals['signal'] == 1).sum()
    sell_signals = (signals['signal'] == -1).sum()
    squeeze_periods = signals['squeeze'].sum()

    print("\n" + "=" * 80)
    print(f"总买入信号: {buy_signals}")
    print(f"总卖出信号: {sell_signals}")
    print(f"Squeeze周期数: {squeeze_periods}")
    print(f"平均RSI: {signals['rsi'].mean():.2f}")
    print(f"平均ATR: {signals['atr'].mean():.2f}")

    return signals


if __name__ == "__main__":
    signals = example_usage()
