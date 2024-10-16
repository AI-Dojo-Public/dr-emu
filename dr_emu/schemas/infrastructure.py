from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel

Base = declarative_base()


class InfrastructureSchema(BaseModel):
    id: int
    name: str
    run_id: int


class ApplianceSchema(BaseModel):
    name: str
    ip: str
    original_ip: str


class NetworkSchema(BaseModel):
    name: str
    ip: str
    appliances: list[ApplianceSchema]


class InfrastructureInfo(InfrastructureSchema):
    networks: list[NetworkSchema]
    attackers: dict
