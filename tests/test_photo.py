import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, Message, PhotoSize, Chat, User, File
from telegram.ext import ContextTypes

os.environ.setdefault("TESTING", "True")

from bot.telegram_router import handle_photo


@pytest.fixture
def mock_update_photo():
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 12345
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 67890
    update.message = MagicMock(spec=Message)
    photo = MagicMock(spec=PhotoSize)
    update.message.photo = [photo]
    return update


@pytest.fixture
def mock_context():
    return MagicMock(spec=ContextTypes.DEFAULT_TYPE)


@pytest.mark.asyncio
async def test_handle_photo_without_caption(mock_update_photo, mock_context):
    mock_update_photo.message.caption = None

    mock_file = MagicMock(spec=File)
    mock_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"img"))
    mock_update_photo.message.photo[-1].get_file = AsyncMock(return_value=mock_file)

    with patch("bot.telegram_router.ask_o3_with_image", new_callable=AsyncMock) as mock_ask, \
         patch("bot.telegram_router.safe_send_message", new_callable=AsyncMock) as mock_send, \
         patch("bot.telegram_router.add_message_with_timestamp") as mock_add:

        mock_ask.return_value = "desc"

        await handle_photo(mock_update_photo, mock_context)

        mock_ask.assert_called_once()
        mock_send.assert_called_once_with(mock_context, 12345, "desc")
        assert mock_add.call_count == 2


@pytest.mark.asyncio
async def test_handle_photo_with_caption(mock_update_photo, mock_context):
    mock_update_photo.message.caption = "Is it a cat?"

    mock_file = MagicMock(spec=File)
    mock_file.download_as_bytearray = AsyncMock(return_value=bytearray(b"img"))
    mock_update_photo.message.photo[-1].get_file = AsyncMock(return_value=mock_file)

    with patch("bot.telegram_router.ask_o3_with_image", new_callable=AsyncMock) as mock_ask, \
         patch("bot.telegram_router.safe_send_message", new_callable=AsyncMock) as mock_send:

        mock_ask.return_value = "sure"

        await handle_photo(mock_update_photo, mock_context)

        mock_ask.assert_called_once_with(b"img", "Is it a cat?")
        mock_send.assert_called_once_with(mock_context, 12345, "sure")


@pytest.mark.asyncio
async def test_handle_photo_size_limits(mock_update_photo, mock_context):
    mock_update_photo.message.caption = None

    # 10 MB image should be processed
    img_small = bytearray(b"a" * 10 * 1024 * 1024)
    mock_file_small = MagicMock(spec=File)
    mock_file_small.download_as_bytearray = AsyncMock(return_value=img_small)
    mock_update_photo.message.photo[-1].get_file = AsyncMock(return_value=mock_file_small)

    with patch("bot.telegram_router.ask_o3_with_image", new_callable=AsyncMock) as mock_ask, \
         patch("bot.telegram_router.safe_send_message", new_callable=AsyncMock) as mock_send:

        mock_ask.return_value = "ok"
        await handle_photo(mock_update_photo, mock_context)
        mock_ask.assert_called_once()
        mock_send.assert_called_once_with(mock_context, 12345, "ok")

    # >20 MB image should be rejected
    img_large = bytearray(b"b" * 21 * 1024 * 1024)
    mock_file_large = MagicMock(spec=File)
    mock_file_large.download_as_bytearray = AsyncMock(return_value=img_large)
    mock_update_photo.message.photo[-1].get_file = AsyncMock(return_value=mock_file_large)

    with patch("bot.telegram_router.ask_o3_with_image", new_callable=AsyncMock) as mock_ask, \
         patch("bot.telegram_router.safe_send_message", new_callable=AsyncMock) as mock_send:

        await handle_photo(mock_update_photo, mock_context)
        mock_ask.assert_not_called()
        mock_send.assert_called_once()

