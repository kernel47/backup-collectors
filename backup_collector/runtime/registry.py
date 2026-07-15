from backup_collector.scopes.baseline import BaselineScope
from backup_collector.scopes.elk import ElkScope
from backup_collector.scopes.pamela import PamelaScope
from backup_collector.sources.datadomain import DataDomainSource
from backup_collector.sources.netbackup import NetBackupSource
from backup_collector.sources.tapelibrary import TapeLibrarySource

SOURCES = {
    "netbackup": NetBackupSource,
    "datadomain": DataDomainSource,
    "tapelibrary": TapeLibrarySource,
}

SCOPES = {
    "pamela": PamelaScope,
    "elk": ElkScope,
    "baseline": BaselineScope,
}

SUPPORTED_COLLECTIONS = {
    "pamela": {"netbackup": {"policies", "jobs"}},
    "elk": {"netbackup": {"policies", "jobs", "images", "shares"}},
    "baseline": {"netbackup": {"baseline"}},
}

