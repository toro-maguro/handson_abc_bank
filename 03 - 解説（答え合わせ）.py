# Databricks notebook source
# MAGIC %md
# MAGIC # 03 答え合わせ 🎓（種明かし）
# MAGIC
# MAGIC お疲れさまでした！ このモジュールは**講師といっしょに**、あなたの発見が当たっていたかを確認します。
# MAGIC （ここから先は**ネタバレ**です。02 を先にやってから読んでください。）
# MAGIC
# MAGIC このモジュールで明らかにすること：
# MAGIC - 2つの謎の**正解**（実際の数字つき）
# MAGIC - Genie が裏側で使っていた**答え合わせ用ビュー `vw_sales_steps`**（4つの履歴をどう結合していたか）
# MAGIC - **正解の可視化**（あなたが 02 で作ったダッシュボードと見比べる）

# COMMAND ----------

# MAGIC %run ./Includes/Classroom-Setup-lite

# COMMAND ----------

# MAGIC %md
# MAGIC ## 種明かし① — Genie は「1枚にまとめたビュー」を裏で使っていた
# MAGIC 02 であなたが日本語で問いかけたとき、Genie は毎回4つの履歴を結合していたわけではありません。
# MAGIC 実は 00 のセットアップで、**メール・架電・商談・成約を顧客単位で1枚にまとめた
# MAGIC ビュー `vw_sales_steps`** をこっそり作っておき、Genie にはそれを見せていました。
# MAGIC （＝結合の"知能"をビューに隠しておいたので、参加者は日本語で聞くだけでよかった、という仕掛けです。）
# MAGIC
# MAGIC このビューは**参加者向けのテーブル一覧にはあえて出していません**。中身を見てみましょう。

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT * FROM vw_sales_steps LIMIT 10;

# COMMAND ----------

# MAGIC %md
# MAGIC ### ビューの定義（どう結合しているか）
# MAGIC 4つの履歴を `customer_id`＋`campaign_id` で突き合わせ、顧客ごとに「どのステップまで進んだか」を
# MAGIC 1行にまとめています。`timely_call`（クリックから120分以内に架電できたか）もここで計算しています。

# COMMAND ----------

# MAGIC %sql
# MAGIC SHOW CREATE TABLE vw_sales_steps;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 種明かし② — 謎その1の正解：勝ち筋は「若い顧客 × クリック後すぐ架電」
# MAGIC メールをクリックした顧客を「若いか（40歳未満）」×「クリック後すぐ架電できたか」で分けると、
# MAGIC **若い顧客にすぐ架電できたときが、商談率・成約率ともに圧倒的に高い**ことが分かります。

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   CASE WHEN age < 40 THEN '若い(40歳未満)' ELSE '40歳以上' END AS `顧客層`,
# MAGIC   CASE WHEN timely_call THEN 'すぐ架電(120分以内)' ELSE '架電が遅い' END AS `架電の速さ`,
# MAGIC   COUNT(*) AS `人数`,
# MAGIC   ROUND(100.0*AVG(CASE WHEN meeting_held THEN 1 ELSE 0 END),1) AS `商談率_pct`,
# MAGIC   ROUND(100.0*AVG(CASE WHEN closed       THEN 1 ELSE 0 END),1) AS `成約率_pct`
# MAGIC FROM vw_sales_steps
# MAGIC WHERE clicked
# MAGIC GROUP BY 1, 2
# MAGIC ORDER BY 1, 2;

# COMMAND ----------

# MAGIC %md
# MAGIC ### さらに：若い顧客の商談は「オンライン」が中心
# MAGIC 勝ち筋の顧客層（若い顧客）は、商談のやり方も特徴的です。

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT meeting_mode AS `商談のやり方`, COUNT(*) AS `件数`,
# MAGIC   ROUND(100.0*COUNT(*)/SUM(COUNT(*)) OVER (),1) AS `割合_pct`
# MAGIC FROM vw_sales_steps
# MAGIC WHERE age < 40 AND meeting_held
# MAGIC GROUP BY meeting_mode;

# COMMAND ----------

# MAGIC %md
# MAGIC <div style="border-left:4px solid #6a1b9a;background:#f3e5f5;padding:14px 18px;border-radius:4px;margin:12px 0;color:#333;">
# MAGIC <b>謎その1の答え：</b>
# MAGIC 「定期預金キャンペーンのメールURLをクリックした<b>若い顧客に、すぐ（120分以内に）架電</b>すると、
# MAGIC 商談率・成約率がはっきり上がる。そしてその商談は<b>ほとんどがオンライン</b>。」<br>
# MAGIC → 施策の示唆：<b>若年層のクリックを即座に検知して、その場で架電＋オンライン商談に誘導</b>する体制が効く。
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## 種明かし③ — 謎その2の正解：脱落がいちばん大きいのは最初の「メール→クリック」
# MAGIC 各ステップの人数と脱落率を並べます。最初の関門（クリックしてもらう）でいちばん多く取りこぼしています。

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   COUNT(*)                                       AS `1_対象`,
# MAGIC   SUM(CASE WHEN clicked      THEN 1 ELSE 0 END)  AS `2_クリック`,
# MAGIC   SUM(CASE WHEN called       THEN 1 ELSE 0 END)  AS `3_架電`,
# MAGIC   SUM(CASE WHEN contacted    THEN 1 ELSE 0 END)  AS `4_接触`,
# MAGIC   SUM(CASE WHEN meeting_held THEN 1 ELSE 0 END)  AS `5_商談`,
# MAGIC   SUM(CASE WHEN closed       THEN 1 ELSE 0 END)  AS `6_成約`
# MAGIC FROM vw_sales_steps;

