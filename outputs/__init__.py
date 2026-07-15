from modules.backup_hub.output import BackupHubOutput
from outputs.json_file import JsonFileOutput
from modules.logstash.output import LogstashOutput
from modules.referential.output import ReferentialOutput
from outputs.stdout import StdoutOutput
from exceptions import ConfigurationError
from settings import Settings

DEFAULT_OUTPUTS = {
    "pamela": "backup_hub",
    "elk": "logstash",
    "baseline": "referential",
}


def build_output(name: str, settings: Settings):
    outputs = {
        "backup_hub": lambda: BackupHubOutput(settings.backup_hub_url, settings.backup_hub_token),
        "logstash": lambda: LogstashOutput(settings.logstash_url, settings.logstash_token),
        "referential": lambda: ReferentialOutput(settings.referential_url, settings.referential_token),
        "json": lambda: JsonFileOutput(settings.output_dir),
        "stdout": StdoutOutput,
    }
    try:
        return outputs[name]()
    except KeyError as exc:
        raise ConfigurationError(f"Unknown output: {name}") from exc

__all__ = [
    "BackupHubOutput",
    "JsonFileOutput",
    "LogstashOutput",
    "ReferentialOutput",
    "StdoutOutput",
    "DEFAULT_OUTPUTS",
    "build_output",
]
