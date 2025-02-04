from typing import Any

import pytest
from unittest.mock import AsyncMock, Mock

from pytest_mock import MockerFixture
from sqlalchemy.exc import NoResultFound
from fastapi.testclient import TestClient

from dr_emu.models import Run, Template, Infrastructure, Instance

from dr_emu.app import app as app
from shared import endpoints


@pytest.fixture()
def test_app(mocker: MockerFixture):
    mocker.patch("dr_emu.app.sessionmanager", AsyncMock())
    with TestClient(app) as client:
        yield client


async def test_main(test_app: TestClient):
    response = test_app.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Dr-Emu will see you now"}


controllers_path = "dr_emu.controllers"


@pytest.mark.asyncio
class TestRun:
    run_controller = f"{controllers_path}.run"

    @pytest.fixture()
    def instance(self):
        run_mock = Mock(spec=Instance)
        run_mock.configure_mock(
            infrastructure=Mock(id=1),
        )
        return run_mock

    @pytest.fixture()
    def run(self, instance: Mock):
        run_mock = Mock(spec=Run)
        run_mock.configure_mock(id=1, name="test_run", template_id=3, instances=[instance])
        return run_mock

    @pytest.fixture()
    def run_schema(self, run: Mock) -> dict[str, Any]:
        return {"id": run.id, "name": run.name, "template_id": run.template_id}

    async def test_list_runs(self, test_app: TestClient, run: Mock, mocker: MockerFixture, run_schema: dict[str, Any]):
        mock_list_runs = AsyncMock(return_value=[run])
        mocker.patch(f"{self.run_controller}.list_runs", side_effect=mock_list_runs)

        response = test_app.get(endpoints.Run.list)
        assert response.status_code == 200
        run_schema["infrastructure_ids"] = [1]
        assert response.json() == [run_schema]

    async def test_get_run(self, test_app: TestClient, run: Mock, mocker: MockerFixture, run_schema: dict[str, Any]):
        mock_list_runs = AsyncMock(return_value=run)
        mocker.patch(f"{self.run_controller}.get_run", side_effect=mock_list_runs)

        response = test_app.get(endpoints.Run.get.format(run.id))
        assert response.status_code == 200
        run_schema["infrastructure_ids"] = [1]
        assert response.json() == run_schema

    async def test_create_run(self, test_app: TestClient, run: Mock, mocker: MockerFixture, run_schema: dict[str, Any]):
        mocker.patch(f"{self.run_controller}.create_run", side_effect=AsyncMock(return_value=run))
        response = test_app.post(
            endpoints.Run.create,
            json={"name": run.name, "template_id": run.template_id},
        )

        assert response.status_code == 201
        assert response.json() == run_schema

    async def test_delete_run(self, test_app: TestClient, run: Mock, mocker: MockerFixture):
        mocker.patch(f"{self.run_controller}.delete_run")
        response = test_app.delete(endpoints.Run.delete.format(run.id))

        assert response.status_code == 204

    async def test_delete_nonexistent_run(self, test_app: TestClient, run: Mock, mocker: MockerFixture):
        mocker.patch(f"{self.run_controller}.delete_run", side_effect=NoResultFound)
        response = test_app.delete(endpoints.Run.delete.format(run.id))

        assert response.status_code == 404

    async def test_start_run(self, test_app: TestClient, run: Mock, mocker: MockerFixture):
        mocker.patch(f"{self.run_controller}.start_run")
        response = test_app.post(endpoints.Run.start.format(run.id), json={"instances": 1})

        assert response.status_code == 200
        assert response.json() == {"message": "Run instance started"}

    async def test_start_nonexistent_run(self, test_app: TestClient, run: Mock, mocker: MockerFixture):
        mocker.patch(f"{self.run_controller}.start_run", side_effect=NoResultFound)
        response = test_app.post(
            f"/runs/start/{run.id}", json={"instances": 1, "supernet": "10.0.0.0/8", "subnets_mask": 24}
        )

        assert response.status_code == 404

    async def test_stop_run(self, test_app: TestClient, run: Mock, mocker: MockerFixture):
        mocker.patch(f"{self.run_controller}.stop_run")
        response = test_app.post(
            endpoints.Run.stop.format(run.id),
        )

        assert response.status_code == 200
        assert response.json() == {"message": f"All instances of Run {run.id} has been stopped"}

    async def test_stop_nonexistent_run(self, test_app: TestClient, run: Mock, mocker: MockerFixture):
        mocker.patch(f"{self.run_controller}.stop_run", side_effect=NoResultFound)
        response = test_app.post(
            endpoints.Run.stop.format(run.id),
        )
        assert response.status_code == 404


