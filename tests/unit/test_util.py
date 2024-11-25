import pytest
from unittest.mock import AsyncMock, patch, Mock
import docker.errors
from pytest_mock import MockerFixture
from dr_emu.lib.util import pull_image, get_image  # Adjust the import based on your module structure
from dr_emu.models import ImageState
from docker.errors import ImageNotFound

from shared.constants import firehole_config_path

# Mock logger to avoid unnecessary logging during tests
logger = AsyncMock()

@pytest.mark.asyncio
async def test_pull_image():
    docker_client = Mock()

    with patch("asyncio.to_thread", new=AsyncMock(side_effect=lambda func, *args: func(*args))):
        await pull_image(docker_client, "image1")

    docker_client.images.pull.assert_called_with("image1")



@pytest.mark.asyncio
async def test_pull_images_server_timeout(mocker: MockerFixture):
    mocker.patch("asyncio.sleep")
    docker_client = Mock()
    docker_client.images.pull.side_effect = docker.errors.DockerException("Server timeout")

    with pytest.raises(docker.errors.ImageNotFound):
        with patch("asyncio.to_thread", new=AsyncMock(side_effect=lambda func, *args: func(*args))):
            await pull_image(docker_client, "image1")

    assert docker_client.images.pull.call_count == 3


@pytest.fixture()
def image():
    services = [
        Mock(type="service1", variable_override={"key1": "value1"}),
        Mock(type="service2", variable_override={"key2": "value2"}),
    ]
    image = Mock(state=ImageState.initialized, pull=False, services=services, firehole_config="test_path")
    image.name = "test-image"
    return image

@pytest.mark.asyncio
async def test_get_image_that_exists(mocker, image):
    """Test case where the image already exists in Docker."""
    # Mocks
    docker_client = Mock()
    docker_client.images.get = Mock()  # No exception means the image exists
    db_session = AsyncMock()

    mocker.patch.object(db_session, "commit", AsyncMock())

    # Test function
    await get_image(docker_client, image, db_session)

    # Assertions
    docker_client.images.get.assert_called_once_with("test-image")
    db_session.commit.assert_called_once()
    assert image.state == ImageState.ready


@pytest.mark.asyncio
async def test_get_image_not_found_and_pulled(mocker, image):
    """Test case where the image is not found but pull is enabled."""
    # Mocks
    image.pull = True
    docker_client = Mock()
    docker_client.images.get = Mock(side_effect=ImageNotFound("tets-image"))
    mock_pull_image = mocker.patch("dr_emu.lib.util.pull_image", AsyncMock())
    db_session = AsyncMock()

    mocker.patch.object(db_session, "commit", AsyncMock())

    # Test function
    await get_image(docker_client, image, db_session)

    # Assertions
    docker_client.images.get.assert_called_once_with("test-image")
    mock_pull_image.assert_called_once_with(docker_client, "test-image")
    assert db_session.commit.call_count == 2
    assert image.state == ImageState.ready


@pytest.mark.asyncio
async def test_get_image_not_found_and_built(mocker, image):
    """Test case where the image is not found and built with services."""
    # Mocks
    docker_client = Mock()
    docker_client.images.get = Mock(side_effect=ImageNotFound("tets-image"))
    mock_build = mocker.patch("dr_emu.lib.util.cif.build", AsyncMock())
    mock_check_forbidden_services = mocker.patch(
        "cif.helpers.check_for_forbidden_services", return_value=[]
    )
    db_session = AsyncMock()

    mocker.patch.object(db_session, "commit", AsyncMock())

    # Test function
    await get_image(docker_client, image, db_session)

    # Assertions
    docker_client.images.get.assert_called_once_with(image.name)
    mock_check_forbidden_services.assert_called_once_with(["service1", "service2"])
    mock_build.assert_called_once_with(
        repository="cif",
        services=["service1", "service2"],
        variables={"key1": "value1", "key2": "value2"},
        actions=[],
        firehole_config="test_path",
        image_tag=image.name,
    )
    assert db_session.commit.call_count == 2
    assert image.state == ImageState.ready


@pytest.mark.asyncio
async def test_get_image_forbidden_services(mocker, image):
    """Test case where the image contains forbidden services."""
    # Mocks
    docker_client = Mock()
    docker_client.images.get = Mock(side_effect=ImageNotFound("tets-image"))
    mock_build = mocker.patch("dr_emu.lib.util.cif.build", AsyncMock())
    mock_check_forbidden_services = mocker.patch(
        "dr_emu.lib.util.cif.helpers.check_for_forbidden_services", return_value=["service2"]
    )
    db_session = AsyncMock()

    mocker.patch.object(db_session, "commit", AsyncMock())

    # Test function
    await get_image(docker_client, image, db_session)

    # Assertions
    docker_client.images.get.assert_called_once_with("test-image")
    mock_check_forbidden_services.assert_called_once_with(["service1", "service2"])
    mock_build.assert_called_once_with(
        repository="cif",
        services=["service1"],  # Excludes "service2"
        variables={"key1": "value1", "key2": "value2"},
        actions=[],
        firehole_config="test_path",
        image_tag=image.name,
    )
    assert db_session.commit.call_count == 2
    assert image.state == ImageState.ready

