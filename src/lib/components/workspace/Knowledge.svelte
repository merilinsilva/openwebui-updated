<script lang="ts">
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { toast } from 'svelte-sonner';
	import { onMount, getContext, tick, onDestroy } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n = getContext<Writable<i18nType>>('i18n');

	import { WEBUI_NAME, user, workspaceActions, workspaceCounts } from '$lib/stores';
	import {
		deleteKnowledgeById,
		searchKnowledgeBases,
		exportKnowledgeById
	} from '$lib/apis/knowledge';

	import { goto } from '$app/navigation';
	import { capitalizeFirstLetter } from '$lib/utils';
	import { getGroups } from '$lib/apis/groups';
	import { getOwnership, ownershipToneClass } from '$lib/utils/ownership';

	import DeleteConfirmDialog from '../common/ConfirmDialog.svelte';
	import ItemMenu from './Knowledge/ItemMenu.svelte';
	import CreateKnowledgeBase from './Knowledge/CreateKnowledgeBase.svelte';
	import Modal from '../common/Modal.svelte';
	import Search from '../icons/Search.svelte';
	import Spinner from '../common/Spinner.svelte';
	import XMark from '../icons/XMark.svelte';
	import Loader from '../common/Loader.svelte';

	// Sharing badge per card ("Weidmann", team name, "Mine").
	let groupNames: Record<string, string> = {};
	getGroups(localStorage.token)
		.then((groups) => {
			groupNames = Object.fromEntries((groups ?? []).map((g) => [g.id, g.name]));
		})
		.catch(() => {});

	type KnowledgeListItem = {
		id: string;
		name: string;
		description?: string;
		updated_at: number;
		file_count?: number;
		write_access?: boolean;
		meta?: any;
		user?: {
			name?: string;
			email?: string;
		};
	};

	export let showCreateOnMount = false;
	export let createModalCloseHref = '';

	let loaded = false;
	let showDeleteConfirm = false;
	let showCreateModal = false;

	let selectedItem: KnowledgeListItem | null = null;

	let page = 1;
	let query = '';
	let searchDebounceTimer: ReturnType<typeof setTimeout>;
	let viewOption = '';
	let sourceOption = '';
	let sortKey = 'updated_at';
	let sortDirection = 'desc';

	let items: KnowledgeListItem[] | null = null;
	let total: number | null = null;

	let allItemsLoaded = false;
	let itemsLoading = false;

	$: if (loaded) {
		workspaceActions.set([
			{
				id: 'knowledge-new',
				label: $i18n.t('Create'),
				onClick: () => {
					showCreateModal = true;
				}
			}
		]);
	}

	const handleSearchInput = () => {
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(() => {
			init();
		}, 300);
	};

	onDestroy(() => {
		clearTimeout(searchDebounceTimer);
	});

	$: if (
		loaded &&
		viewOption !== undefined &&
		sourceOption !== undefined &&
		sortKey !== undefined &&
		sortDirection !== undefined
	) {
		init();
	}

	// Filter chips (same values the backend's view_option accepts).
	$: viewChips = [
		{ value: '', label: $i18n.t('All') },
		{ value: 'created', label: $i18n.t('Created by me') },
		{ value: 'shared', label: $i18n.t('Shared with me') }
	];

	const setViewOption = (value: string) => {
		viewOption = value;
		localStorage.workspaceViewOption = value;
	};

	const setSourceOption = (value: string) => {
		sourceOption = value;
		localStorage.workspaceKnowledgeSourceOption = value;
	};

	// Only offer the "Connected sources" filter when there are any (or it is already on).
	$: showSourceChip =
		sourceOption === 'external' || (items ?? []).some((i) => i?.meta?.source === 'external');

	$: isFiltered = query.trim() !== '' || viewOption !== '' || sourceOption !== '';

	const ownerOf = (item: KnowledgeListItem & { user_id?: string }) => {
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

	const reset = () => {
		page = 1;
		items = null;
		total = null;
		allItemsLoaded = false;
		itemsLoading = false;
	};

	const loadMoreItems = async () => {
		if (allItemsLoaded) return;
		page += 1;
		await getItemsPage();
	};

	const init = async () => {
		if (!loaded) return;

		reset();
		await getItemsPage();
	};

	const getItemsPage = async () => {
		itemsLoading = true;
		const res = await searchKnowledgeBases(
			localStorage.token,
			query,
			viewOption,
			page,
			sourceOption,
			sortKey,
			sortDirection
		).catch(() => {
			return [];
		});

		if (res) {
			console.log(res);
			total = res.total;
			workspaceCounts.update((counts) => ({ ...counts, knowledge: total }));
			const pageItems: KnowledgeListItem[] = res.items ?? [];

			if ((pageItems ?? []).length === 0) {
				allItemsLoaded = true;
			} else {
				allItemsLoaded = false;
			}

			if (items) {
				const existingIds = new Set(items.map((item) => item.id));
				const newItems = pageItems.filter((item) => !existingIds.has(item.id));
				items = [...items, ...newItems];
			} else {
				items = pageItems;
			}
		}

		itemsLoading = false;
		return res;
	};

	const deleteHandler = async (item: KnowledgeListItem | null) => {
		if (!item) return;

		const res = await deleteKnowledgeById(localStorage.token, item.id).catch((e) => {
			toast.error(`${e}`);
		});

		if (res) {
			toast.success($i18n.t('Knowledge deleted successfully.'));
			init();
		}
	};

	const closeCreateModal = async () => {
		showCreateModal = false;

		if (createModalCloseHref) {
			await goto(createModalCloseHref);
		}
	};

	const exportHandler = async (item: KnowledgeListItem) => {
		try {
			const blob = await exportKnowledgeById(localStorage.token, item.id);
			if (blob) {
				const url = URL.createObjectURL(blob);
				const a = document.createElement('a');
				a.href = url;
				a.download = `${item.name}.zip`;
				document.body.appendChild(a);
				a.click();
				document.body.removeChild(a);
				URL.revokeObjectURL(url);
				toast.success($i18n.t('Knowledge exported successfully'));
			}
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	const openKnowledge = (item: KnowledgeListItem) => {
		if (item?.meta?.document) {
			toast.error(
				$i18n.t(
					'Only collections can be edited, create a new knowledge base to edit/add documents.'
				)
			);
			return;
		}

		goto(`/workspace/knowledge/${item.id}`);
	};

	onMount(async () => {
		viewOption = localStorage?.workspaceViewOption || '';
		sourceOption = localStorage?.workspaceKnowledgeSourceOption || '';
		loaded = true;
		await tick();

		if (items === null && !itemsLoading) {
			await init();
		}

		if (showCreateOnMount) {
			showCreateModal = true;
		}
	});
</script>

<svelte:head>
	<!-- LICENSE covers this Open WebUI browser-title identifier.
	Do not alter, remove, obscure, or replace it except as LICENSE permits:
	https://docs.openwebui.com/license. -->
	<title>
		{$i18n.t('Knowledge')} / {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<DeleteConfirmDialog
		bind:show={showDeleteConfirm}
		on:confirm={() => {
			deleteHandler(selectedItem);
		}}
	/>

	<Modal bind:show={showCreateModal} size="md" className="bg-white dark:bg-gray-900 rounded-2xl">
		<CreateKnowledgeBase
			modal={true}
			onBack={() => {
				closeCreateModal();
			}}
		/>
	</Modal>

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
				aria-label={$i18n.t('Search knowledge bases')}
				placeholder={$i18n.t('Search knowledge bases, e.g. "transformer specs"')}
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

			{#if showSourceChip}
				<button
					type="button"
					class={chipClass(sourceOption === 'external')}
					aria-pressed={sourceOption === 'external'}
					on:click={() => setSourceOption(sourceOption === 'external' ? '' : 'external')}
				>
					{$i18n.t('Connected sources')}
				</button>
			{/if}

			<label class="ml-auto flex items-center gap-1.5 text-xs text-gray-500">
				{$i18n.t('Sort')}
				<select
					class="rounded-lg border border-gray-300 bg-white px-2 py-1 text-xs text-gray-800 outline-hidden focus:border-gray-500 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200 dark:scheme-dark"
					value={`${sortKey}:${sortDirection}`}
					on:change={(e) => {
						const [key, dir] = e.currentTarget.value.split(':');
						sortKey = key;
						sortDirection = dir;
					}}
				>
					<option value="updated_at:desc">{$i18n.t('Recently updated')}</option>
					<option value="name:asc">{$i18n.t('Name (A–Z)')}</option>
					<option value="name:desc">{$i18n.t('Name (Z–A)')}</option>
					<option value="updated_at:asc">{$i18n.t('Oldest first')}</option>
				</select>
			</label>
		</div>

		{#if items !== null && total !== null}
			{#if (items ?? []).length !== 0}
				<ul class="grid gap-2.5 md:grid-cols-2">
					{#each items as item (item.id)}
						{@const external = item?.meta?.source === 'external'}
						{@const own = getOwnership(item, $user?.id, groupNames, (k, o) => $i18n.t(k, o))}
						{@const canManage = item?.write_access || $user?.role === 'admin'}
						<li class="group relative">
							<button
								type="button"
								class="flex h-full w-full flex-col rounded-xl border border-gray-200 px-4 py-3 text-left transition hover:border-gray-400 hover:bg-gray-50 focus-visible:border-gray-500 dark:border-gray-800 dark:hover:border-gray-600 dark:hover:bg-gray-850"
								on:click={() => openKnowledge(item)}
							>
								<div class="flex w-full items-center gap-2 {canManage ? 'pr-7' : ''}">
									<span class="min-w-0 flex-1 truncate text-sm font-semibold">{item.name}</span>
									{#if external}
										<span
											class="shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-[0.6875rem] text-gray-700 dark:bg-gray-800 dark:text-gray-300"
										>
											{item?.meta?.external?.provider ?? $i18n.t('Connected')}
										</span>
									{:else}
										<span
											class="max-w-[45%] shrink-0 truncate rounded-full px-2 py-0.5 text-[0.6875rem] {ownershipToneClass(
												own.tone
											)}"
											title={own.description}
										>
											{own.label}
										</span>
									{/if}
								</div>

								<div class="mt-1 line-clamp-2 min-h-[2rem] text-xs text-gray-600 dark:text-gray-400">
									{item.description || $i18n.t('No description')}
								</div>

								<div class="mt-2 flex flex-wrap items-center gap-x-1.5 text-[0.6875rem] text-gray-500">
									{#if item.file_count !== undefined && item.file_count !== null}
										<span>
											{item.file_count === 1
												? $i18n.t('1 document')
												: $i18n.t('{{COUNT}} documents', { COUNT: item.file_count })}
										</span>
										<span aria-hidden="true">·</span>
									{/if}
									<span title={dayjs(item.updated_at * 1000).format('LLLL')}>
										{$i18n.t('updated {{time}}', { time: dayjs(item.updated_at * 1000).fromNow() })}
									</span>
									<span aria-hidden="true">·</span>
									<span class="truncate" title={item?.user?.email ?? ''}>{ownerOf(item)}</span>
									{#if external || !item?.write_access}
										<span aria-hidden="true">·</span>
										<span>{$i18n.t('Read Only')}</span>
									{/if}
								</div>
							</button>

							{#if canManage}
								<div
									class="absolute top-2 right-2 opacity-0 transition group-hover:opacity-100 focus-within:opacity-100"
								>
									<ItemMenu
										onExport={$user?.role === 'admin'
											? () => {
													exportHandler(item);
												}
											: null}
										on:delete={() => {
											selectedItem = item;
											showDeleteConfirm = true;
										}}
									/>
								</div>
							{/if}
						</li>
					{/each}
				</ul>

				{#if !allItemsLoaded}
					<Loader
						on:visible={() => {
							if (!itemsLoading) {
								loadMoreItems();
							}
						}}
					>
						<div class="flex w-full items-center justify-center gap-2 py-4 text-xs animate-pulse">
							<Spinner className=" size-4" />
							<div>{$i18n.t('Loading...')}</div>
						</div>
					</Loader>
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
					<div class="text-base font-semibold">{$i18n.t('No knowledge bases yet')}</div>
					<p class="mt-1 text-sm text-gray-500">
						{$i18n.t(
							'A knowledge base holds documents CHOn can search and quote, like specs, manuals or reports.'
						)}
					</p>
					<button
						type="button"
						class="mt-4 rounded-lg bg-black px-4 py-2 text-sm font-semibold text-white transition hover:bg-gray-800 dark:bg-white dark:text-black dark:hover:bg-gray-200"
						on:click={() => (showCreateModal = true)}
					>
						+ {$i18n.t('New knowledge base')}
					</button>
				</div>
			{/if}
		{:else}
			<div class="flex w-full items-center justify-center py-10">
				<Spinner className="size-4" />
			</div>
		{/if}
	</div>
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner className="size-5" />
	</div>
{/if}
