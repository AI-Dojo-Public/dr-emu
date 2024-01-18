from pydantic import BaseModel


class TemplateSchema(BaseModel):
    name: str
    description: str


class TemplateOut(TemplateSchema):
    id: int
