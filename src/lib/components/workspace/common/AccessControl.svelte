<script lang="ts">
	import { getContext, onMount } from 'svelte';

	const i18n = getContext('i18n');

	import { getGroups, getGroupById, getGroupInfoById } from '$lib/apis/groups';
	import { getUserInfoById, searchUsers } from '$lib/apis/users';
	import { user as sessionUser } from '$lib/stores';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Switch from '$lib/components/common/Switch.svelte';

	type AccessGrant = {
		id?: string;
		principal_type: 'user' | 'group' | 'anyone';
		principal_id: string;
		permission: 'read' | 'write';
	};

	type LegacyAccessControl = {
		read: { group_ids: string[]; user_ids: string[] };
		write: { group_ids: string[]; user_ids: string[] };
	};

	export let onChange: Function = () => {};

	export let accessRoles = ['read'];
	export let accessGrants: AccessGrant[] | any = [];
	export let accessControl: any = undefined;

	export let share = true;
	export let sharePublic = true;
	export let shareOpen = false;
	export let shareUsers = true;
	export let allowGroups = true;
	export let defaultPermission: 'read' | 'write' = 'read';

	let groups: any[] = [];
	const resolvingGroupIds = new Set<string>();
	let userById: Record<string, any> = {};
	const resolvingUserIds = new Set<string>();


	const dedupeAccessGrants = (grants: AccessGrant[] | null | undefined): AccessGrant[] => {
		if (!Array.isArray(grants)) return [];
		const map = new Map<string, AccessGrant>();
		for (const grant of grants) {
			if (!grant) continue;
			const key = `${grant.principal_type}:${grant.principal_id}:${grant.permission}`;
			if (!grant.principal_type || !grant.principal_id || !grant.permission) continue;
			map.set(key, {
				id: grant.id,
				principal_type: grant.principal_type,
				principal_id: grant.principal_id,
				permission: grant.permission
			});
		}
		return Array.from(map.values());
	};

	const legacyAccessControlToGrants = (accessControl: any): AccessGrant[] => {
		if (accessControl === null) {
			return [
				{
					principal_type: 'user',
					principal_id: '*',
					permission: 'read'
				}
			];
		}

		if (!accessControl || typeof accessControl !== 'object') {
			return [];
		}

		const grants: AccessGrant[] = [];
		for (const permission of ['read', 'write'] as const) {
			const entry = accessControl?.[permission] ?? {};
			for (const groupId of entry?.group_ids ?? []) {
				grants.push({
					principal_type: 'group',
					principal_id: groupId,
					permission
				});
			}
			for (const userId of entry?.user_ids ?? []) {
				grants.push({
					principal_type: 'user',
					principal_id: userId,
					permission
				});
			}
		}

		return dedupeAccessGrants(grants);
	};

	const grantsToLegacyAccessControl = (grants: AccessGrant[]): null | LegacyAccessControl => {
		const normalized = dedupeAccessGrants(grants);
		if (hasPublicReadGrant(normalized)) {
			return null;
		}

		const result: LegacyAccessControl = {
			read: { group_ids: [], user_ids: [] },
			write: { group_ids: [], user_ids: [] }
		};

		for (const grant of normalized) {
			if (!['read', 'write'].includes(grant.permission)) {
				continue;
			}

			if (grant.principal_type === 'group') {
				if (!result[grant.permission].group_ids.includes(grant.principal_id)) {
					result[grant.permission].group_ids = [
						...result[grant.permission].group_ids,
						grant.principal_id
					];
				}
			} else if (grant.principal_type === 'user' && grant.principal_id !== '*') {
				if (!result[grant.permission].user_ids.includes(grant.principal_id)) {
					result[grant.permission].user_ids = [
						...result[grant.permission].user_ids,
						grant.principal_id
					];
				}
			}
		}

		return result;
	};

	const normalizeInputToGrants = (value: any): AccessGrant[] => {
		if (value === null) {
			return legacyAccessControlToGrants(null);
		}
		if (Array.isArray(value)) {
			return dedupeAccessGrants(value);
		}
		if (value && typeof value === 'object' && ('read' in value || 'write' in value)) {
			return legacyAccessControlToGrants(value);
		}
		return [];
	};

	const stableStringify = (value: any): string => {
		try {
			return JSON.stringify(value ?? null);
		} catch {
			return '';
		}
	};

	const hasPublicReadGrant = (grants: AccessGrant[]): boolean =>
		grants.some(
			(grant) =>
				grant.principal_type === 'user' && grant.principal_id === '*' && grant.permission === 'read'
		);

	const hasAnyoneReadGrant = (grants: AccessGrant[]): boolean =>
		grants.some(
			(grant) =>
				grant.principal_type === 'anyone' &&
				grant.principal_id === '*' &&
				grant.permission === 'read'
		);

	const hasPublicWriteGrant = (grants: AccessGrant[]): boolean =>
		grants.some(
			(grant) =>
				grant.principal_type === 'user' &&
				grant.principal_id === '*' &&
				grant.permission === 'write'
		);

	const currentGrants = (grants: AccessGrant[] | any = accessGrants): AccessGrant[] =>
		Array.isArray(grants) ? (grants as AccessGrant[]) : [];

	const getPrincipalIdsByPermission = (
		principalType: 'user' | 'group',
		permission: 'read' | 'write',
		grants: AccessGrant[] | any = accessGrants
	): string[] =>
		Array.from(
			new Set(
				currentGrants(grants)
					.filter(
						(grant) => grant.principal_type === principalType && grant.permission === permission
					)
					.map((grant) => grant.principal_id)
			)
		);

	const hasPrincipalGrant = (
		principalType: 'user' | 'group' | 'anyone',
		principalId: string,
		permission: 'read' | 'write'
	): boolean =>
		currentGrants().some(
			(grant) =>
				grant.principal_type === principalType &&
				grant.principal_id === principalId &&
				grant.permission === permission
		);

	const commitAccessGrants = (nextGrants: AccessGrant[]) => {
		accessGrants = dedupeAccessGrants(nextGrants);
		onChange(accessGrants);
	};

	const getVisibility = (grants: AccessGrant[]): 'private' | 'public' | 'open' => {
		if (hasAnyoneReadGrant(grants)) return 'open';
		if (hasPublicReadGrant(grants)) return 'public';
		return 'private';
	};

	const setVisibility = (visibility: 'private' | 'public' | 'open') => {
		const filtered = currentGrants().filter(
			(grant) =>
				!(
					(grant.principal_type === 'user' || grant.principal_type === 'anyone') &&
					grant.principal_id === '*'
				)
		);
		if (visibility === 'public') {
			filtered.push({
				principal_type: 'user',
				principal_id: '*',
				permission: 'read'
			});
		} else if (visibility === 'open') {
			filtered.push({
				principal_type: 'anyone',
				principal_id: '*',
				permission: 'read'
			});
		}
		commitAccessGrants(filtered);
	};

	const togglePublicWrite = () => {
		let next = [...currentGrants()];
		if (hasPublicWriteGrant(next)) {
			next = next.filter(
				(grant) =>
					!(
						grant.principal_type === 'user' &&
						grant.principal_id === '*' &&
						grant.permission === 'write'
					)
			);
		} else {
			next = upsertPrincipalGrant('user', '*', 'write', next);
		}
		commitAccessGrants(next);
	};

	const upsertPrincipalGrant = (
		principalType: 'user' | 'group' | 'anyone',
		principalId: string,
		permission: 'read' | 'write',
		grants: AccessGrant[]
	): AccessGrant[] => {
		if (
			grants.some(
				(grant) =>
					grant.principal_type === principalType &&
					grant.principal_id === principalId &&
					grant.permission === permission
			)
		) {
			return grants;
		}
		return [
			...grants,
			{
				principal_type: principalType,
				principal_id: principalId,
				permission
			}
		];
	};

	const removePrincipalGrant = (
		principalType: 'user' | 'group' | 'anyone',
		principalId: string,
		permission: 'read' | 'write',
		grants: AccessGrant[]
	): AccessGrant[] =>
		grants.filter(
			(grant) =>
				!(
					grant.principal_type === principalType &&
					grant.principal_id === principalId &&
					grant.permission === permission
				)
		);

	const removePrincipal = (principalType: 'user' | 'group' | 'anyone', principalId: string) => {
		let next = [...currentGrants()];
		next = removePrincipalGrant(principalType, principalId, 'read', next);
		next = removePrincipalGrant(principalType, principalId, 'write', next);
		commitAccessGrants(next);
	};

	const togglePrincipalWrite = (
		principalType: 'user' | 'group' | 'anyone',
		principalId: string
	) => {
		let next = [...currentGrants()];
		const hasWrite = hasPrincipalGrant(principalType, principalId, 'write');
		if (hasWrite) {
			next = removePrincipalGrant(principalType, principalId, 'write', next);
		} else {
			next = upsertPrincipalGrant(principalType, principalId, 'read', next);
			next = upsertPrincipalGrant(principalType, principalId, 'write', next);
		}
		commitAccessGrants(next);
	};

	const ensureUsersByIds = async (userIds: string[]) => {
		const pendingIds = userIds.filter((id) => !userById[id] && !resolvingUserIds.has(id));
		if (!pendingIds.length) return;

		for (const id of pendingIds) {
			resolvingUserIds.add(id);
		}

		const fetched = await Promise.all(
			pendingIds.map(async (id) => {
				const user = await getUserInfoById(localStorage.token, id).catch((error) => {
					console.error(error);
					return null;
				});
				return { id, user };
			})
		);

		const nextUserById = { ...userById };
		for (const item of fetched) {
			if (item.user?.id) {
				nextUserById[item.id] = item.user;
			}
			resolvingUserIds.delete(item.id);
		}
		userById = nextUserById;
	};

	const handleAddAccess = ({ userIds, groupIds }: { userIds: string[]; groupIds: string[] }) => {
		let next = [...currentGrants()];

		for (const groupId of groupIds) {
			if (defaultPermission === 'write') {
				next = upsertPrincipalGrant('group', groupId, 'read', next);
			}
			next = upsertPrincipalGrant('group', groupId, defaultPermission, next);
		}
		for (const userId of userIds) {
			if (defaultPermission === 'write') {
				next = upsertPrincipalGrant('user', userId, 'read', next);
			}
			next = upsertPrincipalGrant('user', userId, defaultPermission, next);
		}
		commitAccessGrants(next);
	};

	// NOTE: We must reference `accessGrants` directly in each reactive
	// expression so Svelte tracks the dependency.
	const ensureGroupsByIds = async (groupIds: string[]) => {
		const pendingIds = groupIds.filter(
			(id) => !groups.find((g) => g.id === id) && !resolvingGroupIds.has(id)
		);
		if (!pendingIds.length) return;

		for (const id of pendingIds) {
			resolvingGroupIds.add(id);
		}

		const fetched = await Promise.all(
			pendingIds.map(async (id) => {
				const group = await getGroupInfoById(localStorage.token, id).catch((error) => {
					console.error(error);
					return null;
				});
				return group;
			})
		);

		const newGroups = fetched.filter((g) => g);
		if (newGroups.length > 0) {
			groups = [...groups, ...newGroups].filter(
				(g, index, self) => index === self.findIndex((t) => t.id === g.id)
			);
		}

		for (const id of pendingIds) {
			resolvingGroupIds.delete(id);
		}
	};

	$: if (readGroupIds.length > 0 || writeGroupIds.length > 0) {
		void ensureGroupsByIds([...readGroupIds, ...writeGroupIds]);
	}
	$: readGroupIds = getPrincipalIdsByPermission('group', 'read', accessGrants);
	$: writeGroupIds = getPrincipalIdsByPermission('group', 'write', accessGrants);
	$: readUserIds = getPrincipalIdsByPermission('user', 'read', accessGrants).filter(
		(id) => id !== '*'
	);
	$: writeUserIds = getPrincipalIdsByPermission('user', 'write', accessGrants).filter(
		(id) => id !== '*'
	);

	$: selectedUserIds = Array.from(new Set([...readUserIds, ...writeUserIds]));

	$: selectedUsers = selectedUserIds
		.map((id) => {
			return userById[id] ?? { id, name: id, email: '' };
		})
		.sort((a, b) => a.name.localeCompare(b.name));

	$: accessGroups = groups
		.filter((group) => readGroupIds.includes(group.id) || writeGroupIds.includes(group.id))
		.sort((a, b) => a.name.localeCompare(b.name));

	$: if (selectedUserIds.length > 0) {
		void ensureUsersByIds(selectedUserIds);
	}

	$: {
		if (accessControl !== undefined) {
			const normalizedGrants = normalizeInputToGrants(accessControl);
			if (stableStringify(normalizedGrants) !== stableStringify(accessGrants)) {
				accessGrants = normalizedGrants;
			}
		}
	}

	$: {
		const normalizedGrants = normalizeInputToGrants(accessGrants);
		if (stableStringify(normalizedGrants) !== stableStringify(accessGrants)) {
			accessGrants = normalizedGrants;
		}

		if (accessControl !== undefined) {
			const nextAccessControl = grantsToLegacyAccessControl(normalizedGrants);
			if (stableStringify(nextAccessControl) !== stableStringify(accessControl)) {
				accessControl = nextAccessControl;
			}
		}
	}

	onMount(async () => {
		const res = await getGroups(localStorage.token, true).catch((error) => {
			console.error(error);
			return [];
		});

		groups = [...groups, ...res].filter(
			(g, index, self) => index === self.findIndex((t) => t.id === g.id)
		);
	});

	// ---- CHOn share layout ---------------------------------------------------------------
	// Three levels: Only me / Specific persons / Everyone at Weidmann
	// (+ "Anyone with the link" where Open WebUI allows it).
	type Level = 'only_me' | 'specific' | 'everyone' | 'link';

	const ORG_NAME = 'Weidmann';
	const roleSelectClass =
		'shrink-0 cursor-pointer rounded-lg border border-gray-300 bg-white px-2 py-1 text-xs outline-hidden focus:border-gray-500 dark:border-gray-700 dark:bg-gray-900 dark:scheme-dark';
	const removeButtonClass =
		'shrink-0 rounded-md p-1 text-gray-400 transition hover:bg-gray-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200';

	// Chosen "Specific" but nobody added yet.
	let specificChosen = false;
	// People/teams removed by switching to "Only me", restored if the user switches back.
	let stashedPrincipalGrants: AccessGrant[] = [];

	$: hasPrincipals =
		readGroupIds.length + writeGroupIds.length + readUserIds.length + writeUserIds.length > 0;

	$: visibility = getVisibility(accessGrants ?? []);
	$: level = (
		visibility === 'public'
			? 'everyone'
			: visibility === 'open'
				? 'link'
				: hasPrincipals || specificChosen
					? 'specific'
					: 'only_me'
	) as Level;

	const isPrincipalGrant = (g: AccessGrant) =>
		(g.principal_type === 'user' || g.principal_type === 'group') && g.principal_id !== '*';

	const setLevel = (next: Level) => {
		if (next === level) return;
		if (next === 'only_me') {
			const principals = currentGrants().filter(isPrincipalGrant);
			if (principals.length > 0) stashedPrincipalGrants = principals;
			specificChosen = false;
			commitAccessGrants([]);
		} else if (next === 'specific') {
			specificChosen = true;
			let grants = currentGrants().filter(isPrincipalGrant);
			if (grants.length === 0 && stashedPrincipalGrants.length > 0) {
				grants = stashedPrincipalGrants;
			}
			commitAccessGrants(grants);
		} else if (next === 'everyone') {
			setVisibility('public');
		} else if (next === 'link') {
			setVisibility('open');
		}
	};

	$: canSpecific = share && (shareUsers || allowGroups);
	$: levelOptions = [
		{
			value: 'only_me' as Level,
			label: $i18n.t('Only me'),
			description: $i18n.t('Nobody else can see or use it.'),
			disabled: false
		},
		{
			value: 'specific' as Level,
			label: $i18n.t('Specific persons'),
			description: $i18n.t('Only the people and teams you add below.'),
			disabled: !canSpecific,
			disabledHint: $i18n.t('You do not have permission to share this.')
		},
		{
			value: 'everyone' as Level,
			label: $i18n.t('Everyone at {{org}}', { org: ORG_NAME }),
			note: share && sharePublic ? '' : $i18n.t('needs approval'),
			description: $i18n.t('Everyone at {{org}} can find and use it.', { org: ORG_NAME }),
			// Keep it selectable if it already is public, so it can be read and changed back.
			disabled: !(share && sharePublic) && visibility !== 'public',
			disabledHint: $i18n.t('Ask the CHOn team to share it with everyone.')
		},
		...((share && shareOpen) || visibility === 'open'
			? [
					{
						value: 'link' as Level,
						label: $i18n.t('Anyone with the link'),
						description: $i18n.t('Also people who are not signed in.'),
						disabled: !(share && shareOpen) && visibility !== 'open'
					}
				]
			: [])
	];

	const initials = (name: string) =>
		(name ?? '')
			.split(/\s+/)
			.filter(Boolean)
			.slice(0, 2)
			.map((w) => w[0]?.toUpperCase() ?? '')
			.join('') || '?';

	// ---- Directory search (teams = synced Entra ID groups, plus people) ----------------------
	type DirectoryResult = { kind: 'group' | 'user'; id: string; name: string; detail: string };

	let searchInputElement: HTMLInputElement;
	let directoryQuery = '';
	let directoryUsers: any[] = [];
	let directoryLoading = false;
	let showDirectory = false;
	let directoryTimer: ReturnType<typeof setTimeout>;

	$: searchPlaceholder =
		shareUsers && allowGroups
			? $i18n.t('Add people or teams from the company directory…')
			: allowGroups
				? $i18n.t('Add teams…')
				: $i18n.t('Add people from the company directory…');

	const onDirectoryInput = () => {
		showDirectory = true;
		clearTimeout(directoryTimer);
		if (!shareUsers || !directoryQuery.trim()) {
			directoryUsers = [];
			return;
		}
		directoryLoading = true;
		directoryTimer = setTimeout(async () => {
			const res = await searchUsers(localStorage.token, directoryQuery.trim(), 'name', 'asc', 1).catch(
				() => null
			);
			directoryUsers = res?.users ?? [];
			directoryLoading = false;
		}, 250);
	};

	$: directoryResults = (() => {
		const q = directoryQuery.trim().toLowerCase();
		if (!q) return [] as DirectoryResult[];
		const grantedGroups = new Set([...readGroupIds, ...writeGroupIds]);
		const grantedUsers = new Set([...readUserIds, ...writeUserIds]);
		const teamResults: DirectoryResult[] = allowGroups
			? groups
					.filter((g) => !grantedGroups.has(g.id) && (g.name ?? '').toLowerCase().includes(q))
					.slice(0, 6)
					.map((g) => ({
						kind: 'group',
						id: g.id,
						name: g.name,
						detail: $i18n.t('team, {{count}} people', { count: g?.member_count ?? 0 })
					}))
			: [];
		const peopleResults: DirectoryResult[] = shareUsers
			? directoryUsers
					.filter((u) => !grantedUsers.has(u.id) && u.id !== $sessionUser?.id)
					.slice(0, 8)
					.map((u) => ({ kind: 'user', id: u.id, name: u.name ?? u.email, detail: u.email ?? '' }))
			: [];
		return [...teamResults, ...peopleResults];
	})();

	const pickPrincipal = (result: DirectoryResult) => {
		if (result.kind === 'group') {
			handleAddAccess({ userIds: [], groupIds: [result.id] });
		} else {
			userById = { ...userById, [result.id]: directoryUsers.find((u) => u.id === result.id) ?? userById[result.id] };
			handleAddAccess({ userIds: [result.id], groupIds: [] });
		}
		specificChosen = true;
		directoryQuery = '';
		directoryUsers = [];
		showDirectory = false;
		searchInputElement?.focus();
	};
