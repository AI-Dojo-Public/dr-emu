from pydantic import BaseModel

from dr_emu.lib.util import AgentRole


class AgentPypiSchema(BaseModel):
    name: str
    role: AgentRole
    package_name: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Foo",
                    "role": AgentRole.attacker,
                    "package_name": "ai-agent",
                }
            ]
        }
    }


class AgentLocalSchema(AgentPypiSchema):
    path: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Foo",
                    "role": AgentRole.attacker,
                    "package_name": "ai-agent",
                    "path": "path/to/agent/package",
                }
            ]
        }
    }


class AgentGitSchema(AgentPypiSchema):
    access_token: str
    username: str
    git_project_url: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Foo",
                    "role": AgentRole.attacker,
                    "package_name": "ai-agent",
                    "username": "git_user",
                    "access_token": "git_token",
                    "git_project_url": "https://{git_host}/{owner}/{repo_name}.git",
                }
            ]
        }
    }


class AgentOut(BaseModel):
    id: int
    name: str
    role: AgentRole
    type: str
