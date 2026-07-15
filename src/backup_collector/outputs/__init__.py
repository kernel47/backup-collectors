from backup_collector.outputs.backup_hub import BackupHubOutput
from backup_collector.outputs.json_file import JsonFileOutput
from backup_collector.outputs.logstash import LogstashOutput
from backup_collector.outputs.reference import ReferenceOutput
from backup_collector.outputs.stdout import StdoutOutput
from backup_collector.exceptions import ConfigurationError
from backup_collector.settings import Settings

DEFAULT_OUTPUTS = {
    "pamela": "backup_hub",
    "elk": "logstash",
    "baseline": "reference",
}


def build_output(name: str, settings: Settings):
    outputs = {
        "backup_hub": lambda: BackupHubOutput(settings.backup_hub_url, settings.backup_hub_token),
        "logstash": lambda: LogstashOutput(settings.logstash_url, settings.logstash_token),
        "reference": lambda: ReferenceOutput(settings.reference_url, settings.reference_token),
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
    "ReferenceOutput",
    "StdoutOutput",
    "DEFAULT_OUTPUTS",
    "build_output",
]
