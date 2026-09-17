# Databricks notebook source
# MAGIC %md
# MAGIC # ABC銀行 データ & AI 体験ハンズオン
# MAGIC ## 〜 自然言語でデータと対話し、営業の「勝ち筋」を見つける 〜
# MAGIC
# MAGIC このハンズオンでは、ABC銀行（架空）の**定期預金キャンペーンの営業データ**を題材に、
# MAGIC Databricks 上で **SQL を書かずに、日本語で問いかけるだけ**でデータを探索し、
# MAGIC 「どんな顧客に・どう営業すると成約が伸びるのか」を自分の手で発見します。
# MAGIC 最後は、見つけた気づきを **ダッシュボード**にまとめるところまで体験します。
# MAGIC
# MAGIC ### このハンズオンで体験すること
# MAGIC - Databricks の基本操作（ノートブックでの SQL / Python 実行）
# MAGIC - **Genie**：日本語で問いかけるだけで、裏側で複数の表を自動で結合して答えを返す AI
# MAGIC - 対話で見つけた気づきを、そのまま **AI/BI ダッシュボード**に載せる
# MAGIC
# MAGIC ### モジュール構成（全体で約60〜75分）
# MAGIC | # | 内容 | 目安 |
# MAGIC |---|------|------|
# MAGIC | 00 | はじめに（環境準備とデータ紹介）← いまここ | 10分 |
# MAGIC | 01 | Databricks の使い方（SQL / Python を少し動かす） | 15分 |
# MAGIC | 02 | データ探索ゲーム（Genie で勝ち筋を探す＋ダッシュボード化） | 30分 |
# MAGIC | 03 | 答え合わせ（種明かしと、きれいな正解ダッシュボード） | 15分 |

# COMMAND ----------

# MAGIC %md
# MAGIC ## 前提条件
# MAGIC <div style="border-left:4px solid #f44336;background:#ffebee;padding:16px 20px;border-radius:4px;margin:16px 0;">
# MAGIC   <strong style="color:#c62828;font-size:1.1em;">実行前に必要なもの</strong>
# MAGIC   <ul style="margin:8px 0 0 0;color:#333;">
# MAGIC     <li>Databricks <b>Free Edition</b> のアカウント（各自でサインアップ済み）</li>
# MAGIC     <li>serverless SQL warehouse（Free Edition では自動で用意されています）</li>
# MAGIC   </ul>
# MAGIC   <div style="color:#333;margin-top:8px;">このハンズオンは <code>workspace</code> カタログに <code>abc_bank</code> スキーマを作って進めます（追加設定は不要）。</div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ1 — 環境を準備する
# MAGIC 下のセルを実行すると、次が**自動で・冪等に**用意されます（何度実行しても安全）。
# MAGIC
# MAGIC 1. あなた専用の schema（`workspace.abc_bank`）
# MAGIC 2. 練習用の**合成データ**（すべて架空。実在の個人情報は一切含みません）
# MAGIC 3. 日本語で問いかけられる **Genie エージェント**
# MAGIC
# MAGIC > セル左側の ▶︎ を押すか、`Shift + Enter` で実行します。初回は warehouse の起動に1〜2分かかることがあります。

# COMMAND ----------

# MAGIC %run ./Includes/Classroom-Setup-00

# COMMAND ----------

# MAGIC %md
# MAGIC <div style="border-left:4px solid #43a047;background:#e8f5e9;padding:12px 16px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#2e7d32;">✔ 期待される結果</strong>
# MAGIC   <div style="color:#333;margin-top:4px;">
# MAGIC   上に ✅ が並び、<code>dim_customers: 1,000 行</code> などの件数と、
# MAGIC   「Genie エージェントを作成しました」の緑枠が表示されれば成功です。
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ2 — 今日あつかうデータを知る
# MAGIC ABC銀行が「定期預金キャンペーンのメール」を送ってから成約に至るまでの、**実際に起きた出来事の記録**です。
# MAGIC 4つの履歴と、顧客・キャンペーンの一覧（マスタ）があります。
# MAGIC
# MAGIC | テーブル | 中身 | 粒度 |
# MAGIC |---|---|---|
# MAGIC | `dim_customers` | 顧客の一覧（年齢・定期預金額・退職金運用プラン/年金受取口座の利用 など） | 1顧客=1行 |
# MAGIC | `dim_campaigns` | キャンペーンの一覧 | 1件 |
# MAGIC | `campaign_email_results` | メールの送信・開封・**URLクリック**の記録 | 1顧客=1行 |
# MAGIC | `outbound_call_history` | **架電**の記録（1顧客に複数回の試行あり・通話成立） | 1架電=1行 |
# MAGIC | `meeting_history` | **商談**の記録（オンライン/対面・実施したか） | 1商談=1行 |
# MAGIC | `contract_history` | **成約（契約）**の記録（契約高・期間・金利） | 1契約=1行 |
# MAGIC
# MAGIC <div style="border-left:4px solid #1976d2;background:#e3f2fd;padding:12px 16px;border-radius:4px;margin:12px 0;color:#333;">
# MAGIC これらは <b>バラバラの履歴</b>です。「どんな顧客が成約したか」を知るには本来これらを突き合わせる必要がありますが、
# MAGIC 今日はその面倒な作業を <b>Genie（AI）が裏側でやってくれます</b>。まずはどんなデータかだけ眺めてみましょう。
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ### 顧客の一覧（先頭10行）
# MAGIC 年齢・都道府県・定期預金額や、退職金運用プラン・年金受取口座を使っているか、などが入っています。

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT * FROM dim_customers LIMIT 10;

# COMMAND ----------

# MAGIC %md
# MAGIC ### メールのクリック履歴（先頭10行）
# MAGIC 誰がメールを開き、URL をクリックしたか（`clicked`）と、その日時が入っています。

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT * FROM campaign_email_results LIMIT 10;

# COMMAND ----------

# MAGIC %md
# MAGIC ### 架電・商談・成約の履歴（各先頭5行）
# MAGIC バラバラに記録されている様子を確認してください。

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT * FROM outbound_call_history LIMIT 5;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT * FROM meeting_history LIMIT 5;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT * FROM contract_history LIMIT 5;

# COMMAND ----------

# MAGIC %md
# MAGIC ## まとめ
# MAGIC 環境の準備ができ、今日あつかう **6つのテーブル**（顧客・キャンペーン・4つの履歴）を確認しました。
# MAGIC
# MAGIC **次のモジュール 01** では、いきなり Genie に行く前に、Databricks のノートブックで
# MAGIC **SQL と Python を少しだけ自分で動かして**操作に慣れます。
# MAGIC （Genie が裏でやっていることの「手動版」を体験しておくと、02 の"すごさ"がよく分かります。）
