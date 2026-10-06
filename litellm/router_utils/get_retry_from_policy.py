"""
Get num retries for an exception. 

- Account for retry policy by exception type.
"""

from typing import Dict, Optional, Union

from litellm.exceptions import (
    AuthenticationError,
    BadRequestError,
    ContentPolicyViolationError,
    RateLimitError,
    Timeout,
)
from litellm.types.router import RetryPolicy


def get_num_retries_from_retry_policy(
    exception: Exception,
    retry_policy: Optional[Union[RetryPolicy, dict]] = None,
    model_group: Optional[str] = None,
    model_group_retry_policy: Optional[Dict[str, RetryPolicy]] = None,
):
    """
    BadRequestErrorRetries: Optional[int] = None
    AuthenticationErrorRetries: Optional[int] = None
    TimeoutErrorRetries: Optional[int] = None
    RateLimitErrorRetries: Optional[int] = None
    ContentPolicyViolationErrorRetries: Optional[int] = None
    PaymentRequiredErrorRetries: Optional[int] = None
    OtherErrorRetries: Optional[int] = None
    """
    # if we can find the exception then in the retry policy -> return the number of retries

    if (
        model_group_retry_policy is not None
        and model_group is not None
        and model_group in model_group_retry_policy
    ):
        retry_policy = model_group_retry_policy.get(model_group, None)  # type: ignore

    if retry_policy is None:
        return None
    if isinstance(retry_policy, dict):
        retry_policy = RetryPolicy(**retry_policy)

    # Local patch: HTTP 402 (Payment Required) surfaces as a generic APIError
    # (no dedicated exception class upstream), so match on status_code.
    # Retry policy is checked before `should_retry_this_error` and takes
    # precedence, so setting this makes the router move to the next healthy
    # deployment on 402 instead of raising immediately.
    if (
        getattr(exception, "status_code", None) == 402
        and retry_policy.PaymentRequiredErrorRetries is not None
    ):
        return retry_policy.PaymentRequiredErrorRetries
    if (
        isinstance(exception, AuthenticationError)
        and retry_policy.AuthenticationErrorRetries is not None
    ):
        return retry_policy.AuthenticationErrorRetries
    if isinstance(exception, Timeout) and retry_policy.TimeoutErrorRetries is not None:
        return retry_policy.TimeoutErrorRetries
    if (
        isinstance(exception, RateLimitError)
        and retry_policy.RateLimitErrorRetries is not None
    ):
        return retry_policy.RateLimitErrorRetries
    if (
        isinstance(exception, ContentPolicyViolationError)
        and retry_policy.ContentPolicyViolationErrorRetries is not None
    ):
        return retry_policy.ContentPolicyViolationErrorRetries
    if (
        isinstance(exception, BadRequestError)
        and retry_policy.BadRequestErrorRetries is not None
    ):
        return retry_policy.BadRequestErrorRetries
    # Local patch: catch-all fallback after all specific fields. OtherErrorRetries
    # retries ANY error not covered above (402 w/o its own field, 5xx variants,
    # 403, provider-specific codes), so the router moves to the next healthy
    # deployment in the same model pool. Retry policy is checked before
    # `should_retry_this_error` and takes precedence, so this also covers errors
    # that would otherwise raise immediately.
    if retry_policy.OtherErrorRetries is not None:
        return retry_policy.OtherErrorRetries


def reset_retry_policy() -> RetryPolicy:
    return RetryPolicy()
