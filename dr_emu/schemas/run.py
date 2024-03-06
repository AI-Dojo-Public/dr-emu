from pydantic import BaseModel


class Run(BaseModel):
    name: str
    template_id: int
    agent_ids: list[int]


class RunOut(Run):
    id: int


class RunInfo(RunOut):
    infrastructure_ids: list[int]
