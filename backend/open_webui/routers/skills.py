import logging
import re
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL
from open_webui.constants import ERROR_MESSAGES
from open_webui.events import EVENTS, publish_event
from open_webui.internal.db import get_async_session
from open_webui.models.access_grants import AccessGrants
from open_webui.models.config import Config
from open_webui.models.groups import Groups
from open_webui.models.skills import (
    SkillAccessListResponse,
    SkillAccessResponse,
    SkillForm,
    SkillModel,
    SkillResponse,
    Skills,
    SkillUserModel,
    SkillUserResponse,
)
from open_webui.utils.access_control import filter_allowed_access_grants, has_permission
from open_webui.utils.auth import get_admin_user, get_verified_user
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)

PAGE_ITEM_COUNT = 30

router = APIRouter()


############################
# CHOn (T12): team skills sharing rules
############################

PUBLIC_READ_GRANT = {'principal_type': 'user', 'principal_id': '*', 'permission': 'read'}


def _is_public_grant(grant) -> bool:
    g = grant if isinstance(grant, dict) else grant.model_dump()
    return g.get('principal_type') == 'user' and g.get('principal_id') == '*'


async def chon_filter_skill_grants(user, access_grants, existing_grants=None, db=None):
    """Grants a non-admin may set on a skill.

    - Same public/user/group filtering as upstream (sharing.public_skills etc.).
    - Enforce `sharing.skills` on the server too (upstream only hid the UI):
      without it a user can keep a skill to themselves only.
    - Keep a company-wide ("Everyone") grant that the CHOn team already
      approved, so editing team sharing does not silently remove it.
    """
    permissions = await Config.get('user.permissions')
    grants = await filter_allowed_access_grants(
        permissions, user.id, user.role, access_grants, 'sharing.public_skills'
    )
    if user.role == 'admin':
        return grants

    if not await has_permission(user.id, 'sharing.skills', permissions, db=db):
        grants = []

    grants = list(grants or [])
    for grant in existing_grants or []:
        if _is_public_grant(grant) and not any(_is_public_grant(g) for g in grants):
            g = grant if isinstance(grant, dict) else grant.model_dump()
            grants.append(
                {
                    'principal_type': g['principal_type'],
                    'principal_id': g['principal_id'],
                    'permission': g['permission'],
                }
            )
    return grants


def _skill_meta_dict(skill) -> dict:
    meta = skill.meta
    return meta.model_dump() if hasattr(meta, 'model_dump') else dict(meta or {})


############################
# GetSkills
############################


