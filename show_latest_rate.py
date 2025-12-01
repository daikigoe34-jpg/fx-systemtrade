from __future__ import annotations
import csv
from datetime import datetime
from pathlib import Path

# このスクリプトはCSVを読み込んで最新のドル円レートを調べます
# 小学生でも分かるように、ゆっくり説明を書くよ

CSV_PATH = Path(__file__).resolve().parent / "usdjpy_yahoo_30d_5m.csv"


def read_latest_rate(csv_path: Path) -> tuple[datetime, float]:
    """CSVから一番新しい日時と終値を取り出す"""

    # ファイルを開くよ
    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.reader(csv_file)

        # 最初の3行は説明なので読み飛ばす
        for _ in range(3):
            next(reader, None)

        latest_datetime: datetime | None = None
        latest_close: float | None = None

        for row in reader:
            if len(row) < 2:
                continue

            try:
                current_datetime = datetime.fromisoformat(row[0])
                current_close = float(row[1])
            except ValueError:
                # 数字や日付に変換できない行は飛ばす
                continue

            if latest_datetime is None or current_datetime > latest_datetime:
                latest_datetime = current_datetime
                latest_close = current_close

    if latest_datetime is None or latest_close is None:
        raise ValueError("CSVからデータを読み取れませんでした")

    return latest_datetime, latest_close


def main() -> None:
    latest_datetime, latest_close = read_latest_rate(CSV_PATH)

    # 結果を見やすく出すよ
    print("最新のドル円の終値:")
    print(f"日時: {latest_datetime.isoformat()}")
    print(f"終値: {latest_close:.6f}")


if __name__ == "__main__":
    main()
