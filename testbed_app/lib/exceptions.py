class Error(Exception):
    """
    Base exception class for this project.
    All other exceptions inherit form it.
    """


class GitError(Error):
    """
    For Git related errors.
    """
