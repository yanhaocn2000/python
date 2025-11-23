"""
样本外验证（Out-of-Sample Validation）
使用严格的时间分割，模拟真实交易场景
"""

import pandas as pd
import numpy as np
from typing import Dict, List
import warnings
warnings.filterwarnings('ignore')

from squeeze_momentum_enhanced import SqueezeMomentumEnhanced
from backtest_example import SqueezeBacktester


class OutOfSampleValidator:
    """样本外验证器"""

    def __init__(self):
        # 严格的时间分割（模拟真实场景）
        # 2019-2021: 训练期（开发策略）
        # 2022: 验证期（参数调优）
        # 2023-2024: 测试期（样本外验证）
        self.time_splits = {
            'train': ('2019-09-01', '2021-12-31'),  # 2.3年
            'validation': ('2022-01-01', '2022-12-31'),  # 1年
            'test': ('2023-01-01', '2024-11-23')  # 1.9年
        }

    def split_by_time(self, data: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        按时间分割数据

        这是最严格的验证方式：
        - 训练期：策略开发和初步测试
        - 验证期：参数调优
        - 测试期：完全未见过的数据，真实的样本外验证
        """
        splits = {}

        for name, (start, end) in self.time_splits.items():
            mask = (data.index >= start) & (data.index <= end)
            splits[name] = data[mask].copy()

        print(f"\n时间分割:")
        print("=" * 80)
        for name in ['train', 'validation', 'test']:
            df = splits[name]
            days = (df.index[-1] - df.index[0]).days
            print(f"{name:12s}: {len(df):5d}条 | {df.index[0].date()} 至 {df.index[-1].date()} ({days:4d}天)")

        return splits

    def validate_strategy(
        self,
        data: pd.DataFrame,
        symbol: str,
        config: Dict
    ) -> Dict:
        """
        在单个币种上进行完整验证

        返回训练/验证/测试三个阶段的结果
        """
        print(f"\n{'=' * 80}")
        print(f"样本外验证: {symbol}")
        print(f"{'=' * 80}")

        # 时间分割
        splits = self.split_by_time(data)

        # 创建策略
        indicator = SqueezeMomentumEnhanced(**config)

        results = {}

        # 在每个时间段上运行
        for period_name in ['train', 'validation', 'test']:
            period_data = splits[period_name]

            # 生成信号
            signals = indicator.generate_signals_enhanced(
                period_data['high'],
                period_data['low'],
                period_data['close'],
                period_data['volume']
            )

            # 回测
            backtester = SqueezeBacktester(initial_capital=10000, commission=0.001)
            backtest_results, trades = backtester.run_backtest(period_data, signals)
            metrics = backtester.calculate_metrics(backtest_results, trades)

            # 统计信号
            total_signals = (signals['signal'] != 0).sum()
            avg_strength = signals['signal_strength'].mean()

            results[period_name] = {
                'metrics': metrics,
                'signals': total_signals,
                'avg_strength': avg_strength,
                'period_days': (period_data.index[-1] - period_data.index[0]).days
            }

        return results

    def print_results(self, results: Dict, symbol: str):
        """打印详细结果"""
        print(f"\n{symbol} 性能对比:")
        print(f"{'='* 80}")
        print(f"{'阶段':<15s} {'Sharpe':>8s} {'收益率':>12s} {'回撤':>10s} {'信号':>6s} {'天数':>6s}")
        print("-" * 80)

        for period in ['train', 'validation', 'test']:
            r = results[period]
            m = r['metrics']
            print(f"{period:<15s} {m['sharpe_ratio']:>8.3f} {m['total_return']:>11.2f}% "
                  f"{m['max_drawdown']:>9.2f}% {r['signals']:>6d} {r['period_days']:>6d}")

        # 样本外性能下降分析
        train_sharpe = results['train']['metrics']['sharpe_ratio']
        test_sharpe = results['test']['metrics']['sharpe_ratio']

        if train_sharpe > 0:
            oos_degradation = (train_sharpe - test_sharpe) / train_sharpe * 100
        else:
            oos_degradation = 0

        print(f"\n样本外性能:")
        print(f"  训练期Sharpe: {train_sharpe:.3f}")
        print(f"  测试期Sharpe: {test_sharpe:.3f}")
        print(f"  性能下降: {oos_degradation:+.1f}%")

        if abs(oos_degradation) > 50:
            print(f"  评估: ⚠️ 严重过拟合")
        elif abs(oos_degradation) > 30:
            print(f"  评估: ⚠️ 存在过拟合")
        elif oos_degradation > 0:
            print(f"  评估: ✓ 轻微下降（可接受）")
        else:
            print(f"  评估: ✓✓ 样本外表现优于训练（优秀）")

        return oos_degradation


def run_out_of_sample_validation():
    """运行完整的样本外验证"""
    print("样本外验证（Out-of-Sample Validation）")
    print("=" * 80)
    print("\n验证方法:")
    print("  - 训练期 2019-2021: 策略开发")
    print("  - 验证期 2022: 参数调优")
    print("  - 测试期 2023-2024: 样本外验证（真实未见数据）")
    print("\n这是最严格的验证方式，测试期数据完全独立！")

    # 加载数据
    symbols = {
        'BTC': 'btcusdt_futures_4h.csv',
        'ETH': 'ethusdt_futures_4h.csv'
    }

    # 测试配置
    configs = {
        '增强版（成交量过滤）': {
            'signal_mode': 'enhanced',
            'use_volume_filter': True,
            'use_trend_filter': False,
            'bb_length': 20, 'bb_mult': 2.0,
            'kc_length': 20, 'kc_mult': 1.5
        },
        '增强版（趋势过滤）': {
            'signal_mode': 'enhanced',
            'use_volume_filter': False,
            'use_trend_filter': True,
            'bb_length': 20, 'bb_mult': 2.0,
            'kc_length': 20, 'kc_mult': 1.5
        }
    }

    validator = OutOfSampleValidator()
    all_results = {}

    # 对每个配置在每个币种上测试
    for config_name, config in configs.items():
        print(f"\n\n{'#' * 80}")
        print(f"配置: {config_name}")
        print(f"{'#' * 80}")

        config_results = {}

        for symbol, filename in symbols.items():
            try:
                data = pd.read_csv(filename, index_col=0, parse_dates=True)
                print(f"\n加载 {symbol} 数据: {len(data)}条")

                results = validator.validate_strategy(data, symbol, config)
                degradation = validator.print_results(results, symbol)

                config_results[symbol] = {
                    'results': results,
                    'oos_degradation': degradation
                }

            except Exception as e:
                print(f"\n✗ {symbol} 验证失败: {e}")
                import traceback
                traceback.print_exc()

        all_results[config_name] = config_results

    # 汇总分析
    print(f"\n\n{'=' * 80}")
    print("样本外验证汇总")
    print(f"{'=' * 80}")

    summary_data = []

    for config_name in configs.keys():
        for symbol in ['BTC', 'ETH']:
            if symbol in all_results[config_name]:
                r = all_results[config_name][symbol]['results']
                deg = all_results[config_name][symbol]['oos_degradation']

                summary_data.append({
                    '配置': config_name,
                    '币种': symbol,
                    '训练Sharpe': r['train']['metrics']['sharpe_ratio'],
                    '验证Sharpe': r['validation']['metrics']['sharpe_ratio'],
                    '测试Sharpe': r['test']['metrics']['sharpe_ratio'],
                    '测试收益': r['test']['metrics']['total_return'],
                    '测试回撤': r['test']['metrics']['max_drawdown'],
                    '样本外下降': deg
                })

    summary_df = pd.DataFrame(summary_data)

    print("\n测试期（2023-2024）性能:")
    print("-" * 80)
    print(f"{'配置':<25s} {'币种':<6s} {'Sharpe':>8s} {'收益率':>12s} {'回撤':>10s} {'OOS下降':>10s}")
    print("-" * 80)

    for _, row in summary_df.iterrows():
        print(f"{row['配置']:<25s} {row['币种']:<6s} {row['测试Sharpe']:>8.3f} "
              f"{row['测试收益']:>11.2f}% {row['测试回撤']:>9.2f}% {row['样本外下降']:>9.1f}%")

    # 最佳样本外配置
    print(f"\n\n{'=' * 80}")
    print("样本外最佳配置")
    print(f"{'=' * 80}")

    best_idx = summary_df['测试Sharpe'].idxmax()
    best = summary_df.loc[best_idx]

    print(f"\n最佳配置: {best['配置']} - {best['币种']}")
    print(f"  测试期Sharpe: {best['测试Sharpe']:.3f}")
    print(f"  测试期收益: {best['测试收益']:.2f}%")
    print(f"  测试期回撤: {best['测试回撤']:.2f}%")
    print(f"  样本外下降: {best['样本外下降']:.1f}%")

    # 跨币种稳定性
    print(f"\n跨币种稳定性分析:")
    print("-" * 80)

    for config_name in configs.keys():
        config_data = summary_df[summary_df['配置'] == config_name]
        if len(config_data) >= 2:
            avg_sharpe = config_data['测试Sharpe'].mean()
            std_sharpe = config_data['测试Sharpe'].std()
            avg_deg = config_data['样本外下降'].mean()

            print(f"\n{config_name}:")
            print(f"  平均测试Sharpe: {avg_sharpe:.3f}")
            print(f"  Sharpe标准差: {std_sharpe:.3f}")
            print(f"  平均样本外下降: {avg_deg:+.1f}%")

            if avg_deg < -20:
                print(f"  评级: ⭐⭐⭐⭐⭐ 样本外表现优于训练")
            elif avg_deg < 10:
                print(f"  评级: ⭐⭐⭐⭐ 样本外表现稳定")
            elif avg_deg < 30:
                print(f"  评级: ⭐⭐⭐ 轻微下降，可接受")
            elif avg_deg < 50:
                print(f"  评级: ⭐⭐ 存在过拟合")
            else:
                print(f"  评级: ⭐ 严重过拟合")

    # 保存结果
    summary_df.to_csv('out_of_sample_results.csv', index=False)
    print(f"\n结果已保存到: out_of_sample_results.csv")

    return summary_df, all_results


if __name__ == "__main__":
    summary, results = run_out_of_sample_validation()
