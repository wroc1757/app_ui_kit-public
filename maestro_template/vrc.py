#!/usr/bin/env python3
"""
Visual Regression Checker
使い方:
  pip install pillow anthropic
  python vrc.py <baseline_dir> <current_dir> [--ai] [--threshold 10]
"""

import argparse
import base64
import json
import os
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageFilter
    import numpy as np
except ImportError:
    print("必要なライブラリをインストールしてください:")
    print("  pip install pillow numpy")
    sys.exit(1)

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


# ── ピクセル差分計算 ──────────────────────────────────────────────────
def compute_diff(path_a: Path, path_b: Path, threshold: int = 10):
    img_a = Image.open(path_a).convert("RGBA")
    img_b = Image.open(path_b).convert("RGBA")

    # サイズを揃える
    w = max(img_a.width, img_b.width)
    h = max(img_a.height, img_b.height)
    if img_a.size != (w, h):
        img_a = img_a.resize((w, h), Image.LANCZOS)
    if img_b.size != (w, h):
        img_b = img_b.resize((w, h), Image.LANCZOS)

    arr_a = np.array(img_a, dtype=np.int16)
    arr_b = np.array(img_b, dtype=np.int16)

    diff = np.abs(arr_a[:, :, :3] - arr_b[:, :, :3]).mean(axis=2)
    changed_mask = diff > threshold
    changed_px = int(changed_mask.sum())
    total_px = w * h
    pct = round(changed_px / total_px * 100, 2)

    # 差分ハイライト画像を生成
    highlight = np.zeros((h, w, 4), dtype=np.uint8)
    # 変化なし: 元画像を薄く
    highlight[~changed_mask, :3] = arr_a[~changed_mask, :3] // 3
    highlight[~changed_mask, 3] = 100
    # 変化あり: 赤くハイライト
    intensity = np.clip(diff[changed_mask] * 3, 0, 255).astype(np.uint8)
    highlight[changed_mask, 0] = intensity
    highlight[changed_mask, 1] = 30
    highlight[changed_mask, 2] = 30
    highlight[changed_mask, 3] = 220

    diff_img = Image.fromarray(highlight, "RGBA")
    return {
        "changed_px": changed_px,
        "total_px": total_px,
        "pct": pct,
        "score": "完全一致" if pct == 0 else "軽微" if pct < 1 else "中程度" if pct < 5 else "大きな変化",
        "diff_img": diff_img,
        "size": (w, h),
    }


