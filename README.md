# 訪問マップ

株式会社AImost の訪問営業用アプリ（建物・部屋ごとの訪問記録）。

- 開く場所：https://aimost-iga.github.io/houmon-map/
- ここに置いているのは、プログラムと、誰でも手に入る地図の材料（市区町村の境界・鉄道・道路・町名）だけです。
- ソニーの建物リスト・特記事項・訪問の記録は、Google（Firebase：aimost-houmon-map）の保管場所にあり、許可された人がログインしたときだけ読めます。
- 入れる人のルールは `firestore.rules`（Firebaseの画面の Firestore →「ルール」に貼って使う）。
- 使える人の追加・削除は、管理者がアプリの「設定」から行います。

## 業務（予定・開始/終了・お題・日報・成績）

- 画面は `seiseki.js` と `seiseki.css`。記録は Firebase の `day/<日付>_<人>`（1日1人1文書、ずっと残す）、お題の基準は `cfg/goal`。
- 自動のお知らせメールと Googleカレンダー「AImost 業務予定」への反映は `tools/notify.gs`（毎晩の書き写しと同じ Apps Script に足して、`setupNotify` を一度実行）。
- 前日までの訪問数は、毎晩の書き写し（`tools/nightly.gs`）が `day` の `v` に残してから活動記録を消す。
