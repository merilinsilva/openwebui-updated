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
		config,
		tools as _tools,
		user,
		workspaceActions,
		workspaceCounts
	} from '$lib/stores';

	import { goto } from '$app/navigation';
	import {
		createNewTool,
		loadToolByUrl,
		deleteToolById,
		exportTools,
		getToolById,
		getToolList,
		getTools
	} from '$lib/apis/tools';
	import { capitalizeFirstLetter } from '$lib/utils';
	import { getGroups } from '$lib/apis/groups';
	import { getOwnership, ownershipToneClass } from '$lib/utils/ownership';

	import Tooltip from '../common/Tooltip.svelte';
	import ConfirmDialog from '../common/ConfirmDialog.svelte';
	import ToolMenu from './Tools/ToolMenu.svelte';
	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import ValvesModal from './common/ValvesModal.svelte';
	import ManifestModal from './common/ManifestModal.svelte';
	import Heart from '../icons/Heart.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import GarbageBin from '../icons/GarbageBin.svelte';
	import Search from '../icons/Search.svelte';
	import Spinner from '../common/Spinner.svelte';
	import XMark from '../icons/XMark.svelte';
	import ImportModal from '../ImportModal.svelte';
	import CommunityDiscover from './common/CommunityDiscover.svelte';

	let shiftKey = false;
	let loaded = false;

	let toolsImportInputElement: HTMLInputElement;
	let importFiles;

	let showConfirm = false;
	let query = '';
	let searchDebounceTimer: ReturnType<typeof setTimeout>;

	let showManifestModal = false;
	let showValvesModal = false;
	let selectedTool = null;

	let showDeleteConfirm = false;

	let tools = [];
	let filteredItems = [];

	let viewOption = '';
	let sortKey = 'updated_at';
	let sortDirection = 'desc';
	let openToolMenuId: string | null = null;

	let showImportModal = false;

	$: if (loaded) {
		workspaceActions.set([
			{
				id: 'tools-new',
				label: $i18n.t('Create'),
				href: '/workspace/tools/create'
			},
			{
				id: 'tools-import-link',
				label: $i18n.t('Import From Link'),
				onClick: () => {
					showImportModal = true;
				},
				visible: $user?.role === 'admin'
			},
			{
				id: 'tools-import',
				label: $i18n.t('Import JSON'),
				onClick: () => toolsImportInputElement?.click(),
				visible: $user?.role === 'admin' || $user?.permissions?.workspace?.tools_import
			},
			{
				id: 'tools-export',
				label: $i18n.t('Export JSON'),
				onClick: async () => {
					const _tools = await exportTools(localStorage.token).catch((error) => {
						toast.error(`${error}`);
						return null;
					});

					if (_tools) {
						let blob = new Blob([JSON.stringify(_tools)], {
							type: 'application/json'
						});
						saveAs(blob, `tools-export-${Date.now()}.json`);
					}
				},
				visible: $user?.role === 'admin' || $user?.permissions?.workspace?.tools_export
			}
		]);
	}

	const handleSearchInput = () => {
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(() => {
			setFilteredItems();
		}, 300);
	};

	$: if (
		tools &&
		viewOption !== undefined &&
		sortKey !== undefined &&
		sortDirection !== undefined
	) {
		setFilteredItems();
	}

	const setFilteredItems = () => {
		const filtered = tools.filter((t) => {
			if (query === '' && viewOption === '') return true;
			const lowerQuery = query.toLowerCase();
			return (
				((t.name || '').toLowerCase().includes(lowerQuery) ||
					(t.id || '').toLowerCase().includes(lowerQuery) ||
					(t.user?.name || '').toLowerCase().includes(lowerQuery) || // Search by user name
					(t.user?.email || '').toLowerCase().includes(lowerQuery)) && // Search by user email
				(viewOption === '' ||
					(viewOption === 'created' && t.user_id === $user?.id) ||
					(viewOption === 'shared' && t.user_id !== $user?.id))
			);
		});

		filteredItems = [...filtered].sort((a, b) => {
			const direction = sortDirection === 'asc' ? 1 : -1;

			if (sortKey === 'name') {
				return direction * (a.name ?? '').localeCompare(b.name ?? '');
			}

			return direction * ((a.updated_at ?? 0) - (b.updated_at ?? 0));
		});

		workspaceCounts.update((counts) => ({ ...counts, tools: filteredItems.length }));
	};


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
		{ value: 'shared', label: $i18n.t('Shared with me') }
	];

	const setViewOption = (value: string) => {
		viewOption = value;
		localStorage.workspaceViewOption = value;
	};

	const setSort = (value: string) => {
		const [key, dir] = value.split(':');
		sortKey = key;
		sortDirection = dir;
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

	const openTool = (tool) => {
		goto(`/workspace/tools/edit?id=${encodeURIComponent(tool.id)}`);
	};


	const shareHandler = async (tool) => {
		const item = await getToolById(localStorage.token, tool.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		// LICENSE covers this Open WebUI Community wordmark.
		// Do not alter, remove, obscure, or replace it except as LICENSE permits:
		// https://docs.openwebui.com/license.
		toast.success($i18n.t('Redirecting you to Open WebUI Community'));

		const url = 'https://openwebui.com';

		const tab = await window.open(`${url}/tools/create`, '_blank');

		const messageHandler = (event) => {
			if (event.origin !== url) return;
			if (event.data === 'loaded') {
				tab.postMessage(JSON.stringify(item), '*');
				window.removeEventListener('message', messageHandler);
			}
		};

		window.addEventListener('message', messageHandler, false);
		console.log(item);
	};

	const cloneHandler = async (tool) => {
		const _tool = await getToolById(localStorage.token, tool.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (_tool) {
			sessionStorage.tool = JSON.stringify({
				..._tool,
				id: `${_tool.id}_clone`,
				name: `${_tool.name} (Clone)`
			});
			goto('/workspace/tools/create');
		}
	};

	const exportHandler = async (tool) => {
		const _tool = await getToolById(localStorage.token, tool.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (_tool) {
			let blob = new Blob([JSON.stringify([_tool])], {
				type: 'application/json'
			});
			saveAs(blob, `tool-${_tool.id}-export-${Date.now()}.json`);
		}
	};

	const deleteHandler = async (tool) => {
		const res = await deleteToolById(localStorage.token, tool.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Tool deleted successfully'));
			await init();
		}
	};

	const init = async () => {
		tools = await getToolList(localStorage.token);
		_tools.set(await getTools(localStorage.token));
	};

	onMount(async () => {
		viewOption = localStorage?.workspaceViewOption || '';
		await init();
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
		{$i18n.t('Tools')} / {$WEBUI_NAME}
	</title>
</svelte:head>

<ImportModal
	bind:show={showImportModal}
	onImport={(tool) => {
		sessionStorage.tool = JSON.stringify({
			...tool
		});
		goto('/workspace/tools/create');
	}}
	loadUrlHandler={async (url) => {
		return await loadToolByUrl(localStorage.token, url);
	}}
	successMessage={$i18n.t('Tool imported successfully')}
/>

{#if loaded}
	<input
		id="documents-import-input"
		bind:this={toolsImportInputElement}
		bind:files={importFiles}
		type="file"
		accept=".json"
		hidden
		on:change={() => {
			console.log(importFiles);
			showConfirm = true;
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
				aria-label={$i18n.t('Search Tools')}
				placeholder={$i18n.t('Search tools by name, ID or owner')}
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

		{#if (filteredItems ?? []).length !== 0}
			<ul class="grid gap-2.5 md:grid-cols-2">
				{#each filteredItems as tool (tool.id)}
					{@const own = getOwnership(tool, $user?.id, groupNames, (k, o) => $i18n.t(k, o))}
					<li class="group relative">
						<svelte:element
							this={tool.write_access ? 'button' : 'div'}
							type={tool.write_access ? 'button' : undefined}
							class="flex h-full w-full flex-col rounded-xl border border-gray-200 px-4 py-3 text-left dark:border-gray-800 {tool.write_access
								? 'transition hover:border-gray-400 hover:bg-gray-50 focus-visible:border-gray-500 dark:hover:border-gray-600 dark:hover:bg-gray-850'
								: ''}"
							on:click={() => {
								if (tool.write_access) openTool(tool);
							}}
						>
							<div class="flex w-full items-center gap-2 {tool.write_access ? 'pr-24' : ''}">
								<span class="min-w-0 flex-1 truncate text-sm font-semibold">{tool.name}</span>
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
								{tool?.meta?.description || $i18n.t('No description')}
							</div>

							<div class="mt-2 flex w-full flex-wrap items-center gap-x-1.5 gap-y-1 text-[0.6875rem] text-gray-500">
								<span class="font-mono">{tool.id}</span>
								{#if tool?.meta?.manifest?.version}
									<span aria-hidden="true">·</span>
									<span>v{tool.meta.manifest.version}</span>
								{/if}
								<span aria-hidden="true">·</span>
								<span title={dayjs(tool.updated_at * 1000).format('LLLL')}>
									{$i18n.t('updated {{time}}', { time: dayjs(tool.updated_at * 1000).fromNow() })}
								</span>
								<span aria-hidden="true">·</span>
								<span class="truncate" title={tool?.user?.email ?? ''}>{ownerOf(tool)}</span>
								{#if !tool.write_access}
									<span aria-hidden="true">·</span>
									<span>{$i18n.t('Read Only')}</span>
								{/if}
							</div>
						</svelte:element>

						{#if tool.write_access}
							<!-- Card actions sit outside the card button (no nested buttons). -->
							<div class="absolute top-2 right-2 flex items-center gap-0.5">
								{#if shiftKey}
									<Tooltip content={$i18n.t('Delete')}>
										<button
											class="flex size-7 items-center justify-center rounded-lg text-gray-400 transition hover:bg-gray-100 hover:text-red-600 dark:hover:bg-gray-800"
											type="button"
											aria-label={$i18n.t('Delete')}
											on:click={() => deleteHandler(tool)}
										>
											<GarbageBin className="size-4" />
										</button>
									</Tooltip>
								{:else}
									{#if tool?.meta?.manifest?.funding_url ?? false}
										<Tooltip content={$i18n.t('Support')}>
											<button
												class="flex size-7 items-center justify-center rounded-lg text-gray-400 transition hover:bg-gray-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200"
												type="button"
												aria-label={$i18n.t('Support')}
												on:click={() => {
													selectedTool = tool;
													showManifestModal = true;
												}}
											>
												<Heart className="size-4" />
											</button>
										</Tooltip>
									{/if}

									<Tooltip content={$i18n.t('Settings (valves)')}>
										<button
											class="flex size-7 items-center justify-center rounded-lg text-gray-400 transition hover:bg-gray-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200"
											type="button"
											aria-label={$i18n.t('Valves')}
											on:click={() => {
												selectedTool = tool;
												showValvesModal = true;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="1.5"
												stroke="currentColor"
												class="size-4"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z"
												/>
												<path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
											</svg>
										</button>
									</Tooltip>

									<ToolMenu
										show={openToolMenuId === tool.id}
										editHandler={() => {
											goto(`/workspace/tools/edit?id=${encodeURIComponent(tool.id)}`);
										}}
										shareHandler={() => {
											shareHandler(tool);
										}}
										cloneHandler={() => {
											cloneHandler(tool);
										}}
										exportHandler={() => {
											exportHandler(tool);
										}}
										deleteHandler={async () => {
											selectedTool = tool;
											showDeleteConfirm = true;
										}}
										onClose={() => {
											openToolMenuId = null;
										}}
									>
										<button
											class="flex size-7 items-center justify-center rounded-lg text-gray-400 transition hover:bg-gray-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200"
											type="button"
											aria-label={$i18n.t('Tool Menu')}
											on:click={() => {
												openToolMenuId = openToolMenuId === tool.id ? null : tool.id;
											}}
										>
											<EllipsisHorizontal className="size-4" />
										</button>
									</ToolMenu>
								{/if}
							</div>
						{/if}
					</li>
				{/each}
			</ul>
		{:else if isFiltered}
			<div class="py-16 text-center">
				<div class="text-sm">{$i18n.t('Nothing matches your search')}</div>
				<div class="mt-1 text-xs text-gray-500">
					{$i18n.t('Try another word, or switch the filter back to All.')}
				</div>
			</div>
		{:else}
			<div class="mx-auto flex max-w-sm flex-col items-center py-16 text-center">
				<div class="text-base font-semibold">{$i18n.t('No tools yet')}</div>
				<p class="mt-1 text-sm text-gray-500">
					{$i18n.t(
						'A tool lets a model call code or another system, e.g. look up an order. Tools run code on the server, so only add ones you trust.'
					)}
				</p>
				<a
					href="/workspace/tools/create"
					class="mt-4 rounded-lg bg-black px-4 py-2 text-sm font-semibold text-white transition hover:bg-gray-800 dark:bg-white dark:text-black dark:hover:bg-gray-200"
				>
					+ {$i18n.t('New tool')}
				</a>
			</div>
		{/if}
	</div>

	{#if $config?.features.enable_community_sharing}
		<CommunityDiscover
			href="https://openwebui.com/tools"
			title={$i18n.t('Discover a tool')}
			description={$i18n.t('Discover, download, and explore custom tools')}
		/>
	{/if}

	<DeleteConfirmDialog
		bind:show={showDeleteConfirm}
		title={$i18n.t('Delete tool?')}
		on:confirm={() => {
			deleteHandler(selectedTool);
		}}
	>
		<div class=" text-sm text-gray-500 truncate">
			{$i18n.t('This will delete')} <span class="  font-normal">{selectedTool.name}</span>.
		</div>
	</DeleteConfirmDialog>

	<ValvesModal bind:show={showValvesModal} type="tool" id={selectedTool?.id ?? null} />
	<ManifestModal bind:show={showManifestModal} manifest={selectedTool?.meta?.manifest ?? {}} />

	<ConfirmDialog
		bind:show={showConfirm}
		on:confirm={() => {
			const reader = new FileReader();
			reader.onload = async (event) => {
				const _tools = JSON.parse(event.target.result);
				console.log(_tools);

				for (const tool of _tools) {
					const res = await createNewTool(localStorage.token, tool).catch((error) => {
						toast.error(`${error}`);
						return null;
					});
				}

				toast.success($i18n.t('Tool imported successfully'));
				await init();
				importFiles = null;
				toolsImportInputElement.value = '';
			};

			reader.readAsText(importFiles[0]);
		}}
	>
		<div class="text-sm text-gray-500">
			<div class=" bg-yellow-500/20 text-yellow-700 dark:text-yellow-200 rounded-lg px-4 py-3">
				<div>{$i18n.t('Please carefully review the following warnings:')}</div>

				<ul class=" mt-1 list-disc pl-4 text-xs">
					<li>
						{$i18n.t('Tools have a function calling system that allows arbitrary code execution.')}.
					</li>
					<li>{$i18n.t('Do not install tools from sources you do not fully trust.')}</li>
				</ul>
			</div>

			<div class="my-3">
				{$i18n.t(
					'I acknowledge that I have read and I understand the implications of my action. I am aware of the risks associated with executing arbitrary code and I have verified the trustworthiness of the source.'
				)}
			</div>
		</div>
	</ConfirmDialog>
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner className="size-5" />
	</div>
{/if}
