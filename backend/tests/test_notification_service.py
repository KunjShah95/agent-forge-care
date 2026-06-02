import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.notification_service import create_notification
from tests.conftest import TEST_USER_ID


@pytest.mark.asyncio
async def test_create_notification_success(mock_db):
    with patch(
        "app.services.notification_service.MemoryService"
    ) as MockMemory:
        instance = MockMemory.return_value
        instance.set_memory = AsyncMock()

        await create_notification(mock_db, TEST_USER_ID, "Test Title", "Test body")

        instance.set_memory.assert_called_once()
        args = instance.set_memory.call_args
        assert args[0][0] == TEST_USER_ID
        assert args[0][1].startswith("notification:")
        value = args[0][2]
        assert value["title"] == "Test Title"
        assert value["body"] == "Test body"
        assert value["type"] == "info"
        assert value["read"] is False
        assert args[1]["weight"] == 1.0


@pytest.mark.asyncio
async def test_create_notification_with_email(mock_db):
    with patch(
        "app.services.notification_service.MemoryService"
    ) as MockMemory, patch(
        "app.services.email_service.send_email", new_callable=AsyncMock
    ) as mock_send:
        instance = MockMemory.return_value
        instance.set_memory = AsyncMock()

        await create_notification(
            mock_db, TEST_USER_ID, "Subject", "Body", to_email="user@test.com"
        )

        mock_send.assert_called_once_with(
            to_email="user@test.com", subject="Subject", body="Body"
        )


@pytest.mark.asyncio
async def test_create_notification_without_email(mock_db):
    with patch(
        "app.services.notification_service.MemoryService"
    ) as MockMemory, patch(
        "app.services.email_service.send_email", new_callable=AsyncMock
    ) as mock_send:
        instance = MockMemory.return_value
        instance.set_memory = AsyncMock()

        await create_notification(mock_db, TEST_USER_ID, "Title", "Body")

        mock_send.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("ntype", ["success", "error", "info"])
async def test_create_notification_types(mock_db, ntype):
    with patch(
        "app.services.notification_service.MemoryService"
    ) as MockMemory:
        instance = MockMemory.return_value
        instance.set_memory = AsyncMock()

        await create_notification(
            mock_db, TEST_USER_ID, "T", "B", type=ntype
        )

        value = instance.set_memory.call_args[0][2]
        assert value["type"] == ntype


@pytest.mark.asyncio
async def test_notification_stored_in_memory(mock_db):
    with patch(
        "app.services.notification_service.MemoryService"
    ) as MockMemory:
        instance = MockMemory.return_value
        instance.set_memory = AsyncMock()

        await create_notification(
            mock_db, TEST_USER_ID, "Offer Alert", "New match found", type="success"
        )

        call_args = instance.set_memory.call_args
        key = call_args[0][1]
        value = call_args[0][2]

        assert key.startswith("notification:")
        assert len(key) > len("notification:")
        assert set(value.keys()) == {"title", "body", "type", "read"}
        assert value["title"] == "Offer Alert"
        assert value["body"] == "New match found"
        assert value["type"] == "success"
        assert value["read"] is False
        assert call_args[1]["weight"] == 1.0
