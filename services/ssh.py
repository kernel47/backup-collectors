from typing import Any

from exceptions import ConfigurationError


def create_client(
    hostname: str,
    username: str,
    password: str | None = None,
    *,
    port: int = 22,
    timeout: float = 30.0,
) -> Any:
    try:
        import paramiko
    except ImportError as exc:
        raise ConfigurationError("The paramiko package is not installed") from exc

    client = paramiko.SSHClient()
    client.load_system_host_keys()
    try:
        client.connect(
            hostname=hostname,
            port=port,
            username=username,
            password=password,
            timeout=timeout,
            look_for_keys=password is None,
            allow_agent=password is None,
        )
    except Exception:
        client.close()
        raise
    return client


def run(client: Any, command: str, *, timeout: float | None = None) -> tuple[int, str, str]:
    _, stdout, stderr = client.exec_command(command, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    return exit_code, stdout.read().decode(), stderr.read().decode()
