# 第14号の再現手順

対象はBTC・ETH・XRP・LTCの2017-01-01〜2019-04-06の共通826暦日。入力はCryptoCompareの米ドル建て日足を収録した研究用データ。最終取引所の単独の約定値と混同しない。取引所別・直接取引／他通貨経由の内訳は原表にない。価格・出来高以外の特徴量は利用しない。

## 元資料と加工

[Cryptocurrency Dataset](https://github.com/edloginova/cryptodata/tree/d75a21bf67ad306ec5699691a84bd8685df9243c) はWai Kit Tsang、Ekaterina Loginovaによるゲント大学の研究成果。Guus van Heijningenの修士研究に基づきDries Benoitが指導。元の市場データ取得は同リポジトリの `CryptoValuesAPI.py`（histoday、tsym=USD）、日付・列の対応は `BasetableCreator.py`。研究チームが明示する [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) に従い、加工した入力CSV・集計表・図も同条件で提供する。引用時は研究チームとトピック基地による対象期間の抽出・検算・作図を明示する。第三者の商標や別資料の権利は各権利者に帰属する。

1. `sources.json` の最初のURLから固定版を取得する。ファイル名は `LDA_t2_s0_basetable.p`。研究チームの未補間版を選び、NaNの除去・0置換版、補間版は使わない。原研究側の前処理（無限大の0置換など）は製作コードで確認できる。
2. `python extract.py LDA_t2_s0_basetable.p > extracted.csv`。抽出器はハッシュを照合し、固定されたバイト配置の日時・銘柄・数値ブロックだけを読む。pickleのオブジェクト復元は行わない。読み取るのはUTCの日付、銘柄、close、volumefrom、volumeto。銘柄は原表のcoin列から取得する。原表にはNEOもあるが、依頼の対象外。SOL・ADA・DOGEの値は収録されていない。
3. `extracted.csv` と公開した `input.csv` のSHA-256が `sources.json` と一致するか確認する。各銘柄の対象875行のうち49行は同一日に同じ終値と両方の出来高を持つ余分な行。競合があれば停止する。抽出後は3,304行。暦日の欠損・重複、価格または出来高の非正値・非有限値は集計エラーとする。日次騰落率が大きいという理由だけでは行を除かない。XRPの約2.80倍の日は記事に明示した。
4. `python analyze.py > recomputed.json`。公開した `results.json` と比較する。必要な場合のみMatplotlibで `python charts.py` を実行すると、同じフォルダーに4図を再生成する。価格比較の図は各銘柄の初日を100とする対数目盛。円モデルは為替一定で下落比率だけを適用し、円単位で四捨五入する。

## 窓の定義と独立検算

- 全期間と2017年上半期を別々に集計する。各日までの最高終値に対する比率が最小の日を選び、その後最初に高値以上になった終値を探す。上半期の高値と底は6月30日まで、回復の探索は2019年4月6日まで。元の高値と同値なら回復とする。日数は日付の差。同じ極値なら最初の日を選ぶ。最後の1本（2019年4月7日）は原取得時点で確定済みか証明できず、全系列から一律に除外した。
- `python -m unittest discover -s tests -v` をリポジトリ直下で実行。全8局面について、期間内の高値候補・後続終値の全ペアを列挙する別実装で極値と回復日を照合する。図の値・記事・保存された結果、実データのハッシュ、欠損時の停止も確認する。
- BTCの高値・底値の日を、第8号のBitstamp単一取引所のUSD終値とも照合した。2系列の値には差がある。同じ日の下落率は本資料で−83.29%、Bitstampで−83.43%。ほかの3銘柄について独立した取引所間照合は未実施。
- 4銘柄とも元の通貨単位のcloseを使用する。図に派生資産の付与や、ステーキング・税・取引費用を加えていない。個別イベントの全履歴、同一シンボルに対する提供元の過去の調整方針、2019年4月7日以後の回復は未確認。調査日までの全市場・上場来最大下落ではない。

## 通貨単位の確認（2026-11-23）

参照した実装の2版で次の定数は一致した。これは単位を確認するための資料であり、データ会社の企業行動・フォーク調整台帳の代わりにはならない。

| 銘柄 | 1通貨の最小単位数 | 参照コード |
|---|---:|---|
| BTC | 100,000,000 | Bitcoin Core amount.h [v0.13.2](https://github.com/bitcoin/bitcoin/blob/v0.13.2/src/amount.h)・[v0.17.1](https://github.com/bitcoin/bitcoin/blob/v0.17.1/src/amount.h) |
| LTC | 100,000,000 | Litecoin Core amount.h [v0.13.2.1](https://github.com/litecoin-project/litecoin/blob/v0.13.2.1/src/amount.h)・[v0.16.3](https://github.com/litecoin-project/litecoin/blob/v0.16.3/src/amount.h) |
| ETH | 10¹⁸ wei | go-ethereum [v1.5.5](https://github.com/ethereum/go-ethereum/blob/v1.5.5/common/size.go)・[v1.8.23](https://github.com/ethereum/go-ethereum/blob/v1.8.23/params/denomination.go) |
| XRP | 1,000,000 drops | rippled SystemParameters.h [0.80.0](https://github.com/ripple/rippled/blob/0.80.0/src/ripple/protocol/SystemParameters.h)・[1.2.0](https://github.com/ripple/rippled/blob/1.2.0/src/ripple/protocol/SystemParameters.h) |
