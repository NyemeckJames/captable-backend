class DomainException(Exception):
    """Base exception for domain-related errors"""
    pass


class BusinessRuleViolationException(DomainException):
    """Exception raised when a business rule is violated"""
    pass


class AccessDeniedException(DomainException):
    """Raised when a caller is authenticated but out of scope for the resource.

    Distinct from a business rule violation on purpose: the API layer maps it to
    403 rather than 400, so that an ownership failure is never reported as a
    malformed request.
    """
    pass