@pytest.mark.asyncio
class TestTemplate:
    template_controller = f"{controllers_path}.template"

    @pytest.fixture()
    def template(self):
        template_mock = Mock(spec=Template)
        template_mock.configure_mock(
            id=1,
            name="test_template",
            description="test_description",
        )
        return template_mock

    @pytest.fixture()
    def template_schema(self, template: Mock) -> dict[str, Any]:
        return {"description": template.description, "name": template.name, "id": template.id}

    async def test_list_templates(
        self, template: Mock, test_app: TestClient, mocker: MockerFixture, template_schema: dict[str, Any]
    ):
        mock_list_templates = AsyncMock(return_value=[template])
        mocker.patch(f"{self.template_controller}.list_templates", side_effect=mock_list_templates)

        response = test_app.get(endpoints.Template.list)
        assert response.status_code == 200
        assert response.json() == [template_schema]

    async def test_create_template(
        self, test_app: TestClient, template: Mock, mocker: MockerFixture, template_schema: dict[str, Any]
    ):
        mock_create_template = mocker.patch(
            f"{self.template_controller}.create_template", side_effect=AsyncMock(return_value=template)
        )
        response = test_app.post(
            endpoints.Template.create, json={"name": template.name, "description": template.description}
        )

        mock_create_template.assert_called_once()
        assert response.status_code == 201
        assert response.json() == template_schema

    async def test_delete_template(self, test_app: TestClient, template: Mock, mocker: MockerFixture):
        mock_delete_template = mocker.patch(f"{self.template_controller}.delete_template")
        response = test_app.delete(endpoints.Template.delete.format(template.id))

        mock_delete_template.assert_called_once()
        assert response.status_code == 204

    async def test_delete_nonexistent_template(self, test_app: TestClient, template: Mock, mocker: MockerFixture):
        mocker.patch(f"{self.template_controller}.delete_template", side_effect=NoResultFound)
        response = test_app.delete(endpoints.Template.delete.format(template.id))

        assert response.status_code == 404


@pytest.mark.asyncio
class TestInfrastructure:
    infra_controller = f"{controllers_path}.infrastructure.InfrastructureController"

    @pytest.fixture()
    def infrastructure(self):
        infra = Mock(spec=Infrastructure)
        infra.configure_mock(id=1, name="test_infra", instance=Mock(run_id=1))
        return infra

    async def test_list_infrastructures(self, test_app: TestClient, mocker: MockerFixture, infrastructure: Mock):
        mocker.patch(
            f"{self.infra_controller}.list_infrastructures", side_effect=AsyncMock(return_value=[infrastructure])
        )

        response = test_app.get(endpoints.Infrastructure.list)
        assert response.status_code == 200
        assert response.json() == [{"id": infrastructure.id, "name": infrastructure.name, "run_id": 1}]

    async def test_destroy_infrastructure(self, test_app: TestClient, mocker: MockerFixture):
        infra_mock = Mock()
        mock_stop_infra = mocker.patch(f"{self.infra_controller}.stop_infra")
        mock_delete_infra = mocker.patch(f"{self.infra_controller}.delete_infra")
        mocker.patch(f"{self.infra_controller}.get_infra", side_effect=AsyncMock(return_value=infra_mock))

        response = test_app.delete(endpoints.Infrastructure.delete.format(1))

        mock_stop_infra.assert_called_once_with(infra_mock)
        mock_delete_infra.assert_called_once()

        assert response.status_code == 204

    async def test_delete_nonexistent_infrastructure(self, test_app: TestClient, mocker: MockerFixture):
        mocker.patch(f"{self.infra_controller}.get_infra", side_effect=NoResultFound)
        response = test_app.delete(endpoints.Infrastructure.delete.format(1))

        assert response.status_code == 404