# COMMAND ----------

# MAGIC %sql
# MAGIC -- ステップごとの脱落率（前のステップから何％こぼれたか）を縦持ちで
# MAGIC WITH s AS (
# MAGIC   SELECT
# MAGIC     COUNT(*)                                       AS targeted,
# MAGIC     SUM(CASE WHEN clicked      THEN 1 ELSE 0 END)  AS clicked_n,
# MAGIC     SUM(CASE WHEN called       THEN 1 ELSE 0 END)  AS called_n,
# MAGIC     SUM(CASE WHEN contacted    THEN 1 ELSE 0 END)  AS contacted_n,
# MAGIC     SUM(CASE WHEN meeting_held THEN 1 ELSE 0 END)  AS meeting_n,
# MAGIC     SUM(CASE WHEN closed       THEN 1 ELSE 0 END)  AS closed_n
# MAGIC   FROM vw_sales_steps
# MAGIC )
# MAGIC SELECT `遷移`, `脱落率_pct` FROM (
# MAGIC   SELECT 'A.対象→クリック' AS `遷移`, ROUND(100.0*(1 - clicked_n/targeted),1)   AS `脱落率_pct` FROM s
# MAGIC   UNION ALL SELECT 'B.クリック→架電', ROUND(100.0*(1 - called_n/clicked_n),1)    FROM s
# MAGIC   UNION ALL SELECT 'C.架電→接触',   ROUND(100.0*(1 - contacted_n/called_n),1)  FROM s
# MAGIC   UNION ALL SELECT 'D.接触→商談',   ROUND(100.0*(1 - meeting_n/contacted_n),1) FROM s
# MAGIC   UNION ALL SELECT 'E.商談→成約',   ROUND(100.0*(1 - closed_n/meeting_n),1)    FROM s
# MAGIC ) ORDER BY `遷移`;

# COMMAND ----------

# MAGIC %md
# MAGIC <div style="border-left:4px solid #6a1b9a;background:#f3e5f5;padding:14px 18px;border-radius:4px;margin:12px 0;color:#333;">
# MAGIC <b>謎その2の答え：</b>
# MAGIC 最初の「対象→クリック」で約4分の3が脱落し、ここが最大の関門。次いで「接触→商談」の脱落も大きい。<br>
# MAGIC → 施策の示唆：<b>①メールのクリック率を上げる ②接触後に商談へつなげる</b> の順で効果が大きい。
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## おまけの発見 — 65歳以上の優良顧客は「別の切り口」が見える
# MAGIC 今回の勝ち筋（若年層×即架電）とは別に、**65歳以上で定期預金額が多い顧客**には
# MAGIC はっきりした特徴があります。退職金運用プラン・年金受取口座の利用が非常に多いのです。
# MAGIC （＝この層には、金利キャンペーンとは違う「退職金・年金」を軸にした提案が刺さりそう、という仮説。）

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT
# MAGIC   CASE WHEN age >= 65 AND term_deposit_balance >= (SELECT PERCENTILE(term_deposit_balance,0.5) FROM vw_sales_steps WHERE age>=65)
# MAGIC        THEN '65歳以上×高額定期' ELSE 'それ以外' END AS `顧客層`,
# MAGIC   COUNT(*) AS `人数`,
# MAGIC   ROUND(100.0*AVG(CASE WHEN retirement_plan_flag THEN 1 ELSE 0 END),1) AS `退職金運用プラン利用率_pct`,
# MAGIC   ROUND(100.0*AVG(CASE WHEN pension_account_flag THEN 1 ELSE 0 END),1) AS `年金受取口座利用率_pct`
# MAGIC FROM vw_sales_steps
# MAGIC GROUP BY 1
# MAGIC ORDER BY 1;

# COMMAND ----------

# MAGIC %md
# MAGIC ## 正解の可視化とダッシュボード
# MAGIC 上の各セルの結果表は、左下の「＋」から**グラフ**に切り替えられます。
# MAGIC さらに、結果の「Add to dashboard」から、02 で作ったダッシュボードに**正解のグラフ**を足して、
# MAGIC 「自分の発見」と「正解」を1枚で見比べると理解が深まります。
# MAGIC
# MAGIC <div style="border-left:4px solid #1976d2;background:#e3f2fd;padding:12px 16px;border-radius:4px;margin:12px 0;color:#333;">
# MAGIC <b>講師の方へ：</b>この 03 を投影しながら、参加者に「自分の仮説と合っていたか」を口頭で共有してもらうと盛り上がります。
# MAGIC 各シナリオの数字はこのノートブックを Run すればライブで再計算されます（合成データは決定的なので毎回同じ値）。
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## まとめ 🎉
# MAGIC - **勝ち筋**：クリックした若い顧客に**すぐ架電**＋**オンライン商談**で成約が伸びる
# MAGIC - **最大の取りこぼし**：最初の「メール→クリック」。次いで「接触→商談」
# MAGIC - **別の切り口**：65歳以上の高額定期の顧客は退職金運用・年金受取口座の利用が多く、別提案が有効
# MAGIC
# MAGIC そして何より——これらを **SQL を書かずに、日本語で Genie に問いかけるだけ**で発見できた、
# MAGIC というのが今日のいちばんの体験です。おつかれさまでした！
