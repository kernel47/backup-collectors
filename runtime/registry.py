from scopes.baseline import BaselineScope
from modules.elk import ElkScope
from scopes.pamela import PamelaScope
from sources.datadomain import DataDomainSource
from modules.netbackup import NetBackupSource
from sources.tapelibrary import TapeLibrarySource

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

