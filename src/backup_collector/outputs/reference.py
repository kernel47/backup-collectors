from backup_collector.outputs.backup_hub import HttpOutput


class ReferenceOutput(HttpOutput):
    destination = "Reference"

