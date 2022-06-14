""" Contains all the custom exceptions used. """


class DirectoryAccessError(Exception):
    """Exception to be raised when the directory can't be accessed."""

    pass


class DirectoryCreateError(Exception):
    """Exception to be raised when the directory can't be created."""

    pass
