class BackupCollectorError(Exception):
    """Base error expected by the command-line interface."""


class UnsupportedCollectionError(BackupCollectorError):
    pass


class CollectionError(BackupCollectorError):
    pass


class ParsingError(BackupCollectorError):
    pass


class OutputError(BackupCollectorError):
    pass


class ConfigurationError(BackupCollectorError):
    pass

