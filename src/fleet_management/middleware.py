import threading

_thread_locals = threading.local()


def get_current_request_user():
	"""Get the current user from thread-local storage."""
	return getattr(_thread_locals, 'user', None)


class RequestUserMiddleware:
	"""Middleware to store the current user in thread-local storage for access in signals."""

	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		_thread_locals.user = request.user if request.user.is_authenticated else None
		response = self.get_response(request)
		return response
