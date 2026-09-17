# Databricks notebook source
# MAGIC %md
# MAGIC ## モジュール 00 用セットアップ（初回のデータ構築）
# MAGIC 共通セットアップを呼び、**合成データ・営業ステップのビュー・Genie** を冪等に構築します。
# MAGIC 何度実行しても壊れません（`CREATE OR REPLACE` / 同名 Genie は再利用）。

# COMMAND ----------

# MAGIC %run ./Classroom-Setup-Common

# COMMAND ----------

# 1) 合成データ（顧客・キャンペーン・4つの業務履歴）を生成
generate_data()

# 2) 講師用の答え合わせビュー（参加者一覧には出さない。Genie が裏で使う）
create_sales_steps_view()

# 2b) テーブル/ビューに日本語メタデータ（COMMENT）を付与
#     → 01 でのテーブル探索・Genie / Genie Code の精度を上げる
add_metadata()

# 3) 受講者向けチェック：データが入ったか
for _t, _m in [("dim_customers",1000),("campaign_email_results",1),
               ("outbound_call_history",1),("meeting_history",1),("contract_history",1)]:
    check_row_count(_t, expected_min=_m)

# COMMAND ----------

# 4) 日本語で問える Genie エージェントを作成（API・冪等）
genie_space_id = create_genie_agent()
