from enum import Enum


class AgentRole(Enum):
    attacker = "attacker"
    defender = "defender"


class InstallChoice(Enum):
    git = "git"
    pypi = "pypi"
    local = "local"
