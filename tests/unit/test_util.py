import pytest
from unittest.mock import AsyncMock, patch, Mock
import docker.errors
from pytest_mock import MockerFixture
from dr_emu.lib.util import pull_image  # Adjust the import based on your module structure

# Mock logger to avoid unnecessary logging during tests
logger = AsyncMock()


@pytest.mark.asyncio
async def test_pull_image():
    docker_client = Mock()

    with patch("asyncio.to_thread", new=AsyncMock(side_effect=lambda func, *args: func(*args))):
        await pull_image(docker_client, "image1")

    docker_client.images.get.assert_called_with("image1")


@pytest.mark.asyncio
async def test_pull_nonexistant():
    docker_client = Mock()
    docker_client.images.get.side_effect = docker.errors.ImageNotFound("image1")

    with patch("asyncio.to_thread", new=AsyncMock(side_effect=lambda func, *args: func(*args))):
        await pull_image(docker_client, "image1")

    docker_client.images.pull.assert_called_with("image1")


@pytest.mark.asyncio
async def test_pull_images_server_timeout(mocker: MockerFixture):
    mocker.patch("asyncio.sleep")
    docker_client = Mock()
    docker_client.images.get.side_effect = docker.errors.ImageNotFound("image1")
    docker_client.images.pull.side_effect = docker.errors.DockerException("Server timeout")

    with patch("asyncio.to_thread", new=AsyncMock(side_effect=lambda func, *args: func(*args))):
        await pull_image(docker_client, "image1")

    assert docker_client.images.pull.call_count == 3
