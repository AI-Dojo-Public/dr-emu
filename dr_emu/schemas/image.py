from pydantic import BaseModel


class Service(BaseModel):
    type: str
    version: str
    cves: str


class ImageSchema(BaseModel):
    name: str
    services: set[Service]
    pull: bool


class ImageOut(BaseModel):
    name: str
    id: int
    pull: bool
    services: list[Service]
    packages: list[str]

