# Databricks notebook source
# MAGIC %md
# MAGIC # 共通セットアップ (Classroom-Setup-Common)
# MAGIC
# MAGIC 各モジュールの冒頭から `%run` で呼ばれ、**環境差を吸収しながら冪等に**
# MAGIC ハンズオン用の catalog / schema・合成データ・営業ステップのビュー・Genie を用意します。
# MAGIC 何度実行しても・誰が実行しても壊れません。
# MAGIC
# MAGIC 呼び出し側に公開するもの:
# MAGIC - 変数 `my_catalog` / `my_schema` … 解決済みの書き込み先
# MAGIC - 関数 `generate_data()` … 合成データ(顧客・キャンペーン・4つの業務履歴)を冪等生成
# MAGIC - 関数 `create_sales_steps_view()` … 講師用の答え合わせビュー `vw_sales_steps`(参加者一覧には出さない)
# MAGIC - 関数 `create_genie_agent()` … 日本語で問える Genie を API で作成(冪等)
# MAGIC - 関数 `checkpoint(...)` / `check_row_count(...)` … 受講者向け ✅/❌ 検証表示
# MAGIC
# MAGIC > このノートブックは直接開かず、各モジュールから `%run ./Includes/...` してください。

# COMMAND ----------

import re, json, uuid

# --- ウィジェット（環境ごとに上書き可能） --------------------------------------
# Free Edition は catalog=workspace 固定でよい（CREATE CATALOG しない）。
dbutils.widgets.text("catalog", "workspace", "1. Catalog")
dbutils.widgets.text("schema",  "abc_bank",  "2. Schema")

_req_catalog = dbutils.widgets.get("catalog").strip() or "workspace"
_schema      = dbutils.widgets.get("schema").strip()  or "abc_bank"


