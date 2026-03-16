## ベーステンプレートの前提（Flutter）

このプロジェクトは `app_ui_kit` パッケージを共通UIコンポーネントとして使用しています。
新しいコードを生成する際は必ずこの構成に沿ってください。

### 技術スタック
- Flutter 3.x / Dart 3.x
- flutter_riverpod: ^3.3.1（状態管理）
- app_ui_kit（共通UIコンポーネント・Gitサブモジュール）

### app_ui_kit の使い方
```yaml
# pubspec.yaml に追加
dependencies:
  app_ui_kit:
    git:
      url: https://github.com/wroc1757/app_ui_kit.git
      ref: v1.0.0
```

### 提供しているコンポーネント

#### エラー処理
- `AppException` — API例外の共通モデル
  - `AppException.fromStatusCode(code)` でHTTPステータスコードから生成
  - type: `unauthorized` / `validation` / `server` / `network` / `unknown`
- `ErrorDialog.show(context, exception)` — モーダルダイアログ表示
- `ErrorSnackbar.show(context, exception)` — Snackbar表示

#### ローディング
- `LoadingOverlay(isLoading: bool, child: Widget)` — 全画面オーバーレイ
- `LoadingState<T>` — 非同期処理の状態を表すsealed class
  - `LoadingIdle` / `LoadingInProgress` / `LoadingSuccess(data)` / `LoadingFailure(exception)`

### Riverpod + LoadingState の使い方
```dart
// Notifier
class HogeNotifier extends AutoDisposeNotifier<LoadingState<HogeModel>> {
  @override
  LoadingState<HogeModel> build() => const LoadingIdle();

  Future<void> fetch() async {
    state = const LoadingInProgress();
    try {
      final data = await ref.read(hogeRepositoryProvider).fetch();
      state = LoadingSuccess(data);
    } on AppException catch (e) {
      state = LoadingFailure(e);
    }
  }
}

// View
switch (state) {
  LoadingIdle() => const SizedBox.shrink(),
  LoadingInProgress() => const CircularProgressIndicator(),
  LoadingSuccess(:final data) => HogeView(data: data),
  LoadingFailure(:final exception) => ErrorSnackbar.show(context, exception),
}
```

### やってはいけないこと
- `setState` で非同期処理の状態管理をしない（Riverpod + LoadingState を使う）
- エラーメッセージをハードコードしない（AppException を使う）
- app_ui_kit のコードを直接コピーしてアプリ側に持ち込まない（パッケージを参照する）
