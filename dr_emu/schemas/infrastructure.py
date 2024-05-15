from typing import List
from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, constr

Base = declarative_base()


class InfrastructureSchema(BaseModel):
    id: int
    name: constr(max_length=30)
    run_id: int


class ApplianceSchema(BaseModel):
    name: constr(max_length=30)
    ip: str
    original_ip: str


class NetworkSchema(BaseModel):
    name: constr(max_length=30)
    ip: str
    appliances: list[ApplianceSchema]


class InfrastructureInfo(InfrastructureSchema):
    networks: list[NetworkSchema]
    attackers: dict
