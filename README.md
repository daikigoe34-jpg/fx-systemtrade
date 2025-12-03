FX 自動売買のためのコードを置く場所

## USDJPY 5分足データをダウンロードする
直近30日分の5分足（Datetime, Close, High, Low, Open, Volume）を Yahoo Finance から取得し、
リポジトリ直下に `usdjpy_yahoo_30d_5m.csv` として保存します。コードは Python 3.10 / Pythonista 3 で動く構成にしています。

### 事前準備（共通）
- Python 3.10 以上が入っていること。
- `pip install pandas yfinance` で pandas と yfinance を入れておく。
  - すでに入っている場合はこの手順はスキップしてOKです。

### Mac のターミナルでの実行手順
1. このリポジトリに移動する。
   ```bash
   cd /path/to/fx-systemtrade
   ```
2. 必要なら依存ライブラリを入れる。
   ```bash
   pip install pandas yfinance
   ```
3. スクリプトを実行して CSV を作る。
   ```bash
   python3 download_usdjpy_yahoo.py
   ```
   成功すると `usdjpy_yahoo_30d_5m.csv` がリポジトリ直下に更新されます。

### iPhone の Pythonista 3 での実行手順
1. Pythonista の StaSh を開き、必要ならライブラリを入れる。
   ```bash
   pip install pandas yfinance
   ```
2. `download_usdjpy_yahoo.py` を Pythonista の同じフォルダに保存する。
   - iCloud Drive や AirDrop でファイルを転送するか、内容をコピーして新規スクリプトに貼り付けます。
3. スクリプトを実行する。
   - エディタ右上の再生ボタンを押すか、StaSh で `python download_usdjpy_yahoo.py` と打ちます。
4. 実行後、同じフォルダに `usdjpy_yahoo_30d_5m.csv` が作られます。

## ダウンロードした CSV を使ってバックテストする
1. 上記の手順で `usdjpy_yahoo_30d_5m.csv` を最新化しておく。
2. `backtest_ma_cross.py` を動かす。
   - Mac ならターミナルで以下を実行。
     ```bash
     python3 backtest_ma_cross.py
     ```
   - Pythonista でも同じフォルダで `python backtest_ma_cross.py` を実行すればOKです。

`backtest_ma_cross.py` は同じフォルダにある `usdjpy_yahoo_30d_5m.csv` を読み込む前提なので、
ファイル名や場所を変えずに使ってください。

## Pythonista での実行方法

iPhone / iPad の Pythonista 3 だけで、バックテストを実行できます。

1. Pythonista を開き、「This iPhone」フォルダを開く  
2. `sync_github.py` を実行して、GitHub から最新ファイルを取得する  
3. 取得が終わったら、`backtest_ma_cross.py` を開く  
4. 右上の ▶ ボタンをタップして実行  

コンソールに次の情報が表示されます。

- 最終口座残高  
- トレード回数  
- 勝率  
- 最大ドローダウン  

同時に、同じフォルダに `trades_latest.csv` が出力され、
1トレードごとのエントリー・エグジット・損益が確認できます。

---

## sync_github.py の使い方

`sync_github.py` は、GitHub の `fx-systemtrade` リポジトリと
Pythonista のローカルフォルダを同期するためのシンプルなスクリプトです。

1. スクリプト内の `BASE_URL` が自分の GitHub リポジトリ
   (`https://raw.githubusercontent.com/ユーザー名/fx-systemtrade/main/`) を
   指していることを確認する  
2. `FILES = [...]` に、同期したいファイル名を列挙する  
   例:
   ```python
   FILES = [
       "backtest_ma_cross.py",
       "download_usdjpy_yahoo.py",
       "README.md",
   ]
