<script lang="ts">
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	dayjs.extend(relativeTime);

	import { goto } from '$app/navigation';
	import { onMount, getContext, tick, onDestroy } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { WEBUI_NAME, config, user, workspaceActions, workspaceCounts } from '$lib/stores';

	import {
		createNewPrompt,
		deletePromptById,
		togglePromptById,
		getPromptItems,
		getPromptTags
	} from '$lib/apis/prompts';
	import { capitalizeFirstLetter, slugify, copyToClipboard } from '$lib/utils';
	import { getGroups } from '$lib/apis/groups';
	import { getOwnership, ownershipToneClass } from '$lib/utils/ownership';

	import PromptMenu from './Prompts/PromptMenu.svelte';
	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import Clipboard from '../icons/Clipboard.svelte';
	import Check from '../icons/Check.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Modal from '../common/Modal.svelte';
	import PromptEditor from './Prompts/PromptEditor.svelte';
	import Search from '../icons/Search.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import XMark from '../icons/XMark.svelte';
	import GarbageBin from '../icons/GarbageBin.svelte';
	import CommunityDiscover from './common/CommunityDiscover.svelte';
	import Switch from '../common/Switch.svelte';
	import Pagination from '../common/Pagination.svelte';

	type PromptDraft = {
		id?: string;
		name: string;
		command: string;
		content: string;
		tags: string[];
		access_grants: any[];
		commit_message?: string;
		is_production?: boolean;
	};

	export let showCreateOnMount = false;
	export let createModalCloseHref = '';

	let shiftKey = false;

	const i18n = getContext<Writable<i18nType>>('i18n');
	let promptsImportInputElement: HTMLInputElement;
	let loaded = false;

	let importFiles = null;
	let query = '';
	let searchDebounceTimer: ReturnType<typeof setTimeout>;

	let prompts = null;
	let tags = [];
	let total = null;
	let loading = false;

	let showDeleteConfirm = false;
	let showCreateModal = false;
	let createPrompt: PromptDraft | null = null;
	let deletePrompt = null;

	let viewOption = '';
	let selectedTag = '';
	let copiedId: string | null = null;
	let sortKey = 'updated_at';
	let sortDirection = 'desc';
	let openPromptMenuId: string | null = null;

	let page = 1;

	$: if (loaded) {
		workspaceActions.set([
			{
				id: 'prompts-new',
				label: $i18n.t('Create'),
				onClick: () => {
					createPrompt = null;
					showCreateModal = true;
				}
			},
			{
				id: 'prompts-import',
				label: $i18n.t('Import JSON'),
				onClick: () => promptsImportInputElement?.click(),
				visible: $user?.role === 'admin' || $user?.permissions?.workspace?.prompts_import
			},
			{
				id: 'prompts-export',
				label: $i18n.t('Export JSON'),
				onClick: async () => {
					let blob = new Blob([JSON.stringify(prompts)], {
						type: 'application/json'
					});
					saveAs(blob, `prompts-export-${Date.now()}.json`);
				},
				visible: $user?.role === 'admin' || $user?.permissions?.workspace?.prompts_export
			}
		]);
	}

	const handleSearchInput = () => {
		loading = true;
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(() => {
			if (page !== 1) {
				page = 1;
			} else {
				getPromptList();
			}
		}, 300);
	};

	// Immediate response to page/filter changes
	$: if (
		loaded &&
		page &&
		selectedTag !== undefined &&
		viewOption !== undefined &&
		sortKey !== undefined &&
		sortDirection !== undefined
	) {
		getPromptList();
	}

	// Sharing badge per card ("Weidmann", team name, "Mine").
	let groupNames: Record<string, string> = {};
	getGroups(localStorage.token)
		.then((groups) => {
			groupNames = Object.fromEntries((groups ?? []).map((g) => [g.id, g.name]));
		})
		.catch(() => {});

	// Filter chips (same values the backend's view_option accepts).
	$: viewChips = [
		{ value: '', label: $i18n.t('All') },
		{ value: 'created', label: $i18n.t('Created by me') },
		{ value: 'shared', label: $i18n.t('Shared with me') }
	];

	const setViewOption = (value: string) => {
		viewOption = value;
		localStorage.workspaceViewOption = value;
		page = 1;
	};

	$: isFiltered = query.trim() !== '' || viewOption !== '' || selectedTag !== '';

	const oneLine = (text: string) => (text ?? '').replace(/\s+/g, ' ').trim();

	const ownerOf = (prompt) => {
		if (prompt?.user_id && prompt.user_id === $user?.id) return $i18n.t('owned by you');
		const name = prompt?.user?.name ?? prompt?.user?.email;
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

	const openPrompt = (prompt) => {
		goto(`/workspace/prompts/${prompt.id}`);
	};

	const getPromptList = async () => {
		if (!loaded) return;

		loading = true;
		try {
			const res = await getPromptItems(
				localStorage.token,
				query,
				viewOption,
				selectedTag,
				sortKey,
				sortDirection,
				page
			).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			if (res) {
				prompts = res.items;
				total = res.total;
				workspaceCounts.update((counts) => ({ ...counts, prompts: total }));

				// get tags
				tags = await getPromptTags(localStorage.token).catch((error) => {
					toast.error(`${error}`);
					return [];
				});
			}
		} catch (err) {
			console.error(err);
		} finally {
			loading = false;
		}
	};

	const shareHandler = async (prompt) => {
		// LICENSE covers this Open WebUI Community wordmark.
		// Do not alter, remove, obscure, or replace it except as LICENSE permits:
		// https://docs.openwebui.com/license.
		toast.success($i18n.t('Redirecting you to Open WebUI Community'));

		const url = 'https://openwebui.com';

		const tab = await window.open(`${url}/prompts/create`, '_blank');
		window.addEventListener(
			'message',
			(event) => {
				if (event.origin !== url) return;
				if (event.data === 'loaded') {
					tab.postMessage(JSON.stringify(prompt), '*');
				}
			},
			false
		);
	};

	const toPromptDraft = (prompt: any): PromptDraft => ({
		name: prompt.name || prompt.title || 'Prompt',
		command: prompt.command || '',
		content: prompt.content || '',
		tags: prompt.tags || [],
		access_grants: prompt.access_grants !== undefined ? prompt.access_grants : []
	});

	const openCreateModal = (prompt: PromptDraft | null = null) => {
		createPrompt = prompt;
		showCreateModal = true;
	};

	const closeCreateModal = async () => {
		showCreateModal = false;
		createPrompt = null;

		if (createModalCloseHref) {
			await goto(createModalCloseHref);
		}
	};

	const createPromptHandler = async (prompt: PromptDraft) => {
		const res = await createNewPrompt(localStorage.token, prompt).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Prompt created successfully'));
			page = 1;
			await getPromptList();
			await closeCreateModal();
		}
	};

	const cloneHandler = async (prompt) => {
		const clonedPrompt = { ...prompt };

		clonedPrompt.name = `${clonedPrompt.name} (Clone)`;
		const baseCommand = clonedPrompt.command.startsWith('/')
			? clonedPrompt.command.substring(1)
			: clonedPrompt.command;
		clonedPrompt.command = slugify(`${baseCommand} clone`);

		openCreateModal(toPromptDraft(clonedPrompt));
	};

	const exportHandler = async (prompt) => {
		let blob = new Blob([JSON.stringify([prompt])], {
			type: 'application/json'
		});
		saveAs(blob, `prompt-export-${Date.now()}.json`);
	};

	const copyHandler = async (prompt) => {
		const res = await copyToClipboard(prompt.content);
		if (res) {
			copiedId = prompt.command;
			setTimeout(() => {
				copiedId = null;
			}, 2000);
		}
	};

	const deleteHandler = async (prompt) => {
		const command = prompt.command;

		const res = await deletePromptById(localStorage.token, prompt.id).catch((err) => {
			toast.error(err);
			return null;
		});

		if (res) {
			toast.success($i18n.t(`Deleted {{name}}`, { name: command }));
		}

		page = 1;
		getPromptList();
	};

	onMount(async () => {
		viewOption = localStorage?.workspaceViewOption || '';
		loaded = true;

		const onMessage = async (event: MessageEvent) => {
			if (
				!['https://openwebui.com', 'https://www.openwebui.com', 'http://localhost:9999'].includes(
					event.origin
				)
			) {
				return;
			}

			openCreateModal(toPromptDraft(JSON.parse(event.data)));
		};

		window.addEventListener('message', onMessage);

		if (window.opener ?? false) {
			window.opener.postMessage('loaded', '*');
		}

		if (sessionStorage.prompt) {
			const prompt = JSON.parse(sessionStorage.prompt);
			sessionStorage.removeItem('prompt');
			openCreateModal(toPromptDraft(prompt));
		} else if (showCreateOnMount) {
			openCreateModal();
		}

		const onKeyDown = (event: KeyboardEvent) => {
			if (event.key === 'Shift') {
				shiftKey = true;
			}
		};

		const onKeyUp = (event: KeyboardEvent) => {
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
			window.removeEventListener('message', onMessage);
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
		{$i18n.t('Prompts')} / {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<DeleteConfirmDialog
		bind:show={showDeleteConfirm}
		title={$i18n.t('Delete prompt?')}
		on:confirm={() => {
			deleteHandler(deletePrompt);
		}}
	>
		<div class=" text-sm text-gray-500 truncate">
			{$i18n.t('This will delete')} <span class="  font-normal">{deletePrompt.command}</span>.
		</div>
	</DeleteConfirmDialog>

	<Modal bind:show={showCreateModal} size="md" className="bg-white dark:bg-gray-900 rounded-2xl">
		{#key createPrompt}
			<PromptEditor
				modal={true}
				prompt={createPrompt}
				clone={createPrompt !== null}
				onSubmit={createPromptHandler}
				onCancel={() => {
					closeCreateModal();
				}}
			/>
		{/key}
	</Modal>

	<input
		id="prompts-import-input"
		bind:this={promptsImportInputElement}
		bind:files={importFiles}
		type="file"
		accept=".json"
		hidden
		on:change={() => {
			console.log(importFiles);
			if (!importFiles || importFiles.length === 0) return;

			const reader = new FileReader();
			reader.onload = async (event) => {
				const savedPrompts = JSON.parse(event.target.result);
				console.log(savedPrompts);

				try {
					for (const prompt of savedPrompts) {
						await createNewPrompt(localStorage.token, {
							command: prompt.command,
							name: prompt.name,
							content: prompt.content
						}).catch((error) => {
							toast.error(typeof error === 'string' ? error : JSON.stringify(error));
							return null;
						});
					}

					page = 1;
					await getPromptList();
				} finally {
					importFiles = null;
					promptsImportInputElement.value = '';
				}
			};

			reader.readAsText(importFiles[0]);
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
				aria-label={$i18n.t('Search Prompts')}
				placeholder={$i18n.t('Search prompts, e.g. "meeting minutes"')}
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

			<div class="ml-auto flex flex-wrap items-center gap-3">
				{#if (tags ?? []).length > 0}
					<label class="flex items-center gap-1.5 text-xs text-gray-500">
						{$i18n.t('Topic')}
						<select class={selectClass} bind:value={selectedTag} on:change={() => (page = 1)}>
							<option value="">{$i18n.t('All topics')}</option>
							{#each tags as tag (tag)}
								<option value={tag}>{tag}</option>
							{/each}
						</select>
					</label>
				{/if}

				<label class="flex items-center gap-1.5 text-xs text-gray-500">
					{$i18n.t('Sort')}
					<select
						class={selectClass}
						value={`${sortKey}:${sortDirection}`}
						on:change={(e) => {
							const [key, dir] = e.currentTarget.value.split(':');
							sortKey = key;
							sortDirection = dir;
							page = 1;
						}}
					>
						<option value="updated_at:desc">{$i18n.t('Recently updated')}</option>
						<option value="name:asc">{$i18n.t('Name (A–Z)')}</option>
						<option value="name:desc">{$i18n.t('Name (Z–A)')}</option>
						<option value="updated_at:asc">{$i18n.t('Oldest first')}</option>
					</select>
				</label>
			</div>
		</div>

		{#if prompts === null || loading}
			<div class="flex w-full items-center justify-center py-10">
				<Spinner className="size-5" />
			</div>
		{:else if (prompts ?? []).length !== 0}
			<ul class="grid gap-2.5 md:grid-cols-2">
				{#each prompts as prompt (prompt.id)}
					{@const own = getOwnership(prompt, $user?.id, groupNames, (k, o) => $i18n.t(k, o))}
					{@const enabled = prompt.is_active !== false}
					<li class="group relative">
						<button
							type="button"
							class="flex h-full w-full flex-col rounded-xl border border-gray-200 px-4 pt-3 pb-3 text-left transition hover:border-gray-400 hover:bg-gray-50 focus-visible:border-gray-500 dark:border-gray-800 dark:hover:border-gray-600 dark:hover:bg-gray-850 {enabled
								? ''
								: 'opacity-60'}"
							on:click={() => openPrompt(prompt)}
						>
							<div class="flex w-full items-center gap-2 pr-16">
								<span class="min-w-0 flex-1 truncate text-sm font-semibold">{prompt.name}</span>
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
								{oneLine(prompt.content) || $i18n.t('No content')}
							</div>

							<div
								class="mt-2 flex w-full flex-wrap items-center gap-x-1.5 gap-y-1 pr-12 text-[0.6875rem] text-gray-500"
							>
								<span class="font-mono">/{prompt.command}</span>
								<span aria-hidden="true">·</span>
								<span
									title={dayjs((prompt.updated_at ?? prompt.created_at) * 1000).format('LLLL')}
								>
									{$i18n.t('updated {{time}}', {
										time: dayjs((prompt.updated_at ?? prompt.created_at) * 1000).fromNow()
									})}
								</span>
								<span aria-hidden="true">·</span>
								<span class="truncate" title={prompt?.user?.email ?? ''}>{ownerOf(prompt)}</span>
								{#if !prompt.write_access}
									<span aria-hidden="true">·</span>
									<span>{$i18n.t('Read Only')}</span>
								{/if}
								{#if !enabled}
									<span aria-hidden="true">·</span>
									<span>{$i18n.t('Disabled')}</span>
								{/if}
								{#each prompt.tags ?? [] as tag (tag)}
									<span
										class="rounded-full border border-gray-200 px-1.5 text-[0.625rem] text-gray-600 dark:border-gray-700 dark:text-gray-400"
									>
										{tag}
									</span>
								{/each}
							</div>
						</button>

						<!-- Card actions sit outside the card button (no nested buttons). -->
						<div class="absolute top-2 right-2 flex items-center gap-0.5">
							{#if shiftKey}
								<Tooltip content={$i18n.t('Delete')}>
									<button
										class="flex size-7 items-center justify-center rounded-lg text-gray-400 transition hover:bg-gray-100 hover:text-red-600 dark:hover:bg-gray-800"
										type="button"
										aria-label={$i18n.t('Delete')}
										on:click={() => deleteHandler(prompt)}
									>
										<GarbageBin className="size-4" />
									</button>
								</Tooltip>
							{:else}
								<Tooltip content={$i18n.t('Copy Prompt')}>
									<button
										class="flex size-7 items-center justify-center rounded-lg text-gray-400 opacity-0 transition group-hover:opacity-100 focus-visible:opacity-100 hover:bg-gray-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200 {copiedId ===
										prompt.command
											? 'opacity-100'
											: ''}"
										type="button"
										aria-label={$i18n.t('Copy Prompt')}
										on:click={() => copyHandler(prompt)}
									>
										{#if copiedId === prompt.command}
											<Check className="size-4" strokeWidth="1.5" />
										{:else}
											<Clipboard className="size-4" strokeWidth="1.5" />
										{/if}
									</button>
								</Tooltip>

								<PromptMenu
									show={openPromptMenuId === prompt.id}
									editHandler={() => {
										goto(`/workspace/prompts/${prompt.id}`);
									}}
									shareHandler={() => {
										shareHandler(prompt);
									}}
									cloneHandler={() => {
										cloneHandler(prompt);
									}}
									exportHandler={() => {
										exportHandler(prompt);
									}}
									deleteHandler={async () => {
										deletePrompt = prompt;
										showDeleteConfirm = true;
									}}
									onClose={() => {
										openPromptMenuId = null;
									}}
								>
									<button
										class="flex size-7 items-center justify-center rounded-lg text-gray-400 transition hover:bg-gray-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200"
										type="button"
										aria-label={$i18n.t('Prompt Menu')}
										on:click={() => {
											openPromptMenuId = openPromptMenuId === prompt.id ? null : prompt.id;
										}}
									>
										<EllipsisHorizontal className="size-4" />
									</button>
								</PromptMenu>
							{/if}
						</div>

						<div class="absolute right-3 bottom-3">
							<Tooltip content={enabled ? $i18n.t('Enabled') : $i18n.t('Disabled')}>
								<Switch
									bind:state={prompt.is_active}
									on:change={async () => {
										togglePromptById(localStorage.token, prompt.id);
									}}
								/>
							</Tooltip>
						</div>
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
				<div class="text-base font-semibold">{$i18n.t('No prompts yet')}</div>
				<p class="mt-1 text-sm text-gray-500">
					{$i18n.t(
						'A prompt saves instructions you type often. Use it with / in the message box, or from the Prompts & skills library.'
					)}
				</p>
				<button
					type="button"
					class="mt-4 rounded-lg bg-black px-4 py-2 text-sm font-semibold text-white transition hover:bg-gray-800 dark:bg-white dark:text-black dark:hover:bg-gray-200"
					on:click={() => openCreateModal()}
				>
					+ {$i18n.t('New prompt')}
				</button>
			</div>
		{/if}
	</div>

	{#if $config?.features.enable_community_sharing}
		<CommunityDiscover
			href="https://openwebui.com/prompts"
			title={$i18n.t('Discover a prompt')}
			description={$i18n.t('Discover, download, and explore custom prompts')}
		/>
	{/if}
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner className="size-5" />
	</div>
{/if}
