"""
模型验证和回测
包含防止过拟合的机制：训练集/测试集分割、Walk-Forward分析、参数优化
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from squeeze_momentum import SqueezeMomentumIndicator
from backtest_example import SqueezeBacktester
from binance_data_fetcher import BinanceDataFetcher


class ModelValidator:
    """模型验证器 - 防止过拟合"""

    def __init__(self):
        self.train_ratio = 0.7  # 训练集比例
        self.validation_ratio = 0.15  # 验证集比例
        self.test_ratio = 0.15  # 测试集比例

    def split_data(
        self,
        data: pd.DataFrame,
        method: str = 'simple'
    ) -> Dict[str, pd.DataFrame]:
        """
        分割数据集

        参数:
            data: 完整数据集
            method: 分割方法 ('simple' 或 'walk_forward')

        返回:
            包含train, validation, test的字典
        """
        if method == 'simple':
            return self._simple_split(data)
        elif method == 'walk_forward':
            return self._walk_forward_split(data)
        else:
            raise ValueError(f"未知的分割方法: {method}")

    def _simple_split(self, data: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """简单的时间序列分割"""
        n = len(data)
        train_end = int(n * self.train_ratio)
        val_end = int(n * (self.train_ratio + self.validation_ratio))

        splits = {
            'train': data.iloc[:train_end],
            'validation': data.iloc[train_end:val_end],
            'test': data.iloc[val_end:]
        }

        print("\n数据集分割:")
        print("=" * 80)
        for name, df in splits.items():
            print(f"{name:12s}: {len(df):5d} 条 | {df.index[0]} 至 {df.index[-1]}")

        return splits

    def _walk_forward_split(
        self,
        data: pd.DataFrame,
        n_splits: int = 5
    ) -> List[Dict[str, pd.DataFrame]]:
        """Walk-Forward分割"""
        n = len(data)
        window_size = n // (n_splits + 1)

        splits = []
        for i in range(n_splits):
            train_start = 0
            train_end = window_size * (i + 1)
            test_start = train_end
            test_end = min(test_start + window_size, n)

            if test_end <= test_start:
                break

            splits.append({
                'train': data.iloc[train_start:train_end],
                'test': data.iloc[test_start:test_end],
                'fold': i + 1
            })

        print(f"\nWalk-Forward分割: {len(splits)} 个fold")
        print("=" * 80)
        for split in splits:
            print(f"Fold {split['fold']}:")
            print(f"  训练: {len(split['train']):5d} 条 | {split['train'].index[0]} 至 {split['train'].index[-1]}")
            print(f"  测试: {len(split['test']):5d} 条 | {split['test'].index[0]} 至 {split['test'].index[-1]}")

        return splits

    def optimize_parameters(
        self,
        train_data: pd.DataFrame,
        param_grid: Dict[str, List]
    ) -> Tuple[Dict, pd.DataFrame]:
        """
        参数优化

        参数:
            train_data: 训练数据
            param_grid: 参数网格

        返回:
            最优参数和所有结果
        """
        print("\n参数优化中...")
        print("=" * 80)

        results = []

        # 生成参数组合
        import itertools
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        param_combinations = list(itertools.product(*param_values))

        total = len(param_combinations)
        print(f"总共需要测试 {total} 组参数")

        for idx, params in enumerate(param_combinations, 1):
            param_dict = dict(zip(param_names, params))

            try:
                # 创建指标
                indicator = SqueezeMomentumIndicator(**param_dict)

                # 生成信号
                signals = indicator.generate_signals(
                    train_data['high'],
                    train_data['low'],
                    train_data['close']
                )

                # 回测
                backtester = SqueezeBacktester(initial_capital=10000)
                backtest_results, trades = backtester.run_backtest(train_data, signals)
                metrics = backtester.calculate_metrics(backtest_results, trades)

                # 记录结果
                result = {**param_dict, **metrics}
                results.append(result)

                if idx % 10 == 0:
                    print(f"进度: {idx}/{total} ({idx/total*100:.1f}%)")

            except Exception as e:
                print(f"参数 {param_dict} 测试失败: {e}")
                continue

        results_df = pd.DataFrame(results)

        # 找到最优参数（基于Sharpe比率）
        if len(results_df) > 0:
            best_idx = results_df['sharpe_ratio'].idxmax()
            best_params = results_df.loc[best_idx, param_names].to_dict()

            print(f"\n最优参数:")
            for name, value in best_params.items():
                print(f"  {name}: {value}")
            print(f"\n训练集性能:")
            print(f"  Sharpe比率: {results_df.loc[best_idx, 'sharpe_ratio']:.3f}")
            print(f"  总收益率: {results_df.loc[best_idx, 'total_return']:.2f}%")
            print(f"  最大回撤: {results_df.loc[best_idx, 'max_drawdown']:.2f}%")

            return best_params, results_df
        else:
            raise ValueError("参数优化失败，没有成功的结果")

    def validate_model(
        self,
        data: pd.DataFrame,
        params: Dict,
        dataset_name: str = "验证集"
    ) -> Dict:
        """
        在指定数据集上验证模型

        参数:
            data: 验证数据
            params: 模型参数
            dataset_name: 数据集名称

        返回:
            性能指标
        """
        print(f"\n在{dataset_name}上验证模型...")
        print("=" * 80)

        # 创建指标
        indicator = SqueezeMomentumIndicator(**params)

        # 生成信号
        signals = indicator.generate_signals(
            data['high'],
            data['low'],
            data['close']
        )

        # 回测
        backtester = SqueezeBacktester(initial_capital=10000)
        results, trades = backtester.run_backtest(data, signals)
        metrics = backtester.calculate_metrics(results, trades)

        # 打印结果
        print(f"\n{dataset_name}性能:")
        print(f"  总收益率: {metrics['total_return']:.2f}%")
        print(f"  最大回撤: {metrics['max_drawdown']:.2f}%")
        print(f"  Sharpe比率: {metrics['sharpe_ratio']:.3f}")
        print(f"  总交易次数: {metrics['total_trades']}")
        print(f"  胜率: {metrics['win_rate']:.2f}%")
        print(f"  盈亏比: {metrics['profit_factor']:.2f}")

        return metrics

    def walk_forward_analysis(
        self,
        data: pd.DataFrame,
        param_grid: Dict[str, List],
        n_splits: int = 5
    ) -> pd.DataFrame:
        """
        Walk-Forward分析 - 最强的防过拟合方法

        参数:
            data: 完整数据
            param_grid: 参数网格
            n_splits: 分割数量

        返回:
            每个fold的结果
        """
        print("\n开始Walk-Forward分析...")
        print("=" * 80)

        splits = self._walk_forward_split(data, n_splits)
        wf_results = []

        for split in splits:
            fold = split['fold']
            print(f"\n处理 Fold {fold}...")

            # 在训练集上优化参数
            best_params, _ = self.optimize_parameters(split['train'], param_grid)

            # 在测试集上验证
            test_metrics = self.validate_model(
                split['test'],
                best_params,
                f"Fold {fold} 测试集"
            )

            # 记录结果
            result = {
                'fold': fold,
                'train_start': split['train'].index[0],
                'train_end': split['train'].index[-1],
                'test_start': split['test'].index[0],
                'test_end': split['test'].index[-1],
                **best_params,
                **{f'test_{k}': v for k, v in test_metrics.items()}
            }
            wf_results.append(result)

        wf_df = pd.DataFrame(wf_results)

        # 汇总结果
        print("\n\nWalk-Forward分析汇总:")
        print("=" * 80)
        print(f"平均测试收益: {wf_df['test_total_return'].mean():.2f}%")
        print(f"平均测试Sharpe: {wf_df['test_sharpe_ratio'].mean():.3f}")
        print(f"平均测试胜率: {wf_df['test_win_rate'].mean():.2f}%")
        print(f"收益率标准差: {wf_df['test_total_return'].std():.2f}%")

        return wf_df

    def detect_overfitting(
        self,
        train_metrics: Dict,
        test_metrics: Dict,
        threshold: float = 0.3
    ) -> Dict:
        """
        检测过拟合

        参数:
            train_metrics: 训练集指标
            test_metrics: 测试集指标
            threshold: 性能下降阈值

        返回:
            过拟合分析结果
        """
        print("\n过拟合检测:")
        print("=" * 80)

        # 计算性能下降
        sharpe_drop = (train_metrics['sharpe_ratio'] - test_metrics['sharpe_ratio']) / \
                      (abs(train_metrics['sharpe_ratio']) + 1e-6)
        return_drop = (train_metrics['total_return'] - test_metrics['total_return']) / \
                      (abs(train_metrics['total_return']) + 1e-6)
        winrate_drop = (train_metrics['win_rate'] - test_metrics['win_rate']) / \
                       (abs(train_metrics['win_rate']) + 1e-6)

        overfitting = {
            'sharpe_drop': sharpe_drop,
            'return_drop': return_drop,
            'winrate_drop': winrate_drop,
            'is_overfitting': abs(sharpe_drop) > threshold or abs(return_drop) > threshold
        }

        print(f"Sharpe比率下降: {sharpe_drop*100:.1f}%")
        print(f"收益率下降: {return_drop*100:.1f}%")
        print(f"胜率下降: {winrate_drop*100:.1f}%")

        if overfitting['is_overfitting']:
            print("\n⚠️ 警告: 检测到可能的过拟合!")
            print("建议:")
            print("  1. 简化模型参数")
            print("  2. 增加训练数据")
            print("  3. 使用更保守的参数范围")
        else:
            print("\n✓ 模型泛化性能良好")

        return overfitting


def run_complete_validation():
    """运行完整的模型验证流程"""
    print("Squeeze Momentum策略 - 完整验证流程")
    print("=" * 80)

    # 1. 获取数据
    print("\n步骤 1: 获取BTC 4H数据")
    fetcher = BinanceDataFetcher()

    try:
        # 尝试从文件加载
        data = fetcher.load_from_csv('btc_4h_data.csv')
    except:
        # 如果文件不存在，从API获取
        from datetime import timedelta
        start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
        data = fetcher.get_historical_klines(
            symbol='BTCUSDT',
            interval='4h',
            start_date=start_date
        )
        fetcher.save_to_csv(data, 'btc_4h_data.csv')

    print(f"\n数据量: {len(data)} 条")
    print(f"时间范围: {data.index[0]} 至 {data.index[-1]}")

    # 2. 分割数据集
    print("\n步骤 2: 分割数据集")
    validator = ModelValidator()
    splits = validator.split_data(data, method='simple')

    # 3. 参数优化（在训练集上）
    print("\n步骤 3: 参数优化")
    param_grid = {
        'bb_length': [15, 20, 25],
        'bb_mult': [1.5, 2.0, 2.5],
        'kc_length': [15, 20, 25],
        'kc_mult': [1.0, 1.5, 2.0],
        'rsi_length': [14],
        'rsi_overbought': [70],
        'rsi_oversold': [30],
        'atr_length': [14],
        'atr_mult': [2.0]
    }

    best_params, optimization_results = validator.optimize_parameters(
        splits['train'],
        param_grid
    )

    # 4. 在验证集上测试
    print("\n步骤 4: 验证集测试")
    val_metrics = validator.validate_model(splits['validation'], best_params, "验证集")

    # 5. 在测试集上最终测试
    print("\n步骤 5: 测试集最终评估")
    test_metrics = validator.validate_model(splits['test'], best_params, "测试集")

    # 6. 过拟合检测
    print("\n步骤 6: 过拟合检测")
    # 获取训练集性能
    train_metrics = validator.validate_model(splits['train'], best_params, "训练集")

    overfitting_analysis = validator.detect_overfitting(
        train_metrics,
        test_metrics,
        threshold=0.3
    )

    # 7. Walk-Forward分析
    print("\n步骤 7: Walk-Forward分析")
    wf_results = validator.walk_forward_analysis(
        data,
        param_grid,
        n_splits=5
    )

    # 8. 最终报告
    print("\n\n" + "=" * 80)
    print("最终验证报告")
    print("=" * 80)

    print("\n参数配置:")
    for key, value in best_params.items():
        print(f"  {key}: {value}")

    print("\n性能对比:")
    print(f"{'数据集':<12s} {'收益率':>10s} {'最大回撤':>10s} {'Sharpe':>8s} {'胜率':>8s}")
    print("-" * 60)
    print(f"{'训练集':<12s} {train_metrics['total_return']:>9.2f}% {train_metrics['max_drawdown']:>9.2f}% "
          f"{train_metrics['sharpe_ratio']:>8.3f} {train_metrics['win_rate']:>7.1f}%")
    print(f"{'验证集':<12s} {val_metrics['total_return']:>9.2f}% {val_metrics['max_drawdown']:>9.2f}% "
          f"{val_metrics['sharpe_ratio']:>8.3f} {val_metrics['win_rate']:>7.1f}%")
    print(f"{'测试集':<12s} {test_metrics['total_return']:>9.2f}% {test_metrics['max_drawdown']:>9.2f}% "
          f"{test_metrics['sharpe_ratio']:>8.3f} {test_metrics['win_rate']:>7.1f}%")

    print("\n过拟合风险评估:")
    if overfitting_analysis['is_overfitting']:
        print("  ⚠️ 高风险 - 模型可能存在过拟合")
    else:
        print("  ✓ 低风险 - 模型泛化性能良好")

    # 保存结果
    optimization_results.to_csv('optimization_results.csv', index=False)
    wf_results.to_csv('walk_forward_results.csv', index=False)

    print("\n结果已保存:")
    print("  - optimization_results.csv")
    print("  - walk_forward_results.csv")

    return {
        'best_params': best_params,
        'train_metrics': train_metrics,
        'val_metrics': val_metrics,
        'test_metrics': test_metrics,
        'overfitting_analysis': overfitting_analysis,
        'wf_results': wf_results
    }


if __name__ == "__main__":
    results = run_complete_validation()
