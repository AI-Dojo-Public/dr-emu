from pydantic import BaseModel
from netaddr import IPNetwork


def check_ipnetwork_format(supernet: str):
    return IPNetwork(supernet)


class Run(BaseModel):
    name: str
    template_id: int
    agent_ids: list[int]


class RunOut(Run):
    id: int


class RunInfo(RunOut):
    infrastructure_ids: list[int]
