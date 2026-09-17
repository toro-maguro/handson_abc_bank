# ABC銀行 データ & AI 体験ハンズオン（Databricks Free Edition）

SQL を書かずに、**日本語で Genie に問いかけるだけ**でデータを探索し、銀行の定期預金キャンペーンの
営業データから「勝ち筋」と「取りこぼし」を発見する体験型ハンズオン。最後は気づきを **AI/BI ダッシュボード**にまとめます。

> 本教材のデータは**すべて架空（合成）**です。実在の個人・組織・取引とは関係ありません。銀行名「ABC銀行」も架空です。

## 対象と狙い
- **対象**：これから Databricks を触る非エンジニア／アナリスト（SQL に不慣れでもOK）
- **狙い**：Databricks の基本操作 → Genie での自然言語データ探索 → ダッシュボード化 を1時間強で一気通貫体験

## 進め方（各自の Databricks Free Edition で）
1. このリポジトリを clone するか、ノートブックを各自のワークスペースに取り込む
2. 上から順に実行：
   - **00 - はじめに（環境準備とデータ紹介）** … 最初に1回。データと Genie を自動生成（冪等）
   - **01 - Databricksの使い方** … SQL / Python を少し動かす
   - **02 - データ探索ゲーム** … Genie で勝ち筋を探す＋ダッシュボード化（ハイライト）
   - **03 - 答え合わせ** … 種明かし（講師が投影）

## 構成
```
abc-bank-data-ai-workshop/
├── 00 - はじめに（環境準備とデータ紹介）.py
├── 01 - Databricksの使い方.py
├── 02 - データ探索ゲーム.py
├── 03 - 解説（答え合わせ）.py
├── README.md
└── Includes/
    ├── Classroom-Setup-Common.py    # 環境解決＋合成データ生成＋Genie作成＋チェックポイント
    ├── Classroom-Setup-00.py        # 00 用：データ生成を実行
    └── Classroom-Setup-lite.py      # 01〜03 用：データ存在確認のみ
```

## 環境・前提
- Databricks **Free Edition**（各自でサインアップ）
- catalog = `workspace` / schema = `abc_bank`（`CREATE CATALOG` はしない）
- serverless SQL warehouse（Free Edition に標準）
- Genie エージェントは 00 の実行時に **API で各自のワークスペースに自動作成**（冪等：同名があれば再利用）

## データモデル（参加者に見せるのは生の履歴＋マスタだけ）
- マスタ：`dim_customers`, `dim_campaigns`
- 業務履歴：`campaign_email_results`（メール）, `outbound_call_history`（架電）, `meeting_history`（商談）, `contract_history`（成約）
- **`vw_sales_steps`**：上記を顧客×キャンペーンで1枚に結合した“答え合わせ用”ビュー。参加者一覧には出さず、Genie が裏で使う。03 で種明かし。

## 講師向け
正解・実際の数字・Genie 質問バンク・つまずき対応をまとめた**講師用解答キー**を別途用意しています
（ネタバレのため本リポジトリには含めず、講師に個別配布します）。
