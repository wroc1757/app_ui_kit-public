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
