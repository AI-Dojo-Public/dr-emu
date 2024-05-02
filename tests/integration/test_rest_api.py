import pytest
from dr_emu.models import (
    Instance,
    Run,
    Template,
)
from shared import endpoints


@pytest.fixture(scope="module")
def template():
    template = Template(name="testplate", description=dict())
    return template


@pytest.fixture(scope="module")
def run(template, instance):
    run = Run(name="testrun", template=template, template_id=2, instances=[])
    return run


@pytest.fixture(scope="module")
def instance(run, infrastructure):
    instance = Instance(
        run_id=run.id,
        run=run,
        infrastrucrure=infrastructure,
    )
    return instance


@pytest.fixture(scope="module")
def infrastructure(instance, template):
    infrastructure = Run(name="test_infra", template=template, template_id=1, instances=[instance])
    return infrastructure


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


async def test_run(client):
    create_template = client.post(
        endpoints.Template.create,
        json={"name": "test_name", "description": "test_desc"},
    ).json()

    create_run = client.post(
        endpoints.Run.create,
        json={"name": "test_run", "template_id": create_template["id"]},
    )
    assert create_run.status_code == 201
    assert create_run.json() == {"id": 1, "name": "test_run", "template_id": create_template["id"]}

    delete_run = client.delete(endpoints.Run.delete.format(create_run.json()["id"]))
    assert delete_run.status_code == 204
