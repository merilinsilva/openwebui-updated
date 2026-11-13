<script lang="ts">
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import { toast } from 'svelte-sonner';
	import Sortable from 'sortablejs';

	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { onMount, getContext, tick } from 'svelte';
	import { goto } from '$app/navigation';
	const i18n = getContext('i18n');
	dayjs.extend(relativeTime);

	import {
		WEBUI_NAME,
		config,
		mobile,
		models as _models,
		pinnedModels,
		settings,
		user,
		workspaceActions,
		workspaceCounts
	} from '$lib/stores';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import {
		createNewModel,
		deleteModelById,
		getModelById,
		getModelItems as getWorkspaceModels,
		getModelTags,
		toggleModelById,
		updateModelById
	} from '$lib/apis/models';

	import { getModels } from '$lib/apis';
	import { getGroups } from '$lib/apis/groups';
	import { updateUserSettings } from '$lib/apis/users';

	import { capitalizeFirstLetter, copyToClipboard } from '$lib/utils';
	import { getOwnership, ownershipToneClass } from '$lib/utils/ownership';

	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import CheckCircle from '../icons/CheckCircle.svelte';
	import Minus from '../icons/Minus.svelte';
	import ModelMenu from './Models/ModelMenu.svelte';
	import ModelDeleteConfirmDialog from '../common/ConfirmDialog.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import GarbageBin from '../icons/GarbageBin.svelte';
	import Search from '../icons/Search.svelte';
	import Switch from '../common/Switch.svelte';
	import Spinner from '../common/Spinner.svelte';
	import XMark from '../icons/XMark.svelte';
	import EyeSlash from '../icons/EyeSlash.svelte';
	import Eye from '../icons/Eye.svelte';
	import ChevronDown from '../icons/ChevronDown.svelte';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import CommunityDiscover from './common/CommunityDiscover.svelte';
	import Pagination from '../common/Pagination.svelte';

	let shiftKey = false;

	let importFiles;
	let modelsImportInputElement: HTMLInputElement;

	let loaded = false;

	let showModelDeleteConfirm = false;

	let selectedModel = null;

	let groupIds = [];

	let tags = [];
	let selectedTag = '';

	let query = '';
	let viewOption = '';
	let sortKey = 'updated_at';
	let sortDirection = 'desc';

	let page = 1;
	let models = null;
	let total = null;

	let searchDebounceTimer;

	$: if (loaded) {
		workspaceActions.set([
			{
				id: 'models-new',
				label: $i18n.t('Create'),
				href: '/workspace/models/create'
			},
			{
				id: 'models-import',
				label: $i18n.t('Import JSON'),
				onClick: () => modelsImportInputElement?.click(),
				visible: $user?.role === 'admin' || $user?.permissions?.workspace?.models_import
			},
			{
				id: 'models-export',
				label: $i18n.t('Export JSON'),
				onClick: async () => {
					await downloadModels(models);
				},
				visible: $user?.role === 'admin' || $user?.permissions?.workspace?.models_export
			}
		]);
	}

	$: if (
		loaded &&
		page !== undefined &&
		selectedTag !== undefined &&
		viewOption !== undefined &&
		sortKey !== undefined &&
		sortDirection !== undefined
	) {
		getModelList();
	}

	// Sharing badge per card ("Weidmann", team name, "Mine"); filled from the groups loaded on mount.
	let groupNames: Record<string, string> = {};

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

	const ownerOf = (model) => {
		if (model?.user_id && model.user_id === $user?.id) return $i18n.t('owned by you');
		const name = model?.user?.name ?? model?.user?.email;
		return name
			? $i18n.t('owned by {{name}}', { name: capitalizeFirstLetter(name) })
			: $i18n.t('Deleted User');
	};

	// Editable models open in the editor; read-only ones start a chat.
	const openCard = (model) => {
		if (model.write_access) {
			openModel(model);
		} else {
			goto(`/?model=${encodeURIComponent(model.id)}`);
		}
	};

	const chipClass = (active: boolean) =>
		`shrink-0 rounded-full border px-3 py-1 text-xs transition ${
			active
				? 'border-red-500 bg-red-50 text-red-700 dark:border-red-500 dark:bg-red-950/40 dark:text-red-300'
				: 'border-gray-200 text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-850'
		}`;

	const selectClass =
		'rounded-lg border border-gray-300 bg-white px-2 py-1 text-xs text-gray-800 outline-hidden focus:border-gray-500 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200 dark:scheme-dark';

	const openModel = (model) => {
		if (model.write_access) {
			goto(`/workspace/models/edit?id=${encodeURIComponent(model.id)}`);
		}
	};

	const getModelList = async () => {
		if (!loaded) return;

		try {
			const res = await getWorkspaceModels(
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
				models = res.items;
				total = res.total;
				workspaceCounts.update((counts) => ({ ...counts, models: total }));

				// get tags
				tags = await getModelTags(localStorage.token).catch((error) => {
					toast.error(`${error}`);
					return [];
				});
			}
		} catch (err) {
			console.error(err);
		}
	};

	const deleteModelHandler = async (model) => {
		const res = await deleteModelById(localStorage.token, model.id).catch((e) => {
			toast.error(`${e}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t(`Deleted {{name}}`, { name: model.id }));

			page = 1;
			getModelList();
		}

		await _models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			)
		);
	};

	const getFullModel = async (model: any) =>
		(await getModelById(localStorage.token, model.id).catch(() => null)) ?? model;

	const cloneModelHandler = async (model) => {
		model = await getFullModel(model);
		sessionStorage.model = JSON.stringify({
			...model,
			id: `${model.id}-clone`,
			name: `${model.name} (Clone)`
		});
		goto('/workspace/models/create');
	};

	const shareModelHandler = async (model) => {
		// LICENSE covers this Open WebUI Community wordmark.
		// Do not alter, remove, obscure, or replace it except as LICENSE permits:
		// https://docs.openwebui.com/license.
		toast.success($i18n.t('Redirecting you to Open WebUI Community'));

		const url = 'https://openwebui.com';
		const fullModel = getFullModel(model);

		const tab = await window.open(`${url}/post?type=model`, '_blank');

		const messageHandler = async (event) => {
			if (event.origin !== url) return;
			if (event.data === 'loaded') {
				tab.postMessage(JSON.stringify(await fullModel), '*');
				window.removeEventListener('message', messageHandler);
			}
		};

		window.addEventListener('message', messageHandler, false);
	};

	const hideModelHandler = async (model) => {
		const updatedModel = {
			...model,
			meta: {
				...model.meta,
				hidden: !(model?.meta?.hidden ?? false)
			}
		};

		const res = await updateModelById(localStorage.token, updatedModel.id, updatedModel);

		if (res) {
			models = models.map((model) => (model.id === updatedModel.id ? updatedModel : model));
			toast.success(
				$i18n.t(`Model {{name}} is now {{status}}`, {
					name: updatedModel.id,
					status: updatedModel.meta.hidden ? 'hidden' : 'visible'
				})
			);

			page = 1;
			await getModelList();
		}

		await _models.set(
			await getModels(
				localStorage.token,
				$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
			)
		);
	};

	const copyLinkHandler = async (model) => {
		const baseUrl = window.location.origin;
		const res = await copyToClipboard(`${baseUrl}/?model=${encodeURIComponent(model.id)}`);

		if (res) {
			toast.success($i18n.t('Copied link to clipboard'));
		} else {
			toast.error($i18n.t('Failed to copy link'));
		}
	};

	const downloadModels = async (models) => {
		models = await Promise.all(models.map(getFullModel));
		let blob = new Blob([JSON.stringify(models)], {
			type: 'application/json'
		});
		saveAs(blob, `models-export-${Date.now()}.json`);
	};

	const exportModelHandler = async (model) => {
		model = await getFullModel(model);
		let blob = new Blob([JSON.stringify([model])], {
			type: 'application/json'
		});
		saveAs(blob, `${model.id}-${Date.now()}.json`);
	};

	const pinModelHandler = async (modelId) => {
		settings.set({
			...$settings,
			pinnedModels: $pinnedModels.includes(modelId)
				? $pinnedModels.filter((id) => id !== modelId)
				: [...$pinnedModels, modelId]
		});
		await updateUserSettings(localStorage.token, { ui: $settings });
	};

	const fetchAllWorkspaceModels = async () => {
		// Fetch all workspace models across every page
		const allModels = [];
		let currentPage = 1;
		let fetchedTotal = 0;

		while (true) {
			const res = await getWorkspaceModels(
				localStorage.token,
				query,
				viewOption,
				selectedTag,
				null,
				null,
				currentPage
			);
			if (!res || !res.items || res.items.length === 0) break;
			allModels.push(...res.items);
			fetchedTotal = res.total;
			if (allModels.length >= fetchedTotal) break;
			currentPage++;
		}

		return allModels;
	};

	const enableAllHandler = async () => {
		const allModels = await fetchAllWorkspaceModels();
		const modelsToEnable = allModels.filter((m) => !(m.is_active ?? true));
		if (modelsToEnable.length === 0) return;
		// Optimistic UI update for current page
		(models ?? []).forEach((m) => (m.is_active = true));
		models = models;
		// Sync with server
		await Promise.all(modelsToEnable.map((model) => toggleModelById(localStorage.token, model.id)));
		await getModelList();
	};

	const disableAllHandler = async () => {
		const allModels = await fetchAllWorkspaceModels();
		const modelsToDisable = allModels.filter((m) => m.is_active ?? true);
		if (modelsToDisable.length === 0) return;
		// Optimistic UI update for current page
		(models ?? []).forEach((m) => (m.is_active = false));
		models = models;
		// Sync with server
		await Promise.all(
			modelsToDisable.map((model) => toggleModelById(localStorage.token, model.id))
		);
		await getModelList();
	};

	const showAllHandler = async () => {
		const allModels = await fetchAllWorkspaceModels();
		const modelsToShow = allModels.filter((m) => m?.meta?.hidden === true);
		if (modelsToShow.length === 0) return;
		// Optimistic UI update for current page
		(models ?? []).forEach((m) => {
			m.meta = { ...m.meta, hidden: false };
		});
		models = models;
		// Sync with server
		await Promise.all(
			modelsToShow.map((model) => {
				model.meta = { ...model.meta, hidden: false };
				return updateModelById(localStorage.token, model.id, model);
			})
		);
		await getModelList();
		toast.success($i18n.t('All models are now visible'));
	};

	const hideAllHandler = async () => {
		const allModels = await fetchAllWorkspaceModels();
		const modelsToHide = allModels.filter((m) => !(m?.meta?.hidden ?? false));
		if (modelsToHide.length === 0) return;
		// Optimistic UI update for current page
		(models ?? []).forEach((m) => {
			m.meta = { ...m.meta, hidden: true };
		});
		models = models;
		// Sync with server
		await Promise.all(
			modelsToHide.map((model) => {
				model.meta = { ...model.meta, hidden: true };
				return updateModelById(localStorage.token, model.id, model);
			})
		);
		await getModelList();
		toast.success($i18n.t('All models are now hidden'));
	};

	onMount(async () => {
		viewOption = localStorage.workspaceViewOption ?? '';
		page = 1;

		let groups = await getGroups(localStorage.token);
		groupIds = groups.map((group) => group.id);
		groupNames = Object.fromEntries((groups ?? []).map((g) => [g.id, g.name]));

		await tick();
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
			window.removeEventListener('keydown', onKeyDown);
			window.removeEventListener('keyup', onKeyUp);
			window.removeEventListener('blur', onBlur);
		};
	});
</script>

<svelte:head>
	<!-- LICENSE covers this Open WebUI browser-title identifier.
	Do not alter, remove, obscure, or replace it except as LICENSE permits:
	https://docs.openwebui.com/license. -->
	<title>
		{$i18n.t('Models')} / {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<ModelDeleteConfirmDialog
		bind:show={showModelDeleteConfirm}
		variant="danger"
		title={$i18n.t('Delete model?')}
		message={$i18n.t('This deletes "{{name}}" for everyone who uses it. This cannot be undone.', {
			name: selectedModel?.name ?? ''
		})}
		on:confirm={() => {
			deleteModelHandler(selectedModel);
		}}
	/>

	<input
		id="models-import-input"
		bind:this={modelsImportInputElement}
		bind:files={importFiles}
		type="file"
		accept=".json"
		hidden
		on:change={() => {
			console.log(importFiles);

			let reader = new FileReader();
			reader.onload = async (event) => {
				let savedModels = [];
				try {
					savedModels = JSON.parse(event.target.result);
					console.log(savedModels);
				} catch (e) {
					toast.error($i18n.t('Invalid JSON file'));
					return;
				}

				for (const model of savedModels) {
					if (model?.info ?? false) {
						if ($_models.find((m) => m.id === model.id)) {
							await updateModelById(localStorage.token, model.id, model.info).catch((error) => {
								toast.error(`${error}`);
								return null;
							});
						} else {
							await createNewModel(localStorage.token, model.info).catch((error) => {
								toast.error(`${error}`);
								return null;
							});
						}
					} else {
						if (model?.id && model?.name) {
							await createNewModel(localStorage.token, model).catch((error) => {
								toast.error(`${error}`);
								return null;
							});
						}
					}
				}

				await _models.set(
					await getModels(
						localStorage.token,
						$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
					)
				);

				page = 1;
				getModelList();
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
				aria-label={$i18n.t('Search Models')}
				placeholder={$i18n.t('Search models, e.g. "tender"')}
				maxlength="500"
				on:input={() => {
					clearTimeout(searchDebounceTimer);
					searchDebounceTimer = setTimeout(() => {
						page = 1;
						getModelList();
					}, 300);
				}}
			/>
			{#if query}
				<button
					type="button"
					class="rounded-full p-0.5 text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
					aria-label={$i18n.t('Clear search')}
					on:click={() => {
						query = '';
						page = 1;
						getModelList();
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

				<Dropdown align="end">
					<button
						class="flex items-center gap-1 rounded-lg border border-gray-300 bg-white px-2 py-1 text-xs text-gray-800 transition hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200 dark:hover:bg-gray-800"
						type="button"
					>
						{$i18n.t('Bulk actions')}
						<ChevronDown className="size-3" strokeWidth="2.5" />
					</button>

					<div slot="content">
						<DropdownMenu className="w-[10.625rem] shadow-sm">
							<button
								class="flex h-[1.6875rem] w-full cursor-pointer select-none items-center gap-2 rounded-xl bg-transparent px-2 text-[0.8125rem] hover:text-gray-900 dark:hover:text-gray-100"
								type="button"
								on:click={() => enableAllHandler()}
							>
								<CheckCircle className="size-3.5" />
								<div class="flex items-center">{$i18n.t('Enable All')}</div>
							</button>
							<button
								class="flex h-[1.6875rem] w-full cursor-pointer select-none items-center gap-2 rounded-xl bg-transparent px-2 text-[0.8125rem] hover:text-gray-900 dark:hover:text-gray-100"
								type="button"
								on:click={() => disableAllHandler()}
							>
								<Minus className="size-3.5" />
								<div class="flex items-center">{$i18n.t('Disable All')}</div>
							</button>
							<hr class="mx-1 my-0.5 border-gray-100 dark:border-gray-800" />
							<button
								class="flex h-[1.6875rem] w-full cursor-pointer select-none items-center gap-2 rounded-xl bg-transparent px-2 text-[0.8125rem] hover:text-gray-900 dark:hover:text-gray-100"
								type="button"
								on:click={() => showAllHandler()}
							>
								<Eye className="size-3.5" />
								<div class="flex items-center">{$i18n.t('Show All')}</div>
							</button>
							<button
								class="flex h-[1.6875rem] w-full cursor-pointer select-none items-center gap-2 rounded-xl bg-transparent px-2 text-[0.8125rem] hover:text-gray-900 dark:hover:text-gray-100"
								type="button"
								on:click={() => hideAllHandler()}
							>
								<EyeSlash className="size-3.5" />
								<div class="flex items-center">{$i18n.t('Hide All')}</div>
							</button>
						</DropdownMenu>
					</div>
				</Dropdown>
			</div>
		</div>

		{#if models !== null}
			{#if (models ?? []).length !== 0}
				<ul class="grid gap-2.5 md:grid-cols-2" id="model-list">
					{#each models as model (model.id)}
						{@const own = getOwnership(model, $user?.id, groupNames, (k, o) => $i18n.t(k, o))}
						{@const hidden = model?.meta?.hidden === true}
						{@const enabled = model.is_active !== false}
						<li class="group relative" id="model-item-{model.id}">
							<button
								type="button"
								class="flex h-full w-full items-start gap-3 rounded-xl border border-gray-200 px-4 py-3 text-left transition hover:border-gray-400 hover:bg-gray-50 focus-visible:border-gray-500 dark:border-gray-800 dark:hover:border-gray-600 dark:hover:bg-gray-850 {hidden ||
								!enabled
									? 'opacity-60'
									: ''}"
								title={model.write_access ? $i18n.t('Edit model') : $i18n.t('Start a chat with this model')}
								on:click={() => openCard(model)}
							>
								<img
									src={`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${model.id}&lang=${$i18n.language}`}
									alt=""
									class="size-10 shrink-0 rounded-lg object-cover ring-1 ring-gray-200 dark:ring-white/10"
									loading="lazy"
									decoding="async"
									on:error={(e) => {
										// LICENSE covers this Open WebUI fallback logo.
										// Do not alter, remove, obscure, or replace it except as LICENSE permits:
										// https://docs.openwebui.com/license.
										e.target.src = '/favicon.png';
									}}
								/>

								<div class="flex min-w-0 flex-1 flex-col">
									<div class="flex w-full items-center gap-2 pr-16">
										<span class="min-w-0 flex-1 truncate text-sm font-semibold">{model.name}</span>
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
										{(model?.meta?.description ?? '').trim() || $i18n.t('No description')}
									</div>

									<div
										class="mt-2 flex w-full flex-wrap items-center gap-x-1.5 gap-y-1 pr-12 text-[0.6875rem] text-gray-500"
									>
										{#if model.base_model_id}
											<span class="truncate" title={$i18n.t('Base model')}>
												{$i18n.t('based on {{model}}', { model: model.base_model_id })}
											</span>
											<span aria-hidden="true">·</span>
										{/if}
										<span title={dayjs(model.updated_at * 1000).format('LLLL')}>
											{$i18n.t('updated {{time}}', { time: dayjs(model.updated_at * 1000).fromNow() })}
										</span>
										<span aria-hidden="true">·</span>
										<span class="truncate" title={model?.user?.email ?? ''}>{ownerOf(model)}</span>
										{#if !model.write_access}
											<span aria-hidden="true">·</span>
											<span>{$i18n.t('Read Only')}</span>
										{/if}
										{#if hidden}
											<span aria-hidden="true">·</span>
											<span>{$i18n.t('Hidden')}</span>
										{/if}
										{#if !enabled}
											<span aria-hidden="true">·</span>
											<span>{$i18n.t('Disabled')}</span>
										{/if}
									</div>
								</div>
							</button>

							<!-- Card actions sit outside the card button (no nested buttons). -->
							<div class="absolute top-2 right-2 flex items-center gap-0.5">
								{#if shiftKey && model.write_access}
									<Tooltip content={hidden ? $i18n.t('Show') : $i18n.t('Hide')}>
										<button
											class="flex size-7 items-center justify-center rounded-lg text-gray-400 transition hover:bg-gray-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200"
											type="button"
											aria-label={hidden ? $i18n.t('Show') : $i18n.t('Hide')}
											on:click={() => hideModelHandler(model)}
										>
											{#if hidden}
												<EyeSlash className="size-4" />
											{:else}
												<Eye className="size-4" />
											{/if}
										</button>
									</Tooltip>
									<Tooltip content={$i18n.t('Delete')}>
										<button
											class="flex size-7 items-center justify-center rounded-lg text-gray-400 transition hover:bg-gray-100 hover:text-red-600 dark:hover:bg-gray-800"
											type="button"
											aria-label={$i18n.t('Delete')}
											on:click={() => deleteModelHandler(model)}
										>
											<GarbageBin className="size-4" />
										</button>
									</Tooltip>
								{:else}
									<a
										href={`/?model=${encodeURIComponent(model.id)}`}
										class="rounded-lg px-2 py-1 text-xs text-gray-600 opacity-0 transition group-hover:opacity-100 focus-visible:opacity-100 hover:bg-gray-100 hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800 dark:hover:text-gray-100"
									>
										{$i18n.t('Chat')} →
									</a>
									<ModelMenu
										user={$user}
										{model}
										writeAccess={model.write_access}
										editHandler={() => {
											goto(`/workspace/models/edit?id=${encodeURIComponent(model.id)}`);
										}}
										shareHandler={() => {
											shareModelHandler(model);
										}}
										cloneHandler={() => {
											cloneModelHandler(model);
										}}
										exportHandler={() => {
											exportModelHandler(model);
										}}
										hideHandler={() => {
											hideModelHandler(model);
										}}
										pinModelHandler={() => {
											pinModelHandler(model.id);
										}}
										copyLinkHandler={() => {
											copyLinkHandler(model);
										}}
										deleteHandler={() => {
											selectedModel = model;
											showModelDeleteConfirm = true;
										}}
										onClose={() => {}}
									>
										<div
											class="flex size-7 items-center justify-center rounded-lg text-gray-400 transition hover:bg-gray-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200"
										>
											<EllipsisHorizontal className="size-4" />
										</div>
									</ModelMenu>
								{/if}
							</div>

							{#if model.write_access}
								<div class="absolute right-3 bottom-3">
									<Tooltip content={enabled ? $i18n.t('Enabled') : $i18n.t('Disabled')}>
										<Switch
											bind:state={model.is_active}
											on:change={async () => {
												toggleModelById(localStorage.token, model.id);
												_models.set(
													await getModels(
														localStorage.token,
														$config?.features?.enable_direct_connections &&
															($settings?.directConnections ?? null)
													)
												);
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
					<div class="text-base font-semibold">{$i18n.t('No models yet')}</div>
					<p class="mt-1 text-sm text-gray-500">
						{$i18n.t(
							'A model here is a ready-made assistant: a base model plus instructions, knowledge and tools, e.g. "Tender response helper".'
						)}
					</p>
					<a
						href="/workspace/models/create"
						class="mt-4 rounded-lg bg-black px-4 py-2 text-sm font-semibold text-white transition hover:bg-gray-800 dark:bg-white dark:text-black dark:hover:bg-gray-200"
					>
						+ {$i18n.t('New model')}
					</a>
				</div>
			{/if}
		{:else}
			<div class="flex w-full items-center justify-center py-10">
				<Spinner className="size-4" />
			</div>
		{/if}
	</div>

	{#if $config?.features.enable_community_sharing}
		<CommunityDiscover
			href="https://openwebui.com/models"
			title={$i18n.t('Discover a model')}
			description={$i18n.t('Discover, download, and explore model presets')}
		/>
	{/if}
{:else}
	<div class="w-full h-full flex justify-center items-center">
		<Spinner className="size-5" />
	</div>
{/if}
