class SessionDoesNotExist(Exception):
	"""Raised when a session does not exist."""

class CRSNotFound(Exception):
	"""Raised when CRS info is required and cannot be retrieved."""

class NotUniqueViolation(Exception):
	"""Raised when a key is supposed to be unique, but it already exists."""