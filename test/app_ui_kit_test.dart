import "package:app_ui_kit/app_ui_kit.dart";
import "package:flutter_test/flutter_test.dart";

void main() {
  group("AppException", () {
    test("fromStatusCode 401 returns unauthorized", () {
      final e = AppException.fromStatusCode(401);
      expect(e.type, AppExceptionType.unauthorized);
    });

    test("fromStatusCode 422 returns validation", () {
      final e = AppException.fromStatusCode(422);
      expect(e.type, AppExceptionType.validation);
    });

    test("fromStatusCode 500 returns server", () {
      final e = AppException.fromStatusCode(500);
      expect(e.type, AppExceptionType.server);
    });

    test("fromStatusCode unknown returns unknown", () {
      final e = AppException.fromStatusCode(999);
      expect(e.type, AppExceptionType.unknown);
    });
  });
}
