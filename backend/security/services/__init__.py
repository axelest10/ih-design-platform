from .email import (
    EmailDeliveryError,
    EmailMessage,
    ResendEmailClient,
    TransactionalEmailClient,
    get_email_client,
)
from .magic_links import (
    MagicLinkError,
    consume_magic_link,
    create_magic_link,
    invalidate_other_magic_links,
)

__all__ = [
    "EmailDeliveryError",
    "EmailMessage",
    "MagicLinkError",
    "ResendEmailClient",
    "TransactionalEmailClient",
    "consume_magic_link",
    "create_magic_link",
    "get_email_client",
    "invalidate_other_magic_links",
]
