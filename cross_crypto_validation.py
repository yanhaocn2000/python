"""
跨币种验证
测试策略在不同加密货币上的泛化能力
"""

import pandas as pd
import numpy as np
from typing import Dict, List
import warnings
warnings.filterwarnings('ignore')

from squeeze_momentum_enhanced import SqueezeMomentumEnhanced
from backtest_example import SqueezeBacktester


def validate_single_crypto(data: pd.DataFrame, symbol: str, config: Dict) -> Dict:
    """
    在单个币种上验证策略

    参数:
        data: OHLCV数据
        symbol: 币种符号
        config: 策略配置

    返回:
        验证结果
    """
    print(f"\n{'=' * 80}")
    print(f"验证 {symbol}")
    print(f"{'=' * 80}")

    # 数据分割
    train_ratio = 0.7
    val_ratio = 0.15

    n = len(data)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    train_data = data.iloc[:train_end]
    val_data = data.iloc[train_end:val_end]
    test_data = data.iloc[val_end:]

    print(f"\n数据分割:")
    print(f"  训练集: {len(train_data):4d} 条")
    print(f"  验证集: {len(val_data):4d} 条")
    print(f"  测试集: {len(test_data):4d} 条")

    # 创建指标
    indicator = SqueezeMomentumEnhanced(**config)

    results = {}

    for dataset_name, dataset in [('train', train_data), ('val', val_data), ('test', test_data)]:
        # 生成信号
        signals = indicator.generate_signals_enhanced(
            dataset['high'],
            dataset['low'],
            dataset['close'],
            dataset['volume']
        )

        # 回测
        backtester = SqueezeBacktester(initial_capital=10000, commission=0.001)
        backtest_results, trades = backtester.run_backtest(dataset, signals)
        metrics = backtester.calculate_metrics(backtest_results, trades)

        # 统计信号
        total_signals = (signals['signal'] != 0).sum()
        buy_signals = (signals['signal'] == 1).sum()
        sell_signals = (signals['signal'] == -1).sum()
        avg_strength = signals['signal_strength'].mean()

        results[dataset_name] = {
            'total_signals': total_signals,
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'avg_strength': avg_strength,
            **metrics
        }

    # 打印结果
    print(f"\n性能对比:")
    print(f"{'数据集':<10s} {'信号':>6s} {'收益率':>10s} {'最大回撤':>10s} {'Sharpe':>8s} {'胜率':>7s} {'交易数':>7s}")
    print("-" * 80)

    for dataset_name in ['train', 'val', 'test']:
        r = results[dataset_name]
        print(f"{dataset_name:<10s} {r['total_signals']:>6d} "
              f"{r['total_return']:>9.2f}% {r['max_drawdown']:>9.2f}% "
              f"{r['sharpe_ratio']:>8.3f} {r['win_rate']:>6.1f}% "
              f"{r['total_trades']:>7d}")

    # 过拟合分析
    sharpe_drop = (results['train']['sharpe_ratio'] - results['test']['sharpe_ratio']) / \
                  (abs(results['train']['sharpe_ratio']) + 0.01)

    print(f"\n过拟合分析:")
    print(f"  Sharpe下降: {sharpe_drop*100:+.1f}%")
    if abs(sharpe_drop) > 0.3:
        print(f"  评估: ⚠️ 存在过拟合风险")
    else:
        print(f"  评估: ✓ 泛化良好")

    return {
        'symbol': symbol,
        'results': results,
        'sharpe_drop': sharpe_drop
    }


