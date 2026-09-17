# Databricks notebook source
# MAGIC %md
# MAGIC ## モジュール用セットアップ（軽量・データ確認のみ）
# MAGIC 共通セットアップ（catalog/schema の設定と補助関数）を読み込み、
# MAGIC **00 で作ったデータが存在するか**だけ確認します。データ生成はしません。

# COMMAND ----------

# MAGIC %run ./Classroom-Setup-Common

# COMMAND ----------

# 00 を実行済みか確認（未実行ならここで気づける）
_ok = spark.catalog.tableExists(f"{my_catalog}.{my_schema}.dim_customers")
checkpoint("データの存在確認", _ok,
           "OK: このまま進めます" if _ok else "❌ 先に『00 - はじめに（環境準備）』を上から実行してください")
