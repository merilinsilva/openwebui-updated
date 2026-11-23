<script lang="ts">
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	dayjs.extend(relativeTime);

	import { onMount, getContext, tick, onDestroy } from 'svelte';
	const i18n = getContext('i18n');

	import {
		WEBUI_NAME,
		user,
		skills as _skills,
		workspaceActions,
		workspaceCounts
	} from '$lib/stores';
	import { goto } from '$app/navigation';
	import {
		getSkills,
		getSkillById,
		getSkillItems,
		exportSkills,
		createNewSkill,
		deleteSkillById,
		toggleSkillById,
		updateSkillAccessGrants,
		requestPublicSkill,
		cancelPublicSkillRequest,
		getPublicSkillRequests,
		approvePublicSkill,
		declinePublicSkill
	} from '$lib/apis/skills';
	import { parseSkillFile } from '$lib/utils/skillFiles';
	import AccessControlModal from './common/AccessControlModal.svelte';
	import { capitalizeFirstLetter, parseFrontmatter, formatSkillName, slugify } from '$lib/utils';
	import { getGroups } from '$lib/apis/groups';
	import { getOwnership, ownershipToneClass } from '$lib/utils/ownership';
	import TagInput from '$lib/components/common/Tags/TagInput.svelte';

	import Tooltip from '../common/Tooltip.svelte';
	import ConfirmDialog from '../common/ConfirmDialog.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import GarbageBin from '../icons/GarbageBin.svelte';
	import Search from '../icons/Search.svelte';
	import XMark from '../icons/XMark.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Switch from '../common/Switch.svelte';
	import SkillMenu from './Skills/SkillMenu.svelte';
	import Pagination from '../common/Pagination.svelte';

	let shiftKey = false;
	let loaded = false;

	let importFiles;
	let importInputElement: HTMLInputElement;

	let query = '';
	let searchDebounceTimer: ReturnType<typeof setTimeout>;

	let selectedSkill = null;
	let showDeleteConfirm = false;

	let filteredItems = null;
	let total = null;
	let loading = false;

	let viewOption = '';
	let sortKey = 'updated_at';
	let sortDirection = 'desc';
	let openSkillMenuId: string | null = null;
	let page = 1;

	$: if (loaded) {
		workspaceActions.set([
			{
				id: 'skills-new',
				label: $i18n.t('Create'),
				href: '/workspace/skills/create',
				visible: $user?.role === 'admin' || $user?.permissions?.workspace?.skills
			},
			{
				// CHOn (T12): upload a SKILL.md, a .zip with skill folders, or a JSON export
				id: 'skills-import',
				label: $i18n.t('Upload skill'),
				onClick: () => importInputElement?.click(),
				visible:
					$user?.role === 'admin' ||
					$user?.permissions?.workspace?.skills ||
					$user?.permissions?.workspace?.skills_import
			},
			{
				id: 'skills-export',
				label: $i18n.t('Export JSON'),
				onClick: async () => {
					const _skills = await exportSkills(localStorage.token).catch((error) => {
						toast.error(`${error}`);
						return null;
					});
					if (_skills) {
						let blob = new Blob([JSON.stringify(_skills)], {
							type: 'application/json'
						});
						saveAs(blob, `skills-export-${Date.now()}.json`);
					}
				},
				visible: $user?.role === 'admin' || $user?.permissions?.workspace?.skills_export
			}
		]);
	}

	const loadSkillItems = async () => {
		if (!loaded) return;

		loading = true;
		try {
			// CHOn (T12): admins review company-wide sharing requests
			if (viewOption === 'pending') {
				const pending = await getPublicSkillRequests(localStorage.token).catch((error) => {
					toast.error(`${error}`);
					return [];
				});
				const q = query.trim().toLowerCase();
				filteredItems = (pending ?? [])
					.filter((s) => !q || `${s.name} ${s.description ?? ''}`.toLowerCase().includes(q))
					.map((s) => ({ ...s, write_access: true }));
				total = filteredItems.length;
				pendingCount = total;
				return;
			}

			const res = await getSkillItems(
				localStorage.token,
				query,
				viewOption,
				page,
				sortKey,
				sortDirection
			).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (res) {
				filteredItems = res.items;
				total = res.total;
				workspaceCounts.update((counts) => ({ ...counts, skills: total }));
			}
		} catch (err) {
			console.error(err);
		} finally {
			loading = false;
		}
	};

	const handleSearchInput = () => {
		loading = true;
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(() => {
			if (page !== 1) {
				page = 1;
			} else {
				loadSkillItems();
			}
		}, 300);
	};

	// Immediate response to page/filter changes
	$: if (
		loaded &&
		page &&
		viewOption !== undefined &&
		sortKey !== undefined &&
		sortDirection !== undefined
	) {
		loadSkillItems();
	}


	// Sharing badge per card ("Weidmann", team name, "Mine").
	let groupNames: Record<string, string> = {};
	getGroups(localStorage.token)
		.then((groups) => {
			groupNames = Object.fromEntries((groups ?? []).map((g) => [g.id, g.name]));
		})
		.catch(() => {});

	// Filter chips (same values as the old view selector).
	$: viewChips = [
		{ value: '', label: $i18n.t('All') },
		{ value: 'created', label: $i18n.t('Created by me') },
		{ value: 'shared', label: $i18n.t('Shared with me') },
		// CHOn (T12): admins see open requests to share a skill with everyone
		...($user?.role === 'admin'
			? [
					{
						value: 'pending',
						label: pendingCount
							? $i18n.t('Pending approval ({{count}})', { count: pendingCount })
							: $i18n.t('Pending approval')
					}
				]
			: [])
	];

	// ---- CHOn (T12): sharing and company-wide approval ------------------------------------
	let pendingCount = 0;
	$: if (loaded && $user?.role === 'admin') {
		getPublicSkillRequests(localStorage.token)
			.then((items) => (pendingCount = (items ?? []).length))
			.catch(() => {});
	}

	let showShareModal = false;
	let shareSkill: any = null;
	let shareGrants: any[] = [];

	const refreshAfterChange = async () => {
		await loadSkillItems();
		_skills.set(await getSkills(localStorage.token));
	};

	const openShare = async (skill) => {
		const full = await getSkillById(localStorage.token, skill.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (!full) return;
		shareSkill = full;
		shareGrants = full.access_grants ?? [];
		showShareModal = true;
	};

	const saveShare = async (grants) => {
		if (!shareSkill) return;
		const res = await updateSkillAccessGrants(localStorage.token, shareSkill.id, grants).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);
		if (res) {
			shareSkill = res;
			await refreshAfterChange();
		}
	};

	const requestPublic = async () => {
		if (!shareSkill) return;
		const res = await requestPublicSkill(localStorage.token, shareSkill.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (res) {
			shareSkill = res;
			toast.success($i18n.t('Request sent. The CHOn team will review it.'));
			await refreshAfterChange();
		}
	};

	const cancelPublicRequest = async () => {
		if (!shareSkill) return;
		const res = await cancelPublicSkillRequest(localStorage.token, shareSkill.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (res) {
			shareSkill = res;
			await refreshAfterChange();
		}
	};

	let decisionBusy: string | null = null;
	const decide = async (skill, approve: boolean) => {
		let note: string | null = null;
		if (!approve) {
			note = window.prompt($i18n.t('Optional: tell the owner why (shown in the share dialog).')) ?? null;
		}
		decisionBusy = skill.id;
		const res = await (approve
			? approvePublicSkill(localStorage.token, skill.id)
			: declinePublicSkill(localStorage.token, skill.id, note)
		).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		decisionBusy = null;
		if (res) {
			toast.success(
				approve
					? $i18n.t('"{{name}}" is now shared with everyone at Weidmann.', { name: skill.name })
					: $i18n.t('Request for "{{name}}" declined.', { name: skill.name })
			);
			await refreshAfterChange();
		}
	};

	const requestState = (skill) => skill?.meta?.public_request?.status ?? null;

	const setViewOption = (value: string) => {
		viewOption = value;
		localStorage.workspaceViewOption = value;
		page = 1;
	};

	const setSort = (value: string) => {
		const [key, dir] = value.split(':');
		sortKey = key;
		sortDirection = dir;
		page = 1;
	};

	$: isFiltered = query.trim() !== '' || viewOption !== '';

	const ownerOf = (item) => {
		if (item?.user_id && item.user_id === $user?.id) return $i18n.t('owned by you');
		const name = item?.user?.name ?? item?.user?.email;
		return name
			? $i18n.t('owned by {{name}}', { name: capitalizeFirstLetter(name) })
			: $i18n.t('Deleted User');
	};

	const chipClass = (active: boolean) =>
		`shrink-0 rounded-full border px-3 py-1 text-xs transition ${
			active
				? 'border-red-500 bg-red-50 text-red-700 dark:border-red-500 dark:bg-red-950/40 dark:text-red-300'
				: 'border-gray-200 text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-850'
		}`;

	const selectClass =
		'rounded-lg border border-gray-300 bg-white px-2 py-1 text-xs text-gray-800 outline-hidden focus:border-gray-500 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200 dark:scheme-dark';

	const openSkill = (skill) => {
		goto(`/workspace/skills/edit?id=${encodeURIComponent(skill.id)}`);
	};


	const cloneHandler = async (skill) => {
		const _skill = await getSkillById(localStorage.token, skill.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (_skill) {
			sessionStorage.skill = JSON.stringify({
				..._skill,
				id: `${_skill.id}_clone`,
				name: `${_skill.name} (Clone)`
			});
			goto('/workspace/skills/create');
		}
	};

	const exportHandler = async (skill) => {
		const _skill = await getSkillById(localStorage.token, skill.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (_skill) {
			let blob = new Blob([JSON.stringify([_skill])], {
				type: 'application/json'
			});
			saveAs(blob, `skill-${_skill.id}-export-${Date.now()}.json`);
		}
	};

	const deleteHandler = async (skill) => {
		const res = await deleteSkillById(localStorage.token, skill.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Skill deleted successfully'));
		}

		page = 1;
		loadSkillItems();
		await _skills.set(await getSkills(localStorage.token));
	};

	// CHOn (T12): one skill opens in the editor to review; several are created directly
	// (private to the uploader) and can then be shared from each card.
	const uploadSkillFile = async (file: File) => {
		let parsed = [];
		try {
			parsed = await parseSkillFile(file);
		} catch (e) {
			toast.error(`${(e as Error)?.message ?? e}`);
			return;
		}
		if (parsed.length === 0) {
			toast.error($i18n.t('No SKILL.md found in this file.'));
			return;
		}

		const ignored = parsed.flatMap((p) => p.ignoredFiles);
		if (ignored.length > 0) {
			toast.info(
				$i18n.t('Only SKILL.md is used. {{count}} other file(s) were not imported: {{files}}', {
					count: ignored.length,
					files: ignored.slice(0, 3).join(', ') + (ignored.length > 3 ? ', …' : '')
				})
			);
		}

		if (parsed.length === 1) {
			const skill = parsed[0];
			sessionStorage.skill = JSON.stringify({
				name: skill.name,
				id: skill.id,
				description: skill.description,
				content: skill.content,
				is_active: true,
				access_grants: []
			});
			goto('/workspace/skills/create');
			return;
		}

		let created = 0;
		for (const skill of parsed) {
			const res = await createNewSkill(localStorage.token, {
				id: skill.id,
				name: skill.name,
				description: skill.description,
				content: skill.content,
				meta: { tags: [] },
				is_active: true,
				access_grants: []
			}).catch((error) => {
				toast.error(`${skill.name}: ${error}`);
				return null;
			});
			if (res) created++;
		}
		if (created > 0) {
			toast.success(
				$i18n.t('{{count}} skills uploaded. Use Share on a skill to give your team access.', {
					count: created
				})
			);
			page = 1;
			await refreshAfterChange();
		}
	};

	onMount(async () => {
		viewOption = localStorage?.workspaceViewOption || '';
		loaded = true;

		const onKeyDown = (event) => {
			if (event.key === 'Shift') {
				shiftKey = true;
			}
		};

		const onKeyUp = (event) => {
			if (event.key === 'Shift') {
				shiftKey = false;
			}
		};

		const onBlur = () => {
			shiftKey = false;
		};

		window.addEventListener('keydown', onKeyDown);
		window.addEventListener('keyup', onKeyUp);
		window.addEventListener('blur', onBlur);

		return () => {
			clearTimeout(searchDebounceTimer);
			window.removeEventListener('keydown', onKeyDown);
			window.removeEventListener('keyup', onKeyUp);
			window.removeEventListener('blur', onBlur);
		};
	});

	onDestroy(() => {
		clearTimeout(searchDebounceTimer);
	});
</script>

<svelte:head>
	<!-- LICENSE covers this Open WebUI browser-title identifier.
	Do not alter, remove, obscure, or replace it except as LICENSE permits:
	https://docs.openwebui.com/license. -->
	<title>
		{$i18n.t('Skills')} / {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<input
		bind:this={importInputElement}
		bind:files={importFiles}
		type="file"
		accept=".md,.zip,.json"
		hidden
		on:change={() => {
			if (importFiles && importFiles.length > 0) {
				const file = importFiles[0];
				const ext = file.name.split('.').pop()?.toLowerCase();

				if (ext === 'json') {
					// JSON import: create skills via API
					const reader = new FileReader();
					reader.onload = async (event) => {
						try {
							const content = event.target?.result;
							if (typeof content !== 'string') return;

							const parsedSkills = JSON.parse(content);
							const items = Array.isArray(parsedSkills) ? parsedSkills : [parsedSkills];

							for (const skill of items) {
								await createNewSkill(localStorage.token, skill).catch((error) => {
									toast.error(`${error}`);
								});
							}

							toast.success($i18n.t('Skill imported successfully'));
							page = 1;
							loadSkillItems();
							_skills.set(await getSkills(localStorage.token));
						} catch (e) {
							toast.error($i18n.t('Invalid JSON file'));
						}
					};
					reader.readAsText(file);
				} else {
					// CHOn (T12): SKILL.md or .zip (one folder per skill)
					uploadSkillFile(file);
				}

				importInputElement.value = '';
			}
		}}
	/>

	<!-- Breathing room below the workspace tabs / Create button (layout only adds pb-1). -->
	<div class="flex flex-col gap-4 pt-5 text-gray-900 dark:text-gray-100">
		<label
			class="flex items-center gap-2 rounded-lg border border-gray-300 px-3 py-2 focus-within:border-gray-500 dark:border-gray-700 dark:focus-within:border-gray-500"
		>
			<Search className="size-3.5 shrink-0 text-gray-500" />
			<input
				class="w-full bg-transparent text-sm outline-hidden placeholder:text-gray-400"
				bind:value={query}
				on:input={handleSearchInput}
				aria-label={$i18n.t('Search Skills')}
				placeholder={$i18n.t('Search skills, e.g. "document formatting"')}
			/>
			{#if query}
				<button
					type="button"
					class="rounded-full p-0.5 text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
					aria-label={$i18n.t('Clear search')}
					on:click={() => {
						query = '';
						handleSearchInput();
					}}
				>
					<XMark className="size-3" strokeWidth="2" />
				</button>
			{/if}
		</label>

		<div class="flex flex-wrap items-center gap-1.5">
			{#each viewChips as chip (chip.value)}
				<button
					type="button"
					class={chipClass(viewOption === chip.value)}
					aria-pressed={viewOption === chip.value}
					on:click={() => setViewOption(chip.value)}
				>
					{chip.label}
				</button>
			{/each}

			<label class="ml-auto flex items-center gap-1.5 text-xs text-gray-500">
				{$i18n.t('Sort')}
				<select
					class={selectClass}
					value={`${sortKey}:${sortDirection}`}
					on:change={(e) => setSort(e.currentTarget.value)}
				>
					<option value="updated_at:desc">{$i18n.t('Recently updated')}</option>
					<option value="name:asc">{$i18n.t('Name (A–Z)')}</option>
					<option value="name:desc">{$i18n.t('Name (Z–A)')}</option>
					<option value="updated_at:asc">{$i18n.t('Oldest first')}</option>
				</select>
			</label>
		</div>

		{#if filteredItems === null || loading}
			<div class="flex w-full items-center justify-center py-10">
				<Spinner className="size-5" />
			</div>
		{:else if (filteredItems ?? []).length !== 0}
			<ul class="grid gap-2.5 md:grid-cols-2">
				{#each filteredItems as skill (skill.id)}
					{@const own = getOwnership(skill, $user?.id, groupNames, (k, o) => $i18n.t(k, o))}
					{@const enabled = skill.is_active !== false}
					<li class="group relative">
						<button
							type="button"
							class="flex h-full w-full flex-col rounded-xl border border-gray-200 px-4 py-3 text-left transition hover:border-gray-400 hover:bg-gray-50 focus-visible:border-gray-500 dark:border-gray-800 dark:hover:border-gray-600 dark:hover:bg-gray-850 {enabled
								? ''
								: 'opacity-60'}"
							on:click={() => openSkill(skill)}
						>
							<div class="flex w-full items-center gap-2 {skill.write_access ? 'pr-8' : ''}">
								<span class="min-w-0 flex-1 truncate text-sm font-semibold">{skill.name}</span>
								<span
									class="max-w-[45%] shrink-0 truncate rounded-full px-2 py-0.5 text-[0.6875rem] {ownershipToneClass(
										own.tone
									)}"
									title={own.description}
								>
									{own.label}
								</span>
							</div>

							<div class="mt-1 line-clamp-2 min-h-[2rem] text-xs text-gray-600 dark:text-gray-400">
								{skill.description || $i18n.t('No description')}
							</div>

							<div
								class="mt-2 flex w-full flex-wrap items-center gap-x-1.5 gap-y-1 {skill.write_access
									? 'pr-12'
									: ''} text-[0.6875rem] text-gray-500"
							>
								<span class="font-mono">{skill.id}</span>
								<span aria-hidden="true">·</span>
								<span title={dayjs((skill.updated_at ?? skill.created_at) * 1000).format('LLLL')}>
									{$i18n.t('updated {{time}}', {
										time: dayjs((skill.updated_at ?? skill.created_at) * 1000).fromNow()
									})}
								</span>
								<span aria-hidden="true">·</span>
								<span class="truncate" title={skill?.user?.email ?? ''}>{ownerOf(skill)}</span>
								{#if !skill.write_access}
									<span aria-hidden="true">·</span>
									<span>{$i18n.t('Read Only')}</span>
								{/if}
								{#if !enabled}
									<span aria-hidden="true">·</span>
									<span>{$i18n.t('Disabled')}</span>
								{/if}
								{#if skill.write_access && requestState(skill) === 'pending'}
									<span
										class="rounded-full bg-amber-50 px-2 py-0.5 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300"
										title={skill?.meta?.public_request?.requested_by_name
											? $i18n.t('Requested by {{name}}', {
													name: skill.meta.public_request.requested_by_name
												})
											: ''}
									>
										{$i18n.t('Waiting for approval')}
									</span>
								{:else if skill.write_access && requestState(skill) === 'declined' && own.tone !== 'org'}
									<span
										class="rounded-full bg-gray-100 px-2 py-0.5 text-gray-700 dark:bg-gray-800 dark:text-gray-300"
										title={skill?.meta?.public_request?.note ?? ''}
									>
										{$i18n.t('Company-wide sharing declined')}
									</span>
								{/if}
							</div>
						</button>

						{#if viewOption === 'pending' && $user?.role === 'admin'}
							<!-- CHOn (T12): approve or decline company-wide sharing -->
							<div class="mt-1.5 flex items-center gap-2 px-1">
								<button
									type="button"
									class="rounded-lg bg-black px-3 py-1 text-xs font-semibold text-white hover:bg-gray-800 disabled:opacity-60 dark:bg-white dark:text-black dark:hover:bg-gray-200"
									disabled={decisionBusy === skill.id}
									on:click={() => decide(skill, true)}
								>
									{$i18n.t('Approve: share with everyone')}
								</button>
								<button
									type="button"
									class="rounded-lg border border-gray-300 px-3 py-1 text-xs font-medium hover:bg-gray-50 disabled:opacity-60 dark:border-gray-700 dark:hover:bg-gray-850"
									disabled={decisionBusy === skill.id}
									on:click={() => decide(skill, false)}
								>
									{$i18n.t('Decline')}
								</button>
							</div>
						{/if}

						{#if skill.write_access}
							<!-- Card actions sit outside the card button (no nested buttons). -->
							<div class="absolute top-2 right-2">
								{#if shiftKey}
									<Tooltip content={$i18n.t('Delete')}>
										<button
											class="flex size-7 items-center justify-center rounded-lg text-gray-400 transition hover:bg-gray-100 hover:text-red-600 dark:hover:bg-gray-800"
											type="button"
											aria-label={$i18n.t('Delete')}
											on:click={() => deleteHandler(skill)}
										>
											<GarbageBin className="size-4" />
										</button>
									</Tooltip>
								{:else}
									<SkillMenu
										editHandler={() => {
											goto(`/workspace/skills/edit?id=${encodeURIComponent(skill.id)}`);
										}}
										cloneHandler={() => {
											cloneHandler(skill);
										}}
										exportHandler={() => {
											exportHandler(skill);
										}}
										shareHandler={$user?.role === 'admin' || $user?.permissions?.sharing?.skills
											? () => openShare(skill)
											: null}
										deleteHandler={async () => {
											selectedSkill = skill;
											showDeleteConfirm = true;
										}}
										onClose={() => {
											openSkillMenuId = null;
										}}
									>
										<button
											class="flex size-7 items-center justify-center rounded-lg text-gray-400 transition hover:bg-gray-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200"
											type="button"
											aria-label={$i18n.t('Skill Menu')}
										>
											<EllipsisHorizontal className="size-4" />
										</button>
									</SkillMenu>
								{/if}
							</div>

							<div class="absolute right-3 bottom-3">
								<Tooltip content={enabled ? $i18n.t('Enabled') : $i18n.t('Disabled')}>
									<Switch
										bind:state={skill.is_active}
										on:change={async () => {
											toggleSkillById(localStorage.token, skill.id);
										}}
									/>
								</Tooltip>
							</div>
						{/if}
					</li>
				{/each}
			</ul>

			{#if total > 30}
				<div class="flex justify-center">
					<Pagination bind:page count={total} perPage={30} />
				</div>
			{/if}
		{:else if isFiltered}
			<div class="py-16 text-center">
				<div class="text-sm">{$i18n.t('Nothing matches your search')}</div>
				<div class="mt-1 text-xs text-gray-500">
					{$i18n.t('Try another word, or switch the filter back to All.')}
				</div>
			</div>
		{:else}
			<div class="mx-auto flex max-w-sm flex-col items-center py-16 text-center">
				<div class="text-base font-semibold">{$i18n.t('No skills yet')}</div>
				<p class="mt-1 text-sm text-gray-500">
					{$i18n.t(
						'A skill is a set of instructions CHOn follows for a specific job, e.g. formatting documents in the Weidmann style.'
					)}
				</p>
				{#if $user?.role === 'admin' || $user?.permissions?.workspace?.skills}
					<a
						href="/workspace/skills/create"
						class="mt-4 rounded-lg bg-black px-4 py-2 text-sm font-semibold text-white transition hover:bg-gray-800 dark:bg-white dark:text-black dark:hover:bg-gray-200"
					>
						+ {$i18n.t('New skill')}
					</a>
				{/if}
			</div>
		{/if}
	</div>

	{#if shareSkill}
		<!-- CHOn (T12): share a skill with people, teams, or (after approval) everyone -->
		<AccessControlModal
			bind:show={showShareModal}
			bind:accessGrants={shareGrants}
			accessRoles={['read', 'write']}
			itemName={shareSkill.name}
			subtitle={$i18n.t('Skill')}
			share={$user?.permissions?.sharing?.skills || $user?.role === 'admin'}
			sharePublic={$user?.permissions?.sharing?.public_skills || $user?.role === 'admin'}
			shareUsers={($user?.permissions?.access_grants?.allow_users ?? true) || $user?.role === 'admin'}
			publicRequest={shareSkill?.meta?.public_request ?? null}
			onRequestPublic={requestPublic}
			onCancelPublicRequest={cancelPublicRequest}
			onChange={saveShare}
		/>
	{/if}

	<DeleteConfirmDialog
		bind:show={showDeleteConfirm}
		title={$i18n.t('Delete skill?')}
		on:confirm={() => {
			deleteHandler(selectedSkill);
		}}
	>
		<div class=" text-sm text-gray-500 truncate">
			{$i18n.t('This will delete')} <span class="  font-normal">{selectedSkill.name}</span>.
		</div>
	</DeleteConfirmDialog>
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner className="size-5" />
	</div>
{/if}
