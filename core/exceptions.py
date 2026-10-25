class BackupCollectorError(Exception):
    """Expected application error; messages must not contain credentials."""


class CollectionError(BackupCollectorError):
    pass


class ParsingError(BackupCollectorError):
    pass


class ConfigurationError(BackupCollectorError):
    pass
