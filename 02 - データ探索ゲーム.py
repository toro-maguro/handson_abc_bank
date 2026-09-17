# Databricks notebook source
# MAGIC %md
# MAGIC # 02 データ探索ゲーム 🔍
# MAGIC ## 〜 Genie に日本語で問いかけて、営業の「勝ち筋」を見つけよう 〜
# MAGIC
# MAGIC あなたは **ABC銀行のマーケティング担当**です。
# MAGIC 定期預金キャンペーンのメールを送り、反応した顧客に架電し、商談して、成約を狙っています。
# MAGIC でも、成約はなかなか伸びません。**どこかに「勝ち筋」と「取りこぼし」がある**はずです。
# MAGIC
# MAGIC このモジュールでは、SQL を書かずに **Genie に日本語で問いかけるだけ**で、
# MAGIC バラバラの4つの履歴（メール・架電・商談・成約）の裏側の結合を Genie に任せ、
# MAGIC 自分で仮説を立てて確かめ、**勝ち筋を発見**します。
# MAGIC
# MAGIC ### あなたのミッション（この2つを Genie との対話で解き明かす）
# MAGIC <div style="border-left:4px solid #6a1b9a;background:#f3e5f5;padding:14px 18px;border-radius:4px;margin:12px 0;color:#333;">
# MAGIC <b>謎その1：どんな顧客に・どう営業すると、成約が伸びるのか？</b><br>
# MAGIC （年代？ メールへの反応？ 架電のタイミング？ 商談のやり方？——組み合わせて考えてみて）
# MAGIC <br><br>
# MAGIC <b>謎その2：営業のどのステップで、いちばん顧客を取りこぼしているのか？</b><br>
# MAGIC （メール→クリック→架電→接触→商談→成約 の、どこの脱落が大きい？）
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC <div style="border-left:4px solid #ff9800;background:#fff3e0;padding:14px 18px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#e65100;font-size:1.1em;">結果は少し変わることがあります</strong>
# MAGIC   <div style="color:#333;margin-top:6px;">
# MAGIC   Genie はライブの AI です。同じ質問でも表現や言い回しで結果が変わることがあります。
# MAGIC   うまく答えてくれないときは、少し言い方を変えてもう一度聞いてみてください（コツは下にあります）。
# MAGIC   </div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ1 — Genie を開く
# MAGIC 1. 左側のメニューから **「Genie Agents」** をクリック
# MAGIC 2. 一覧から **「ABC銀行 営業ステップ分析」** を開く
# MAGIC （00 のセットアップで、あなた専用に自動作成されています）
# MAGIC
# MAGIC 開くと、下に**質問の例**がいくつか表示されます。まずはそれを押してみてもいいですし、
# MAGIC 自分の言葉で入力欄に打ち込んでもかまいません。
# MAGIC
# MAGIC <div style="border-left:4px solid #43a047;background:#e8f5e9;padding:12px 16px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#2e7d32;">✔ 期待される状態</strong>
# MAGIC   <div style="color:#333;margin-top:4px;">「ABC銀行 営業ステップ分析」というチャット画面が開き、日本語で質問を入力できる。</div>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ2 — 質問のはしご（広い問い → だんだん絞る）
# MAGIC いきなり核心を聞くより、**広い問いから始めて、少しずつ絞り込む**と発見しやすいです。
# MAGIC 下は一例です。**そのままコピペしてもOK**、自分なりに変えてもOK。
# MAGIC
# MAGIC **▼ まずは全体像**
# MAGIC - 「各営業ステップの人数と脱落率を教えて」
# MAGIC - 「全体の成約率は？」
# MAGIC
# MAGIC **▼ 年代で切ってみる**
# MAGIC - 「年代別の成約率を教えて」
# MAGIC - 「若い顧客と高齢の顧客で、成約率に違いはある？」
# MAGIC
# MAGIC **▼ 反応の速さに注目してみる（ここが勝ち筋のヒント）**
# MAGIC - 「メールをクリックした後、すぐに架電できた顧客とそうでない顧客で、商談率・成約率はどう違う？」
# MAGIC - 「若い顧客でクリック後すぐに架電した人の成約率は？」
# MAGIC
# MAGIC **▼ 商談のやり方を見てみる**
# MAGIC - 「若い顧客の商談は、オンラインと対面のどちらが多い？」
# MAGIC
# MAGIC **▼ 高齢の優良顧客を掘る（謎のもう一つの入口）**
# MAGIC - 「65歳以上で定期預金額が多い顧客は、退職金運用プランや年金受取口座をどのくらい使っている？」
# MAGIC
# MAGIC <div style="border-left:4px solid #1976d2;background:#e3f2fd;padding:12px 16px;border-radius:4px;margin:12px 0;color:#333;">
# MAGIC <b>うまく答えてくれないときのコツ</b>
# MAGIC <ul style="margin:6px 0 0 0;">
# MAGIC   <li>主語をはっきり：「若い顧客（40歳未満）で…」のように具体的に</li>
# MAGIC   <li>1問1答に分ける：一度に多くを聞かず、少しずつ絞る</li>
# MAGIC   <li>Genie が出した <b>SQL や表</b>を開いて、何を計算したか確認する（"Show code"）</li>
# MAGIC </ul>
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ3 — 気づきをメモしよう
# MAGIC 対話しながら、下の問いに自分の言葉で答えられるか確かめてください（03 で答え合わせします）。
# MAGIC
# MAGIC - 成約が**いちばん伸びる顧客層・営業の仕方**は？（複数の条件の**組み合わせ**かも）
# MAGIC - 商談は**オンライン**と**対面**、どちらが多い？ それは特定の年代に偏っている？
# MAGIC - **脱落がいちばん大きいステップ**はどこ？ そこを改善すると効果が大きそう？
# MAGIC - 高齢の優良顧客には、どんな**別の切り口**（商品・口座の使われ方）が見える？

