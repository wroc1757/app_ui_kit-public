# app_ui_kit

Flutter アプリ共通 UI コンポーネントパッケージ。

## 提供コンポーネント

- エラー処理（AppException / ErrorDialog / ErrorSnackbar）
- ローディング（LoadingOverlay / LoadingState）

## 使い方
```yaml
dependencies:
  app_ui_kit:
    git:
      url: https://github.com/wroc1757/app_ui_kit-public.git
      ref: v1.0.0
```
```dart
import "package:app_ui_kit/app_ui_kit.dart";
```

## ビジュアルリグレッションテスト

`maestro_template/` に Maestro + vrc.py によるスクショ比較テストのテンプレートがあります。
新しいアプリに導入する際は `maestro_template/` をプロジェクトの `.maestro/` にコピーしてください。

詳細: [maestro_template/README.md](maestro_template/README.md)

## 新しいコンポーネントを追加するとき

1. `lib/src/` 以下に実装
2. `lib/app_ui_kit.dart` にexportを追加
3. `test/` にテストを追加
4. `flutter analyze && flutter test` が通ることを確認
5. バージョンタグを切る（`git tag v1.x.x && git push origin v1.x.x`）
