#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
from pathlib import Path

# =========================================================
# パラメータ（ここだけいじれば戦略を調整できる）
# =========================================================
DEFAULT_PARAMS = {
    "short_window": 20,       # 短期移動平均の本数
    "long_window": 60,        # 長期移動平均の本数
    "initial_capital": 10000, # 初期資金（円）
    "fee_rate": 0.00002,      # 片道手数料率（0.002% = 0.00002）
    "trade_size": 1,          # 1トレードあたりの数量（ここでは 1 万通貨みたいなイメージ）
}

# バックテストに使う CSV ファイル
CSV_PATH = "usdjpy_yahoo_30d_5m.csv"

# トレード一覧出力先
TRADES_CSV = "trades_latest.csv"


# =========================================================
# データ読み込み
# =========================================================
def load_price_data(path: str) -> pd.DataFrame:
    """CSV からデータを読み込んで、きれいに整える。"""

    df = pd.read_csv(
        path,
        skiprows=2,  # 先頭2行はメタ情報なのでスキップ
        names=["Datetime", "Close", "High", "Low", "Open", "Volume"],
    )

    # 文字の時間を datetime 型に変換（変換できないものは NaT）
    df["Datetime"] = pd.to_datetime(df["Datetime"], errors="coerce")

    # 日付に変換できなかった行を捨てる
    df = df.dropna(subset=["Datetime"])

    # 時間順（古い → 新しい）に並べ直す
    df = df.sort_values("Datetime").reset_index(drop=True)

    return df


# =========================================================
# 最大ドローダウン計算
# =========================================================
def calculate_max_drawdown(equity_curve):
    """資産曲線から最大ドローダウン（マイナスの割合）を計算する。"""
    max_peak = 0
    max_dd = 0.0
    for eq in equity_curve:
        max_peak = max(max_peak, eq)
        if max_peak > 0:
            dd = (eq - max_peak) / max_peak
            max_dd = min(max_dd, dd)
    return max_dd  # 例: -0.0159 → -1.59%


# =========================================================
# バックテスト本体
# =========================================================
def backtest(params: dict, price_df: pd.DataFrame):
    """
    移動平均クロスでロングだけするシンプル戦略。
    params: パラメータ dict
    price_df: load_price_data() で読み込んだ DataFrame
    """
    df = price_df.copy()

    short_w = int(params["short_window"])
    long_w = int(params["long_window"])
    fee = float(params["fee_rate"])
    size = float(params["trade_size"])
    initial_capital = float(params["initial_capital"])

    # 短期・長期 SMA を計算
    df["sma_short"] = df["Close"].rolling(window=short_w).mean()
    df["sma_long"] = df["Close"].rolling(window=long_w).mean()

    # SMA が計算できない最初の方は捨てる
    df = df.dropna(subset=["sma_short", "sma_long"]).reset_index(drop=True)

    cash = initial_capital
    position = 0.0  # 0 or size
    entry_price = 0.0
    entry_time = None

    equity_curve = []
    trades = []

    for i in range(len(df)):
        row = df.iloc[i]
        price = float(row["Close"])
        now = row["Datetime"]

        # 1本前と現在の SMA でクロス判定
        if i == 0:
            signal = 0
        else:
            prev = df.iloc[i - 1]
            prev_short = float(prev["sma_short"])
            prev_long = float(prev["sma_long"])
            cur_short = float(row["sma_short"])
            cur_long = float(row["sma_long"])

            if prev_short <= prev_long and cur_short > cur_long:
                signal = 1   # ゴールデンクロス → 買い
            elif prev_short >= prev_long and cur_short < cur_long:
                signal = -1  # デッドクロス → 手仕舞い
            else:
                signal = 0

        # ===== 手仕舞い（ロングを持っていて、売りシグナル） =====
        if position > 0 and signal == -1:
            # 売り決済（成行でクローズ）
            cash += price * size              # 売り代金
            cash -= price * size * fee        # 手数料

            pnl = (price - entry_price) * size - (
                entry_price * size * fee + price * size * fee
            )

            trades.append(
                {
                    "entry_time": entry_time,
                    "exit_time": now,
                    "direction": "LONG",
                    "entry_price": entry_price,
                    "exit_price": price,
                    "pnl": pnl,
                    "equity_after": cash,
                }
            )

            position = 0.0
            entry_price = 0.0
            entry_time = None

        # ===== 新規エントリー（ポジションなし & 買いシグナル） =====
        if position == 0 and signal == 1:
            entry_price = price
            entry_time = now

            cash -= price * size              # 買い代金
            cash -= price * size * fee        # 手数料
            position = size

        # 毎バーの評価額
        equity = cash + position * price
        equity_curve.append(equity)

    # バックテスト終了時点でポジションが残っている場合は、そのまま評価額に含めるだけ
    final_balance = equity_curve[-1] if equity_curve else initial_capital
    max_dd = calculate_max_drawdown(equity_curve)

    # 成績集計
    wins = [t for t in trades if t["pnl"] > 0]
    win_rate = (len(wins) / len(trades) * 100.0) if trades else 0.0

    result = {
        "final_balance": final_balance,
        "max_drawdown": max_dd,
        "win_rate": win_rate,
        "trade_count": len(trades),
        "equity_curve": equity_curve,
        "trades": trades,
    }
    return result


# =========================================================
# トレード一覧を CSV に保存
# =========================================================
def save_trades_to_csv(trades, path: str = TRADES_CSV):
    if not trades:
        print("※ トレードが 0 件なので、CSV は保存しません。")
        return

    df_trades = pd.DataFrame(trades)
    df_trades.to_csv(path, index=False, encoding="utf-8")
    print(f"トレード一覧を保存しました: {path}")


# =========================================================
# GA 用の評価関数（今はメモ程度に使う）
# =========================================================
def evaluate_params(params: dict, price_df: pd.DataFrame) -> float:
    """
    GA から呼び出す想定の評価関数。
    入力: params dict
    出力: スコア（大きいほど良い）
    """
    result = backtest(params, price_df)
    final_balance = result["final_balance"]
    max_dd = result["max_drawdown"]  # マイナス値

    # シンプルに「最終残高 - ドローダウンにペナルティをかけたもの」
    fitness = final_balance + max_dd * 10000  # DD が -0.02 なら -200 のペナルティ
    return float(fitness)


# =========================================================
# メイン
# =========================================================
def main():
    # データ読み込み
    price_df = load_price_data(CSV_PATH)

    # デフォルトパラメータでバックテスト
    result = backtest(DEFAULT_PARAMS, price_df)

    # トレード一覧を CSV に書き出し
    save_trades_to_csv(result["trades"])

    # コンソールに成績表示
    print("===== バックテスト結果 =====")
    print(f"最終口座残高: {result['final_balance']:.2f} 円")
    print(f"トレード回数: {result['trade_count']}")
    print(f"勝率: {result['win_rate']:.2f}%")
    print(f"最大ドローダウン: {result['max_drawdown'] * 100:.2f}%")

    # おまけ：評価関数のスコアも表示（GA 用の確認）
    score = evaluate_params(DEFAULT_PARAMS, price_df)
    print(f"評価関数のスコア: {score:.2f}")


if __name__ == "__main__":
    main()