from pathlib import PosixPath, Path

import pytest
from unittest.mock import AsyncMock, patch, Mock, MagicMock
import docker.errors
from pytest_mock import MockerFixture
from dr_emu.lib.util import pull_image, get_image, build_cif_image  # Adjust the import based on your module structure
from dr_emu.models import ImageState
from docker.errors import ImageNotFound


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
    image = Mock(state=ImageState.initialized, pull=False, services=services, data=[], packages=[])
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
async def test_build_cif_image_not_found_and_built(mocker, image):
    """Test case where the image is not found and built with services."""
    # Mocks
    docker_client = Mock()
    docker_client.images.get = Mock(side_effect=ImageNotFound("tets-image"))
    mock_build = mocker.patch("dr_emu.lib.util.build_cif_image", AsyncMock())
    db_session = AsyncMock()

    mocker.patch.object(db_session, "commit", AsyncMock())

    # Test function
    await get_image(docker_client, image, db_session)

    # Assertions
    docker_client.images.get.assert_called_once_with(image.name)
    mock_build.assert_called_once()
    assert db_session.commit.call_count == 2
    assert image.state == ImageState.ready


@pytest.mark.asyncio
async def test_build_cif_image(mocker, image):
    mock_build = mocker.patch("dr_emu.lib.util.cif.build")
    mock_new_path = MagicMock()
    mocker.patch("dr_emu.lib.util.uuid1", return_value="test_uuid")
    mocker.patch("dr_emu.lib.util.cif.helpers.check_for_forbidden_services", return_value=[])
    mocker.patch.object(mock_new_path, "exists", return_value=True)
    data_path_mock =mocker.patch("dr_emu.lib.util.constants.cif_tmp_data_path")
    data_path_mock.__truediv__.return_value = mock_new_path


    image.data = [
        Mock(contents="file_contents_1", image_file_path="path/to/file1"),
    ]

    # Act
    await build_cif_image(image)

    # Check if cif.build was called with correct arguments
    mock_build.assert_called_once_with(
        services=["service1", "service2"],
        variables={"key1": "value1", "key2": "value2"},
        actions=[('create-user', {})],
        final_tag="test-image",
        files=[(mock_new_path, 'path/to/file1', None, None, None)],  # Can assert specific file details if needed
        packages=[],
        clean_up=True
        )

    # Check that file.write_text was called for each file
    mock_new_path.write_text.assert_called_once_with("file_contents_1")

    # Ensure file unlinking happens
    assert mock_new_path.unlink.call_count == 1  # There are two files being processed


