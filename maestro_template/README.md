# Maestro ビジュアルリグレッションテスト テンプレート

Maestro + vrc.py によるスクショ比較でUIリグレッションを検出するテンプレートです。

## セットアップ

### 1. このディレクトリをプロジェクトにコピー

```bash
cp -r maestro_template/ /path/to/your-app/.maestro/
chmod +x /path/to/your-app/.maestro/run_regression.sh
```

### 2. ツールをインストール

```bash
# Maestro
curl -Ls "https://get.maestro.mobile.dev" | bash

# vrc.py の依存
pip install pillow numpy

# (オプション) AI差分コメント
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...
```

### 3. フローを作成

`01_sample_login.yaml` を参考に、アプリのフローを作成：

```yaml
appId: com.example.yourApp
---
- launchApp:
    clearState: true
- tapOn:
    text: "許可"
    optional: true
- tapOn: "ログイン"
- extendedWaitUntil:
    visible: "ホーム"
    timeout: 10000
```

### 4. run_regression.sh にフローを登録

`run_flows()` 関数内にフローとスクショを追加：

```bash
echo "=== Flow 1: ログイン ==="
maestro test "$DIR/01_login.yaml" 2>/dev/null
screenshot "01_login" "$target_dir"
```

## 使い方

```bash
cd /path/to/your-app

# ベースライン作成（UIが正常な状態で1回）
./.maestro/run_regression.sh baseline

# コード変更後に比較
./.maestro/run_regression.sh compare

# AI差分コメント付き
./.maestro/run_regression.sh compare --ai
```

## 出力

```
.maestro/
├── screenshots/
│   ├── baseline/     ← 正常時のスクショ
│   └── current/      ← 今回のテスト結果
└── vrc_report.html   ← HTMLレポート（ブラウザで開く）
```

### レポートの見方

| スコア | 変化率 | 意味 |
|--------|--------|------|
| 完全一致 | 0% | 差分なし |
| 軽微 | < 1% | 時刻表示など（通常は問題なし） |
| 中程度 | 1〜5% | テキストやレイアウトの軽い変更 |
| 大きな変化 | > 5% | UIの大幅な変更（要確認） |

## Tips

- **時刻差分は正常**: ベースラインと現在で時刻が異なるため、0.1%程度の差分は想定内
- **ベースライン更新**: UIを意図的に変更した後は `baseline` を再実行
- **フロー追加**: 新しい画面を追加したら YAML + screenshot を追加
- **CLAUDE.md に記載**: 「リグレッションテスト実行して」で Claude Code が実行できるよう CLAUDE.md に記載推奨

## Flutter アプリでの注意点

Flutter は独自のレンダリングエンジンを使うため、Maestro との組み合わせでいくつかハマりポイントがあります。

### 1. テキストマッチは正規表現を使う

`assertVisible: "テキスト"` は**完全一致**です。Flutter の `Text.rich` や GestureDetector でラップされたウィジェットは、アクセシビリティツリー上でテキストが結合されます（絵文字接頭辞、改行を含む）。

```yaml
# ❌ 動かない（完全一致のため部分的なテキストにマッチしない）
- assertVisible: "ログイン"

# ✅ 正規表現で部分マッチ
- assertVisible:
    text: ".*ログイン.*"

# ✅ tapOn も同様
- tapOn:
    text: ".*送信.*"
```

### 2. キーボードの閉じ方

Flutter アプリでは `hideKeyboard` が動作しません。`inputText` 後にキーボードを閉じるには `scroll` が有効です。

```yaml
- tapOn: "メールアドレス"
- inputText: "test@example.com"

# ❌ Flutter では動かない
# - hideKeyboard

# ✅ スクロールでキーボードが閉じる
- scroll
```

### 3. スクロールが必要な画面

長い画面では要素がビューポート外にある場合があります。`assertVisible` や `tapOn` の前に `scroll` を入れてください。

```yaml
# 画面上部の要素を確認
- assertVisible:
    text: ".*タイトル.*"

# スクロールして下部の要素を表示
- scroll

# 画面下部の要素を確認
- assertVisible:
    text: ".*送信ボタン.*"
```

### 4. アクセシビリティツリーのデバッグ

要素が見つからないときは `maestro hierarchy` でMaestroから見えるツリーをダンプできます。

```bash
# アプリを起動した状態で実行
maestro hierarchy

# テキスト要素だけ抽出（Python でパース）
maestro hierarchy 2>&1 | python3 -c "
import sys, json
data = sys.stdin.read()
lines = data.split('\n')
idx = next(i for i, l in enumerate(lines) if l.strip().startswith('{') or 'None:' in l)
json_str = '\n'.join(lines[idx:])
if json_str.startswith('None:'): json_str = json_str[5:].strip()
tree = json.loads(json_str)
def show(node, depth=0):
    for key in ['accessibilityText', 'text', 'hintText']:
        v = node.get('attributes', {}).get(key, '')
        if v: print(f\"{'  '*depth}{key}={v}\")
    for c in node.get('children', []): show(c, depth+1)
show(tree)
"
```

よくあるパターン:
- `Text.rich` → TextSpan のテキストが結合される（例: `"✏️ お名前を入力"`）
- `GestureDetector` 内の複数 Text → 改行区切りで1つのノードになる（例: `"😤\nノーマル\n基本モード"`）
- `TextField` の hintText → そのまま `accessibilityText` に表示される
