#!/usr/bin/env python3
"""
Google Calendar APIのリフレッシュトークンを取得するための、1回だけ手元で実行する
セットアップ用スクリプト。GitHub Actions上では実行しない。

事前準備:
    1. Google Cloud Consoleでプロジェクトを作成し、Google Calendar APIを有効化する。
    2. 「APIとサービス > 認証情報」で OAuthクライアントID を作成する
       (アプリケーションの種類: デスクトップアプリ)。
    3. 作成したクライアントの「JSONをダウンロード」を押し、このスクリプトと
       同じフォルダに `client_secret.json` という名前で保存する。

使い方:
    pip install google-auth-oauthlib
    python get_google_refresh_token.py

ブラウザが開くのでGoogleアカウントでログインし、アクセスを許可する。
完了すると client_id / client_secret / refresh_token が表示されるので、
GitHub Actionsのsecretsに以下の名前でそれぞれ登録する:
    GOOGLE_CLIENT_ID
    GOOGLE_CLIENT_SECRET
    GOOGLE_REFRESH_TOKEN
"""

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar"]
CLIENT_SECRET_FILE = "client_secret.json"


def main():
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
    # access_type=offlineかつprompt=consentでrefresh_tokenを確実に発行させる
    creds = flow.run_local_server(
        port=0, access_type="offline", prompt="consent"
    )

    print("\n=== 以下をGitHub Actionsのsecretsに登録してください ===")
    print(f"GOOGLE_CLIENT_ID={creds.client_id}")
    print(f"GOOGLE_CLIENT_SECRET={creds.client_secret}")
    print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}")


if __name__ == "__main__":
    main()
