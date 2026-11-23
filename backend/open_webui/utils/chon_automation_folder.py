"""CHOn: put chats created by automations into an "Automations" folder.

When an automation runs without a folder chosen by the user, its chat goes into
the owner's "Automations" folder. The folder is created on first use. It is
found by a marker in its meta (so renaming it keeps it working), with a
fallback to a top-level folder named "Automations".

When the folder is created, the owner's existing automation chats that are
not in any folder are moved into it, so all automation results sit together.
A folder chosen explicitly on an automation is always respected.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from open_webui.models.chats import Chats
from open_webui.models.folders import FolderForm, Folders

log = logging.getLogger(__name__)

FOLDER_NAME = 'Automations'
FOLDER_MARKER = 'chon_automations'

# One lock per user so two automations finishing together create one folder.
_locks: dict[str, asyncio.Lock] = {}


def _is_marked(folder) -> bool:
    meta = getattr(folder, 'meta', None) or {}
    return bool(isinstance(meta, dict) and meta.get(FOLDER_MARKER))


async def _find_folder(user_id: str):
    for folder in await Folders.get_folders_by_user_id(user_id):
        if _is_marked(folder):
            return folder
    return await Folders.get_folder_by_parent_id_and_user_id_and_name(None, user_id, FOLDER_NAME)


def _is_automation_chat(chat) -> bool:
    body = getattr(chat, 'chat', None) or {}
    meta = body.get('meta') if isinstance(body, dict) else None
    return bool(isinstance(meta, dict) and meta.get('automation_id'))


async def _move_existing_automation_chats(user_id: str, folder_id: str) -> int:
    moved = 0
    try:
        chats = await Chats.get_chats_by_user_id(user_id)
        for chat in chats.items:
            if chat.folder_id is None and _is_automation_chat(chat):
                if await Chats.update_chat_folder_id_by_id_and_user_id(chat.id, user_id, folder_id):
                    moved += 1
    except Exception as e:
        log.warning('Could not move existing automation chats for %s: %s', user_id, e)
    return moved


async def ensure_automations_folder(user_id: str) -> tuple[Optional[str], bool]:
    """(folder id, created now). Creates the folder if needed; (None, False) on failure."""
    lock = _locks.setdefault(user_id, asyncio.Lock())
    async with lock:
        try:
            folder = await _find_folder(user_id)
            if folder:
                return folder.id, False

            folder = await Folders.insert_new_folder(
                user_id,
                FolderForm(name=FOLDER_NAME, meta={FOLDER_MARKER: True}),
            )
            if not folder:
                return None, False

            moved = await _move_existing_automation_chats(user_id, folder.id)
            log.info('Created Automations folder for %s, moved %d existing chat(s)', user_id, moved)
            return folder.id, True
        except Exception as e:
            # Never fail an automation because of the folder.
            log.warning('Automations folder unavailable for %s: %s', user_id, e)
            return None, False


async def get_or_create_automations_folder_id(user_id: str) -> Optional[str]:
    """Id of the user's Automations folder, creating it if needed. None on failure."""
    folder_id, _ = await ensure_automations_folder(user_id)
    return folder_id


async def notify_folders_changed(user_id: str) -> None:
    """Tell the user's open sessions to reload the sidebar (folders included)."""
    try:
        from open_webui.socket.main import sio

        await sio.emit('events', {'chat_id': None, 'data': {'type': 'chat:list'}}, room=f'user:{user_id}')
    except Exception as e:
        log.debug('Could not notify sidebar refresh for %s: %s', user_id, e)


async def assign_default_folder(form_data, user_id: str) -> None:
    """Automation create/update: no folder and not a channel -> the Automations folder."""
    target = getattr(form_data.data, 'target', None)
    target_type = getattr(target, 'type', None) if target is not None else None
    if target_type == 'channel' or form_data.folder_id:
        return
    folder_id, created = await ensure_automations_folder(user_id)
    if folder_id:
        form_data.folder_id = folder_id
        if created:
            await notify_folders_changed(user_id)