</script>

<div class="flex flex-col gap-3 text-gray-900 dark:text-gray-100">
	<div>
		<div class="mb-1.5 text-sm font-semibold">{$i18n.t('Who can use it')}</div>

		<div class="flex flex-col gap-1.5" role="radiogroup" aria-label={$i18n.t('Who can use it')}>
			{#each levelOptions as option (option.value)}
				<button
					type="button"
					role="radio"
					aria-checked={level === option.value}
					disabled={option.disabled}
					title={option.disabled ? option.disabledHint : undefined}
					class="flex w-full items-start gap-2.5 rounded-lg border px-3 py-2 text-left text-sm transition disabled:cursor-not-allowed {level ===
					option.value
						? 'border-red-500 bg-red-50 dark:border-red-500 dark:bg-red-950/30'
						: 'border-gray-300 hover:bg-gray-50 disabled:hover:bg-transparent dark:border-gray-700 dark:hover:bg-gray-850'}"
					on:click={() => setLevel(option.value)}
				>
					<span
						class="mt-1 flex size-3 shrink-0 items-center justify-center rounded-full border {level ===
						option.value
							? 'border-red-600 dark:border-red-400'
							: 'border-gray-400'}"
						aria-hidden="true"
					>
						{#if level === option.value}
							<span class="size-1.5 rounded-full bg-red-600 dark:bg-red-400"></span>
						{/if}
					</span>
					<span class="min-w-0">
						<span class="font-semibold {option.disabled ? 'text-gray-400 dark:text-gray-600' : ''}">
							{option.label}
						</span>
						{#if option.note}
							<span class="text-gray-500">— {option.note}</span>
						{/if}
						{#if option.description && level === option.value}
							<span class="block text-xs text-gray-500">{option.description}</span>
						{/if}
					</span>
				</button>
			{/each}
		</div>

		{#if !(share && sharePublic) && level !== 'everyone'}
			<p class="mt-1.5 text-xs text-gray-500">
				{$i18n.t('Sharing with everyone at Weidmann needs approval. Ask the CHOn team.')}
			</p>
		{/if}

		{#if level === 'everyone' && accessRoles.includes('write')}
			<label class="mt-2 flex items-center justify-between gap-3 text-sm">
				<span>
					{$i18n.t('Everyone can edit')}
					<span class="block text-xs text-gray-500">
						{$i18n.t('Otherwise everyone can use it, and only the people below can edit.')}
					</span>
				</span>
				<Switch state={hasPublicWriteGrant(accessGrants ?? [])} on:change={() => togglePublicWrite()} />
			</label>
		{/if}
	</div>

	{#if share && (level === 'specific' || (level === 'everyone' && hasPrincipals))}
		<div class="flex flex-col gap-2">
			{#if level === 'everyone'}
				<div class="text-xs font-semibold text-gray-700 dark:text-gray-300">
					{$i18n.t('People and teams with extra rights')}
				</div>
			{/if}

			<!-- Directory search: teams (synced Entra ID groups) and people -->
			<div class="relative">
				<input
					bind:this={searchInputElement}
					class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm outline-hidden placeholder:text-gray-400 focus:border-gray-500 dark:border-gray-700 dark:bg-gray-900 dark:focus:border-gray-500"
					placeholder={searchPlaceholder}
					aria-label={searchPlaceholder}
					bind:value={directoryQuery}
					on:input={onDirectoryInput}
					on:focus={() => (showDirectory = true)}
					on:blur={() => setTimeout(() => (showDirectory = false), 150)}
					on:keydown={(e) => {
						if (e.key === 'Enter') {
							e.preventDefault();
							const first = directoryResults[0];
							if (first) pickPrincipal(first);
						} else if (e.key === 'Escape') {
							e.stopPropagation();
							showDirectory = false;
						}
					}}
				/>

				{#if showDirectory && directoryQuery.trim()}
					<div
						class="absolute top-full right-0 left-0 z-10 mt-1 max-h-56 overflow-y-auto rounded-lg border border-gray-200 bg-white p-1 shadow-lg dark:border-gray-800 dark:bg-gray-900"
						role="listbox"
					>
						{#if directoryLoading && directoryResults.length === 0}
							<div class="px-2 py-2 text-xs text-gray-500">{$i18n.t('Searching…')}</div>
						{:else if directoryResults.length === 0}
							<div class="px-2 py-2 text-xs text-gray-500">
								{$i18n.t('No people or teams found')}
							</div>
						{:else}
							{#each directoryResults as result (result.kind + result.id)}
								<button
									type="button"
									role="option"
									aria-selected="false"
									class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-800"
									on:mousedown|preventDefault={() => pickPrincipal(result)}
								>
									<span
										class="flex size-7 shrink-0 items-center justify-center rounded-full bg-gray-700 text-[0.625rem] font-semibold text-white dark:bg-gray-300 dark:text-gray-900"
									>
										{initials(result.name)}
									</span>
									<span class="min-w-0 flex-1">
										<span class="block truncate font-medium">{result.name}</span>
										<span class="block truncate text-xs text-gray-500">{result.detail}</span>
									</span>
								</button>
							{/each}
						{/if}
					</div>
				{/if}
			</div>

			{#if accessGroups.length > 0 || (shareUsers && selectedUsers.length > 0)}
				<ul class="flex flex-col gap-1.5">
					{#each accessGroups as group (group.id)}
						<li class="flex items-center gap-2">
							<span
								class="flex size-8 shrink-0 items-center justify-center rounded-full bg-gray-700 text-xs font-semibold text-white dark:bg-gray-300 dark:text-gray-900"
								aria-hidden="true"
							>
								{initials(group.name)}
							</span>
							<span class="min-w-0 flex-1 text-sm">
								<span class="font-semibold">{group.name}</span>
								<span class="text-gray-500">
									· {$i18n.t('team, {{count}} people', { count: group?.member_count ?? 0 })}
								</span>
							</span>
							{#if accessRoles.includes('write')}
								<select
									aria-label={$i18n.t('Role for {{name}}', { name: group.name })}
									class={roleSelectClass}
									value={writeGroupIds.includes(group.id) ? 'write' : 'read'}
									on:change={(e) => {
										if ((e.currentTarget.value === 'write') !== writeGroupIds.includes(group.id)) {
											togglePrincipalWrite('group', group.id);
										}
									}}
								>
									<option value="read">{$i18n.t('Can use')}</option>
									<option value="write">{$i18n.t('Can edit')}</option>
								</select>
							{:else}
								<span class="text-xs text-gray-500">{$i18n.t('Can use')}</span>
							{/if}
							<button
								type="button"
								class={removeButtonClass}
								aria-label={$i18n.t('Remove {{name}}', { name: group.name })}
								on:click={() => removePrincipal('group', group.id)}
							>
								<XMark className="size-3.5" />
							</button>
						</li>
					{/each}

					{#if shareUsers}
						{#each selectedUsers as user (user.id)}
							<li class="flex items-center gap-2">
								<img
									class="size-8 shrink-0 rounded-full object-cover"
									src={`${WEBUI_API_BASE_URL}/users/${user.id}/profile/image`}
									alt=""
								/>
								<span class="min-w-0 flex-1 text-sm">
									<span class="block truncate font-semibold" title={user.email}>
										{user.name ?? user.id}
									</span>
									{#if user.email}
										<span class="block truncate text-xs text-gray-500">{user.email}</span>
									{/if}
								</span>
								{#if accessRoles.includes('write')}
									<select
										aria-label={$i18n.t('Role for {{name}}', { name: user.name ?? user.id })}
										class={roleSelectClass}
										value={writeUserIds.includes(user.id) ? 'write' : 'read'}
										on:change={(e) => {
											if ((e.currentTarget.value === 'write') !== writeUserIds.includes(user.id)) {
												togglePrincipalWrite('user', user.id);
											}
										}}
									>
										<option value="read">{$i18n.t('Can use')}</option>
										<option value="write">{$i18n.t('Can edit')}</option>
									</select>
								{:else}
									<span class="text-xs text-gray-500">{$i18n.t('Can use')}</span>
								{/if}
								<button
									type="button"
									class={removeButtonClass}
									aria-label={$i18n.t('Remove {{name}}', { name: user.name ?? user.id })}
									on:click={() => removePrincipal('user', user.id)}
								>
									<XMark className="size-3.5" />
								</button>
							</li>
						{/each}
					{/if}
				</ul>
			{:else if level === 'specific'}
				<p class="text-xs text-gray-500">
					{$i18n.t('Nobody added yet. Until you add someone, only you can use it.')}
				</p>
			{/if}
		</div>
	{/if}
</div>
