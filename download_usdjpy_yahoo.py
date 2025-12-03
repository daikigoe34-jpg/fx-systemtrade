"""
USDJPYの日足データをYahoo Financeから取得して保存するスクリプト。
Python 3.10 と Pythonista 3 で動くように、
標準ライブラリ + requests だけで書いています。
(※pandas / yfinance は使っていません)
"""

from pathlib import Path
from typing import List
import csv
import datetime as dt
import time
import urllib.parse

import requests

# 使うティッカー（Yahoo Finance での USD/JPY レート）
TICKER = "USDJPY=X"

# 何日分さかのぼるか（必要に応じてここを増やしてOK）
LOOKBACK_DAYS = 365  # とりあえず直近1年分

# 保存するファイル名（リポジトリ直下に置く）
# バックテスト側のコードを変えなくていいように、元のファイル名をそのまま使う
OUTPUT_CSV = Path(__file__).resolve().parent / "usdjpy_yahoo_30d_5m.csv"


def _build_yahoo_url() -> str:
    """Yahoo Finance CSV ダウンロード用のURLを組み立てる。"""
    base = "https://query1.finance.yahoo.com/v7/finance/download/"
    ticker_escaped = urllib.parse.quote(TICKER, safe="")

    now = dt.datetime.utcnow()
    start = now - dt.timedelta(days=LOOKBACK_DAYS)

    period1 = int(start.timestamp())
    period2 = int(now.timestamp())

    query = (
        f"?period1={period1}"
        f"&period2={period2}"
        f"&interval=1d"
        f"&events=history"
        f"&includeAdjustedClose=true"
    )

    return base + ticker_escaped + query


def fetch_usdjpy_daily() -> List[List[str]]:
    """USDJPY の日足データを取得して、行のリストとして返す。"""
    url = _build_yahoo_url()
    print("Downloading:", url)

    try:
        r = requests.get(url, timeout=30)
    except Exception as exc:
        raise SystemExit(f"HTTPリクエストでエラーが発生しました: {exc}")

    if r.status_code != 200:
        raise SystemExit(f"ダウンロードに失敗しました (HTTP {r.status_code})")

    text = r.text
    lines = text.splitlines()

    if not lines:
        raise SystemExit("ダウンロード結果が空でした。")

    reader = csv.DictReader(lines)
    rows: List[List[str]] = []

    for row in reader:
        # Yahoo のヘッダ想定:
        # Date,Open,High,Low,Close,Adj Close,Volume
        date = row.get("Date", "")
        open_ = row.get("Open", "")
        high = row.get("High", "")
        low = row.get("Low", "")
        close = row.get("Close", "")
        volume = row.get("Volume", "")

        # バックテスト用CSVの列順に合わせる:
        # Datetime, Close, High, Low, Open, Volume
        if date:
            rows.append([date, close, high, low, open_, volume])

    if not rows:
        raise SystemExit("有効な行が一つもありませんでした。フォーマットを確認してください。")

    return rows


def save_with_metadata(rows: List[List[str]]) -> None:
    """
    先頭にメタ情報2行をつけてCSVに保存する。
    バックテスト側の load_price_data が
    skiprows=2, names=[...] で読む前提のフォーマット。
    """
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)

        # 1行目: Ticker 行
        writer.writerow(
            [
                "Ticker",
                TICKER,
                TICKER,
                TICKER,
                TICKER,
                TICKER,
            ]
        )

        # 2行目: Datetime 行（中身は空でOK）
        writer.writerow(["Datetime", "", "", "", "", ""])

        # 3行目以降: データ本体（ヘッダ行は付けない）
        for row in rows:
            writer.writerow(row)


def main() -> None:
    print("=== USDJPY 日足ダウンロード開始 ===")
    rows = fetch_usdjpy_daily()
    save_with_metadata(rows)
    print(f"保存が完了しました: {OUTPUT_CSV}")
    print(f"行数（メタ行除く）: {len(rows)}")


if __name__ == "__main__":
    main()