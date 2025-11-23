"""
跨币种测试脚本
下载多个币种的数据并进行策略验证
"""

import pandas as pd
from datetime import datetime, timedelta
from binance_data_fetcher import BinanceDataFetcher
from generate_sample_data import generate_realistic_crypto_data


def fetch_crypto_data(symbol='ETHUSDT', days=730):
    """
    获取加密货币数据

    如果API可用则从币安获取真实数据，否则生成模拟数据
    """
    fetcher = BinanceDataFetcher()

    try:
        print(f"\n尝试从币安获取 {symbol} 数据...")
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        data = fetcher.get_historical_klines(
            symbol=symbol,
            interval='4h',
            start_date=start_date
        )

        print(f"✓ 成功从币安获取 {len(data)} 条真实数据")
        return data, 'real'

    except Exception as e:
        print(f"✗ 币安API获取失败: {e}")
        print(f"生成 {symbol} 模拟数据...")

        # 根据币种设置不同的初始价格和波动率
        symbol_configs = {
            'ETHUSDT': {'initial_price': 2000, 'volatility': 0.035},
            'BTCUSDT': {'initial_price': 30000, 'volatility': 0.025},
            'BNBUSDT': {'initial_price': 300, 'volatility': 0.04},
            'ADAUSDT': {'initial_price': 0.5, 'volatility': 0.045},
            'SOLUSDT': {'initial_price': 50, 'volatility': 0.05}
        }

        config = symbol_configs.get(symbol, {'initial_price': 100, 'volatility': 0.03})

        data = generate_realistic_crypto_data(
            start_date="2023-01-01",
            periods=3000,
            interval="4h",
            initial_price=config['initial_price'],
            volatility=config['volatility'],
            trend=0.0001
        )

        print(f"✓ 生成 {len(data)} 条模拟数据")
        return data, 'simulated'


def main():
    """下载多个币种的数据"""
    symbols = ['ETHUSDT', 'BTCUSDT']

    for symbol in symbols:
        print(f"\n{'=' * 80}")
        print(f"处理 {symbol}")
        print(f"{'=' * 80}")

        data, data_type = fetch_crypto_data(symbol, days=730)

        # 保存数据
        filename = f"{symbol.lower()}_4h_data.csv"
        data.to_csv(filename)

        print(f"\n数据统计:")
        print(f"  时间范围: {data.index[0]} 至 {data.index[-1]}")
        print(f"  数据量: {len(data)} 条")
        print(f"  数据类型: {data_type}")
        print(f"  价格范围: ${data['close'].min():.2f} - ${data['close'].max():.2f}")
        print(f"  平均价格: ${data['close'].mean():.2f}")
        print(f"  已保存到: {filename}")

        # 显示最新数据
        print(f"\n最新数据:")
        print(data[['open', 'high', 'low', 'close', 'volume']].tail())


if __name__ == "__main__":
    main()
