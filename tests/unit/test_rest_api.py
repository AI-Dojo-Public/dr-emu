import pytest
from unittest.mock import AsyncMock, Mock
from sqlalchemy.exc import NoResultFound
from fastapi.testclient import TestClient

from dr_emu.models import Agent, AgentGit, AgentLocal, AgentPypi, Run, Template, Infrastructure, Instance

from dr_emu.app import app as app
from shared import endpoints


@pytest.fixture()
def test_app(mocker):
    mocker.patch("dr_emu.app.sessionmanager", AsyncMock())
    with TestClient(app) as client:
        yield client


async def test_main(test_app):
    response = test_app.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Dr-Emu will see you now"}


controllers_path = "dr_emu.controllers"


@pytest.mark.asyncio
class TestAgent:
    agent_controller = f"{controllers_path}.agent"

    @pytest.fixture
    def git_agent_installation(self, mocker):
        installation_method_mock = Mock(spec=AgentGit)
        mocker.patch("dr_emu.api.endpoints.agent.AgentGit", return_value=installation_method_mock)
        installation_method_mock.configure_mock(
            **{
                "access_token": "test_token",
                "username": "test",
                "host": "test_git",
                "owner": "test_owner",
                "repo_name": "test_repo",
                "package_name": "test_pkg",
                "type": "git",
            }
        )
        return installation_method_mock

    @pytest.fixture
    def pypi_agent_installation(self):
        installation_method_mock = Mock(spec=AgentPypi)
        installation_method_mock.configure_mock(**{"type": "pypi", "package_name": "test_pkg"})
        return installation_method_mock

    @pytest.fixture
    def local_agent_installation(self):
        installation_method_mock = Mock(spec=AgentLocal)
        installation_method_mock.configure_mock(**{"type": "local", "package_name": "test_pkg", "path": "test_path"})
        return installation_method_mock

    @pytest.fixture()
    def agent(self):
        agent_mock = Mock(spec=Agent)
        agent_mock.configure_mock(id=1, name="test_agent", role="attacker")
        return agent_mock

    async def test_list_agents(self, agent, test_app, mocker, git_agent_installation):
        agent.install_method = git_agent_installation
        mock_list_agents = AsyncMock(return_value=[agent])
        mocker.patch(f"{self.agent_controller}.list_agents", side_effect=mock_list_agents)
        response = test_app.get(endpoints.Agent.list)
        assert response.status_code == 200
        assert response.json() == [{"id": 1, "name": agent.name, "role": agent.role, "type": "git"}]

    async def test_create_git_agent(self, test_app, agent, git_agent_installation, mocker):
        agent.install_method = git_agent_installation
        mocker.patch(f"{self.agent_controller}.create_agent", return_value=agent)
        response = test_app.post(
            endpoints.Agent.create_git,
            json={
                "access_token": git_agent_installation.access_token,
                "git_project_url": f"https://{git_agent_installation.username}:{git_agent_installation.access_token}@"
                f"{git_agent_installation.host}/{git_agent_installation.owner}/"
                f"{git_agent_installation.repo_name}",
                "name": agent.name,
                "package_name": git_agent_installation.package_name,
                "role": agent.role,
                "username": git_agent_installation.username,
            },
        )

        assert response.status_code == 201
        assert response.json() == {
            "id": agent.id,
            "name": agent.name,
            "role": agent.role,
            "type": agent.install_method.type,
        }

    async def test_create_pypi_agent(self, test_app, agent, pypi_agent_installation, mocker):
        agent.install_method = pypi_agent_installation
        mocker.patch(f"{self.agent_controller}.create_agent", return_value=agent)
        response = test_app.post(
            endpoints.Agent.create_pypi,
            json={
                "name": agent.name,
                "role": agent.role,
                "package_name": pypi_agent_installation.package_name,
            },
        )

        assert response.status_code == 201
        assert response.json() == {
            "id": agent.id,
            "name": agent.name,
            "role": agent.role,
            "type": agent.install_method.type,
        }

    async def test_create_local_agent(self, test_app, agent, local_agent_installation, mocker):
        agent.install_method = local_agent_installation
        mocker.patch(f"{self.agent_controller}.create_agent", return_value=agent)
        response = test_app.post(
            endpoints.Agent.create_pypi,
            json={
                "name": agent.name,
                "role": agent.role,
                "package_name": local_agent_installation.package_name,
                "path": local_agent_installation.path,
            },
        )

        assert response.status_code == 201
        assert response.json() == {
            "id": agent.id,
            "name": agent.name,
            "role": agent.role,
            "type": agent.install_method.type,
        }

    async def test_delete_agent(self, test_app, agent, mocker):
        mocker.patch(f"{self.agent_controller}.delete_agent")
        response = test_app.delete(endpoints.Agent.delete.format(1))

        assert response.status_code == 204


