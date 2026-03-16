enum AppExceptionType {
  unauthorized,
  validation,
  server,
  network,
  unknown,
}

class AppException implements Exception {
  const AppException({
    required this.message,
    required this.type,
    this.statusCode,
  });

  final String message;
  final AppExceptionType type;
  final int? statusCode;

  factory AppException.fromStatusCode(int? code) {
    return switch (code) {
      401 => const AppException(
          message: "認証が切れました。再度ログインしてください。",
          type: AppExceptionType.unauthorized,
          statusCode: 401,
        ),
      422 => const AppException(
          message: "入力内容を確認してください。",
          type: AppExceptionType.validation,
          statusCode: 422,
        ),
      500 => const AppException(
          message: "サーバーエラーが発生しました。",
          type: AppExceptionType.server,
          statusCode: 500,
        ),
      _ => const AppException(
          message: "予期せぬエラーが発生しました。",
          type: AppExceptionType.unknown,
        ),
    };
  }
}
