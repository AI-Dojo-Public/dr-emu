import pytest
from dr_emu.models import (
    Base,
    Network,
    Service,
    Router,
    Interface,
    Node,
    Attacker,
    FirewallRule,
    Instance,
    AgentPypi,
    Agent,
    Run,
    Template,
)
from shared import endpoints


@pytest.fixture(scope="module")
def template():
    template = Template(name="testplate", description="testscription")
    return template


@pytest.fixture(scope="module")
def run(agent, template, instance):
    run = Run(name="testrun", agents=[agent], template=None, template_id=2, instances=[])
    return run


@pytest.fixture(scope="module")
def instance(run, infrastructure):
    instance = Instance(
        run_id=run.id,
        run=run,
        agent_instances="test",
        infrastrucrure=infrastructure,
    )
    return instance


@pytest.fixture(scope="module")
def infrastructure(instance, agent):
    infrastructure = Run(name="test_infra", agents=[agent], template="test", template_id=1, instances=[instance])
    return infrastructure


@pytest.fixture(scope="module")
def pypi_install():
    pypi_install = AgentPypi(
        package_name="testagent",
    )
    return pypi_install


@pytest.fixture(scope="module")
def agent(pypi_install):
    agent = Agent(name="testagent", role="attacker", install_method=pypi_install)
    return agent


@pytest.mark.parametrize(
    "endpoint, agent_dict, agent_type",
    [
        (endpoints.Agent.create_pypi, {"name": "testagent", "role": "attacker", "package_name": "testpackg"}, "pypi"),
        (
                endpoints.Agent.create_local,
                {
                    "name": "Foo",
                    "role": "attacker",
                    "package_name": "ai-agent",
                    "path": "path/to/agent/package",
                },
                "local"
        ),
        (
                endpoints.Agent.create_git,
                {
                    "access_token": "test",
                    "git_project_url": "https://gitlab.test.test2.cz/test/test-project.git",
                    "name": "Foo",
                    "package_name": "aidojo-agent",
                    "role": "attacker",
                    "username": "oauth2",
                },
                "git"
        ),
    ],
)
async def test_agent(client, mocker, endpoint, agent_dict, agent_type):
    mocker.patch("dr_emu.models.Agent.install")
    response = client.get(endpoints.Agent.list)
    assert response.status_code == 200
    assert response.json() == []

    create_response = client.post(
        endpoint,
        json=agent_dict,
    )
    assert create_response.status_code == 201
    assert create_response.json() == {"id": 1, "name": agent_dict["name"], "role": agent_dict["role"],
                                      "type": agent_type}

    list_response = client.get(endpoints.Agent.list)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    delete_response = client.delete(endpoints.Agent.delete.format(list_response.json()[0]["id"]))
    assert delete_response.status_code == 204


async def test_template(client):
    response = client.get(endpoints.Template.list)
    assert response.status_code == 200
    assert response.json() == []

    create_response = client.post(
        endpoints.Template.create,
        json={"name": "test_template", "description": "test_description"},
    )
    assert create_response.json() == {"id": 1, "name": "test_template", "description": "test_description"}
    assert create_response.status_code == 201

    list_response = client.get(endpoints.Template.list)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    delete_response = client.delete(endpoints.Template.delete.format(list_response.json()[0]["id"]))
    assert delete_response.status_code == 204


async def test_run(client, mocker):
    mocker.patch("dr_emu.models.Agent.install")
    create_agent = client.post(
        endpoints.Agent.create_pypi,
        json={"name": "testagent", "role": "attacker", "package_name": "testpackg"},
    ).json()
    create_template = client.post(
        endpoints.Template.create,
        json={"name": "test_name", "description": "test_desc"},
    ).json()

    create_run = client.post(
        endpoints.Run.create,
        json={"name": "test_run", "template_id": create_template["id"], "agent_ids": [create_agent["id"]]},
    )
    assert create_run.status_code == 201
    assert create_run.json() == {"id": 1, "name": "test_run", "template_id": create_template["id"],
                                 "agent_ids": [create_agent["id"]]}

    delete_run = client.delete(endpoints.Run.delete.format(create_run.json()["id"]))
    assert delete_run.status_code == 204
