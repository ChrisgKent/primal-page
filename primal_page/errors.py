from click import UsageError


class PrimerNameError(UsageError):
    """Raised when a primername is invalid"""

    def __init__(self, primername: str):
        super().__init__(
            f"Invalid primernames: {primername}. Please use format (name)_(amplicon-number)_(LEFT|RIGHT) with optional _(primer-number)"
        )


class PrimerVersionError(UsageError):
    """Raised when a primername is unexpected"""

    def __init__(self, message: str):
        super().__init__(message)


class InvalidBedFileLine(UsageError):
    """Raised when a bedline is invalid"""

    def __init__(self, message: str):
        super().__init__(message)


class SchemeExists(UsageError):
    """Raised when a Scheme already exists"""

    def __init__(self, message: str):
        super().__init__(message)


class FileNotFound(UsageError):
    """Raised when a file is not found"""

    def __init__(self, message: str):
        super().__init__(message)


class InvalidReference(UsageError):
    """Raised when a file is not found"""

    def __init__(self, message: str):
        super().__init__(message)


class InvalidSchemeID(UsageError):
    """Raised when a schemeid is invalid"""

    def __init__(self, message: str):
        super().__init__(message)


class InvalidSchemeName(UsageError):
    """Raised when a schemename is invalid"""

    def __init__(self, message: str):
        super().__init__(message)


class InvalidAmpliconSize(UsageError):
    """Raised when a schemeversion is invalid"""

    def __init__(self, message: str):
        super().__init__(message)


class InvalidSchemeVersion(UsageError):
    """Raised when a schemeversion is invalid"""

    def __init__(self, message: str):
        super().__init__(message)