@router.get('/', response_model=list[SkillUserResponse])
async def get_skills(
    request: Request,
    query: Optional[str] = None,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if user.role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL:
        skills = await Skills.get_skills(db=db)
    else:
        skills = await Skills.get_skills(db=db, user_id=user.id)

    if query:
        q = query.casefold()
        skills = [skill for skill in skills if q in (skill.name or '').casefold()]

    return skills


############################
# GetSkillList
############################


@router.get('/list', response_model=SkillAccessListResponse)
async def get_skill_list(
    query: Optional[str] = None,
    view_option: Optional[str] = None,
    order_by: Optional[str] = None,
    direction: Optional[str] = None,
    page: Optional[int] = 1,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    limit = PAGE_ITEM_COUNT

    page = max(1, page)
    skip = (page - 1) * limit

    filter = {}
    if query:
        filter['query'] = query
    if view_option:
        filter['view_option'] = view_option
    if order_by:
        filter['order_by'] = order_by
    if direction:
        filter['direction'] = direction

    is_bypass_admin = user.role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL
    user_group_ids = {group.id for group in await Groups.get_groups_by_member_id(user.id, db=db)}

    if not is_bypass_admin:
        filter['group_ids'] = user_group_ids
        filter['user_id'] = user.id

    result = await Skills.search_skills(user.id, filter=filter, skip=skip, limit=limit, db=db)

    writable_skill_ids = await AccessGrants.get_accessible_resource_ids(
        user_id=user.id,
        resource_type='skill',
        resource_ids=[skill.id for skill in result.items],
        permission='write',
        user_group_ids=user_group_ids,
        db=db,
    )

    return SkillAccessListResponse(
        items=[
            SkillAccessResponse(
                **skill.model_dump(),
                write_access=(is_bypass_admin or user.id == skill.user_id or skill.id in writable_skill_ids),
            )
            for skill in result.items
        ],
        total=result.total,
    )


############################
# ExportSkills
############################


@router.get('/export', response_model=list[SkillModel])
async def export_skills(
    request: Request,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if user.role != 'admin' and not await has_permission(
        user.id,
        'workspace.skills_export',
        await Config.get('user.permissions'),
        db=db,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    if user.role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL:
        return await Skills.get_skills(db=db)
    else:
        return await Skills.get_skills(db=db, user_id=user.id)


############################
# CreateNewSkill
############################


@router.post('/create', response_model=Optional[SkillResponse])
async def create_new_skill(
    request: Request,
    form_data: SkillForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if user.role != 'admin' and not (
        await has_permission(user.id, 'workspace.skills', await Config.get('user.permissions'), db=db)
        or await has_permission(user.id, 'workspace.skills_import', await Config.get('user.permissions'), db=db)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    form_data.id = form_data.id.lower().replace(' ', '-')

    # The id goes into /id/{id}/... paths, so anything outside the slug charset is unreachable once stored.
    if not re.fullmatch(r'[a-z0-9_-]+', form_data.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT('Invalid skill ID'),
        )

    existing = await Skills.get_skill_by_id(form_data.id, db=db)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ID_TAKEN,
        )

    # Strip public/user grants the requesting user is not permitted to assign
    # (matches the channel/notes/calendar pattern). Without this, a user with
    # workspace.skills permission could attach principal_id='*' read/write
    # grants in the create payload, bypassing the sharing.public_skills gate
    # that the dedicated /access/update endpoint already enforces.
    form_data.access_grants = await chon_filter_skill_grants(user, form_data.access_grants, db=db)

    # CHOn (T12): skill names are unique company-wide; say so instead of a DB error.
    if await Skills.get_skill_by_name(form_data.name, db=db):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'A skill named "{form_data.name}" already exists. Choose a different name.',
        )

    # The approval state is managed by the server only.
    if form_data.meta is not None and hasattr(form_data.meta, 'public_request'):
        delattr(form_data.meta, 'public_request')

    try:
        skill = await Skills.insert_new_skill(user.id, form_data, db=db)
        if skill:
            await publish_event(
                request,
                EVENTS.SKILL_CREATED,
                actor=user,
                subject_id=skill.id,
                data={'name': skill.name},
            )
            return skill
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Error creating skill'),
            )
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f'Failed to create skill: {e}')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e, 'Error creating skill'),
        )


############################
# GetSkillById
############################


