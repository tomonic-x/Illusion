Illusion
=======================================================================
コンソール端末での日本語混じりのコーディングを支援する補助フォントです。


特徴
-----------------------------------------------------------------------

* 主な英数文字は Roboto Mono をベースに半角幅に調整。
* Unicode の East Asian Width の扱いに応じたバリエーションを実装。
* 通常の日本語等幅フォントとの併用を想定。
* アスキーコード、JIS X 0208 の Ambiguous な記号類、コンソール端末用の
  罫線素片とブロック要素を収録。

![Illusion](https://github.com/tomonic-x/Illusion/raw/master/img/screenshot.png)


### 好みの日本語フォントとの組み合わせ

好みの日本語等幅フォントと組み合わせて使えるよう、
日本語の平仮名・片仮名・漢字は含めていません。

+ ブラウザでは CSS の `font-family` での併記で自由に組み合わせられます。
+ Windows では多くのアプリでレジストリの `FontLink` が利用できます。


### 三種類のバリエーション

Unicode の East Asian Width の *曖昧 (Ambiguous)* と *中立 (Neutral)* について、
**半角** と **全角** の両方の組み合わせに対応しています。

| 曖昧 | 中立 | Font Family          | 主な使い分け                       |
|:----:|:----:|:---------------------|:-----------------------------------|
| 半角 | 半角 | Illusion N (Narrow)  | 国際的なコンソール環境との互換重視 |
| 全角 | 半角 | Illusion W (Wide)    | Shift_JIS や EUC-JP との互換重視   |
| 全角 | 全角 | Illusion Z (Zenkaku) | 多くの日本語等幅フォントと同様の幅 |


#### 共通部分

+ Roboto Mono を半角幅に調整し、一部の小文字の高さを抑えました。
+ 括弧や記号類は、コーディングと全角文字とのバランスを重視して作成しました。

![screenshot ASCII](https://github.com/tomonic-x/Illusion/raw/master/img/screenshot-ascii.png)


#### Illusion N (Narrow)

+ Unicode 対応の国際的なコンソール環境と互換の文字幅。
+ JIS X 0208 の Ambiguous な記号類を半角幅でデザイン。
+ 丸付き数字 `⑩` ローマ数字 `Ⅳ` なども半角として実装。

![Illusion N with Yu Gothic](https://github.com/tomonic-x/Illusion/raw/master/img/screenshot-n.png)


#### Illusion W (Wide)

+ 従来の Shift_JIS や EUC-JP と互換の文字幅。
+ 実装を省くことで、組み合わせ先の日本語等幅フォントを積極的に利用します。
+ メイリオでプロポーショナルな JIS X 0208 の記号類を全角幅で実装。
+ 罫線素片とブロック要素の Neutral は半角扱い。

![Illusion W with Meiryo](https://github.com/tomonic-x/Illusion/raw/master/img/screenshot-w.png)


#### Illusion Z (Zenkaku)

+ 多くの日本語等幅フォントと同様の文字幅。
+ 罫線素片とブロック要素の Neutral も全角扱い。

![Illusion Z with BIZ UDGothic](https://github.com/tomonic-x/Illusion/raw/master/img/screenshot-z.png)


日本語等幅フォントとの組み合わせに関して
-----------------------------------------------------------------------

### ブラウザ

+ メイリオや游ゴシックなど、比較的自由に組み合わせ可能です。
+ 罫線の行間の隙間を整えるには `line-height: 1.25` を併用して下さい。


### Windows のレジストリの FontLink

`HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\FontLink\SystemLink`

メニューバーから [編集]-[新規]-[複数行文字列値] で

| キーの名前      | データ                     |
|:----------------|:---------------------------|
| Illusion N      | mplus-1m-regular.ttf,M+ 1m |
| Illusion N Bold | mplus-1m-bold.ttf,M+ 1m    |
| Illusion W      | mplus-1m-regular.ttf,M+ 1m |
| Illusion W Bold | mplus-1m-bold.ttf,M+ 1m    |
| Illusion Z      | mplus-1m-regular.ttf,M+ 1m |
| Illusion Z Bold | mplus-1m-bold.ttf,M+ 1m    |

といった要領で組み合わせられます。

なお `BIZ UDゴシック` など、`OS/2` テーブルの `AvgCharWidth` が、
`head` テーブルの `UnitsPerEm` の 1/2 でない等幅フォントの場合、
FontLink で組み合わせると、文字が被ります。


TODO
-----------------------------------------------------------------------
+ ヒンティングの調整。（罫線素片とブロック要素、小文字の `g` など）


既知の問題
-----------------------------------------------------------------------
+ 等幅フォントを前提としないアプリで、
  文字サイズが 2px の整数倍（1.5pt の整数倍）でない時に
  ズレる場合があります。


ビルド方法
-----------------------------------------------------------------------

### 必要なもの

+ FontForge
+ ttfautohint
+ Python 3.x
+ afdko (fontTools, ttf2ttc)


### 手順

1. `src/Illusion-*.sfd` を FontForge で開く。
    + Roboto Mono 由来のグリフは X 座標を 83.0078125% に縮小。
    + イタリックグリフは U+Fxxxx 第15面の私用領域に配置。
    + 全角グリフは U+10xxxx 第16面の私用領域に配置。
    + 全角のイタリックには対応しない。
2. `src/Illusion-*.ttf` に TrueType フォントを出力。
    + オプションは「OpenTypeの仕様」のみチェック。
3. `python build.py` を実行して `dist/` に生成。
    + ttfautohint 用の `src/Illusion-*-ctrl.txt` はまだダミーです。


ライセンス
-----------------------------------------------------------------------
+ Roboto Mono (Google) の Apache License 2.0 に準じます。


グリフ詳細
-----------------------------------------------------------------------

### 凡例

![Legend](https://github.com/tomonic-x/Illusion/raw/master/img/chart-legend.png)


### ASCII

![ASCII](https://github.com/tomonic-x/Illusion/raw/master/img/chart-ascii.png)


### Unicode

![Unicode](https://github.com/tomonic-x/Illusion/raw/master/img/chart-unicode.png)


### JIS X 0208 Ambiguous Half-Width

![JIS X 0208 Ambiguous Half-Width](https://github.com/tomonic-x/Illusion/raw/master/img/chart-jisx0208-hwid1.png)

![JIS X 0208 Ambiguous Half-Width](https://github.com/tomonic-x/Illusion/raw/master/img/chart-jisx0208-hwid2.png)


### JIS X 0208 Ambiguous Full-Width

![JIS X 0208 Ambiguous Full-Width](https://github.com/tomonic-x/Illusion/raw/master/img/chart-jisx0208-fwid1.png)

![JIS X 0208 Ambiguous Full-Width](https://github.com/tomonic-x/Illusion/raw/master/img/chart-jisx0208-fwid2.png)


### Box Drawing, Block Elements Half-Width

![Box Drawing, Block Elements Half-Width](https://github.com/tomonic-x/Illusion/raw/master/img/chart-box-hwid.png)

### Box Drawing, Block Elements Full-Width

![Box Drawing, Block Elements Full-Width](https://github.com/tomonic-x/Illusion/raw/master/img/chart-box-fwid.png)


<!-- End Of File -->

