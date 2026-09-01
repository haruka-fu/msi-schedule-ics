# msi-schedule-ics

League of Legends の試合スケジュールを lolesports 公式の非公開APIから取得し、
1つのICSファイル(`all_leagues_schedule.ics`)にまとめて生成するスクリプト。

## 対象大会

`lol_esports_to_ics.py` の `TARGET_LEAGUE_SLUGS` で指定する。現状:

- `msi` (MSI)
- `worlds` (Worlds)
- `first_stand` (First Stand)
- `lck` (LCK)

## リーグ単位の絞り込み

`LEAGUE_FILTERS` に指定したリーグは、さらにチーム/ステージで絞り込まれる。

- `teams`: チームcode基準(例: `T1`)。未指定なら全チーム対象。
- `block_names`: `getSchedule` の `blockName` 基準(例: `Regional Qualifier`)。未指定なら全ステージ対象。

現状は LCK のみ、T1 の Regional Qualifier(リージョナルチャンピオンシップ、Worlds出場権予選)戦のみを対象にしている。

```python
LEAGUE_FILTERS = {
    "lck": {"teams": ["T1"], "block_names": ["Regional Qualifier"]},
}
```

対象を増やす/変える場合は、このdictにリーグslugをキーとして追加・編集する。

## 使い方

```bash
pip install -r requirements.txt
python lol_esports_to_ics.py
```

生成された `all_leagues_schedule.ics` は GitHub Actions で定期実行してリポジトリにコミットすることで自動更新される。
Google カレンダー側は、その raw ファイルの URL を「他のカレンダーを追加 > URLで追加」で購読する。