@router.get('/id/{id}', response_model=Optional[SkillAccessResponse])
async def get_skill_by_id(id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)):
    skill = await Skills.get_skill_by_id(id, db=db)

    if skill:
        if (
            user.role == 'admin'
            or skill.user_id == user.id
            or await AccessGrants.has_access(
                user_id=user.id,
                resource_type='skill',
                resource_id=skill.id,
                permission='read',
                db=db,
            )
        ):
            return SkillAccessResponse(
                **skill.model_dump(),
                write_access=(
                    (user.role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL)
                    or user.id == skill.user_id
                    or await AccessGrants.has_access(
                        user_id=user.id,
                        resource_type='skill',
                        resource_id=skill.id,
                        permission='write',
                        db=db,
                    )
                ),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# UpdateSkillById
############################


@router.post('/id/{id}/update', response_model=Optional[SkillModel])
async def update_skill_by_id(
    request: Request,
    id: str,
    form_data: SkillForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    skill = await Skills.get_skill_by_id(id, db=db)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        skill.user_id != user.id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='skill',
            resource_id=skill.id,
            permission='write',
            db=db,
        )
        and user.role != 'admin'
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    # Strip public/user grants the requesting user is not permitted to assign
    # (matches the channel/notes/calendar pattern). The access check above only
    # restricts WHO can write to the skill; this filter restricts WHICH grants
    # they may set, so a non-admin owner cannot make their own skill publicly
    # readable/writable without sharing.public_skills permission.
    form_data.access_grants = await chon_filter_skill_grants(
        user, form_data.access_grants, skill.access_grants, db=db
    )

    if form_data.name != skill.name:
        other = await Skills.get_skill_by_name(form_data.name, db=db)
        if other and other.id != skill.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'A skill named "{form_data.name}" already exists. Choose a different name.',
            )

    try:
        updated = {
            **form_data.model_dump(exclude={'id'}),
        }
        # CHOn (T12): the company-wide sharing request is server-owned state
        meta = dict(updated.get('meta') or {})
        meta.pop('public_request', None)
        existing_request = _skill_meta_dict(skill).get('public_request')
        if existing_request:
            meta['public_request'] = existing_request
        updated['meta'] = meta

        skill = await Skills.update_skill_by_id(id, updated, db=db)

        if skill:
            await publish_event(
                request,
                EVENTS.SKILL_UPDATED,
                actor=user,
                subject_id=skill.id,
                data={'name': skill.name},
            )
            return skill
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Error updating skill'),
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e, 'Error updating skill'),
        )


############################
# UpdateSkillAccessById
############################


class SkillAccessGrantsForm(BaseModel):
    access_grants: list[dict]


@router.post('/id/{id}/access/update', response_model=Optional[SkillModel])
async def update_skill_access_by_id(
    request: Request,
    id: str,
    form_data: SkillAccessGrantsForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    skill = await Skills.get_skill_by_id(id, db=db)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        skill.user_id != user.id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='skill',
            resource_id=skill.id,
            permission='write',
            db=db,
        )
        and user.role != 'admin'
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    form_data.access_grants = await chon_filter_skill_grants(
        user, form_data.access_grants, skill.access_grants, db=db
    )

    await AccessGrants.set_access_grants('skill', id, form_data.access_grants, db=db)

    skill = await Skills.get_skill_by_id(id, db=db)
    await publish_event(
        request,
        EVENTS.SKILL_UPDATED,
        actor=user,
        subject_id=id,
        data={'access_updated': True, 'name': skill.name if skill else None},
    )
    return skill


############################
# ToggleSkillById
############################


@router.post('/id/{id}/toggle', response_model=Optional[SkillModel])
async def toggle_skill_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    skill = await Skills.get_skill_by_id(id, db=db)
    if skill:
        if (
            user.role == 'admin'
            or skill.user_id == user.id
            or await AccessGrants.has_access(
                user_id=user.id,
                resource_type='skill',
                resource_id=skill.id,
                permission='write',
                db=db,
            )
        ):
            skill = await Skills.toggle_skill_by_id(id, db=db)

            if skill:
                await publish_event(
                    request,
                    EVENTS.SKILL_ENABLED if skill.is_active else EVENTS.SKILL_DISABLED,
                    actor=user,
                    subject_id=skill.id,
                    data={'name': skill.name},
                )
                return skill
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT('Error toggling skill'),
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES.UNAUTHORIZED,
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# DeleteSkillById
############################


@router.delete('/id/{id}/delete', response_model=bool)
async def delete_skill_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    skill = await Skills.get_skill_by_id(id, db=db)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        skill.user_id != user.id
        and not await AccessGrants.has_access(
            user_id=user.id,
            resource_type='skill',
            resource_id=skill.id,
            permission='write',
            db=db,
        )
        and user.role != 'admin'
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    result = await Skills.delete_skill_by_id(id, db=db)
    if result:
        await publish_event(
            request,
            EVENTS.SKILL_DELETED,
            actor=user,
            subject_id=id,
            data={'name': skill.name},
        )
    return result


############################
# CHOn (T12): company-wide sharing requests
# A user asks the CHOn team to share a skill with everyone at Weidmann;
# admins approve (adds a read grant for everyone) or decline.
############################