def run_cross_crypto_validation():
    """运行跨币种验证"""
    print("跨币种策略验证")
    print("=" * 80)

    # 配置要测试的币种和策略
    symbols = {
        'BTC': 'btcusdt_4h_data.csv',
        'ETH': 'ethusdt_4h_data.csv'
    }

    # 测试多种配置
    configs = {
        '增强版（趋势过滤）': {
            'signal_mode': 'enhanced',
            'use_volume_filter': False,
            'use_trend_filter': True,
            'bb_length': 20, 'bb_mult': 2.0,
            'kc_length': 20, 'kc_mult': 1.5
        },
        '增强版（成交量过滤）': {
            'signal_mode': 'enhanced',
            'use_volume_filter': True,
            'use_trend_filter': False,
            'bb_length': 20, 'bb_mult': 2.0,
            'kc_length': 20, 'kc_mult': 1.5
        },
        '增强版（完整过滤）': {
            'signal_mode': 'enhanced',
            'use_volume_filter': True,
            'use_trend_filter': True,
            'bb_length': 20, 'bb_mult': 2.0,
            'kc_length': 20, 'kc_mult': 1.5
        }
    }

    all_results = []

    # 对每个配置在每个币种上测试
    for config_name, config in configs.items():
        print(f"\n\n{'#' * 80}")
        print(f"测试配置: {config_name}")
        print(f"{'#' * 80}")

        config_results = {'config': config_name}

        for symbol, filename in symbols.items():
            try:
                # 加载数据
                data = pd.read_csv(filename, index_col=0, parse_dates=True)
                print(f"\n✓ 加载 {symbol} 数据: {len(data)} 条")

                # 验证
                result = validate_single_crypto(data, symbol, config)

                # 保存结果
                config_results[symbol] = result

            except FileNotFoundError:
                print(f"\n✗ 找不到 {symbol} 数据文件: {filename}")
                continue
            except Exception as e:
                print(f"\n✗ {symbol} 验证失败: {e}")
                import traceback
                traceback.print_exc()
                continue

        all_results.append(config_results)

    # 汇总分析
    print(f"\n\n{'=' * 80}")
    print("跨币种性能汇总")
    print(f"{'=' * 80}")

    # 创建汇总表
    summary_data = []

    for result in all_results:
        config_name = result['config']

        for symbol in ['BTC', 'ETH']:
            if symbol in result:
                symbol_result = result[symbol]
                test_metrics = symbol_result['results']['test']

                summary_data.append({
                    '配置': config_name,
                    '币种': symbol,
                    '测试集Sharpe': test_metrics['sharpe_ratio'],
                    '测试集收益': test_metrics['total_return'],
                    '测试集回撤': test_metrics['max_drawdown'],
                    '测试集信号': symbol_result['results']['test']['total_signals'],
                    '测试集交易': test_metrics['total_trades'],
                    'Sharpe下降': symbol_result['sharpe_drop']
                })

    summary_df = pd.DataFrame(summary_data)

    # 按币种分组显示
    print("\n测试集性能对比:")
    print("-" * 80)
    print(f"{'配置':<25s} {'币种':<6s} {'Sharpe':>8s} {'收益率':>10s} {'回撤':>10s} {'信号':>6s}")
    print("-" * 80)

    for _, row in summary_df.iterrows():
        print(f"{row['配置']:<25s} {row['币种']:<6s} {row['测试集Sharpe']:>8.3f} "
              f"{row['测试集收益']:>9.2f}% {row['测试集回撤']:>9.2f}% {row['测试集信号']:>6.0f}")

    # 跨币种一致性分析
    print(f"\n\n{'=' * 80}")
    print("跨币种一致性分析")
    print(f"{'=' * 80}")

    for config_name in configs.keys():
        config_data = summary_df[summary_df['配置'] == config_name]

        if len(config_data) >= 2:
            btc_sharpe = config_data[config_data['币种'] == 'BTC']['测试集Sharpe'].values
            eth_sharpe = config_data[config_data['币种'] == 'ETH']['测试集Sharpe'].values

            if len(btc_sharpe) > 0 and len(eth_sharpe) > 0:
                avg_sharpe = (btc_sharpe[0] + eth_sharpe[0]) / 2
                sharpe_diff = abs(btc_sharpe[0] - eth_sharpe[0])
                consistency = 1 - sharpe_diff / (avg_sharpe + 0.01)

                print(f"\n{config_name}:")
                print(f"  BTC Sharpe: {btc_sharpe[0]:>6.3f}")
                print(f"  ETH Sharpe: {eth_sharpe[0]:>6.3f}")
                print(f"  平均值: {avg_sharpe:>6.3f}")
                print(f"  差异: {sharpe_diff:>6.3f}")
                print(f"  一致性: {consistency:>6.1%}")

                if consistency > 0.8:
                    print(f"  评级: ⭐⭐⭐⭐⭐ 优秀（高度一致）")
                elif consistency > 0.6:
                    print(f"  评级: ⭐⭐⭐⭐ 良好")
                elif consistency > 0.4:
                    print(f"  评级: ⭐⭐⭐ 一般")
                else:
                    print(f"  评级: ⭐⭐ 较差（币种特异性强）")

    # 推荐策略
    print(f"\n\n{'=' * 80}")
    print("跨币种推荐策略")
    print(f"{'=' * 80}")

    # 计算每个配置的综合得分
    config_scores = []
    for config_name in configs.keys():
        config_data = summary_df[summary_df['配置'] == config_name]

        if len(config_data) >= 2:
            avg_sharpe = config_data['测试集Sharpe'].mean()
            min_sharpe = config_data['测试集Sharpe'].min()
            sharpe_std = config_data['测试集Sharpe'].std()

            # 综合得分：平均Sharpe × 最小Sharpe / 标准差
            score = avg_sharpe * min_sharpe / (sharpe_std + 0.1)

            config_scores.append({
                '配置': config_name,
                '平均Sharpe': avg_sharpe,
                '最小Sharpe': min_sharpe,
                'Sharpe标准差': sharpe_std,
                '综合得分': score
            })

    scores_df = pd.DataFrame(config_scores).sort_values('综合得分', ascending=False)

    print("\n配置排名（按综合得分）:")
    print("-" * 80)
    print(f"{'排名':<4s} {'配置':<25s} {'平均Sharpe':>12s} {'最小Sharpe':>12s} {'标准差':>10s} {'综合得分':>10s}")
    print("-" * 80)

    for idx, row in scores_df.iterrows():
        rank = scores_df.index.get_loc(idx) + 1
        print(f"{rank:<4d} {row['配置']:<25s} {row['平均Sharpe']:>12.3f} "
              f"{row['最小Sharpe']:>12.3f} {row['Sharpe标准差']:>10.3f} {row['综合得分']:>10.3f}")

    # 最佳配置
    if len(scores_df) > 0:
        best = scores_df.iloc[0]
        print(f"\n最佳跨币种配置: {best['配置']}")
        print(f"  原因:")
        print(f"    - 平均Sharpe: {best['平均Sharpe']:.3f}")
        print(f"    - 最小Sharpe: {best['最小Sharpe']:.3f}（保证最差情况）")
        print(f"    - Sharpe标准差: {best['Sharpe标准差']:.3f}（稳定性）")
        print(f"    - 综合得分: {best['综合得分']:.3f}")

    # 保存结果
    summary_df.to_csv('cross_crypto_results.csv', index=False)
    if len(scores_df) > 0:
        scores_df.to_csv('cross_crypto_scores.csv', index=False)

    print(f"\n结果已保存:")
    print(f"  - cross_crypto_results.csv")
    print(f"  - cross_crypto_scores.csv")

    return summary_df, scores_df


if __name__ == "__main__":
    summary, scores = run_cross_crypto_validation()