# ── AI差分分析 ────────────────────────────────────────────────────────
def analyze_with_ai(path_a: Path, path_b: Path, stats: dict, api_key: str) -> dict:
    try:
        import anthropic
    except ImportError:
        print("  [AI] anthropic をインストールしてください: pip install anthropic")
        return {"summary": "AI分析スキップ（anthropicライブラリ未インストール）", "findings": []}

    client = anthropic.Anthropic(api_key=api_key)

    def to_b64(path):
        with open(path, "rb") as f:
            return base64.standard_b64encode(f.read()).decode()

    ext_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    mt_a = ext_map.get(path_a.suffix.lower(), "image/png")
    mt_b = ext_map.get(path_b.suffix.lower(), "image/png")

    prompt = f"""あなたはUIビジュアルリグレッションテストの専門家です。
2枚のアプリスクリーンショットを比較しています。
- 画像1: ベースライン（以前の正常な状態）
- 画像2: 現在の状態

ピクセル差分の統計:
- 変化したピクセル数: {stats['changed_px']:,} px
- 変化率: {stats['pct']}%

以下のカテゴリで分析し、JSONのみを返してください（マークダウン不要）:
{{
  "findings": [
    {{"type": "layout|text|color|element|ok", "description": "日本語で具体的な説明（1〜2文）"}}
  ],
  "summary": "全体的な変化の要約（1文）"
}}

typeの意味: layout=レイアウトのずれ, text=テキスト変化, color=色・スタイル変化, element=要素の消失・追加, ok=変化なし"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": mt_a, "data": to_b64(path_a)}},
                {"type": "image", "source": {"type": "base64", "media_type": mt_b, "data": to_b64(path_b)}},
                {"type": "text", "text": prompt},
            ]
        }]
    )

    raw = response.content[0].text.strip().replace("```json", "").replace("```", "")
    try:
        return json.loads(raw)
    except Exception:
        return {"summary": raw[:200], "findings": []}


# ── HTMLレポート生成 ──────────────────────────────────────────────────
def img_to_b64(img: Image.Image) -> str:
    import io
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.standard_b64encode(buf.getvalue()).decode()

def path_to_b64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode()

def ext_to_mime(path: Path) -> str:
    return {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(path.suffix.lstrip(".").lower(), "image/png")


BADGE_CSS = {
    "layout": ("レイアウト", "#faeeda", "#854f0b"),
    "text":   ("テキスト",   "#e6f1fb", "#185fa5"),
    "color":  ("色・スタイル","#eeedfe", "#534ab7"),
    "element":("要素",       "#fcebeb", "#a32d2d"),
    "ok":     ("✓ 正常",     "#eaf3de", "#3b6d11"),
}


def build_report(results: list, output_path: Path, use_ai: bool):
    total = len(results)
    changed = sum(1 for r in results if r["stats"]["pct"] > 0)
    identical = total - changed

    cards_html = ""
    for r in results:
        stats = r["stats"]
        ai = r.get("ai", {})

        # スコアバッジ色
        score_colors = {
            "完全一致": ("#eaf3de", "#3b6d11"),
            "軽微":     ("#faeeda", "#854f0b"),
            "中程度":   ("#fcebeb", "#a32d2d"),
            "大きな変化":("#fcebeb", "#a32d2d"),
        }
        sb, sc = score_colors.get(stats["score"], ("#f1efe8", "#5f5e5a"))

        findings_html = ""
        if ai.get("summary"):
            findings_html += f'<p style="font-size:13px;color:#6b6b66;margin-bottom:10px;padding-bottom:10px;border-bottom:0.5px solid #e0e0da;">{ai["summary"]}</p>'
        for f in ai.get("findings", []):
            badge_label, bg, tc = BADGE_CSS.get(f["type"], ("その他", "#f1efe8", "#5f5e5a"))
            findings_html += f'''<div style="display:flex;gap:10px;padding:8px 0;border-bottom:0.5px solid #f0f0ea;align-items:flex-start;">
  <span style="font-size:11px;font-weight:500;padding:3px 9px;border-radius:5px;white-space:nowrap;background:{bg};color:{tc};flex-shrink:0;">{badge_label}</span>
  <span style="font-size:13px;line-height:1.6;">{f["description"]}</span>
</div>'''

        ai_section = ""
        if use_ai and findings_html:
            ai_section = f'''<div style="margin-top:14px;">
  <div style="font-size:11px;font-weight:500;color:#9e9e99;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:10px;">AI 差分レポート</div>
  {findings_html}
</div>'''
        elif use_ai and ai.get("summary"):
            ai_section = f'<p style="margin-top:12px;font-size:13px;color:#6b6b66;">{ai["summary"]}</p>'

        cards_html += f'''
<div style="background:#fff;border:0.5px solid #e0e0da;border-radius:14px;padding:1.25rem;margin-bottom:16px;">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
    <span style="font-size:14px;font-weight:500;font-family:monospace;">{r["name"]}</span>
    <span style="font-size:11px;font-weight:500;padding:3px 10px;border-radius:5px;background:{sb};color:{sc};">{stats["score"]} {stats["pct"]}%</span>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:14px;">
    <div style="text-align:center;">
      <div style="font-size:11px;color:#9e9e99;margin-bottom:4px;">ベースライン</div>
      <img src="data:{ext_to_mime(r['path_a'])};base64,{path_to_b64(r['path_a'])}" style="width:100%;border-radius:8px;border:0.5px solid #e0e0da;">
    </div>
    <div style="text-align:center;">
      <div style="font-size:11px;color:#9e9e99;margin-bottom:4px;">現在</div>
      <img src="data:{ext_to_mime(r['path_b'])};base64,{path_to_b64(r['path_b'])}" style="width:100%;border-radius:8px;border:0.5px solid #e0e0da;">
    </div>
    <div style="text-align:center;">
      <div style="font-size:11px;color:#9e9e99;margin-bottom:4px;">差分ハイライト</div>
      <img src="data:image/png;base64,{img_to_b64(r['stats']['diff_img'])}" style="width:100%;border-radius:8px;border:0.5px solid #e0e0da;">
    </div>
  </div>
  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:4px;">
    <div style="background:#f5f5f3;border-radius:8px;padding:10px 12px;"><div style="font-size:11px;color:#9e9e99;">変化ピクセル</div><div style="font-size:18px;font-weight:500;">{stats["changed_px"]:,}</div></div>
    <div style="background:#f5f5f3;border-radius:8px;padding:10px 12px;"><div style="font-size:11px;color:#9e9e99;">変化率</div><div style="font-size:18px;font-weight:500;">{stats["pct"]} <span style="font-size:12px;color:#9e9e99;">%</span></div></div>
    <div style="background:#f5f5f3;border-radius:8px;padding:10px 12px;"><div style="font-size:11px;color:#9e9e99;">サイズ</div><div style="font-size:18px;font-weight:500;">{stats["size"][0]}<span style="font-size:12px;color:#9e9e99;">×{stats["size"][1]}</span></div></div>
  </div>
  {ai_section}
</div>'''

    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>VRC Report — {datetime.now().strftime('%Y-%m-%d %H:%M')}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{font-family:-apple-system,BlinkMacSystemFont,'Helvetica Neue',sans-serif;background:#efefec;color:#1a1a18;padding:2rem 1rem;}}
  .container{{max-width:900px;margin:0 auto;}}
  h1{{font-size:22px;font-weight:500;margin-bottom:6px;}}
  .sub{{font-size:13px;color:#6b6b66;margin-bottom:1.5rem;}}
  .stats-row{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:1.5rem;}}
  .stat-card{{background:#fff;border:0.5px solid #e0e0da;border-radius:10px;padding:14px;}}
  .stat-label{{font-size:11px;color:#9e9e99;margin-bottom:6px;}}
  .stat-value{{font-size:24px;font-weight:500;}}
  .filter-row{{display:flex;gap:8px;margin-bottom:1rem;flex-wrap:wrap;}}
  .filter-btn{{padding:6px 14px;font-size:13px;border:0.5px solid #d3d1c7;border-radius:7px;background:#fff;cursor:pointer;transition:background 0.15s;}}
  .filter-btn:hover{{background:#f5f5f3;}}
  .filter-btn.active{{background:#1a1a18;color:#fff;border-color:#1a1a18;}}
  @media(max-width:600px){{.stats-row{{grid-template-columns:1fr 1fr;}}}}
</style>
</head>
<body>
<div class="container">
  <h1>Visual Regression Report</h1>
  <p class="sub">{datetime.now().strftime('%Y年%m月%d日 %H:%M')} — {total} ファイル比較</p>

  <div class="stats-row">
    <div class="stat-card"><div class="stat-label">比較ファイル数</div><div class="stat-value">{total}</div></div>
    <div class="stat-card"><div class="stat-label">差分あり</div><div class="stat-value" style="color:#a32d2d;">{changed}</div></div>
    <div class="stat-card"><div class="stat-label">完全一致</div><div class="stat-value" style="color:#3b6d11;">{identical}</div></div>
  </div>

  <div class="filter-row">
    <button class="filter-btn active" onclick="filterCards('all', this)">すべて</button>
    <button class="filter-btn" onclick="filterCards('changed', this)">差分あり</button>
    <button class="filter-btn" onclick="filterCards('ok', this)">完全一致</button>
  </div>

  <div id="cards">
    {cards_html}
  </div>
  <p style="text-align:center;font-size:12px;color:#9e9e99;margin-top:2rem;">Visual Regression Checker — Powered by Claude</p>
</div>
<script>
const cards = document.querySelectorAll('#cards > div');
function filterCards(mode, btn) {{
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  cards.forEach(card => {{
    const badge = card.querySelector('span[style*="font-size:11px"]');
    const isOk = badge && badge.textContent.includes('完全一致');
    if (mode === 'all') card.style.display = '';
    else if (mode === 'ok') card.style.display = isOk ? '' : 'none';
    else card.style.display = !isOk ? '' : 'none';
  }});
}}
</script>
</body>
</html>'''

    output_path.write_text(html, encoding="utf-8")


# ── メイン ────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Visual Regression Checker")
    parser.add_argument("baseline", help="ベースラインのディレクトリ")
    parser.add_argument("current",  help="現在のディレクトリ")
    parser.add_argument("--ai",     action="store_true", help="AIによる差分コメントを有効化")
    parser.add_argument("--threshold", type=int, default=10, help="ピクセル変化検出しきい値 (default: 10)")
    parser.add_argument("--output", default="vrc_report.html", help="レポートの出力先 (default: vrc_report.html)")
    parser.add_argument("--no-open", action="store_true", help="ブラウザを自動で開かない")
    args = parser.parse_args()

    baseline_dir = Path(args.baseline)
    current_dir  = Path(args.current)

    if not baseline_dir.is_dir():
        print(f"エラー: {baseline_dir} はディレクトリではありません")
        sys.exit(1)
    if not current_dir.is_dir():
        print(f"エラー: {current_dir} はディレクトリではありません")
        sys.exit(1)

    # ファイル名でマッチング
    baseline_files = {f.name: f for f in baseline_dir.iterdir() if f.suffix.lower() in IMAGE_EXTS}
    current_files  = {f.name: f for f in current_dir.iterdir()  if f.suffix.lower() in IMAGE_EXTS}
    common = sorted(set(baseline_files) & set(current_files))

    only_baseline = sorted(set(baseline_files) - set(current_files))
    only_current  = sorted(set(current_files)  - set(baseline_files))

    if not common:
        print("共通のファイルが見つかりませんでした。ファイル名を確認してください。")
        sys.exit(1)

    print(f"\n=== Visual Regression Checker ===")
    print(f"ベースライン: {baseline_dir}")
    print(f"現在        : {current_dir}")
    print(f"比較対象    : {len(common)} ファイル")
    if only_baseline: print(f"ベースラインのみ: {', '.join(only_baseline)}")
    if only_current:  print(f"現在のみ       : {', '.join(only_current)}")
    print()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if args.ai and not api_key:
        print("警告: ANTHROPIC_API_KEY が未設定です。--ai オプションは無視されます。")
        print("  export ANTHROPIC_API_KEY=sk-ant-...")
        args.ai = False

    results = []
    for name in common:
        path_a = baseline_files[name]
        path_b = current_files[name]
        print(f"比較中: {name} ... ", end="", flush=True)

        stats = compute_diff(path_a, path_b, threshold=args.threshold)
        print(f"{stats['score']} ({stats['pct']}%)", end="")

        ai_result = {}
        if args.ai and stats["pct"] > 0:
            print(" → AI分析中...", end="", flush=True)
            ai_result = analyze_with_ai(path_a, path_b, stats, api_key)

        print()
        results.append({"name": name, "path_a": path_a, "path_b": path_b, "stats": stats, "ai": ai_result})

    output_path = Path(args.output)
    print(f"\nレポートを生成中: {output_path}")
    build_report(results, output_path, use_ai=args.ai)
    print(f"完了: {output_path.resolve()}")

    if not args.no_open:
        webbrowser.open(output_path.resolve().as_uri())


if __name__ == "__main__":
    main()
