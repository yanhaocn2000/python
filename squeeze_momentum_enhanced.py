"""
Squeeze Momentum Indicator - 优化版本
改进：
1. 增强的信号生成逻辑
2. 成交量确认过滤
3. 趋势过滤（EMA）
4. 动态信号强度评分
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional


class SqueezeMomentumEnhanced:
    """Squeeze Momentum增强版指标"""

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
        atr_mult: float = 2.0,
        volume_ma_length: int = 20,
        volume_mult: float = 1.2,
        trend_ema_length: int = 50,
        use_volume_filter: bool = True,
        use_trend_filter: bool = True,
        signal_mode: str = 'enhanced'  # 'strict' 或 'enhanced'
    ):
        """
        参数:
            signal_mode: 信号模式
                - 'strict': 仅在squeeze释放时产生信号（原版）
                - 'enhanced': 基于momentum变化和多重确认（增强版）
            use_volume_filter: 是否使用成交量过滤
            use_trend_filter: 是否使用趋势过滤
        """
        self.bb_length = int(bb_length)
        self.bb_mult = float(bb_mult)
        self.kc_length = int(kc_length)
        self.kc_mult = float(kc_mult)
        self.rsi_length = int(rsi_length)
        self.rsi_overbought = float(rsi_overbought)
        self.rsi_oversold = float(rsi_oversold)
        self.atr_length = int(atr_length)
        self.atr_mult = float(atr_mult)
        self.volume_ma_length = int(volume_ma_length)
        self.volume_mult = float(volume_mult)
        self.trend_ema_length = int(trend_ema_length)
        self.use_volume_filter = use_volume_filter
        self.use_trend_filter = use_trend_filter
        self.signal_mode = signal_mode

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
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=self.kc_length).mean()
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
            x_mean = x.mean()
            y_mean = y.mean()
            b = np.sum((x - x_mean) * (y - y_mean)) / np.sum((x - x_mean) ** 2)
            a = y_mean - b * x_mean
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
        hl_avg = (high + low) / 2
        linreg = self.linear_regression(close - hl_avg, length)
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

    def calculate_ema(self, data: pd.Series, length: int) -> pd.Series:
        """计算EMA"""
        return data.ewm(span=length, adjust=False).mean()

    def calculate_volume_filter(self, volume: pd.Series) -> pd.Series:
        """计算成交量过滤器"""
        volume_ma = volume.rolling(window=self.volume_ma_length).mean()
        volume_above_avg = volume > volume_ma * self.volume_mult
        return volume_above_avg

    def calculate_trend_filter(self, close: pd.Series) -> pd.Series:
        """
        计算趋势过滤器
        返回: 1 (上升趋势), -1 (下降趋势), 0 (无明确趋势)
        """
        ema = self.calculate_ema(close, self.trend_ema_length)
        trend = pd.Series(0, index=close.index)
        trend[close > ema] = 1
        trend[close < ema] = -1
        return trend

    def calculate_signal_strength(
        self,
        momentum: pd.Series,
        rsi: pd.Series,
        squeeze: pd.Series,
        volume_confirmed: Optional[pd.Series] = None,
        trend: Optional[pd.Series] = None
    ) -> pd.Series:
        """
        计算信号强度评分 (0-100)

        评分因素:
        - Momentum强度: 30分
        - RSI位置: 20分
        - Squeeze状态: 20分
        - 成交量确认: 15分
        - 趋势一致: 15分
        """
        score = pd.Series(0.0, index=momentum.index)

        # Momentum强度 (0-30分)
        mom_abs = momentum.abs()
        mom_max = mom_abs.rolling(window=100).max()
        mom_score = (mom_abs / (mom_max + 1e-6)) * 30
        score += mom_score.fillna(0)

        # RSI位置 (0-20分)
        # RSI在40-60之间得分最高
        rsi_dist_from_50 = abs(rsi - 50)
        rsi_score = (1 - rsi_dist_from_50 / 50) * 20
        score += rsi_score.fillna(0).clip(0, 20)

        # Squeeze状态 (0-20分)
        # 刚释放或即将释放得分高
        squeeze_score = pd.Series(0.0, index=squeeze.index)
        squeeze_release = squeeze.shift(1) & ~squeeze
        squeeze_about_to_release = squeeze & ~squeeze.shift(-1).fillna(False)
        squeeze_score[squeeze_release] = 20
        squeeze_score[squeeze_about_to_release] = 15
        squeeze_score[~squeeze] = 10
        score += squeeze_score

        # 成交量确认 (0-15分)
        if volume_confirmed is not None:
            score[volume_confirmed] += 15

        # 趋势一致 (0-15分)
        if trend is not None:
            # Momentum方向和趋势一致得分
            mom_direction = pd.Series(0, index=momentum.index)
            mom_direction[momentum > 0] = 1
            mom_direction[momentum < 0] = -1
            trend_match = (mom_direction == trend)
            score[trend_match] += 15

        return score

    def generate_signals_enhanced(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: Optional[pd.Series] = None
    ) -> pd.DataFrame:
        """
        增强的信号生成逻辑

        特点:
        - 基于Momentum变化和趋势
        - 多重确认机制
        - 信号强度评分
        - 更多交易机会
        """
        # 计算所有指标
        bb_upper, bb_basis, bb_lower = self.calculate_bollinger_bands(close)
        kc_upper, kc_basis, kc_lower = self.calculate_keltner_channels(high, low, close)
        squeeze = (bb_lower > kc_lower) & (bb_upper < kc_upper)
        momentum = self.calculate_momentum(high, low, close, length=20)
        rsi = self.calculate_rsi(close)
        atr = self.calculate_atr(high, low, close)

        # 可选过滤器
        volume_confirmed = None
        if volume is not None and self.use_volume_filter:
            volume_confirmed = self.calculate_volume_filter(volume)

        trend = None
        if self.use_trend_filter:
            trend = self.calculate_trend_filter(close)

        # 计算信号强度
        signal_strength = self.calculate_signal_strength(
            momentum, rsi, squeeze, volume_confirmed, trend
        )

        # 生成信号
        signal = pd.Series(0, index=close.index)

        if self.signal_mode == 'strict':
            # 原版严格模式：仅在squeeze释放时
            squeeze_release = squeeze.shift(1) & ~squeeze
            for i in range(1, len(close)):
                if squeeze_release.iloc[i]:
                    if momentum.iloc[i] > 0 and rsi.iloc[i] < self.rsi_overbought:
                        signal.iloc[i] = 1
                    elif momentum.iloc[i] < 0 and rsi.iloc[i] > self.rsi_oversold:
                        signal.iloc[i] = -1
        else:
            # 增强模式：基于Momentum变化和信号强度
            mom_change = momentum.diff()
            mom_positive = momentum > 0
            mom_negative = momentum < 0
            mom_crossing_up = (momentum > 0) & (momentum.shift(1) <= 0)
            mom_crossing_down = (momentum < 0) & (momentum.shift(1) >= 0)

            for i in range(2, len(close)):
                # 跳过前面的NaN值
                if pd.isna(signal_strength.iloc[i]) or signal_strength.iloc[i] < 40:
                    continue

                # 买入信号条件
                if (mom_crossing_up.iloc[i] or
                    (mom_positive.iloc[i] and mom_change.iloc[i] > 0 and signal_strength.iloc[i] > 60)):

                    # RSI确认
                    if rsi.iloc[i] < self.rsi_overbought and rsi.iloc[i] > self.rsi_oversold:
                        # 趋势确认（如果启用）
                        if not self.use_trend_filter or (trend is not None and trend.iloc[i] >= 0):
                            # 成交量确认（如果启用）
                            if not self.use_volume_filter or (volume_confirmed is not None and volume_confirmed.iloc[i]):
                                signal.iloc[i] = 1
                            elif not self.use_volume_filter:
                                signal.iloc[i] = 1

                # 卖出信号条件
                elif (mom_crossing_down.iloc[i] or
                      (mom_negative.iloc[i] and mom_change.iloc[i] < 0 and signal_strength.iloc[i] > 60)):

                    # RSI确认
                    if rsi.iloc[i] > self.rsi_oversold and rsi.iloc[i] < self.rsi_overbought:
                        # 趋势确认（如果启用）
                        if not self.use_trend_filter or (trend is not None and trend.iloc[i] <= 0):
                            # 成交量确认（如果启用）
                            if not self.use_volume_filter or (volume_confirmed is not None and volume_confirmed.iloc[i]):
                                signal.iloc[i] = -1
                            elif not self.use_volume_filter:
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
            'signal_strength': signal_strength,
            'stop_loss': stop_loss,
            'bb_upper': bb_upper,
            'bb_lower': bb_lower,
            'kc_upper': kc_upper,
            'kc_lower': kc_lower
        })

        if volume is not None:
            result['volume'] = volume
            if volume_confirmed is not None:
                result['volume_confirmed'] = volume_confirmed

        if trend is not None:
            result['trend'] = trend

        return result

    def calculate_trailing_stop(
        self,
        close: pd.Series,
        atr: pd.Series,
        signal: pd.Series
    ) -> pd.Series:
        """计算ATR跟踪止损"""
        stop_loss = pd.Series(index=close.index, dtype=float)
        current_stop = None
        position = 0

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
                new_stop = close.iloc[i] - self.atr_mult * atr.iloc[i]
                if current_stop is not None:
                    current_stop = max(current_stop, new_stop)
                else:
                    current_stop = new_stop
                if close.iloc[i] < current_stop:
                    position = 0
                    current_stop = None
            elif position == -1:
                new_stop = close.iloc[i] + self.atr_mult * atr.iloc[i]
                if current_stop is not None:
                    current_stop = min(current_stop, new_stop)
                else:
                    current_stop = new_stop
                if close.iloc[i] > current_stop:
                    position = 0
                    current_stop = None

            stop_loss.iloc[i] = current_stop if current_stop is not None else np.nan

        return stop_loss


def compare_strategies():
    """比较原版和增强版策略"""
    from squeeze_momentum import SqueezeMomentumIndicator
    import pandas as pd
    import numpy as np

    # 加载数据
    try:
        data = pd.read_csv('btc_4h_data.csv', index_col=0, parse_dates=True)
    except:
        print("请先运行 generate_sample_data.py 生成数据")
        return

    print("策略对比测试")
    print("=" * 80)
    print(f"数据量: {len(data)} 条")

    # 原版策略
    print("\n1. 原版策略（严格模式）")
    print("-" * 80)
    indicator_original = SqueezeMomentumIndicator(
        bb_length=20, bb_mult=2.0,
        kc_length=20, kc_mult=1.5
    )
    signals_original = indicator_original.generate_signals(
        data['high'], data['low'], data['close']
    )
    buy_signals_original = (signals_original['signal'] == 1).sum()
    sell_signals_original = (signals_original['signal'] == -1).sum()
    print(f"买入信号: {buy_signals_original}")
    print(f"卖出信号: {sell_signals_original}")
    print(f"总信号数: {buy_signals_original + sell_signals_original}")

    # 增强版策略
    print("\n2. 增强版策略（无过滤器）")
    print("-" * 80)
    indicator_enhanced_no_filter = SqueezeMomentumEnhanced(
        bb_length=20, bb_mult=2.0,
        kc_length=20, kc_mult=1.5,
        signal_mode='enhanced',
        use_volume_filter=False,
        use_trend_filter=False
    )
    signals_enhanced_no_filter = indicator_enhanced_no_filter.generate_signals_enhanced(
        data['high'], data['low'], data['close'], data['volume']
    )
    buy_signals_enh = (signals_enhanced_no_filter['signal'] == 1).sum()
    sell_signals_enh = (signals_enhanced_no_filter['signal'] == -1).sum()
    print(f"买入信号: {buy_signals_enh}")
    print(f"卖出信号: {sell_signals_enh}")
    print(f"总信号数: {buy_signals_enh + sell_signals_enh}")

    # 增强版策略（带过滤器）
    print("\n3. 增强版策略（带成交量和趋势过滤）")
    print("-" * 80)
    indicator_enhanced_full = SqueezeMomentumEnhanced(
        bb_length=20, bb_mult=2.0,
        kc_length=20, kc_mult=1.5,
        signal_mode='enhanced',
        use_volume_filter=True,
        use_trend_filter=True
    )
    signals_enhanced_full = indicator_enhanced_full.generate_signals_enhanced(
        data['high'], data['low'], data['close'], data['volume']
    )
    buy_signals_full = (signals_enhanced_full['signal'] == 1).sum()
    sell_signals_full = (signals_enhanced_full['signal'] == -1).sum()
    print(f"买入信号: {buy_signals_full}")
    print(f"卖出信号: {sell_signals_full}")
    print(f"总信号数: {buy_signals_full + sell_signals_full}")

    print("\n平均信号强度: {:.1f}".format(signals_enhanced_full['signal_strength'].mean()))


if __name__ == "__main__":
    compare_strategies()
