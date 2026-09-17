# Databricks notebook source
# MAGIC %md
# MAGIC # 01 Databricks の使い方（SQL / Python を少し動かす）
# MAGIC
# MAGIC このモジュールでは、02 の Genie 体験の前に、**ノートブックで自分の手を動かして**
# MAGIC Databricks の基本操作に慣れます。ここで「手作業だと少し面倒」を体験しておくと、
# MAGIC 02 で Genie がそれを肩代わりする"ありがたさ"がはっきり分かります。
# MAGIC
# MAGIC ### このモジュールの到達目標
# MAGIC - ノートブックのセルで **SQL** を実行し、結果を表・グラフで見られる
# MAGIC - `GROUP BY` で**集計**できる
# MAGIC - **Python（PySpark）**でも同じことができると分かる
# MAGIC - 複数の表を**結合（JOIN）**する大変さを体感する ← 02 への伏線
# MAGIC
# MAGIC ### 所要時間
# MAGIC 約 15 分

# COMMAND ----------

# MAGIC %md
# MAGIC ## 環境セットアップ
# MAGIC 下のセルで、00 で作ったデータが使える状態にします（データ生成はしません。数秒で終わります）。

# COMMAND ----------

# MAGIC %run ./Includes/Classroom-Setup-lite

# COMMAND ----------

# MAGIC %md
# MAGIC ## ノートブックの基本
# MAGIC - このページは**セル**の集まりです。セルには **Markdown（説明文）** と **コード** があります。
# MAGIC - コードセルは、左上の ▶︎ を押すか **`Shift + Enter`** で実行します。
# MAGIC - コードセルの先頭に `%sql` と書くと **SQL**、何も書かなければ **Python** として動きます。
# MAGIC
# MAGIC まずは一番かんたんな SQL から。次のセルを実行してみましょう。

# COMMAND ----------

# MAGIC %sql
# MAGIC -- 顧客テーブルから10行だけ取り出す
# MAGIC SELECT customer_id, age, age_band, segment, term_deposit_balance
# MAGIC FROM dim_customers
# MAGIC LIMIT 10;

# COMMAND ----------

# MAGIC %md
# MAGIC <div style="border-left:4px solid #43a047;background:#e8f5e9;padding:12px 16px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#2e7d32;">✔ 期待される結果</strong>
# MAGIC   <div style="color:#333;margin-top:4px;">10行の顧客データが表で表示されます。列ヘッダをクリックすると並べ替えもできます。</div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## 集計してみる（`GROUP BY`）
# MAGIC 「年代ごとに何人いるか」を数えてみます。`GROUP BY` は「〜ごとにまとめる」という意味です。

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT age_band AS `年代`, COUNT(*) AS `人数`
# MAGIC FROM dim_customers
# MAGIC GROUP BY age_band
# MAGIC ORDER BY age_band;

# COMMAND ----------

# MAGIC %md
# MAGIC <div style="border-left:4px solid #1976d2;background:#e3f2fd;padding:12px 16px;border-radius:4px;margin:12px 0;color:#333;">
# MAGIC <b>ヒント：グラフにしてみよう</b><br>
# MAGIC 結果表の左下にある「＋」や「Visualization」から、棒グラフに切り替えられます。
# MAGIC 「年代」を横軸、「人数」を縦軸にすると分布が見えます。
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## 少しだけ実務的に：メールの開封率・クリック率
# MAGIC 販促メールの「送った数・開いた数・クリックした数」を数えて、率を出してみます。

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   COUNT(*)                                        AS `送信数`,
# MAGIC   SUM(CASE WHEN opened  THEN 1 ELSE 0 END)        AS `開封数`,
# MAGIC   SUM(CASE WHEN clicked THEN 1 ELSE 0 END)        AS `クリック数`,
# MAGIC   ROUND(100.0*AVG(CASE WHEN clicked THEN 1 ELSE 0 END),1) AS `クリック率_pct`
# MAGIC FROM campaign_email_results;

# COMMAND ----------

# MAGIC %md
# MAGIC ## Python（PySpark）でも同じことができる
# MAGIC SQL だけでなく Python でもデータを扱えます。書き方が違うだけで、やっていることは同じです。

# COMMAND ----------

# spark.table(...) でテーブルを読み、groupBy で集計、display() で表示
df = spark.table("dim_customers")
display(
    df.groupBy("segment").count().orderBy("segment")
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## ここが伏線：表を「結合（JOIN）」するのは少し大変
# MAGIC 「**メールをクリックした人が、実際に成約したか**」を知りたいとします。
# MAGIC でも、クリックの記録（`campaign_email_results`）と成約の記録（`contract_history`）は**別々の表**です。
# MAGIC 突き合わせる（JOIN する）には、こんな SQL を書く必要があります。

# COMMAND ----------

# MAGIC %sql
# MAGIC -- クリックした人のうち、成約に至った割合
# MAGIC SELECT
# MAGIC   ROUND(100.0 * COUNT(DISTINCT ct.customer_id) / COUNT(DISTINCT e.customer_id), 1) AS `クリック者の成約率_pct`
# MAGIC FROM campaign_email_results e
# MAGIC LEFT JOIN contract_history ct
# MAGIC   ON e.customer_id = ct.customer_id AND e.campaign_id = ct.campaign_id
# MAGIC WHERE e.clicked = true;

# COMMAND ----------

# MAGIC %md
# MAGIC <div style="border-left:4px solid #ff9800;background:#fff3e0;padding:14px 18px;border-radius:4px;margin:12px 0;color:#333;">
# MAGIC これはまだ2つの表の結合です。今日のデータは<b>メール・架電・商談・成約の4つ</b>に分かれているので、
# MAGIC 「クリック後すぐ架電した若い顧客の成約率は？」のような問いに答えるには、<b>4つ全部を正しく結合</b>する
# MAGIC 必要があり、慣れていないと大変です。<br><br>
# MAGIC <b>——この面倒を、次のモジュールでは Genie（AI）が肩代わりしてくれます。</b>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## ✅ チェックポイント

# COMMAND ----------

check_row_count("campaign_email_results", expected_min=1)
checkpoint("01 完了", True, "SQL・Python・JOIN の基本を体験しました。02 に進みましょう。")

# COMMAND ----------

# MAGIC %md
# MAGIC ## まとめ
# MAGIC ノートブックで SQL / Python を動かし、集計と結合の基本を体験しました。
# MAGIC そして「4つの表を結合するのは大変」という**伏線**を仕込みました。
# MAGIC
# MAGIC **次のモジュール 02** では、いよいよ **Genie に日本語で問いかけるだけ**で、
# MAGIC この面倒な結合を裏側でやってもらい、営業の「勝ち筋」を探しにいきます。
