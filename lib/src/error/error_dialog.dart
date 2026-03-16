import "package:flutter/material.dart";
import "app_exception.dart";

class ErrorDialog extends StatelessWidget {
  const ErrorDialog({super.key, required this.exception});

  final AppException exception;

  static Future<void> show(BuildContext context, AppException exception) {
    return showDialog(
      context: context,
      builder: (_) => ErrorDialog(exception: exception),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text("エラー"),
      content: Text(exception.message),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text("閉じる"),
        ),
        if (exception.type == AppExceptionType.unauthorized)
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text("ログインへ"),
          ),
      ],
    );
  }
}
