"""
币安永续合约数据获取器
支持获取历史永续合约K线数据
"""

import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from typing import Optional
import os


class BinanceFuturesDataFetcher:
    """币安永续合约数据获取器"""

    def __init__(self):
        # 使用永续合约API
        self.base_url = "https://fapi.binance.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json'
        })

    def get_historical_futures_klines(
        self,
        symbol: str = "BTCUSDT",
        interval: str = "4h",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 1500
    ) -> pd.DataFrame:
        """
        获取永续合约历史K线数据

        参数:
            symbol: 交易对，如'BTCUSDT'
            interval: K线间隔 (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M)
            start_date: 开始日期 'YYYY-MM-DD'
            end_date: 结束日期 'YYYY-MM-DD'
            limit: 每次请求的数量上限（最大1500）

        返回:
            包含OHLCV数据的DataFrame
        """
        endpoint = "/fapi/v1/klines"
        all_klines = []

        # 转换日期为时间戳
        if start_date:
            start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
        else:
            # 默认从2019年开始（永续合约上线时间）
            start_ts = int(datetime(2019, 9, 1).timestamp() * 1000)

        if end_date:
            end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)
        else:
            end_ts = int(datetime.now().timestamp() * 1000)

        current_ts = start_ts
        request_count = 0
        max_retries = 3

        print(f"开始获取 {symbol} 永续合约 {interval} 数据...")
        print(f"时间范围: {start_date or '2019-09-01'} 至 {end_date or '现在'}")
        print(f"使用API: {self.base_url}{endpoint}")

        while current_ts < end_ts:
            params = {
                'symbol': symbol,
                'interval': interval,
                'startTime': current_ts,
                'endTime': end_ts,
                'limit': limit
            }

            retry_count = 0
            success = False

            while retry_count < max_retries and not success:
                try:
                    response = self.session.get(
                        self.base_url + endpoint,
                        params=params,
                        timeout=30
                    )

                    if response.status_code == 200:
                        klines = response.json()

                        if not klines:
                            print(f"\n已获取所有可用数据")
                            break

                        all_klines.extend(klines)
                        current_ts = klines[-1][0] + 1  # 下一个时间戳
                        request_count += 1

                        print(f"\r已获取 {len(all_klines)} 条数据... (请求 #{request_count})", end='')

                        # API限制：避免触发限流
                        time.sleep(0.2)
                        success = True

                    elif response.status_code == 429:  # 触发限流
                        wait_time = 2 ** retry_count
                        print(f"\n触发限流，等待 {wait_time} 秒...")
                        time.sleep(wait_time)
                        retry_count += 1

                    else:
                        print(f"\nAPI返回错误: {response.status_code}")
                        print(f"错误内容: {response.text}")
                        retry_count += 1
                        time.sleep(1)

                except requests.exceptions.RequestException as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        wait_time = 2 ** retry_count
                        print(f"\n请求失败: {e}")
                        print(f"重试 {retry_count}/{max_retries}，等待 {wait_time} 秒...")
                        time.sleep(wait_time)
                    else:
                        print(f"\n达到最大重试次数，已获取数据: {len(all_klines)} 条")
                        if all_klines:
                            break
                        else:
                            raise

            if not success and retry_count >= max_retries:
                break

        if not all_klines:
            raise ValueError(f"未能获取 {symbol} 的数据")

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

        # 去重（以防万一）
        df = df[~df.index.duplicated(keep='first')]

        # 按时间排序
        df = df.sort_index()

        return df

    def save_to_csv(self, df: pd.DataFrame, filename: str):
        """保存数据到CSV文件"""
        df.to_csv(filename)
        print(f"数据已保存到 {filename}")

    def load_from_csv(self, filename: str) -> pd.DataFrame:
        """从CSV文件加载数据"""
        if not os.path.exists(filename):
            raise FileNotFoundError(f"文件不存在: {filename}")
        df = pd.read_csv(filename, index_col=0, parse_dates=True)
        print(f"从 {filename} 加载了 {len(df)} 条数据")
        return df


def download_futures_data():
    """下载永续合约数据"""
    fetcher = BinanceFuturesDataFetcher()

    # 要下载的币种
    symbols = ['BTCUSDT', 'ETHUSDT']

    for symbol in symbols:
        print(f"\n{'=' * 80}")
        print(f"下载 {symbol} 永续合约数据")
        print(f"{'=' * 80}")

        filename = f"{symbol.lower()}_futures_4h.csv"

        # 检查文件是否已存在
        if os.path.exists(filename):
            try:
                existing_data = fetcher.load_from_csv(filename)
                print(f"✓ 文件已存在，包含 {len(existing_data)} 条数据")
                print(f"  时间范围: {existing_data.index[0]} 至 {existing_data.index[-1]}")

                user_input = input(f"是否重新下载？(y/n): ").lower()
                if user_input != 'y':
                    print("跳过下载")
                    continue
            except Exception as e:
                print(f"加载现有文件失败: {e}")

        try:
            # 从2019年9月开始（永续合约上线时间）
            data = fetcher.get_historical_futures_klines(
                symbol=symbol,
                interval='4h',
                start_date='2019-09-01',
                end_date=None  # 到现在
            )

            # 显示数据信息
            print(f"\n数据概览:")
            print(f"  时间范围: {data.index[0]} 至 {data.index[-1]}")
            print(f"  总数据量: {len(data)} 条")
            print(f"  覆盖天数: {(data.index[-1] - data.index[0]).days} 天")
            print(f"\n价格统计:")
            print(f"  最高价: ${data['high'].max():,.2f}")
            print(f"  最低价: ${data['low'].min():,.2f}")
            print(f"  平均价: ${data['close'].mean():,.2f}")
            print(f"\n最新数据:")
            print(data.tail())

            # 保存数据
            fetcher.save_to_csv(data, filename)

            print(f"\n✓ {symbol} 数据下载完成")

        except Exception as e:
            print(f"\n✗ {symbol} 下载失败: {e}")
            import traceback
            traceback.print_exc()
            continue

    print(f"\n{'=' * 80}")
    print("所有数据下载完成")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    download_futures_data()
