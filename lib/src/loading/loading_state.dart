import "../error/app_exception.dart";

sealed class LoadingState<T> {
  const LoadingState();
}

class LoadingIdle<T> extends LoadingState<T> {
  const LoadingIdle();
}

class LoadingInProgress<T> extends LoadingState<T> {
  const LoadingInProgress();
}

class LoadingSuccess<T> extends LoadingState<T> {
  const LoadingSuccess(this.data);
  final T data;
}

class LoadingFailure<T> extends LoadingState<T> {
  const LoadingFailure(this.exception);
  final AppException exception;
}