@pytest.mark.asyncio
class TestRun:
    run_controller = f"{controllers_path}.run"

    @pytest.fixture()
    def instance(self):
        run_mock = Mock(spec=Instance)
        run_mock.configure_mock(infrastructure=Mock(id=1),)
        return run_mock

    @pytest.fixture()
    def run(self, instance):
        run_mock = Mock(spec=Run)
        run_mock.configure_mock(id=1, name="test_run", agents=[Mock(id=2)], template_id=3, instances=[instance])
        return run_mock

    @pytest.fixture()
    def run_schema(self, run):
        return {"id": run.id, "name": run.name, "agent_ids": [2], "template_id": run.template_id}

    async def test_list_runs(self, test_app, run, mocker, run_schema):
        mock_list_runs = AsyncMock(return_value=[run])
        mocker.patch(f"{self.run_controller}.list_runs", side_effect=mock_list_runs)

        response = test_app.get(endpoints.Run.list)
        assert response.status_code == 200
        run_schema["infrastructure_ids"] = [1]
        assert response.json() == [run_schema]

    async def test_get_run(self, test_app, run, mocker, run_schema):
        mock_list_runs = AsyncMock(return_value=run)
        mocker.patch(f"{self.run_controller}.get_run", side_effect=mock_list_runs)

        response = test_app.get(endpoints.Run.get.format(run.id))
        assert response.status_code == 200
        run_schema["infrastructure_ids"] = [1]
        assert response.json() == run_schema

    async def test_create_run(self, test_app, run, mocker, run_schema):
        mocker.patch(f"{self.run_controller}.create_run", side_effect=AsyncMock(return_value=run))
        response = test_app.post(
            endpoints.Run.create,
            json={"name": run.name, "template_id": run.template_id, "agent_ids": [agent.id for agent in run.agents]},
        )

        assert response.status_code == 201
        assert response.json() == run_schema

    async def test_delete_run(self, test_app, run, mocker):
        mocker.patch(f"{self.run_controller}.delete_run")
        response = test_app.delete(endpoints.Run.delete.format(run.id))

        assert response.status_code == 204

    async def test_delete_nonexistent_run(self, test_app, run, mocker):
        mocker.patch(f"{self.run_controller}.delete_run", side_effect=NoResultFound)
        response = test_app.delete(endpoints.Run.delete.format(run.id))

        assert response.status_code == 404

    async def test_start_run(self, test_app, run, mocker):
        mocker.patch(f"{self.run_controller}.start_run")
        response = test_app.post(endpoints.Run.start.format(run.id))

        assert response.status_code == 200
        assert response.json() == {"message": f"{1} Run instances created"}

    async def test_start_nonexistent_run(self, test_app, run, mocker):
        mocker.patch(f"{self.run_controller}.start_run", side_effect=NoResultFound)
        response = test_app.post(
            f"/runs/start/{run.id}?instances=1",
        )

        assert response.status_code == 404

    async def test_stop_run(self, test_app, run, mocker):
        mocker.patch(f"{self.run_controller}.stop_run")
        response = test_app.post(
            endpoints.Run.stop.format(run.id),
        )

        assert response.status_code == 200
        assert response.json() == {"message": f"All instances of Run {run.id} has been stopped"}

    async def test_stop_nonexistent_run(self, test_app, run, mocker):
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
    def template_schema(self, template):
        return {"description": template.description, "name": template.name, "id": template.id}

    async def test_list_templates(self, template, test_app, mocker, template_schema):
        mock_list_templates = AsyncMock(return_value=[template])
        mocker.patch(f"{self.template_controller}.list_templates", side_effect=mock_list_templates)

        response = test_app.get(endpoints.Template.list)
        assert response.status_code == 200
        assert response.json() == [template_schema]

    async def test_create_template(self, test_app, template, mocker, template_schema):
        mock_create_template = mocker.patch(
            f"{self.template_controller}.create_template", side_effect=AsyncMock(return_value=template)
        )
        response = test_app.post(
            endpoints.Template.create, json={"name": template.name, "description": template.description}
        )

        mock_create_template.assert_called_once()
        assert response.status_code == 201
        assert response.json() == template_schema

    async def test_delete_template(self, test_app, template, mocker):
        mock_delete_template = mocker.patch(f"{self.template_controller}.delete_template")
        response = test_app.delete(endpoints.Template.delete.format(template.id))

        mock_delete_template.assert_called_once()
        assert response.status_code == 204

    async def test_delete_nonexistent_template(self, test_app, template, mocker):
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

    async def test_list_infrastructures(self, test_app, mocker, infrastructure):
        mocker.patch(
            f"{self.infra_controller}.list_infrastructures", side_effect=AsyncMock(return_value=[infrastructure])
        )

        response = test_app.get(endpoints.Infrastructure.list)
        assert response.status_code == 200
        assert response.json() == [{"id": infrastructure.id, "name": infrastructure.name, "run_id": 1}]

    async def test_destroy_infrastructure(self, test_app, mocker):
        infra_mock = Mock()
        mock_stop_infra = mocker.patch(f"{self.infra_controller}.stop_infra")
        mock_delete_infra = mocker.patch(f"{self.infra_controller}.delete_infra")
        mocker.patch(f"{self.infra_controller}.get_infra", side_effect=AsyncMock(return_value=infra_mock))

        response = test_app.delete(endpoints.Infrastructure.delete.format(1))

        mock_stop_infra.assert_called_once_with(infra_mock)
        mock_delete_infra.assert_called_once()

        assert response.status_code == 204

    async def test_delete_nonexistent_infrastructure(self, test_app, mocker):
        mocker.patch(f"{self.infra_controller}.get_infra", side_effect=NoResultFound)
        response = test_app.delete(endpoints.Infrastructure.delete.format(1))

        assert response.status_code == 404
