class Error(Exception):
    """
    Base exception class for this project.
    All other exceptions inherit form it.
    """


class GitError(Error):
    """
    For Git related errors.
    """


class ContainerNotRunning(Error):
    """
    Requested docker container is not in running state.
    """


class PackageNotAccessible(Error):
    """
    Cannot find or access python package
    """
