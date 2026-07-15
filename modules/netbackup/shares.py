from typing import Any

from context import CollectionContext
from modules.netbackup.policies import _as_dict


def collect_shares(client: Any, context: CollectionContext) -> list[dict]:
    """Temporary adapter: expose protected clients until nbu gains a shares service."""
    del context
    return [_as_dict(item) for item in client.policies.clients()]

