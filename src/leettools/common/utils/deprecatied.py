import functools
import warnings


def deprecated(reason: str):
    """
    A basic decorator to mark functions as deprecated.
    """

    def decorator(func):
        @functools.wraps(func)  # Preserves original function metadata
        def wrapper(*args, **kwargs):
            warnings.warn(
                f"{func.__name__}() is deprecated: {reason}",
                category=DeprecationWarning,
                stacklevel=2,  # Points to the caller of the decorated function
            )
            return func(*args, **kwargs)

        # Add note to docstring if possible
        docstring = func.__doc__ if func.__doc__ else ""
        reason_note = f"\n\n.. deprecated::\n   {reason}"
        wrapper.__doc__ = docstring + reason_note
        return wrapper

    return decorator
