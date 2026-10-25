"""Placeholder for the user's SSH implementation; no transport is installed yet."""

from collections.abc import Iterator
from dataclasses import dataclass, field

from core.exceptions import ConfigurationError


@dataclass
class SSHClient:
    host: str
    username: str
    password: str | None = field(default=None, repr=False)
    port: int = 22
    options: dict = field(default_factory=dict, repr=False)

    def execute(self, command: str):
        """Replace with the existing SSH command implementation."""
        raise ConfigurationError("SSH command execution is not integrated yet")

    def get_policy_clients(self, policy_name: str) -> list[str]:
        """Return client names for one policy using the user's SSH implementation."""
        raise ConfigurationError("SSH get_policy_clients is not integrated yet")

    def get_image_contents(self, image_id: str) -> Iterator[str]:
        """Yield directory paths progressively for one image; implement in the SSH module."""
        raise ConfigurationError("SSH get_image_contents is not integrated yet")

    def close(self):
        """The final implementation must release its connection here."""
