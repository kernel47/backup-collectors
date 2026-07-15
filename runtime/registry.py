from scopes.baseline import BaselineScope
from scopes.logstash import LogstashScope
from scopes.pamela import PamelaScope
from modules.datadomain import DataDomainSource
from modules.netbackup import NetBackupSource
from modules.tapelibrary import TapeLibrarySource

SOURCES = {
    "netbackup": NetBackupSource,
    "datadomain": DataDomainSource,
    "tapelibrary": TapeLibrarySource,
}

SCOPES = {
    "pamela": PamelaScope,
    "logstash": LogstashScope,
    "baseline": BaselineScope,
}

SUPPORTED_COLLECTIONS = {
    "pamela": {"netbackup": {"policies", "jobs"}},
    "logstash": {"netbackup": {"policies", "jobs", "images", "shares"}},
    "baseline": {"netbackup": {"baseline"}},
}
