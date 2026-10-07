# msi-schedule-ics

League of Legends の試合スケジュールをICSファイルにまとめて生成するスクリプト群。

- `all_leagues_schedule.ics`: lolesports 公式の非公開APIから取得した大会(MSI/Worlds/First Stand/LCKなど)
- `ltk_schedule.ics`: LTK (League The K4sen) Season Finale のスケジュール(公式APIが無いため手動データ)

それぞれ別カレンダーとしてGoogleカレンダーに購読することで、色分けして表示できる。

## 対象大会

`lol_esports_to_ics.py` の `TARGET_LEAGUE_SLUGS` で指定する。現状:

- `msi` (MSI)
- `worlds` (Worlds)
- `first_stand` (First Stand)
- `lck` (LCK)

## リーグ単位の絞り込み

`LEAGUE_FILTERS` に指定したリーグは、さらにチーム/ステージ/期間で絞り込まれる。

- `teams`: チームcode基準(例: `T1`)。未指定なら全チーム対象。
- `block_names`: `getSchedule` の `blockName` 基準(例: `プレイオフ`)。未指定なら全ステージ対象。
- `start_date`: ISO8601日付(例: `"2026-08-24"`)以降の試合のみ対象。未指定なら全期間。

現状は LCK のみ、T1 の Regional Championship(Worlds出場権をかけた最終ステージ)戦のみを対象にしている。

```python
LEAGUE_FILTERS = {
    "lck": {
        "teams": ["T1"],
        "block_names": ["プレイオフ", "Finals"],
        "start_date": "2026-08-24",
    },
}
```

### なぜ `block_names` だけでは絞り込めないのか(毎年の要更新ポイント)

lolesports API の `blockName` は年によって表記が変わる。例えば LCK の
Worlds出場権をかけた最終ステージは、2024〜2025年は `Regional Qualifier`
という専用の名前だったが、2026年は単に `プレイオフ`/`Finals` になっており、
**Split1などの通常プレイオフと同じ名前を使い回している**。そのため
`block_names` だけで絞り込むと、無関係な通常シーズンのプレイオフ試合まで
混ざってしまう。

これを避けるため `start_date` で該当シーズンの開始日を指定し、期間で
絞り込んでいる。**シーズンが切り替わるたびに、以下の手順で
`block_names` / `start_date` を確認・更新すること。**

1. [lolesports公式サイト](https://lolesports.com/) または `getStandings` API
   (`https://esports-api.lolesports.com/persisted/gw/getStandings?hl=ja-JP&tournamentId=<対象split のtournamentId>`)
   でステージ構成(`slug`が`regional_championship`など)を確認する。
2. 該当ステージに属する試合の実際の `startTime` / `blockName` を
   `getSchedule` のレスポンスで確認する(スクリプト内の `get_all_schedule_events`
   を使って手動で調べるのが早い)。
3. `LEAGUE_FILTERS` の `block_names` / `start_date` を実際の値に合わせて書き換える。

`tournamentId` の一覧は `getTournamentsForLeague` API
(`https://esports-api.lolesports.com/persisted/gw/getTournamentsForLeague?hl=ja-JP&leagueId=<リーグID>`)
で取得できる。LCKのリーグIDは `98767991310872058`。

## 使い方

```bash
pip install -r requirements.txt
python lol_esports_to_ics.py      # all_leagues_schedule.ics を生成
python ltk_schedule_to_ics.py     # ltk_schedule.ics を生成
```

生成されたICSファイルは GitHub Actions で定期実行してリポジトリにコミットすることで自動更新される。
Google カレンダー側は、各raw ファイルのURLを「他のカレンダーを追加 > URLで追加」でそれぞれ購読する
(ファイルを分けて購読することで、Googleカレンダー上でカレンダーごとに別の色を設定できる)。

## LTK (League The K4sen) スケジュールの更新

`ltk_schedule_to_ics.py` は lolesports APIを使わず、公式サイトや配信で発表された
スケジュール画像をもとに `REGULAR_STAGE` / `MASTERS_CUP` / `PLAYOFF_DAYS` に
直接記述している。日程が追加・変更されたらこのファイルを直接編集すること。

試合開始時刻は未発表のため、現状はすべて終日イベントとして登録している。
時刻が判明した場合は `build_allday_vevent` を `DTSTART`/`DTEND`(日時指定)に変更する。
