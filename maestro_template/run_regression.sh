#!/bin/bash
# ビジュアルリグレッションテスト (Maestro + vrc.py)
#
# 使い方:
#   ./run_regression.sh baseline   ← 正常時のスクショを保存
#   ./run_regression.sh compare    ← 今回のスクショと比較 → HTMLレポート
#   ./run_regression.sh compare --ai  ← AI差分コメント付き
#
# セットアップ:
#   1. Maestro: curl -Ls "https://get.maestro.mobile.dev" | bash
#   2. Python:  pip install pillow numpy
#   3. (AI用):  pip install anthropic && export ANTHROPIC_API_KEY=sk-ant-...

set -e
export PATH="$PATH:$HOME/.maestro/bin:/usr/bin"

DIR="$(cd "$(dirname "$0")" && pwd)"
MODE="${1:-compare}"
AI_FLAG="${2:-}"
BASELINE_DIR="$DIR/screenshots/baseline"
CURRENT_DIR="$DIR/screenshots/current"

screenshot() {
  local name="$1"
  local target_dir="$2"
  sleep 1
  xcrun simctl io booted screenshot "$target_dir/${name}.png" 2>/dev/null
  echo "  📸 $name"
}

run_flows() {
  local target_dir="$1"
  rm -rf "$target_dir"
  mkdir -p "$target_dir"

  # === ここにフローを追加 ===
  # 例:
  # echo ""
  # echo "=== Flow 1: ログイン ==="
  # maestro test "$DIR/01_login.yaml" 2>/dev/null
  # screenshot "01_login" "$target_dir"
  #
  # echo ""
  # echo "=== Flow 2: メイン画面 ==="
  # maestro test "$DIR/02_main.yaml" 2>/dev/null
  # screenshot "02_main" "$target_dir"

  echo ""
  echo "⚠️  フローが未定義です。YAMLフローを作成し、このスクリプトに追加してください。"
  echo "   参考: maestro_template/README.md"

  echo ""
  echo "✅ スクショ保存完了: $target_dir"
  ls "$target_dir"/*.png 2>/dev/null | while read f; do echo "  $(basename "$f")"; done
}

case "$MODE" in
  baseline)
    echo "📷 ベースラインスクショを作成します..."
    run_flows "$BASELINE_DIR"
    echo ""
    echo "🎯 ベースライン作成完了！"
    echo "   今後 './run_regression.sh compare' で比較できます"
    ;;
  compare)
    if [ ! -d "$BASELINE_DIR" ]; then
      echo "❌ ベースラインが未作成です"
      echo "   先に './run_regression.sh baseline' を実行してください"
      exit 1
    fi

    echo "🔍 リグレッション比較テストを実行します..."
    run_flows "$CURRENT_DIR"

    echo ""
    echo "=== vrc.py で比較 ==="
    VRC_ARGS="$BASELINE_DIR $CURRENT_DIR --output $DIR/vrc_report.html"
    if [ "$AI_FLAG" = "--ai" ]; then
      VRC_ARGS="$VRC_ARGS --ai"
    fi
    python3 "$DIR/vrc.py" $VRC_ARGS
    ;;
  *)
    echo "使い方:"
    echo "  $0 baseline       ベースラインスクショを作成"
    echo "  $0 compare        比較テスト → HTMLレポート"
    echo "  $0 compare --ai   AI差分コメント付き比較"
    exit 1
    ;;
esac
