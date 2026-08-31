"""Safe persistence errors that never expose backend connection details."""


class PersistenceError(Exception):
    code = "PERSISTENCE_UNAVAILABLE"


class PersistenceConfigurationError(PersistenceError):
    code = "PERSISTENCE_CONFIGURATION_INVALID"


class PersistenceUnavailableError(PersistenceError):
    code = "PERSISTENCE_UNAVAILABLE"


class PersistenceConflictError(PersistenceError):
    code = "PERSISTENCE_CONFLICT"


class PersistenceDataInvalidError(PersistenceError):
    code = "PERSISTENCE_DATA_INVALID"


class PersistenceSchemaUnsupportedError(PersistenceError):
    code = "PERSISTENCE_SCHEMA_UNSUPPORTED"

