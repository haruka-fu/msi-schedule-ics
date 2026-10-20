# Google Calendar API連携 - 残作業

Google Calendar APIへの切り替え実装は完了済み。あとは以下の手動セットアップを
行い、GitHub Actionsのsecretsを登録すれば自動反映が始まる。

詳細手順は [README.md](README.md) の「Googleカレンダーへの反映方法」セクションにも
記載済み。ここではチェックリストとしてまとめる。

## チェックリスト

- [ ] 1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成
- [ ] 2. 「APIとサービス > ライブラリ」で **Google Calendar API** を有効化
- [ ] 3. 「APIとサービス > OAuth同意画面」で自分のGoogleアカウントをテストユーザーに追加
- [ ] 4. 「APIとサービス > 認証情報」で **OAuthクライアントID**(種類: デスクトップアプリ)を作成
- [ ] 5. 作成したクライアントのJSONをダウンロードし、リポジトリ直下に
      `client_secret.json` として保存(コミットしないこと。`.gitignore`済み)
- [ ] 6. ローカルで以下を実行し、表示されたリフレッシュトークンを控える

      ```bash
      pip install -r requirements.txt
      python get_google_refresh_token.py
      ```

- [ ] 7. GitHubリポジトリの **Settings > Secrets and variables > Actions** に
      以下の3つを登録

      - `GOOGLE_CLIENT_ID`
      - `GOOGLE_CLIENT_SECRET`
      - `GOOGLE_REFRESH_TOKEN`

- [ ] 8. Actionsタブから `Update LoL Esports ICS` ワークフローを
      `workflow_dispatch` で手動実行し、ログに
      `Googleカレンダー同期完了: ...` が出ることを確認
- [ ] 9. Googleカレンダーの左サイドバーに「LoL Esports Schedule」という
      カレンダーが自動作成されていること、イベントが入っていることを確認
- [ ] 10. 動作確認が済んだら、このファイル(`TODO_GOOGLE_CALENDAR_SETUP.md`)を削除してよい

## 補足

- `client_secret.json` と `get_google_refresh_token.py` はこの1回限りのセットアップ用。
  リフレッシュトークンを取得したあとは `client_secret.json` を手元に残す必要はない
  (削除してもよい)。
- 既存のICS購読(URLで追加)は引き続き動作するが、Google Calendar API経由の同期が
  メインの反映経路になる。両方残すか、ICS購読を解除するかは任意。
