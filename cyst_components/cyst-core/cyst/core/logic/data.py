import uuid

from typing import Optional

from cyst.api.logic.data import Data


class DataImpl(Data):
    def __init__(self, id: Optional[str], owner: str, description: str = ""):
        if id:
            self._id = id
        else:
            self._id = str(uuid.uuid4())
        self._owner = owner
        self._description = description

    @property
    def id(self) -> str:
        return self._id

    @property
    def owner(self) -> str:
        return self._owner

    @property
    def description(self) -> str:
        return self._description
