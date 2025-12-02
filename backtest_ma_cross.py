import pandas as pd

# ここに設定する数字を変えると、簡単にルールを調整できるよ
SHORT_WINDOW = 20  # 短い期間の本数（短期の移動平均）
LONG_WINDOW = 60   # 長い期間の本数（長期の移動平均）
INITIAL_CAPITAL = 10000.0  # スタートのおこづかい（円）
FEE_RATE = 0.00002  # 手数料率（0.002% = 0.00002）
TRADE_SIZE = 1  # 1回に買う量。ここでは1単位で固定。

# CSVファイルの場所（リポジトリのルートにある）
CSV_PATH = "usdjpy_yahoo_30d_5m.csv"


def load_price_data(path: str) -> pd.DataFrame:
    """CSVからデータを読み込み、きれいに整える関数。"""
    # Yahoo FinanceのCSVは先頭に余計な行があるので2行スキップするよ
    df = pd.read_csv(
        path,
        skiprows=2,
        names=["Datetime", "Close", "High", "Low", "Open", "Volume"],
    )

    # 文字の時間を日時データに変換
    df["Datetime"] = pd.to_datetime(df["Datetime"])

    # 時間順（古い → 新しい）に並び替える
    df = df.sort_values("Datetime").reset_index(drop=True)

    # 短期と長期の単純移動平均（SMA）を計算する
    df["sma_short"] = df["Close"].rolling(window=SHORT_WINDOW).mean()
    df["sma_long"] = df["Close"].rolling(window=LONG_WINDOW).mean()

    return df


def calculate_max_drawdown(equity_curve):
    """資産曲線から最大ドローダウンを計算するよ。"""
    max_peak = 0
    max_dd = 0
    for eq in equity_curve:
        max_peak = max(max_peak, eq)
        if max_peak > 0:
            dd = (eq - max_peak) / max_peak
            max_dd = min(max_dd, dd)
    return max_dd


def backtest(df: pd.DataFrame):
    """移動平均クロスのバックテストをするメインの関数。"""
    cash = INITIAL_CAPITAL  # 現金（お財布の中身）
    position_price = None  # 今持っているポジションの買値
    trades = 0  # 完了したトレード回数
    wins = 0  # 勝ちトレードの回数
    equity_curve = []  # 時間ごとの資産の記録（ドローダウン用）

    for i in range(1, len(df)):
        row_prev = df.iloc[i - 1]
        row = df.iloc[i]

        # 移動平均が計算できていない最初のころはスキップ
        if pd.isna(row_prev["sma_short"]) or pd.isna(row_prev["sma_long"]) or pd.isna(row["sma_short"]) or pd.isna(row["sma_long"]):
            # 資産の記録だけは進める
            current_price = row["Close"]
            current_equity = cash
            if position_price is not None:
                current_equity += (current_price - position_price) * TRADE_SIZE
            equity_curve.append(current_equity)
            continue

        short_prev = row_prev["sma_short"]
        long_prev = row_prev["sma_long"]
        short_now = row["sma_short"]
        long_now = row["sma_long"]
        price = row["Close"]

        # シグナル：短期が長期を下から上に抜けたら買い
        buy_signal = short_prev <= long_prev and short_now > long_now
        # シグナル：短期が長期を上から下に抜けたら決済
        sell_signal = short_prev >= long_prev and short_now < long_now

        # 買うタイミング
        if position_price is None and buy_signal:
            fee = price * TRADE_SIZE * FEE_RATE
            cash -= price * TRADE_SIZE  # 買ったぶんお金が減る
            cash -= fee  # 手数料を払う
            position_price = price  # 買った価格をメモ

        # 売って終わるタイミング
        elif position_price is not None and sell_signal:
            fee = price * TRADE_SIZE * FEE_RATE
            cash += price * TRADE_SIZE  # 売ってお金が戻る
            cash -= fee  # 手数料を払う
            profit = (price - position_price) * TRADE_SIZE - fee
            trades += 1
            if profit > 0:
                wins += 1
            position_price = None

        # 現在の資産（現金＋含み益/損）を記録
        current_equity = cash
        if position_price is not None:
            current_equity += (price - position_price) * TRADE_SIZE
        equity_curve.append(current_equity)

    # データの最後まで来たときにまだポジションがあれば、最後の価格で決済して結果を出す
    if position_price is not None:
        price = df.iloc[-1]["Close"]
        fee = price * TRADE_SIZE * FEE_RATE
        cash += price * TRADE_SIZE
        cash -= fee
        profit = (price - position_price) * TRADE_SIZE - fee
        trades += 1
        if profit > 0:
            wins += 1
        position_price = None
        # 決済後の資産も記録
        equity_curve.append(cash)

    # 最終的な数字を計算
    final_balance = cash
    win_rate = wins / trades if trades > 0 else 0.0
    max_dd = calculate_max_drawdown(equity_curve)

    return {
        "final_balance": final_balance,
        "trades": trades,
        "win_rate": win_rate,
        "max_drawdown": max_dd,
    }


def main():
    # データを読み込む
    df = load_price_data(CSV_PATH)

    # バックテストを実行
    results = backtest(df)

    # 結果をわかりやすく表示
    print("===== バックテスト結果 =====")
    print(f"最終口座残高: {results['final_balance']:.2f} 円")
    print(f"トレード回数: {results['trades']}")
    print(f"勝率: {results['win_rate'] * 100:.2f}%")
    # 最大ドローダウンはマイナスの割合で返ってくるので、%表示にする
    print(f"最大ドローダウン: {results['max_drawdown'] * 100:.2f}%")


if __name__ == "__main__":
    main()
