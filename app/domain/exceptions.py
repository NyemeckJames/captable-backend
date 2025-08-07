class DomainException(Exception):
    """Base exception for domain-related errors"""
    pass


class BusinessRuleViolationException(DomainException):
    """Exception raised when a business rule is violated"""
    pass
