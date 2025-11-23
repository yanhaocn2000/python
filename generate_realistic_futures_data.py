"""
生成基于真实市场特征的高质量模拟数据
使用历史价格统计特征和市场周期模式
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple


class RealisticCryptoDataGenerator:
    """基于真实统计特征的数据生成器"""

    # 基于真实历史数据的统计特征（2019-2024）
    BTC_STATS = {
        'start_price': 10000,
        'end_price': 43000,
        'annual_return': 0.35,  # 35%年化收益
        'volatility': 0.04,  # 4%日波动率（4h换算）
        'max_drawdown': 0.75,  # 最大回撤75%
        'sharpe_ratio': 1.2,
        'skewness': 0.5,  # 正偏态
        'kurtosis': 5.0,  # 高峰度
    }

    ETH_STATS = {
        'start_price': 180,
        'end_price': 2200,
        'annual_return': 0.50,  # 50%年化收益
        'volatility': 0.05,  # 5%日波动率
        'max_drawdown': 0.80,
        'sharpe_ratio': 1.0,
        'skewness': 0.6,
        'kurtosis': 6.0,
    }

    def __init__(self, symbol: str = 'BTC'):
        self.stats = self.BTC_STATS if symbol == 'BTC' else self.ETH_STATS
        self.symbol = symbol

    def generate_returns(self, n_periods: int) -> np.ndarray:
        """
        生成符合真实统计特征的收益率序列

        特点：
        - 正确的波动率
        - 波动率聚类
        - 趋势和均值回归
        """
        # 基础随机收益（4小时周期）
        base_volatility = self.stats['volatility'] * 0.3  # 调整为4小时
        returns = np.random.normal(0, base_volatility, n_periods)

        # 波动率聚类（GARCH效应）
        volatility = np.ones(n_periods) * base_volatility
        for i in range(1, n_periods):
            volatility[i] = (
                0.05 * base_volatility +
                0.10 * abs(returns[i-1]) +
                0.85 * volatility[i-1]
            )
            returns[i] = np.random.normal(0, volatility[i])

        # 添加温和的趋势成分
        total_return = np.log(self.stats['end_price'] / self.stats['start_price'])
        trend_per_period = total_return / n_periods
        trend = np.full(n_periods, trend_per_period)

        # 添加温和的均值回归
        cumulative = np.cumsum(returns)
        mean_reversion = -0.005 * cumulative  # 减小均值回归强度

        # 组合所有成分，添加限制
        final_returns = returns + trend + mean_reversion

        # 限制极端值，避免溢出
        final_returns = np.clip(final_returns, -0.2, 0.2)  # 限制单周期收益±20%

        return final_returns

    def add_market_regimes(self, prices: np.ndarray) -> np.ndarray:
        """
        添加真实的市场状态变化

        状态：
        - 牛市（强上涨）
        - 熊市（下跌）
        - 震荡（横盘）
        - 崩盘（急跌）
        """
        n = len(prices)
        adjusted_prices = prices.copy()

        # 定义市场周期（基于2019-2024真实周期）
        cycles = [
            (0, int(n * 0.15), 'sideways', 1.0),      # 2019年底震荡
            (int(n * 0.15), int(n * 0.30), 'bull', 1.8),  # 2020年牛市
            (int(n * 0.30), int(n * 0.35), 'crash', 0.5),  # 2020年3月暴跌
            (int(n * 0.35), int(n * 0.55), 'bull', 2.2),  # 2020-2021大牛市
            (int(n * 0.55), int(n * 0.70), 'bear', 0.6),  # 2022年熊市
            (int(n * 0.70), int(n * 0.85), 'sideways', 0.9),  # 2023年震荡
            (int(n * 0.85), n, 'bull', 1.4),          # 2024年回升
        ]

        base_price = prices[0]
        for start_idx, end_idx, regime, multiplier in cycles:
            segment_length = end_idx - start_idx
            if segment_length <= 0:
                continue

            if regime == 'bull':
                # 牛市：稳定上涨
                growth = np.linspace(1.0, multiplier, segment_length)
                adjusted_prices[start_idx:end_idx] *= growth

            elif regime == 'bear':
                # 熊市：逐步下跌
                decline = np.linspace(1.0, multiplier, segment_length)
                adjusted_prices[start_idx:end_idx] *= decline

            elif regime == 'crash':
                # 崩盘：快速下跌后反弹
                crash_point = segment_length // 3
                crash_pattern = np.concatenate([
                    np.linspace(1.0, multiplier, crash_point),
                    np.linspace(multiplier, 0.8, segment_length - crash_point)
                ])
                adjusted_prices[start_idx:end_idx] *= crash_pattern

            elif regime == 'sideways':
                # 震荡：小幅波动
                noise = np.random.normal(1.0, 0.02, segment_length)
                adjusted_prices[start_idx:end_idx] *= noise

        return adjusted_prices

    def generate_ohlcv(
        self,
        start_date: str = '2019-09-01',
        end_date: str = '2024-11-23',
        interval_hours: int = 4
    ) -> pd.DataFrame:
        """
        生成完整的OHLCV数据

        参数:
            start_date: 开始日期
            end_date: 结束日期
            interval_hours: K线间隔（小时）

        返回:
            完整的OHLCV DataFrame
        """
        # 计算需要的K线数量
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        total_hours = (end - start).total_seconds() / 3600
        n_periods = int(total_hours / interval_hours)

        print(f"生成 {self.symbol} 数据...")
        print(f"  时间范围: {start_date} 至 {end_date}")
        print(f"  K线间隔: {interval_hours}小时")
        print(f"  数据点数: {n_periods}")

        # 生成时间索引
        dates = pd.date_range(start=start, periods=n_periods, freq=f'{interval_hours}H')

        # 生成收益率序列
        returns = self.generate_returns(n_periods)

        # 转换为价格
        prices = self.stats['start_price'] * np.exp(np.cumsum(returns))

        # 添加市场周期
        prices = self.add_market_regimes(prices)

        # 生成OHLC
        data = []
        for i, price in enumerate(prices):
            # K线内波动
            volatility_mult = np.random.uniform(0.5, 1.5)
            intra_volatility = self.stats['volatility'] * 0.3 * volatility_mult

            # Open
            if i == 0:
                open_price = self.stats['start_price']
            else:
                open_price = prices[i-1] * (1 + np.random.normal(0, intra_volatility * 0.5))

            # Close
            close_price = price

            # High and Low
            high_offset = abs(np.random.normal(0, intra_volatility))
            low_offset = abs(np.random.normal(0, intra_volatility))

            high_price = max(open_price, close_price) * (1 + high_offset)
            low_price = min(open_price, close_price) * (1 - low_offset)

            # Volume（与价格变化和波动率相关）
            price_change = abs(close_price - open_price) / open_price
            base_volume = 1000 + np.random.exponential(2000)
            volume = base_volume * (1 + price_change * 20) * volatility_mult

            data.append({
                'timestamp': dates[i],
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume
            })

        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)

        # 数据质量检查
        print(f"\n数据统计:")
        print(f"  起始价格: ${df['close'].iloc[0]:,.2f}")
        print(f"  结束价格: ${df['close'].iloc[-1]:,.2f}")
        print(f"  最高价格: ${df['high'].max():,.2f}")
        print(f"  最低价格: ${df['low'].min():,.2f}")
        print(f"  总收益率: {(df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100:.1f}%")

        return df


def generate_full_dataset():
    """生成完整的BTC和ETH数据集"""
    print("生成真实特征的加密货币数据")
    print("=" * 80)

    # BTC数据
    btc_generator = RealisticCryptoDataGenerator('BTC')
    btc_data = btc_generator.generate_ohlcv(
        start_date='2019-09-01',
        end_date='2024-11-23',
        interval_hours=4
    )
    btc_data.to_csv('btcusdt_futures_4h.csv')
    print(f"✓ BTC数据已保存")

    print(f"\n{'=' * 80}\n")

    # ETH数据
    eth_generator = RealisticCryptoDataGenerator('ETH')
    eth_data = eth_generator.generate_ohlcv(
        start_date='2019-09-01',
        end_date='2024-11-23',
        interval_hours=4
    )
    eth_data.to_csv('ethusdt_futures_4h.csv')
    print(f"✓ ETH数据已保存")

    print(f"\n{'=' * 80}")
    print("数据生成完成")
    print(f"{'=' * 80}")

    return btc_data, eth_data


if __name__ == "__main__":
    btc, eth = generate_full_dataset()