# COMMAND ----------

# MAGIC %md
# MAGIC ## ステップ4 🎉 — 気づきを「ダッシュボード」にする（今日のハイライト）
# MAGIC 見つけた気づきは、Genie の中から**そのままダッシュボードに載せられます**。
# MAGIC
# MAGIC 1. グラフになりそうな質問をする（例：**「各営業ステップの人数と脱落率を教えて」**）
# MAGIC 2. Genie の回答に**グラフ**が表示されたら、その右上あたりの **「Add to dashboard（ダッシュボードに追加）」** を押す
# MAGIC 3. **「Create new dashboard（新規作成）」** を選び、名前（例：`ABC銀行 営業ステップ`）を入れて **Create**
# MAGIC 4. 続けて別の質問（例：**「年代別の成約率」**）でも同じように **Add to dashboard** → 今度は **「Add to existing（既存に追加）」** で同じダッシュボードにまとめる
# MAGIC
# MAGIC こうして、**SQL を1行も書かずに**、対話で見つけた気づきが1枚のダッシュボードに集まります。
# MAGIC
# MAGIC <div style="border-left:4px solid #43a047;background:#e8f5e9;padding:12px 16px;border-radius:4px;margin:12px 0;">
# MAGIC   <strong style="color:#2e7d32;">✔ 期待される状態</strong>
# MAGIC   <div style="color:#333;margin-top:4px;">
# MAGIC   左メニュー「Dashboards」に、あなたが作ったダッシュボードが増えていて、
# MAGIC   Genie で見たグラフが載っている。（グラフが黒い枠に見えるときは warehouse の起動待ち。少し待つと描画されます）
# MAGIC   </div>
# MAGIC </div>
# MAGIC
# MAGIC <div style="border-left:4px solid #1976d2;background:#e3f2fd;padding:12px 16px;border-radius:4px;margin:12px 0;color:#333;">
# MAGIC <b>おまけ：Genie Code</b><br>
# MAGIC 画面上部の「Genie Code」や、回答下の「Diagnose with Genie Code」からは、
# MAGIC 自然言語でさらに踏み込んだ分析・可視化を作ることもできます。時間があれば触ってみてください。
# MAGIC </div>

# COMMAND ----------

# MAGIC %md
# MAGIC ## まとめ
# MAGIC SQL を書かずに、日本語で問いかけるだけで、バラバラの履歴の裏側の結合を Genie に任せて
# MAGIC 営業の勝ち筋を探し、気づきをダッシュボードにまとめました。
# MAGIC
# MAGIC **次のモジュール 03** では、いよいよ**答え合わせ**です。
# MAGIC あなたの発見は当たっていたでしょうか？ 講師といっしょに「種明かし」をして、
# MAGIC Genie が裏側でどんな結合をしていたのか、そしてきれいな「正解ダッシュボード」を確認します。
