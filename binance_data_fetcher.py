"""
币安数据获取器
从Binance API获取历史K线数据
"""

import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from typing import Optional, List


class BinanceDataFetcher:
    """币安数据获取器"""

    def __init__(self, use_testnet: bool = False):
        if use_testnet:
            self.base_url = "https://testnet.binance.vision"
        else:
            self.base_url = "https://api.binance.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0'
        })

    def get_historical_klines(
        self,
        symbol: str = "BTCUSDT",
        interval: str = "4h",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 1000
    ) -> pd.DataFrame:
        """
        获取历史K线数据

        参数:
            symbol: 交易对，如'BTCUSDT'
            interval: K线间隔 (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M)
            start_date: 开始日期 'YYYY-MM-DD'
            end_date: 结束日期 'YYYY-MM-DD'
            limit: 每次请求的数量上限

        返回:
            包含OHLCV数据的DataFrame
        """
        endpoint = "/api/v3/klines"
        all_klines = []

        # 转换日期为时间戳
        if start_date:
            start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
        else:
            # 默认获取最近1年的数据
            start_ts = int((datetime.now() - timedelta(days=365)).timestamp() * 1000)

        if end_date:
            end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)
        else:
            end_ts = int(datetime.now().timestamp() * 1000)

        current_ts = start_ts

        print(f"开始获取 {symbol} {interval} 数据...")
        print(f"时间范围: {start_date or '1年前'} 至 {end_date or '现在'}")

        while current_ts < end_ts:
            params = {
                'symbol': symbol,
                'interval': interval,
                'startTime': current_ts,
                'endTime': end_ts,
                'limit': limit
            }

            try:
                response = self.session.get(
                    self.base_url + endpoint,
                    params=params,
                    timeout=10
                )
                response.raise_for_status()
                klines = response.json()

                if not klines:
                    break

                all_klines.extend(klines)
                current_ts = klines[-1][0] + 1  # 下一个时间戳

                print(f"已获取 {len(all_klines)} 条数据...", end='\r')
                time.sleep(0.5)  # 避免触发API限制

            except requests.exceptions.RequestException as e:
                print(f"\n获取数据时出错: {e}")
                if all_klines:
                    print(f"已获取 {len(all_klines)} 条数据，继续处理...")
                    break
                else:
                    raise

        print(f"\n总共获取 {len(all_klines)} 条数据")

        # 转换为DataFrame
        df = pd.DataFrame(all_klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])

        # 数据类型转换
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')

        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)

        # 设置索引
        df.set_index('timestamp', inplace=True)

        # 只保留需要的列
        df = df[['open', 'high', 'low', 'close', 'volume']]

        return df

    def get_recent_klines(
        self,
        symbol: str = "BTCUSDT",
        interval: str = "4h",
        limit: int = 500
    ) -> pd.DataFrame:
        """
        获取最近的K线数据

        参数:
            symbol: 交易对
            interval: K线间隔
            limit: 数据条数

        返回:
            包含OHLCV数据的DataFrame
        """
        endpoint = "/api/v3/klines"

        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }

        try:
            response = self.session.get(
                self.base_url + endpoint,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            klines = response.json()

            # 转换为DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])

            # 数据类型转换
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)

            df.set_index('timestamp', inplace=True)
            df = df[['open', 'high', 'low', 'close', 'volume']]

            print(f"成功获取 {len(df)} 条 {symbol} {interval} 数据")

            return df

        except requests.exceptions.RequestException as e:
            print(f"获取数据时出错: {e}")
            raise

    def save_to_csv(self, df: pd.DataFrame, filename: str):
        """保存数据到CSV文件"""
        df.to_csv(filename)
        print(f"数据已保存到 {filename}")

    def load_from_csv(self, filename: str) -> pd.DataFrame:
        """从CSV文件加载数据"""
        df = pd.read_csv(filename, index_col=0, parse_dates=True)
        print(f"从 {filename} 加载了 {len(df)} 条数据")
        return df


def main():
    """示例使用"""
    fetcher = BinanceDataFetcher()

    # 获取BTC 4小时数据（最近2年）
    start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')

    df = fetcher.get_historical_klines(
        symbol='BTCUSDT',
        interval='4h',
        start_date=start_date,
        end_date=end_date
    )

    # 显示数据信息
    print("\n数据概览:")
    print("=" * 80)
    print(f"数据范围: {df.index[0]} 至 {df.index[-1]}")
    print(f"总数据量: {len(df)} 条")
    print(f"\n最新数据:")
    print(df.tail())

    print(f"\n数据统计:")
    print(df.describe())

    # 保存到CSV
    filename = 'btc_4h_data.csv'
    fetcher.save_to_csv(df, filename)

    return df


if __name__ == "__main__":
    df = main()
