from pydantic import BaseModel, Field, ConfigDict, ValidationError, AfterValidator
from typing_extensions import Annotated
from netaddr import IPNetwork


def check_ipnetwork_format(supernet: str):
    return IPNetwork(supernet)


class RunStart(BaseModel):
    instances: int = Field(1, description="What number of instances (infrastructure copies) should be created")
    supernet: Annotated[str, AfterValidator(check_ipnetwork_format)] = Field(
        "10.0.0.0/8",
        description="The network defining the IP range from which the infrastructure " "networks will be created",
    )
    subnets_mask: int = Field(24, description="Specifies the size of subnets, that will be created from 'supernet'")


class Run(BaseModel):
    name: str
    template_id: int
    agent_ids: list[int]


class RunOut(Run):
    id: int


class RunInfo(RunOut):
    infrastructure_ids: list[int]
