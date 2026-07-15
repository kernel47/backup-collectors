from backup_collector.outputs.backup_hub import HttpOutput


class LogstashOutput(HttpOutput):
    destination = "Logstash"