class PublicRequestDecisionForm(BaseModel):
    note: Optional[str] = None


async def _get_skill_for_owner(id: str, user, db):
    skill = await Skills.get_skill_by_id(id, db=db)
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)
    if (
        skill.user_id != user.id
        and user.role != 'admin'
        and not await AccessGrants.has_access(
            user_id=user.id, resource_type='skill', resource_id=skill.id, permission='write', db=db
        )
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.UNAUTHORIZED)
    return skill


async def _set_public_request(id: str, public_request, db):
    skill = await Skills.get_skill_by_id(id, db=db)
    meta = _skill_meta_dict(skill)
    if public_request is None:
        meta.pop('public_request', None)
    else:
        meta['public_request'] = public_request
    return await Skills.update_skill_by_id(id, {'meta': meta}, db=db)


@router.post('/id/{id}/public/request', response_model=Optional[SkillModel])
async def request_public_skill(
    request: Request, id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    skill = await _get_skill_for_owner(id, user, db)
    if any(_is_public_grant(g) for g in skill.access_grants):
        raise HTTPException(status_code=400, detail='This skill is already shared with everyone at Weidmann.')

    permissions = await Config.get('user.permissions')
    if user.role != 'admin' and not await has_permission(user.id, 'sharing.skills', permissions, db=db):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.UNAUTHORIZED)

    updated = await _set_public_request(
        id,
        {
            'status': 'pending',
            'requested_by': user.id,
            'requested_by_name': user.name,
            'requested_at': int(time.time()),
        },
        db,
    )
    await publish_event(
        request,
        EVENTS.SKILL_UPDATED,
        actor=user,
        subject_id=id,
        data={'name': skill.name, 'public_request': 'pending'},
    )
    return updated


@router.post('/id/{id}/public/cancel', response_model=Optional[SkillModel])
async def cancel_public_skill_request(
    id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    await _get_skill_for_owner(id, user, db)
    return await _set_public_request(id, None, db)


@router.get('/public/requests', response_model=list[SkillUserModel])
async def get_public_skill_requests(user=Depends(get_admin_user), db: AsyncSession = Depends(get_async_session)):
    skills = await Skills.get_skills(db=db)
    return [s for s in skills if (_skill_meta_dict(s).get('public_request') or {}).get('status') == 'pending']


async def _decide_public_request(request, id, decision, note, user, db):
    skill = await Skills.get_skill_by_id(id, db=db)
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if decision == 'approved':
        grants = [
            {'principal_type': g.principal_type, 'principal_id': g.principal_id, 'permission': g.permission}
            for g in skill.access_grants
            if not _is_public_grant(g)
        ]
        grants.append(dict(PUBLIC_READ_GRANT))
        await AccessGrants.set_access_grants('skill', id, grants, db=db)

    previous = _skill_meta_dict(skill).get('public_request') or {}
    updated = await _set_public_request(
        id,
        {
            **previous,
            'status': decision,
            'decided_by': user.id,
            'decided_by_name': user.name,
            'decided_at': int(time.time()),
            'note': note or None,
        },
        db,
    )
    await publish_event(
        request,
        EVENTS.SKILL_UPDATED,
        actor=user,
        subject_id=id,
        data={'name': skill.name, 'public_request': decision, 'access_updated': decision == 'approved'},
    )
    return updated


@router.post('/id/{id}/public/approve', response_model=Optional[SkillModel])
async def approve_public_skill(
    request: Request,
    id: str,
    form_data: Optional[PublicRequestDecisionForm] = None,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await _decide_public_request(request, id, 'approved', form_data.note if form_data else None, user, db)


@router.post('/id/{id}/public/decline', response_model=Optional[SkillModel])
async def decline_public_skill(
    request: Request,
    id: str,
    form_data: Optional[PublicRequestDecisionForm] = None,
    user=Depends(get_admin_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await _decide_public_request(request, id, 'declined', form_data.note if form_data else None, user, db)
