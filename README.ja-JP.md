# Gemini CLI API

このプロジェクトは、`gemini-cli`ツールをラップすることにより、**OpenAI API仕様と互換性のあるRESTful API**を提供します。これにより、開発者は既存のOpenAI互換アプリケーションやライブラリを使用して、コードの変更を最小限に抑えながら、Googleの強力なGeminiモデルを活用できます。
### 無料枠の利点：Gemini CLI vs. Gemini API

このプロジェクトの主な差別化要因は、Google AI Studioが提供する**寛大な無料枠**（`gemini-cli`がアクセスするもの）を活用できる点です。これにより、開発とプロトタイピングにおいて大きな利点が得られます：

| 機能                               | Gemini CLI（Google AI Studio無料枠経由） | 直接的なGemini API（有料枠） |
| :--------------------------------- | :--------------------------------------- | :--------------------------- |
| **コスト**                         | 無料                                     | 従量課金制                   |
| **ユーザーあたりの毎分リクエスト数** | 120                                      | 大幅に多い                   |
| **ユーザーあたりの1日あたりのリクエスト数** | 1000（個人）、1500（標準）               | 大幅に多い                   |

これにより、APIコストを発生させることなくAI搭載アプリケーションを開発し、広範囲にテストできるため、以下のような場合に理想的なソリューションとなります：

-   **ゼロコスト開発：** API呼び出しにお金を費やすことなく、Geminiモデルを活用したアプリケーションを構築・テストできます。
-   **即時互換性：** APIベースURLを変更するだけで、OpenAI互換ツールやライブラリの広大なエコシステムとシームレスに統合できます。
-   **本番環境への道筋：** 無料で開発し、APIキーとURLを更新するだけで、大規模なコードリファクタリングなしに、本番環境用の有料OpenAIモデルや直接的なGemini API統合に簡単に移行できます。

### 主な機能
-   **OpenAI API互換性：** OpenAI標準を模倣した`/v1/chat/completions`エンドポイントを公開します。
-   **ステートレスな対話：** 各API呼び出しは新しい`gemini --prompt`プロセスを呼び出し、各リクエストが完全にステートレスな方法で処理されることを保証します。
-   **ストリーミング対応：** 多言語コンテンツに最適化された、インタラクティブなアプリケーション向けのリアルタイムストリーミング応答をサポートします。

## 前提条件

このサーバーを実行する前に、`gemini-cli`ツールがインストールされており、その実行可能コマンドである`gemini`がシステムの`PATH`で利用可能である必要があります。インストール手順は[こちら](https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/cli)で確認できます。

## はじめに

APIサーバーを起動するには、提供されているシェルスクリプトを実行するだけです：

```bash
./start_server.sh
```

このスクリプトは次のことを行います：
1.  `.env`ファイルから環境変数を読み込みます（存在する場合）。
2.  `gemini` CLIがアクセス可能であることを確認するための簡単なチェックを実行します。
3.  `uvicorn`を使用してFastAPIアプリケーションを起動します。

サーバーは通常、`http://localhost:8000`（または`.env`ファイルで指定されたポート）で実行されます。その後、`http://localhost:8000/docs`でAPIドキュメントにアクセスできます。

### クイックスタート例

サーバーが起動したら、`curl`を使用してチャット補完リクエストを行うことができます：

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{ "model": "gemini-2.5-flash", "messages": [{"role": "user", "content": "こんにちは、今日の調子はどうですか？"}], "stream": false }'
```


## 制限事項

APIサーバーのバックエンドとして`gemini-cli`を使用することには、ユーザーが認識しておくべきいくつかの重要な制限があります：

1.  **無視されるAPIパラメータ：** `gemini-cli`ツールは、公式のOpenAI Chat Completions APIで利用可能なすべてのパラメータをサポートしているわけではありません。そのため、`temperature`、`top_p`、`n`、`stop`、`max_tokens`、`presence_penalty`、`frequency_penalty`、`logit_bias`などのパラメータは**受け入れられますが、無視されます**。

2.  **モデル選択：** APIリクエスト（`POST /v1/chat/completions`）の`model`パラメータは、Geminiモデルを選択するために使用されます。現在、明示的にサポートされているのは`gemini-2.5-flash`と`gemini-2.5-pro`のみです。サポートされていないモデルがリクエストされた場合、サーバーは`.env`ファイルで設定された`DEFAULT_GEMINI_MODEL`にフォールバックします。

3.  **トークン使用量：** `gemini-cli`は`--prompt`フラグを使用する際にトークン使用量情報を提供しません。したがって、APIレスポンスの`usage`フィールドは常に`null`になります。

4.  **パフォーマンス：** 各API呼び出しは新しいコマンドラインサブプロセスを生成するため、ネイティブなAPI統合と比較してオーバーヘッドとレイテンシが大きくなります。

5.  **エラーハンドリング：** エラーは`gemini`サブプロセスの出力と終了コードに直接依存するため、ネイティブなAPIエラーよりも構造化されていなかったり、詳細でなかったりする場合があります。

## 設定

このサーバーは設定に環境変数を使用しており、プロジェクトルートにある`.env`ファイルで簡単に管理できます。サーバーが起動すると、これらの変数が自動的に読み込まれ、FastAPIアプリケーションと基盤となる`gemini` CLIプロセスの両方からアクセス可能になります。

以下は、`.env`ファイルで設定できる主要な設定オプションです：

```dotenv
# Gemini APIキー（gemini-cliが機能するために必須）
GEMINI_API_KEY=your_api_key_here

# Google CloudプロジェクトID（gemini-cliが必要とする場合）
# GOOGLE_CLOUD_PROJECT=your_project_id

# サーバーポート：FastAPIサーバーがリッスンするポート。
# 指定がない場合のデフォルトは8000です。
PORT=8000

# デフォルトGeminiモデル：クライアントがサポートされているモデルを指定しない場合、
# または無効なモデルを指定した場合に使用するモデル。サポートされている値は "gemini-2.5-flash" または "gemini-2.5-pro" です。
# デフォルトは "gemini-2.5-flash" です。
DEFAULT_GEMINI_MODEL=gemini-2.5-flash

# デバッグ機能：
# デバッグ目的でのリクエスト/レスポンスデータのダンプを有効/無効にします。
DEBUG_DUMP_ENABLED=false
# デバッグダンプが保存されるディレクトリ。
DEBUG_DUMP_DIR=./debug_dumps

# コンソール出力：
# サーバーからの詳細なコンソールログを有効/無効にします。
CONSOLE_OUTPUT_ENABLED=true
CONSOLE_OUTPUT_VERBOSE=true

# プロキシ設定：
# プロキシの内側にいる場合は、HTTPS_PROXY環境変数を設定してください。
# これはサーバーを起動する前、またはこの.envファイルで設定できます。
# 例：HTTPS_PROXY=http://your.proxy.server:port
# HTTPS_PROXY=
```

### Note: Translated by Gemini-2.5-flash