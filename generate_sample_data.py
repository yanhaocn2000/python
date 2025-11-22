"""
生成真实市场特征的模拟数据
用于演示和测试
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta


def generate_realistic_crypto_data(
    start_date: str = "2023-01-01",
    periods: int = 3000,
    interval: str = "4h",
    initial_price: float = 30000.0,
    volatility: float = 0.03,
    trend: float = 0.0002
) -> pd.DataFrame:
    """
    生成具有真实加密货币市场特征的模拟数据

    参数:
        start_date: 开始日期
        periods: 数据点数量
        interval: 时间间隔
        initial_price: 初始价格
        volatility: 波动率
        trend: 趋势强度

    返回:
        包含OHLCV数据的DataFrame
    """
    np.random.seed(42)

    # 生成时间序列
    start = pd.to_datetime(start_date)
    if interval == "4h":
        freq = "4H"
    elif interval == "1h":
        freq = "1H"
    elif interval == "1d":
        freq = "1D"
    else:
        freq = interval

    dates = pd.date_range(start=start, periods=periods, freq=freq)

    # 生成价格序列（带有趋势和均值回归）
    prices = np.zeros(periods)
    prices[0] = initial_price

    for i in range(1, periods):
        # 随机游走 + 趋势 + 均值回归
        random_return = np.random.normal(trend, volatility)

        # 添加周期性波动（模拟市场周期）
        cycle = 0.001 * np.sin(2 * np.pi * i / 500)

        # 添加突发波动（模拟市场事件）
        if np.random.random() < 0.01:  # 1%概率出现大波动
            random_return *= 3

        prices[i] = prices[i-1] * (1 + random_return + cycle)

        # 防止价格过低
        if prices[i] < initial_price * 0.5:
            prices[i] = initial_price * 0.5 * (1 + abs(random_return))

    # 生成OHLC数据
    data = []
    for i, price in enumerate(prices):
        # 模拟每个K线的波动
        intrabar_volatility = volatility * 0.5
        high_offset = abs(np.random.normal(0, intrabar_volatility))
        low_offset = abs(np.random.normal(0, intrabar_volatility))

        open_price = price * (1 + np.random.normal(0, intrabar_volatility * 0.3))
        high_price = max(open_price, price) * (1 + high_offset)
        low_price = min(open_price, price) * (1 - low_offset)
        close_price = price

        # 确保OHLC关系正确
        high_price = max(high_price, open_price, close_price)
        low_price = min(low_price, open_price, close_price)

        # 生成成交量（与价格波动相关）
        price_change = abs(close_price - open_price) / open_price
        base_volume = 1000 + np.random.exponential(500)
        volume = base_volume * (1 + price_change * 10)

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

    return df


def add_market_regimes(df: pd.DataFrame) -> pd.DataFrame:
    """
    添加不同的市场状态（牛市、熊市、震荡）

    参数:
        df: 原始数据

    返回:
        调整后的数据
    """
    n = len(df)
    regimes = []

    # 定义不同市场状态的区间
    bull_market_1 = (0, int(n * 0.25))          # 牛市
    bear_market = (int(n * 0.25), int(n * 0.45))  # 熊市
    sideways = (int(n * 0.45), int(n * 0.65))     # 震荡
    bull_market_2 = (int(n * 0.65), n)           # 牛市

    for i in range(n):
        if bull_market_1[0] <= i < bull_market_1[1]:
            # 牛市：强趋势上涨
            multiplier = 1 + (i - bull_market_1[0]) / (bull_market_1[1] - bull_market_1[0]) * 0.5
            regimes.append('bull')
        elif bear_market[0] <= i < bear_market[1]:
            # 熊市：趋势下跌
            multiplier = 1.5 - (i - bear_market[0]) / (bear_market[1] - bear_market[0]) * 0.4
            regimes.append('bear')
        elif sideways[0] <= i < sideways[1]:
            # 震荡：横盘
            multiplier = 1.1 + 0.1 * np.sin(2 * np.pi * (i - sideways[0]) / 100)
            regimes.append('sideways')
        else:
            # 牛市2
            multiplier = 1.1 + (i - bull_market_2[0]) / (bull_market_2[1] - bull_market_2[0]) * 0.6
            regimes.append('bull')

        df.iloc[i, df.columns.get_loc('close')] *= multiplier
        df.iloc[i, df.columns.get_loc('open')] *= multiplier
        df.iloc[i, df.columns.get_loc('high')] *= multiplier
        df.iloc[i, df.columns.get_loc('low')] *= multiplier

    return df


def main():
    """生成示例数据"""
    print("生成BTC 4H模拟数据...")
    print("=" * 80)

    # 生成约2年的4小时数据（约3000个数据点）
    df = generate_realistic_crypto_data(
        start_date="2023-01-01",
        periods=3000,
        interval="4h",
        initial_price=30000.0,
        volatility=0.025,  # 2.5%的标准差
        trend=0.0001       # 轻微上涨趋势
    )

    # 添加市场状态
    df = add_market_regimes(df)

    print(f"\n数据量: {len(df)} 条")
    print(f"时间范围: {df.index[0]} 至 {df.index[-1]}")
    print(f"\n最新数据:")
    print(df.tail())

    print(f"\n数据统计:")
    print(df.describe())

    # 保存到CSV
    filename = 'btc_4h_data.csv'
    df.to_csv(filename)
    print(f"\n数据已保存到 {filename}")

    return df


if __name__ == "__main__":
    df = main()
