**こちらはらくらくNS+（開発中）のページです。らくらくNS（bat版）のページは[こちら](https://github.com/ahakuoku/rakurakuNS/blob/main/readme.md)。**

# らくらくNS+とは？
SimutransのNSを管理するツールです。
- サーバーがクラッシュした場合に自動で再起動、それに付帯して必要な動作もすべて自動で行います。
- セーブ条件を指定することで、オートセーブが可能です。オートセーブしたファイルのバックアップも可能です。

といった機能があります。

# 導入方法
1. らくらくNS+をダウンロードする
2. zipを解凍し、任意のフォルダに各種pyファイルを入れる
3. config.template.pyをコピーし、config.pyにファイル名を変更し設定を行う

# ダウンロード
ダウンロードは[こちら](https://github.com/ahakuoku/rakurakuNS-plus/releases)から行えます。

# 使用条件
ahakuoku simutrans addon license(ASAL)のファイル公開時点における最新版を適用します。  
ただし、同梱のnettoolについてはSimutransの各開発者様に著作権が帰属します。  
また、同梱のAzure ttk themeはrdbende様に著作権が帰属します。

## ASAL 3.2全文
利用者は、次の条件を守ることでこのアドオン・ツール等（以下、本作品）を自由にご利用いただけます。

### していいこと
- ソースがある場合の本作品の改変
- 改変をした場合の本作品の再配布

### しなければならないこと
- 本作品を再配布する際の本作品作者名表記
- 本作品を上書きするアドオンの配布時に、その旨を周知する事（Pakset配布の必要がある場合を除く）
- 本作品が改造品だった場合は、原作品のライセンスに従う事

### してはいけないこと
- 本作品の自作宣言
- 本作品の無改造再配布（Pakset配布の必要がある場合を除く）
- 本作品の営利目的での利用
- ソースがない場合の本作品の改変や再配布

### その他細則
- Pakset配布の必要がある場合とは、NSやセーブデータ配布などのことを指します。
- 本作品を利用したことによる損害は一切責任を負いません。
- 本作品の作者は、本規約に違反したユーザーを除き、特定のユーザーに対して不利に差別的な取り扱いを行ってはならないものとします。

# 内容
（0.1.0 alpha3時点）  
## config.template.py
設定ファイルのテンプレートです。設定方法は本ファイル内をご覧ください。

## main.py
メインのpythonファイルです。これを実行するとらくらくNS+の処理が始まります。  
らくらくNS（bat版）とは異なり、これ一つで全てが完結します。

## readme
本ドキュメントへのリンクです。

# 機能一覧
(Version 0.1.0 alpha3時点の情報です。最新情報は[各バージョンのリリースページ](https://github.com/ahakuoku/rakurakuNS-plus/releases)をご覧ください。

## クラッシュ時自動再起動
サーバーがクラッシュした場合に、自動再起動などの必要な操作を自動で行います。  
また、オプションで次の機能も使用可能です。
- Discordのbotを利用した復旧通知（現在はSimutrans World Monitor経由での暫定的な実装です）

## オートセーブ
一定の間隔でオートセーブを行うことが可能です。また、オートセーブ30秒前に予告メッセージを流します。  
オートセーブ前のデータはデフォルトでは80個までバックアップすることが可能です。（オプションでバックアップ個数を変更できます）  
オートセーブを行うタイミングとして設定可能であるのは次の5種類である予定です。これらは併用できます。
- らくらくNSを起動してからの一定間隔（らくらくNS（bat版）と同じ動作です。時間、分、秒間隔で指定できます）
- 指定した特定のタイミング（n曜日もしくは毎日のn時n分n秒、どの間隔で繰り返すかどうかは指定可能、複数指定可能）
- 最後のロードから経過した時間
- 手動（セーブ予告の関係上ボタンを押してから実際にセーブが入るまで30秒ほどかかります）

## 定時再起動
一日一回まで特定の時間に再起動を行えます。  
使用には設定ファイルでの設定が必要です。

# らくらくNS（bat版）との相違点
らくらくNS+はらくらくNS（bat版）とは全く異なるアプリケーションです。  
このため、**らくらくNS（bat版）との互換性はありません**し、使用方法も全く異なります。  
※らくらくNS（bat版）の設定を一部インポートすることは可能とする予定です。

具体的には、以下の相違点があります。
- クロスプラットフォーム対応  
Windows、Mac、Linuxの3OSに対応しています。  
というつもりでアプリを設計していますが、作者の方にWindows以外での検証環境がないため実際のところWindows以外で動くかどうか不明です。  
検証してくださる方は作者の方までお声がけください。
- アプリの配置フォルダ  
らくらくNS（bat版）は、サーバーと同一のフォルダと配置する必要がありましたが、らくらくNS+は任意のフォルダに配置することができます。
- 大規模な仕様変更  
らくらくNS（bat版）と比べて大幅に仕様が変更されているところがあります。下記はその一例です。
  - nettoolのパスワードの自動取得
  - serverオプションを含むショートカットの作成が不要に
- いくつかの設定項目  
らくらくNS+では、らくらくNS（bat版）と大幅に仕様が変更されているところがあるため、いくつかの設定項目が異なります。

将来的には、以下のような相違点が発生する見込みです。
- GUIでの操作が可能
- 全ての操作が1つのアプリケーションで完結する（らくらくNS（bat版）では状況次第で複数のbatファイルを起動する必要がありました）
- アプリケーションの設定がアプリケーション内で完結する
- Simutrans World Monitor連携機能は廃止予定（代替として、Discordへの直接書き込み機能を実装します。）
- その他、細かい仕様等
# 今後実装予定の機能一覧
## GUI化
らくらくNS（bat版）とは異なり、GUIでの操作を可能にする予定です。
## クラッシュ時自動再起動
将来的に、次のオプションを実装予定です。
- クラッシュによりリセットされたBANリストの再設定
## オートセーブ
追加で実装する予定のオプションがあり、次の通りです。現在実装済みの一定間隔のセーブとこれらは併用できます。
- らくらくNSを起動してからの一定間隔（らくらくNS（bat版）や現行版と同じ動作です。現在は秒単位でのみ指定できますが、将来的には時間、分、秒間隔での指定を実装します。）
- 指定した特定のタイミング（n曜日もしくは毎日のn時n分n秒、どの間隔で繰り返すかどうかは指定可能、複数指定可能）
- 最後のロードから経過した時間
- 手動（セーブ予告の関係上ボタンを押してから実際にセーブが入るまで30秒ほどかかります）
## メンテナンスモード・再起動・サーバー自動終了
事前に設定された時刻、もしくはすぐにメンテナンスモードへ移行することまたは再起動が可能です。  
メンテナンスモード開始時に自動でサーバーを落とすほか、メンテナンスモード中は自動再起動が無効になります。  
メンテナンスモードを終了すると再起動します。

また、操作により設定された時刻もしくはすぐに再起動することを可能にする予定です。

さらに、操作により設定された時刻もしくはすぐにサーバーを終了することを可能にする予定です。
## Pak更新・本体更新
事前に設定された時刻、もしくはすぐにPak更新や本体更新を行うことを可能にする予定です。  
画面の指示に従って操作してください。
## ロールバック
直前のロード時もしくはバックアップからデータを復旧させることを可能にする予定です。
## nettoolのGUI操作
nettoolをコマンド入力なしに自由に操作するすることを可能にする予定です。
## Discordへのメッセージ投稿機能
らくらくNS+では、Discordへのメッセージ投稿機能を使用する事により次のことが行えるようになる予定です。
- サーバーがクラッシュしたこと、復旧したことをDiscordで通知できる（最終ロード時刻も表示できます）
- メンテナンス、再起動の告知をDiscordで行う
- 接続先IPアドレスの変更を検出し、Discordに書き込む
- オートセーブの予告をDiscordで自動的に行える（デフォルトでは無効です）

なお、これらの機能を使用するには設定が必要です。これらの機能は、それぞれ有効/無効を切り替えられます。  
また、[Simutrans world monitor](https://github.com/teamhimeh/simutrans_world_monitor)との連携機能は将来的に廃止予定です。（代替のDiscord直接書き込み機能を実装予定です）

# 更新履歴
- [こちらをご覧ください。](https://github.com/ahakuoku/rakurakuNS-plus/releases)