def _safe(s: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", s.lower())


_user_email = spark.sql("SELECT current_user()").first()[0]

# --- catalog / schema の解決（schema 作成を主軸に。CREATE CATALOG はしない） -----
_catalog = _req_catalog
try:
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{_catalog}`.`{_schema}`")
except Exception as e:  # noqa: BLE001
    # workspace catalog に書けない環境では現在の catalog にフォールバック
    _catalog = spark.sql("SELECT current_catalog()").first()[0]
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{_catalog}`.`{_schema}`")

spark.sql(f"USE CATALOG `{_catalog}`")
spark.sql(f"USE SCHEMA `{_schema}`")
my_catalog, my_schema = _catalog, _schema
_fqs = f"`{my_catalog}`.`{my_schema}`"   # fully-qualified schema

# COMMAND ----------

# --- 受講者向けチェックポイント（詰まりを ✅/❌ で可視化） -------------------------
def checkpoint(label: str, ok: bool, detail: str = ""):
    color, bg, icon = (("#2e7d32", "#e8f5e9", "✅") if ok else ("#c62828", "#ffebee", "❌"))
    extra = f'<div style="color:#333;margin-top:4px;">{detail}</div>' if detail else ""
    displayHTML(
        f'<div style="border-left:4px solid {color};background:{bg};'
        f'padding:10px 14px;border-radius:4px;margin:8px 0;font-family:sans-serif;">'
        f'<strong style="color:{color};font-size:1.05em;">{icon} {label}</strong>{extra}</div>')


def check_row_count(table: str, expected_min: int = 1) -> int:
    n = spark.table(f"{_fqs}.`{table}`").count()
    checkpoint(f"{table}: {n:,} 行", n >= expected_min, f"期待: {expected_min:,} 行以上")
    return n

# COMMAND ----------

# --- 合成データ生成（決定的・冪等。全て架空。実在の個人情報は一切含まない） ----------
# 顧客1,000人 + キャンペーン1件 + 4つの業務履歴（メール／架電／商談／契約）。
# 埋め込む信号(生成後にグループ集計で検証できる):
#   ① 若い顧客(40歳未満)がURLクリック後すぐ架電されると、商談・成約が伸びる。商談はほぼオンライン。
#   ② 65歳以上で定期預金が多い顧客は、退職金運用プラン・年金受取口座の利用が多い。
def generate_data():
    # 1) 顧客ディメンション
    spark.sql(f"""
    CREATE OR REPLACE TABLE {_fqs}.dim_customers AS
    WITH b AS (
      SELECT concat('C', lpad(cast(id AS string),5,'0')) AS customer_id, id AS sid,
        pmod(hash(id,101),100000)/100000.0 AS u_age, pmod(hash(id,102),100000)/100000.0 AS u_gender,
        pmod(hash(id,103),100000)/100000.0 AS u_seg, pmod(hash(id,104),100000)/100000.0 AS u_pref,
        pmod(hash(id,105),100000)/100000.0 AS u_bal, pmod(hash(id,106),100000)/100000.0 AS u_ret,
        pmod(hash(id,107),100000)/100000.0 AS u_pen, pmod(hash(id,108),100000)/100000.0 AS u_dnc,
        pmod(hash(id,109),100000)/100000.0 AS u_consent, pmod(hash(id,110),100000)/100000.0 AS u_reg
      FROM range(1,1001)
    ),
    a AS (
      SELECT *,
        CASE WHEN u_age<0.33 THEN cast(25 + u_age/0.33*14 AS int)
             WHEN u_age<0.65 THEN cast(40 + (u_age-0.33)/0.32*24 AS int)
             ELSE cast(65 + (u_age-0.65)/0.35*20 AS int) END AS age,
        cast(500000 + u_bal*19500000 AS bigint) AS term_deposit_balance
      FROM b
    )
    SELECT customer_id, age,
      concat(cast(floor(age/10)*10 AS int), CASE WHEN age>=70 THEN '代以上' ELSE '代' END) AS age_band,
      CASE WHEN u_gender<0.5 THEN '男性' ELSE '女性' END AS gender,
      CASE WHEN u_seg<0.2 THEN 'マス' WHEN u_seg<0.6 THEN 'マスリテール' WHEN u_seg<0.9 THEN '準富裕層' ELSE '富裕層' END AS segment,
      element_at(array('東京都','神奈川県','千葉県','埼玉県','大阪府','愛知県','福岡県','北海道'), cast(u_pref*8 AS int)+1) AS prefecture,
      term_deposit_balance,
      cast(term_deposit_balance*(1.2+u_bal*1.5) AS bigint) AS total_deposit,
      ((age>=65 AND u_bal>=0.5 AND u_ret<0.82) OR (NOT(age>=65 AND u_bal>=0.5) AND u_ret<0.05)) AS retirement_plan_flag,
      ((age>=65 AND u_bal>=0.5 AND u_pen<0.85) OR (NOT(age>=65 AND u_bal>=0.5) AND u_pen<0.06)) AS pension_account_flag,
      (u_dnc<0.05) AS do_not_call_flag, (u_consent<0.90) AS consent,
      date_add(date'2018-01-01', cast(u_reg*2900 AS int)) AS registration_date
    FROM a
    """)

    # 2) キャンペーンディメンション
    spark.sql(f"""
    CREATE OR REPLACE TABLE {_fqs}.dim_campaigns AS
    SELECT 'CP001' AS campaign_id, '定期預金金利アップキャンペーン2026夏' AS campaign_name,
           'P001' AS product_id, 'スーパー定期300' AS product_name, 'email' AS channel, date'2026-06-01' AS start_date
    """)

    # 3) 内部スパイン（全イベント判定・時系列を1枚に。生成専用。参加者には見せない）
    spark.sql(f"""
    CREATE OR REPLACE TABLE {_fqs}._spine AS
    WITH c AS (
      SELECT customer_id, age, (age<40) AS is_young, do_not_call_flag, consent,
        pmod(hash(customer_id,201),100000)/100000.0 AS u_open, pmod(hash(customer_id,202),100000)/100000.0 AS u_click,
        pmod(hash(customer_id,203),100000)/100000.0 AS u_call, pmod(hash(customer_id,204),100000)/100000.0 AS u_timely,
        pmod(hash(customer_id,205),100000)/100000.0 AS u_conn, pmod(hash(customer_id,206),100000)/100000.0 AS u_meet,
        pmod(hash(customer_id,207),100000)/100000.0 AS u_mode, pmod(hash(customer_id,208),100000)/100000.0 AS u_close,
        pmod(hash(customer_id,209),20160) AS h_send, pmod(hash(customer_id,210),2880) AS h_open,
        pmod(hash(customer_id,211),720) AS h_click, pmod(hash(customer_id,212),2600) AS h_call,
        pmod(hash(customer_id,213),4320) AS h_meet, pmod(hash(customer_id,214),7) AS h_ct,
        pmod(hash(customer_id,215),95) AS h_amt, pmod(hash(customer_id,216),4) AS h_term,
        pmod(hash(customer_id,217),70) AS h_rate, pmod(hash(customer_id,218),3) AS h_att
      FROM {_fqs}.dim_customers
    ),
    elig AS ( SELECT * FROM c WHERE (NOT do_not_call_flag AND consent) ),
    s AS ( SELECT *, timestampadd(MINUTE, h_send, timestamp'2026-06-01 09:00:00') AS sent_at FROM elig ),
    op AS ( SELECT *, (u_open<0.55) AS opened, CASE WHEN u_open<0.55 THEN timestampadd(MINUTE, 30+h_open, sent_at) END AS opened_at FROM s ),
    ck AS ( SELECT *, (opened AND u_click<0.45) AS clicked, CASE WHEN (opened AND u_click<0.45) THEN timestampadd(MINUTE, 10+h_click, opened_at) END AS clicked_at FROM op ),
    ca AS ( SELECT *, (clicked AND u_call<0.90) AS called, (clicked AND u_call<0.90 AND u_timely<0.5) AS timely_call,
              CASE WHEN (clicked AND u_call<0.90) THEN (CASE WHEN u_timely<0.5 THEN 5+cast(h_click%110 AS int) ELSE 200+h_call END) END AS time_to_call_minutes FROM ck ),
    ca2 AS ( SELECT *, CASE WHEN called THEN timestampadd(MINUTE, time_to_call_minutes, clicked_at) END AS called_at, (called AND u_conn<0.85) AS connected FROM ca ),
    mp AS ( SELECT *, CASE WHEN is_young AND timely_call THEN 0.75 WHEN (NOT is_young) AND timely_call THEN 0.45
                           WHEN is_young AND (NOT timely_call) THEN 0.30 ELSE 0.24 END AS p_meet FROM ca2 ),
    mh AS ( SELECT *, (connected AND u_meet < p_meet/0.85) AS meeting_scheduled, (connected AND u_meet < p_meet) AS meeting_held FROM mp ),
    mh2 AS ( SELECT *, CASE WHEN (connected AND u_meet < p_meet/0.85) THEN timestampadd(MINUTE, 60+h_meet, called_at) END AS meeting_at,
              CASE WHEN (connected AND u_meet < p_meet/0.85) THEN (CASE WHEN is_young THEN (CASE WHEN u_mode<0.75 THEN 'online' ELSE 'branch' END) ELSE (CASE WHEN u_mode<0.35 THEN 'online' ELSE 'branch' END) END) END AS meeting_mode FROM mh ),
    cl AS ( SELECT *, (meeting_held AND u_close<0.72) AS closed FROM mh2 ),
    cl2 AS ( SELECT *,
              CASE WHEN (meeting_held AND u_close<0.72) THEN date_add(cast(meeting_at AS date), h_ct) END AS contract_date,
              CASE WHEN (meeting_held AND u_close<0.72) THEN cast(500000 + h_amt*100000 AS bigint) END AS principal_amount,
              CASE WHEN (meeting_held AND u_close<0.72) THEN element_at(array(6,12,36,60), h_term+1) END AS term_months,
              CASE WHEN (meeting_held AND u_close<0.72) THEN round(0.10 + h_rate/100.0, 2) END AS interest_rate FROM cl )
    SELECT customer_id, age, is_young, 'CP001' AS campaign_id, sent_at, opened, opened_at, clicked, clicked_at,
      called, timely_call, time_to_call_minutes, called_at, connected,
      meeting_scheduled, meeting_held, meeting_at, meeting_mode, closed, contract_date, principal_amount, term_months, interest_rate,
      (1 + h_att + CASE WHEN connected THEN 0 ELSE 1 END) AS n_attempts
    FROM cl2
    """)

    # 4) 参加者に見せる「生の業務履歴」4つ
    spark.sql(f"""CREATE OR REPLACE TABLE {_fqs}.campaign_email_results AS
      SELECT concat('EM-', customer_id) AS email_id, campaign_id, customer_id, sent_at, opened, opened_at, clicked, clicked_at FROM {_fqs}._spine""")
    spark.sql(f"""CREATE OR REPLACE TABLE {_fqs}.meeting_history AS
      SELECT concat('MT-', customer_id) AS meeting_id, customer_id, campaign_id, meeting_at, meeting_mode, meeting_held AS held,
        CASE WHEN closed THEN '成約' WHEN meeting_held THEN '継続検討' ELSE '不成立' END AS meeting_result
      FROM {_fqs}._spine WHERE meeting_scheduled""")
    spark.sql(f"""CREATE OR REPLACE TABLE {_fqs}.contract_history AS
      SELECT concat('CT-', customer_id) AS contract_id, customer_id, campaign_id, contract_date, principal_amount, term_months, interest_rate, 'P001' AS product_id
      FROM {_fqs}._spine WHERE closed""")
    spark.sql(f"""CREATE OR REPLACE TABLE {_fqs}.outbound_call_history AS
      WITH base AS (SELECT customer_id, campaign_id, called_at, connected, n_attempts FROM {_fqs}._spine WHERE called)
      SELECT concat('CL-', b.customer_id, '-', t.attempt) AS call_id, b.customer_id, b.campaign_id,
        timestampadd(MINUTE, (t.attempt-1)*720, b.called_at) AS called_at,
        CASE WHEN b.connected AND t.attempt=b.n_attempts THEN 'connected' WHEN pmod(hash(b.customer_id,t.attempt),3)=0 THEN 'busy' ELSE 'no_answer' END AS call_result,
        (b.connected AND t.attempt=b.n_attempts) AS connected,
        concat('AG', lpad(cast(pmod(hash(b.customer_id),8)+1 AS string),2,'0')) AS agent_id,
        CASE WHEN b.connected AND t.attempt=b.n_attempts THEN 120+pmod(hash(b.customer_id),780) ELSE 0 END AS duration_sec
      FROM base b LATERAL VIEW posexplode(sequence(1, b.n_attempts)) t AS pos, attempt""")

    # 生成専用の内部テーブルは片付ける（参加者一覧に出さない。4履歴は既に materialize 済み）
    # ※ テーブル/列コメントは add_metadata() でまとめて付与する（テーブル・ビュー両方に効かせるため）
    spark.sql(f"DROP TABLE IF EXISTS {_fqs}._spine")

# COMMAND ----------

# --- 講師用の答え合わせビュー vw_sales_steps（4履歴を JOIN。参加者一覧には出さない） ------
# 「見込み客が成約に至るまでの流れ」を顧客×キャンペーン粒度で1行にまとめたもの。
# Genie はこのビューを裏側で使って、参加者の日本語の問いに答える（JOIN の知能をここに隠す）。
def create_sales_steps_view():
    spark.sql(f"""
    CREATE OR REPLACE VIEW {_fqs}.vw_sales_steps AS
    WITH calls AS (
      SELECT customer_id, campaign_id, min(called_at) AS first_called_at, max(cast(connected AS int))=1 AS contacted
      FROM {_fqs}.outbound_call_history GROUP BY customer_id, campaign_id ),
    meet AS (
      SELECT customer_id, campaign_id, max(cast(held AS int))=1 AS meeting_held,
        max(CASE WHEN held THEN meeting_mode END) AS meeting_mode, min(CASE WHEN held THEN meeting_at END) AS meeting_at
      FROM {_fqs}.meeting_history GROUP BY customer_id, campaign_id ),
    ct AS (
      SELECT customer_id, campaign_id, true AS closed, sum(principal_amount) AS contract_amount,
        max(term_months) AS term_months, max(interest_rate) AS interest_rate
      FROM {_fqs}.contract_history GROUP BY customer_id, campaign_id )
    SELECT e.customer_id, e.campaign_id, e.clicked,
      (c.customer_id IS NOT NULL) AS called,
      CASE WHEN e.clicked AND c.first_called_at IS NOT NULL THEN timestampdiff(MINUTE, e.clicked_at, c.first_called_at) END AS time_to_call_minutes,
      coalesce(e.clicked AND c.first_called_at IS NOT NULL AND timestampdiff(MINUTE, e.clicked_at, c.first_called_at) <= 120, false) AS timely_call,
      coalesce(c.contacted,false) AS contacted,
      coalesce(m.meeting_held,false) AS meeting_held, m.meeting_mode,
      coalesce(ct.closed,false) AS closed, ct.contract_amount, ct.term_months, ct.interest_rate,
      d.age, d.age_band, d.gender, d.segment, d.prefecture, d.term_deposit_balance, d.total_deposit,
      d.retirement_plan_flag, d.pension_account_flag
    FROM {_fqs}.campaign_email_results e
    JOIN {_fqs}.dim_customers d ON e.customer_id=d.customer_id
    LEFT JOIN calls c ON e.customer_id=c.customer_id AND e.campaign_id=c.campaign_id
    LEFT JOIN meet m ON e.customer_id=m.customer_id AND e.campaign_id=m.campaign_id
    LEFT JOIN ct   ON e.customer_id=ct.customer_id AND e.campaign_id=ct.campaign_id
    """)

# COMMAND ----------

# --- テーブル/ビューに日本語メタデータ（COMMENT）を付与 ------------------------------
# 参加者は 01 でテーブルを直接探索し、Genie / Genie Code もこのコメントを文脈に使う。
# ★ビューの列コメントは元テーブルから継承されないため、テーブルとビューの両方に付ける。
def add_metadata():
    def _tbl_comment(tbl, text):
        spark.sql(f"COMMENT ON TABLE {_fqs}.{tbl} IS '{text}'")
    def _col_comments(tbl, cols):
        for c, t in cols.items():
            spark.sql(f"COMMENT ON COLUMN {_fqs}.{tbl}.{c} IS '{t}'")

    _tbl_comment("dim_customers", "顧客マスタ。年齢・定期預金額・退職金運用プランや年金受取口座の利用など。1顧客1行。全て架空データ")
    _col_comments("dim_customers", {
        "customer_id":"顧客ID（主キー）", "age":"年齢（数値）", "age_band":"年代区分（20代/30代/…/70代以上）",
        "gender":"性別", "segment":"顧客セグメント（マス/マスリテール/準富裕層/富裕層）", "prefecture":"都道府県",
        "term_deposit_balance":"定期預金額（円）", "total_deposit":"総預金額（円）",
        "retirement_plan_flag":"退職金運用プランの利用有無（true/false）",
        "pension_account_flag":"年金受取口座としてABC銀行を利用しているか（true/false）",
        "do_not_call_flag":"電話連絡お断り（true=架電対象外）", "consent":"連絡同意の有無",
        "registration_date":"口座開設日"})

    _tbl_comment("dim_campaigns", "キャンペーンマスタ。定期預金の販促メール施策")
    _col_comments("dim_campaigns", {
        "campaign_id":"キャンペーンID", "campaign_name":"キャンペーン名", "product_id":"商品ID",
        "product_name":"商品名", "channel":"配信チャネル（email）", "start_date":"開始日"})

    _tbl_comment("campaign_email_results", "販促メールの送信・開封・URLクリック履歴。1顧客1行")
    _col_comments("campaign_email_results", {
        "email_id":"メールID", "campaign_id":"キャンペーンID", "customer_id":"顧客ID",
        "sent_at":"メール送信日時", "opened":"開封したか", "opened_at":"開封日時",
        "clicked":"メール内URLをクリックしたか（関心の合図）", "clicked_at":"クリック日時"})

    _tbl_comment("outbound_call_history", "アウトバウンド架電の履歴。1顧客に複数回の試行がありうる。1架電1行")
    _col_comments("outbound_call_history", {
        "call_id":"架電ID", "customer_id":"顧客ID", "campaign_id":"キャンペーンID", "called_at":"架電日時",
        "call_result":"架電結果（connected=通話成立 / no_answer=不在 / busy=話中）",
        "connected":"この架電で通話がつながったか", "agent_id":"担当オペレーターID", "duration_sec":"通話秒数"})

    _tbl_comment("meeting_history", "商談の履歴。1商談1行")
    _col_comments("meeting_history", {
        "meeting_id":"商談ID", "customer_id":"顧客ID", "campaign_id":"キャンペーンID", "meeting_at":"商談日時",
        "meeting_mode":"商談のやり方（online=オンライン商談 / branch=対面・来店商談）",
        "held":"商談を実際に実施したか", "meeting_result":"商談結果（成約/継続検討/不成立）"})

    _tbl_comment("contract_history", "成約（契約）の履歴。1契約1行")
    _col_comments("contract_history", {
        "contract_id":"契約ID", "customer_id":"顧客ID", "campaign_id":"キャンペーンID（成約の帰属）",
        "contract_date":"契約日", "principal_amount":"契約高（元本・円）", "term_months":"契約期間（月：6/12/36/60）",
        "interest_rate":"適用金利（%）", "product_id":"商品ID"})

    # ビュー本体＋ビューの全列（元テーブルから継承しないので別途付与）
    _tbl_comment("vw_sales_steps", "見込み客が成約に至るまでの各営業ステップを顧客×キャンペーンで1行にまとめた分析ビュー（メール→架電→商談→成約を結合）")
    _col_comments("vw_sales_steps", {
        "customer_id":"顧客ID", "campaign_id":"キャンペーンID",
        "clicked":"メール内URLをクリックしたか", "called":"架電したか",
        "time_to_call_minutes":"クリックから最初の架電までの経過分。小さいほど早い対応",
        "timely_call":"すぐ架電フラグ（クリック後120分以内に架電できたか）",
        "contacted":"架電で通話がつながった経験があるか", "meeting_held":"商談を実施したか",
        "meeting_mode":"商談のやり方（online=オンライン / branch=対面）",
        "closed":"成約したか", "contract_amount":"契約高（元本合計・円）",
        "term_months":"契約期間（月）", "interest_rate":"適用金利（%）",
        "age":"顧客年齢", "age_band":"年代区分", "gender":"性別", "segment":"顧客セグメント",
        "prefecture":"都道府県", "term_deposit_balance":"定期預金額（円）", "total_deposit":"総預金額（円）",
        "retirement_plan_flag":"退職金運用プランの利用有無", "pension_account_flag":"年金受取口座の利用有無"})

# COMMAND ----------

# --- Genie エージェントを API で作成（冪等：同名があれば再利用） ---------------------
def create_genie_agent():
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    title = "ABC銀行 営業ステップ分析"
    T = f"{my_catalog}.{my_schema}.vw_sales_steps"

    # 稼働中/利用可能な warehouse を1つ選ぶ
    whs = list(w.warehouses.list())
    if not whs:
        checkpoint("Genie 作成をスキップ", False, "利用可能な SQL warehouse が見つかりません")
        return None
    warehouse_id = whs[0].id

    # 冪等：同名 space があれば作らずその ID を返す
    try:
        existing = w.api_client.do("GET", "/api/2.0/genie/spaces")
        for s in (existing.get("spaces") or []):
            if s.get("title") == title:
                checkpoint("Genie は作成済み（再利用）", True, f"space_id: {s.get('space_id')}")
                return s.get("space_id")
    except Exception:
        pass

    nid = lambda: uuid.uuid4().hex
    column_configs = sorted([
      {"column_name":"clicked","description":["キャンペーンメールのURLをクリックしたか"],"synonyms":["クリック","URLクリック"]},
      {"column_name":"timely_call","description":["すぐ架電フラグ。クリック後120分以内に架電できたか"],"synonyms":["すぐ架電","クリック後すぐ電話","タイムリーな架電"],"enable_format_assistance":True},
      {"column_name":"time_to_call_minutes","description":["URLクリックから最初の架電までの経過分。小さいほど早い対応"],"synonyms":["架電までの時間","反応の速さ"]},
      {"column_name":"contacted","description":["架電で通話がつながった経験があるか"],"synonyms":["接触","通話成立"]},
      {"column_name":"meeting_held","description":["商談が実際に行われたか"],"synonyms":["商談","面談"]},
      {"column_name":"meeting_mode","description":["商談のやり方。online=オンライン商談 / branch=対面(来店)商談"],"synonyms":["商談形態","オンライン商談","対面商談"],"enable_format_assistance":True,"enable_entity_matching":True},
      {"column_name":"closed","description":["成約(契約成立)したか"],"synonyms":["成約","契約","クロージング"]},
      {"column_name":"contract_amount","description":["契約高(成約時の元本合計)"],"synonyms":["契約高","契約金額"]},
      {"column_name":"age","description":["顧客年齢"],"synonyms":["年齢","歳"]},
      {"column_name":"term_deposit_balance","description":["定期預金額"],"synonyms":["定期預金額","定期残高","高額定期"]},
      {"column_name":"retirement_plan_flag","description":["退職金運用プランの利用有無"],"synonyms":["退職金運用プラン","退職金運用"]},
      {"column_name":"pension_account_flag","description":["年金受取口座としてABC銀行を利用しているか"],"synonyms":["年金受取口座","年金口座"]},
    ], key=lambda x:x["column_name"])

    example_sqls = sorted([
      {"id":nid(),"question":["若い顧客でクリック後すぐ架電した人の商談率と成約率は?"],
       "sql":[f"SELECT (age < 40) AS is_young, timely_call, COUNT(*) AS n, ROUND(100.0*AVG(CASE WHEN meeting_held THEN 1 ELSE 0 END),1) AS meeting_rate_pct, ROUND(100.0*AVG(CASE WHEN closed THEN 1 ELSE 0 END),1) AS close_rate_pct FROM {T} WHERE clicked GROUP BY is_young, timely_call ORDER BY is_young DESC, timely_call DESC"]},
      {"id":nid(),"question":["各営業ステップの人数と脱落率は?"],
       "sql":[f"SELECT COUNT(*) AS targeted, SUM(CASE WHEN clicked THEN 1 ELSE 0 END) AS clicked_n, SUM(CASE WHEN called THEN 1 ELSE 0 END) AS called_n, SUM(CASE WHEN contacted THEN 1 ELSE 0 END) AS contacted_n, SUM(CASE WHEN meeting_held THEN 1 ELSE 0 END) AS meeting_n, SUM(CASE WHEN closed THEN 1 ELSE 0 END) AS closed_n FROM {T}"]},
      {"id":nid(),"question":["65歳以上で定期預金額が多い顧客の退職金運用プランと年金受取口座の利用率は?"],
       "sql":[f"SELECT COUNT(*) AS n, ROUND(100.0*AVG(CASE WHEN retirement_plan_flag THEN 1 ELSE 0 END),1) AS retirement_pct, ROUND(100.0*AVG(CASE WHEN pension_account_flag THEN 1 ELSE 0 END),1) AS pension_pct FROM {T} WHERE age >= 65 AND term_deposit_balance >= (SELECT PERCENTILE(term_deposit_balance,0.5) FROM {T} WHERE age >= 65)"]},
    ], key=lambda x:x["id"])

    text_instructions = [{"id":nid(),"content":[
      "このエージェントはABC銀行の定期預金の販促(メール→架電→商談→成約)を分析する。対象は営業企画・マーケ担当。",
      "営業ステップの順序: 対象 → clicked(クリック) → called(架電) → contacted(接触) → meeting_held(商談) → closed(成約)。",
      "人数・率・脱落率・傾向の分析は必ず vw_sales_steps を使う。脱落率 = 1 −(そのステップの人数 / 前のステップの人数)。",
      "「すぐ架電」は timely_call=true(クリックから120分以内)。「若い顧客」は age<40、「65歳以上」は age>=65。",
      "「オンライン商談」は meeting_mode='online'、「対面商談」は meeting_mode='branch'。",
      "率は必ず%で答え、根拠の件数(n)も添える。対象は連絡拒否・同意なしを除外済み。"]}]

    sample_questions = sorted([
      {"id":nid(),"question":["若い顧客でクリック後すぐに架電した人の商談率と成約率は?"]},
      {"id":nid(),"question":["各営業ステップの人数と脱落率を教えて"]},
      {"id":nid(),"question":["65歳以上で定期預金額が多い顧客の退職金運用プランと年金受取口座の利用率は?"]},
      {"id":nid(),"question":["若い顧客の商談はオンラインと対面のどちらが多い?"]},
    ], key=lambda x:x["id"])

    serialized = json.dumps({"version":2,
      "config":{"sample_questions":sample_questions},
      "data_sources":{"tables":[{"identifier":T,"column_configs":column_configs}]},
      "instructions":{"example_question_sqls":example_sqls,"text_instructions":text_instructions}})

    parent = f"/Workspace/Users/{_user_email}/genie_spaces"
    try:
        w.workspace.mkdirs(parent)
    except Exception:
        pass

    resp = w.api_client.do("POST", "/api/2.0/genie/spaces", body={
        "warehouse_id": warehouse_id, "title": title,
        "description": "ABC銀行の定期預金の販促(メール→架電→商談→成約)を日本語で分析するエージェント",
        "parent_path": parent, "serialized_space": serialized})
    sid = resp.get("space_id")
    checkpoint("Genie エージェントを作成しました", bool(sid),
               f"space_id: {sid}｜左メニュー『Genie Agents』から「{title}」を開けます")
    return sid

# COMMAND ----------

# --- セットアップ情報バナー ------------------------------------------------------
displayHTML(f"""
<div style="border-left:4px solid #1976d2;background:#e3f2fd;padding:14px 18px;
     border-radius:4px;margin:12px 0;font-family:sans-serif;">
  <strong style="color:#0d47a1;font-size:1.1em;">✅ 共通セットアップ 読み込み完了</strong>
  <table style="margin-top:10px;color:#333;border-collapse:collapse;">
    <tr><td style="padding:2px 16px 2px 0;"><b>ユーザー</b></td><td>{_user_email}</td></tr>
    <tr><td style="padding:2px 16px 2px 0;"><b>Catalog</b></td><td><code>{my_catalog}</code></td></tr>
    <tr><td style="padding:2px 16px 2px 0;"><b>Schema</b></td><td><code>{my_schema}</code></td></tr>
  </table>
</div>
""")
