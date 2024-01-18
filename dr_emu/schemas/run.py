from pydantic import BaseModel


class Run(BaseModel):
    name: str
    template_id: int
    agent_ids: list[int]


class RunOut(BaseModel):
    name: str
    id: int
