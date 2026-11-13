<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { onMount, getContext, tick } from 'svelte';
	import { models, tools, functions, user } from '$lib/stores';
	import { WEBUI_BASE_URL, DEFAULT_CAPABILITIES } from '$lib/constants';

	import { getTools } from '$lib/apis/tools';
	import { getSkills } from '$lib/apis/skills';
	import { getFunctions } from '$lib/apis/functions';
	import { getModelsDefaults } from '$lib/apis/configs';
	import { getBaseModelTags, getModelTags } from '$lib/apis/models';
	import { getVoices } from '$lib/apis/audio';

	import AdvancedParams from '$lib/components/chat/Settings/Advanced/AdvancedParams.svelte';
	import ModelSelector from '$lib/components/chat/ModelSelector/Selector.svelte';
	import Tags from '$lib/components/common/Tags.svelte';
	import Knowledge from '$lib/components/workspace/Models/Knowledge.svelte';
	import ToolsSelector from '$lib/components/workspace/Models/ToolsSelector.svelte';
	import SkillsSelector from '$lib/components/workspace/Models/SkillsSelector.svelte';
	import FiltersSelector from '$lib/components/workspace/Models/FiltersSelector.svelte';
	import ActionsSelector from '$lib/components/workspace/Models/ActionsSelector.svelte';
	import Capabilities from '$lib/components/workspace/Models/Capabilities.svelte';
	import Textarea from '$lib/components/common/Textarea.svelte';
	import AccessControl from '../common/AccessControl.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import DefaultFiltersSelector from './DefaultFiltersSelector.svelte';
	import PromptSuggestions from './PromptSuggestions.svelte';
	import TaskPrompts from './TaskPrompts.svelte';
	import TerminalSelector from './TerminalSelector.svelte';
	import TTSVoiceInput from './TTSVoiceInput.svelte';
	import AccessControlModal from '../common/AccessControlModal.svelte';
	import { extractInputVariables } from '$lib/utils';

	const i18n = getContext('i18n');

	export let onSubmit: Function;
	export let onBack: null | Function = null;

	export let model = null;
	export let edit = false;

	export let preset = true;

	let loading = false;
	let success = false;

	let filesInputElement;
	let inputFiles;

	let showAdvanced = false;
	let showPreview = false;
	let showAccessControlModal = false;

	let loaded = false;

	// ///////////
	// model
	// ///////////

	let id = '';
	let name = '';

	let enableDescription = true;

	$: if (!edit) {
		if (name) {
			id = name
				.replace(/\s+/g, '-')
				.replace(/[^a-zA-Z0-9-]/g, '')
				.toLowerCase();
		}
	}

	let system = '';
	let news = '';

	let info = {
		id: '',
		base_model_id: null,
		name: '',
		meta: {
			// LICENSE covers this Open WebUI fallback logo.
			// Do not alter, remove, obscure, or replace it except as LICENSE permits:
			// https://docs.openwebui.com/license.
			profile_image_url: `${WEBUI_BASE_URL}/static/favicon.png`,
			description: '',
			suggestion_prompts: null,
			task_prompt_ids: [],
			tags: []
		},
		params: {
			system: ''
		}
	};

	let params = {
		system: ''
	};

	let knowledge = [];
	let toolIds = [];
	let skillIds = [];
	let skillsList = [];

	let filterIds = [];
	let defaultFilterIds = [];

	let capabilities = { ...DEFAULT_CAPABILITIES };
	let defaultFeatureIds = [];
	let builtinTools = {};

	let actionIds = [];
	let accessGrants = [];
	let terminalId = '';
	let tts = { voice: '' };
	export let suggestionTags: { name: string }[] = [];
	let voices: { id: string; name?: string }[] = [];

	const chatVariableKeyRegex = /^[a-z][a-z0-9_]*$/;
	const getChatVariablesPreview = (prompt: string) => {
		const variables = extractInputVariables(prompt);
		const warnings: string[] = [];
		const seenDefinitions: Record<string, string> = {};
		const typedRegex = /{{\s*chat\.variables\.([a-zA-Z0-9_.-]+)\s*\|\s*([^}]*)\s*}}/g;
		const typedUserRegex = /{{\s*user\.variables\.([a-zA-Z0-9_.-]+)\s*\|\s*([^}]*)\s*}}/g;

		for (const match of prompt.matchAll(typedRegex)) {
			const key = match[1];
			const definition = match[2].trim();
			if (seenDefinitions[key] && seenDefinitions[key] !== definition) {
				warnings.push(`${key} has conflicting duplicate definitions`);
			}
			seenDefinitions[key] = definition;
		}

		const fields = Object.entries(variables)
			.filter(([name]) => name.startsWith('chat.variables.'))
			.map(([name, field]) => ({ key: name.replace('chat.variables.', ''), ...(field as any) }));
		const userFields = Object.entries(variables)
			.filter(([name]) => name.startsWith('user.variables.'))
			.map(([name]) => ({ key: name.replace('user.variables.', '') }));

		for (const match of prompt.matchAll(typedUserRegex)) {
			warnings.push(`${match[1]} uses metadata, but User Variables are configured by each user`);
		}

		for (const field of fields) {
			const key = field.key;
			if (!chatVariableKeyRegex.test(key)) {
				warnings.push(`${key} must be lowercase snake case`);
				continue;
			}

			if (
				field.type === 'select' &&
				(!Array.isArray(field.options) || field.options.length === 0)
			) {
				warnings.push(`${key} select needs options=[...]`);
			}
		}

		for (const field of userFields) {
			if (!chatVariableKeyRegex.test(field.key)) {
				warnings.push(`${field.key} must be lowercase snake case`);
			}
		}

		return { fields, userFields, warnings };
	};

	$: chatVariablesPreview = getChatVariablesPreview(system ?? '');

	const getBaseModelItems = (models: any[] = []) => {
		const currentModelId = (model as any)?.id;

		return models
			.filter(
				(baseModel) =>
					(!currentModelId ||
						baseModel.id !== currentModelId ||
						(edit && baseModel.id === info.base_model_id)) &&
					(!baseModel?.preset || (edit && baseModel.id === info.base_model_id)) &&
					baseModel?.owned_by !== 'arena' &&
					!(baseModel?.direct ?? false) &&
					($user?.role === 'admin' ||
						!(baseModel?.info?.meta?.hidden ?? false) ||
						baseModel.id === info.base_model_id)
			)
			.map((baseModel) => ({
				value: baseModel.id,
				label: baseModel.name,
				model: baseModel
			}));
	};

	const loadSuggestionTags = async () => {
		const res: string[] = await (preset ? getModelTags : getBaseModelTags)(
			localStorage.token
		).catch(() => []);
		suggestionTags = res.map((tag) => ({ name: tag }));
	};

	const loadVoices = async () => {
		const res = await getVoices(localStorage.token).catch(() => null);
		voices = res?.voices ?? [];
	};

	const toModelKnowledgeReference = (item: any) => {
		if (!item || typeof item !== 'object') {
			return item;
		}

		return Object.fromEntries(
			[
				'id',
				'name',
				'type',
				'description',
				'context',
				'legacy',
				'collection_name',
				'collection_names'
			]
				.filter((key) => item[key] !== undefined && item[key] !== null && item[key] !== '')
				.map((key) => [key, item[key]])
		);
	};

	const submitHandler = async () => {
		loading = true;

		info.id = id;
		info.name = name;

		if (id === '') {
			toast.error($i18n.t('Model ID is required.'));
			loading = false;

			return;
		}

		if (name === '') {
			toast.error($i18n.t('Model Name is required.'));
			loading = false;

			return;
		}

		if (preset && !info.base_model_id) {
			toast.error($i18n.t('Base Model is required.'));
			loading = false;

			return;
		}

		if (knowledge.some((item) => item.status === 'uploading')) {
			toast.error($i18n.t('Please wait until all files are uploaded.'));
			loading = false;

			return;
		}

		info.params = { ...info.params, ...params };

		info.access_grants = accessGrants;
		info.meta.capabilities = capabilities;

		if (enableDescription) {
			info.meta.description = info.meta.description.trim() === '' ? null : info.meta.description;
		} else {
			info.meta.description = null;
		}

		if (knowledge.length > 0) {
			info.meta.knowledge = knowledge.map(toModelKnowledgeReference);
		} else {
			if (info.meta.knowledge) {
				delete info.meta.knowledge;
			}
		}

		if (toolIds.length > 0) {
			info.meta.toolIds = toolIds;
		} else {
			if (info.meta.toolIds) {
				delete info.meta.toolIds;
			}
		}

		if (skillIds.length > 0) {
			info.meta.skillIds = skillIds;
		} else {
			if (info.meta.skillIds) {
				delete info.meta.skillIds;
			}
		}

		if (filterIds.length > 0) {
			info.meta.filterIds = filterIds;
		} else {
			if (info.meta.filterIds) {
				delete info.meta.filterIds;
			}
		}

		if (defaultFilterIds.length > 0) {
			info.meta.defaultFilterIds = defaultFilterIds;
		} else {
			if (info.meta.defaultFilterIds) {
				delete info.meta.defaultFilterIds;
			}
		}

		if (actionIds.length > 0) {
			info.meta.actionIds = actionIds;
		} else {
			if (info.meta.actionIds) {
				delete info.meta.actionIds;
			}
		}

		if (defaultFeatureIds.length > 0) {
			info.meta.defaultFeatureIds = defaultFeatureIds;
		} else {
			if (info.meta.defaultFeatureIds) {
				delete info.meta.defaultFeatureIds;
			}
		}

		if (Object.keys(builtinTools).length > 0) {
			info.meta.builtinTools = builtinTools;
		} else {
			if (info.meta.builtinTools) {
				delete info.meta.builtinTools;
			}
		}

		if (terminalId) {
			info.meta.terminalId = terminalId;
		} else {
			if (info.meta.terminalId) {
				delete info.meta.terminalId;
			}
		}

		if (tts.voice !== '') {
			if (!info.meta.tts) info.meta.tts = {};
			info.meta.tts.voice = tts.voice;
		} else {
			if (info.meta.tts?.voice) {
				delete info.meta.tts.voice;
				if (Object.keys(info.meta.tts).length === 0) {
					delete info.meta.tts;
				}
			}
		}

		info.params.system = system.trim() === '' ? null : system;

		if (news.trim() !== '') {
			info.meta.news = news.trim();
		} else {
			delete info.meta.news;
		}
		// Drop the retired greeting field so it doesn't linger in saved models.
		delete info.meta.greeting;

		// New-chat task cards: up to 4 prompt-library IDs, in display order.
		const taskPromptIds = [
			...new Set((info.meta.task_prompt_ids ?? []).filter((id) => typeof id === 'string' && id))
		].slice(0, 4);
		if (taskPromptIds.length > 0) {
			info.meta.task_prompt_ids = taskPromptIds;
		} else {
			delete info.meta.task_prompt_ids;
		}
		// Hand-written task cards were replaced by prompt-library picks.
		delete info.meta.tasks;

		info.params.stop = params.stop
			? (typeof params.stop === 'string' ? params.stop.split(',') : params.stop).filter((s) =>
					s.trim()
				)
			: null;
		Object.keys(info.params).forEach((key) => {
			if (info.params[key] === '' || info.params[key] === null) {
				delete info.params[key];
			}
		});

		await onSubmit(info);

		loading = false;
		success = false;
	};

	onMount(async () => {
		await tools.set((await getTools(localStorage.token).catch(() => null)) ?? []);
		skillsList = (await getSkills(localStorage.token).catch(() => null)) ?? [];
		if (!$functions) {
			await functions.set(await getFunctions(localStorage.token));
		}
		if (suggestionTags.length === 0) {
			await loadSuggestionTags();
		}
		if (voices.length === 0) {
			await loadVoices();
		}

		// Fetch admin-configured default model metadata so the editor
		// reflects the actual defaults rather than hardcoded values
		const modelsConfig = await getModelsDefaults(localStorage.token).catch(() => null);
		const defaultMeta = modelsConfig?.DEFAULT_MODEL_METADATA ?? {};

		// Use admin defaults as base, falling back to hardcoded defaults
		capabilities = { ...DEFAULT_CAPABILITIES, ...(defaultMeta.capabilities ?? {}) };
		defaultFeatureIds = defaultMeta.defaultFeatureIds ?? [];
		builtinTools = defaultMeta.builtinTools ?? {};

		// Scroll to top 'workspace-container' element
		const workspaceContainer = document.getElementById('workspace-container');
		if (workspaceContainer) {
			workspaceContainer.scrollTop = 0;
		}

		if (model) {
			name = model.name;
			await tick();

			id = model.id;

			enableDescription = model?.meta?.description !== null;

			if (model.base_model_id) {
				const base_model = $models
					.filter(
						(m) => (!m?.preset && !(m?.arena ?? false)) || (edit && m.id === model.base_model_id)
					)
					.find((m) => [model.base_model_id, `${model.base_model_id}:latest`].includes(m.id));

				console.log('base_model', base_model);

				if (base_model) {
					model.base_model_id = base_model.id;
				} else if (!edit) {
					model.base_model_id = null;
				}
			}

			system = model?.params?.system ?? '';
			// Prefill from the old greeting field so existing text carries over on next save.
			news = model?.meta?.news ?? model?.meta?.greeting ?? '';

			params = { ...params, ...model?.params };
			params.stop = params?.stop
				? (typeof params.stop === 'string' ? params.stop.split(',') : (params?.stop ?? [])).join(
						','
					)
				: null;

			knowledge = (model?.meta?.knowledge ?? []).map((item) => {
				if (item?.collection_name && item?.type !== 'file') {
					return {
						id: item.collection_name,
						name: item.name,
						legacy: true
					};
				} else if (item?.collection_names) {
					return {
						name: item.name,
						type: 'collection',
						collection_names: item.collection_names,
						legacy: true
					};
				} else {
					return item;
				}
			});

			toolIds = model?.meta?.toolIds ?? [];
			skillIds = model?.meta?.skillIds ?? [];
			filterIds = model?.meta?.filterIds ?? [];
			defaultFilterIds = model?.meta?.defaultFilterIds ?? [];
			actionIds = model?.meta?.actionIds ?? [];

			// Per-model overrides take precedence over admin defaults
			capabilities = { ...capabilities, ...(model?.meta?.capabilities ?? {}) };
			defaultFeatureIds = model?.meta?.defaultFeatureIds ?? defaultFeatureIds;
			builtinTools = model?.meta?.builtinTools ?? builtinTools;
			terminalId = model?.meta?.terminalId ?? '';
			tts = { voice: model?.meta?.tts?.voice ?? '' };

			accessGrants = model?.access_grants ?? [];

			info = {
				...info,
				...JSON.parse(
					JSON.stringify(
						model
							? model
							: {
									id: model.id,
									name: model.name
								}
					)
				)
			};

			console.log(model);
		}

		loaded = true;
	});

	// CHOn form styles (same as the prompt and knowledge forms).
	const fieldClass =
		'w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm outline-hidden placeholder:text-gray-400 focus:border-gray-500 disabled:bg-gray-50 disabled:text-gray-500 dark:border-gray-700 dark:bg-gray-900 dark:focus:border-gray-500 dark:disabled:bg-white/[0.03]';
	const sectionClass =
		'flex flex-col gap-4 rounded-xl border border-gray-200 px-4 py-4 dark:border-gray-800';

	// One-line "who can use this" in the footer.
	$: accessSummary =
		(accessGrants ?? []).length === 0
			? $i18n.t('Only you can use this model.')
			: (accessGrants ?? []).some((g) => g.principal_id === '*')
				? $i18n.t('Everyone at Weidmann can use this model.')
				: $i18n.t('Shared with selected people or teams.');
</script>

{#if loaded}
	<AccessControlModal
	itemName={name}
	subtitle={$i18n.t('Model')}
		bind:show={showAccessControlModal}
		bind:accessGrants
		accessRoles={preset ? ['read', 'write'] : ['read']}
		share={$user?.permissions?.sharing?.models || $user?.role === 'admin'}
		sharePublic={$user?.permissions?.sharing?.public_models || $user?.role === 'admin'}
		shareUsers={($user?.permissions?.access_grants?.allow_users ?? true) || $user?.role === 'admin'}
	/>

	<div class="flex h-full min-h-0 w-full flex-col">
		{#if onBack}
			<button
				class="mb-1 flex h-6 w-fit items-center gap-1 rounded-md text-xs text-gray-400 transition-colors duration-75 hover:text-gray-700 dark:text-gray-600 dark:hover:text-gray-300"
				type="button"
				on:click={() => {
					onBack();
				}}
			>
				<ChevronLeft className="size-3" strokeWidth="2" />
				<span>{$i18n.t('Back')}</span>
			</button>
		{/if}

		<div class="min-h-0 w-full flex-1 overflow-y-auto pr-1 scrollbar-hover">
			<input
				bind:this={filesInputElement}
				bind:files={inputFiles}
				type="file"
				hidden
				accept="image/*"
				on:change={() => {
					let reader = new FileReader();
					reader.onload = (event) => {
						let originalImageUrl = `${event.target?.result}`;

						// For animated formats (gif, webp), skip resizing to preserve animation
						const fileType = (inputFiles[0] as any)?.['type'];
						if (fileType === 'image/gif' || fileType === 'image/webp') {
							info.meta.profile_image_url = originalImageUrl;
							inputFiles = null;
							filesInputElement.value = '';
							return;
						}

						const img = new Image();
						img.src = originalImageUrl;

						img.onload = function () {
							const canvas = document.createElement('canvas');
							const ctx = canvas.getContext('2d');

							// Calculate the aspect ratio of the image
							const aspectRatio = img.width / img.height;

							// Calculate the new width and height to fit within 100x100
							let newWidth, newHeight;
							if (aspectRatio > 1) {
								newWidth = 250 * aspectRatio;
								newHeight = 250;
							} else {
								newWidth = 250;
								newHeight = 250 / aspectRatio;
							}

							// Set the canvas size
							canvas.width = 250;
							canvas.height = 250;

							// Calculate the position to center the image
							const offsetX = (250 - newWidth) / 2;
							const offsetY = (250 - newHeight) / 2;

							// Draw the image on the canvas
							ctx.drawImage(img, offsetX, offsetY, newWidth, newHeight);

							// Get the base64 representation of the compressed image
							const compressedSrc = canvas.toDataURL('image/webp', 0.8);

							// Display the compressed image
							info.meta.profile_image_url = compressedSrc;

							inputFiles = null;
							filesInputElement.value = '';
						};
					};

					if (
						inputFiles &&
						inputFiles.length > 0 &&
						['image/gif', 'image/webp', 'image/jpeg', 'image/png', 'image/svg+xml'].includes(
							(inputFiles[0] as any)?.['type']
						)
					) {
						reader.readAsDataURL(inputFiles[0]);
					} else {
						console.log(`Unsupported File Type '${(inputFiles[0] as any)?.['type']}'.`);
						inputFiles = null;
					}
				}}
			/>

			{#if !edit || (edit && model)}
				<form
					id="model-editor-form"
					class="mx-auto flex w-full max-w-4xl flex-col gap-4 px-1 pt-1 pb-6 text-gray-900 dark:text-gray-100"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<!-- Header: image, name, id, sharing -->
					<div class="flex w-full min-w-0 items-start gap-4">
						<!-- LICENSE covers this Open WebUI fallback logo.
						Do not alter, remove, obscure, or replace it except as LICENSE permits:
						https://docs.openwebui.com/license. -->
						<div class="group relative size-14 shrink-0 md:size-16">
							<button
								class="group relative flex size-full items-center overflow-hidden rounded-xl {info
									.meta.profile_image_url !== `${WEBUI_BASE_URL}/static/favicon.png`
									? 'bg-transparent'
									: 'bg-gray-50 dark:bg-gray-850'} ring-1 ring-gray-200 transition hover:ring-gray-400 dark:ring-white/10 dark:hover:ring-white/20"
								type="button"
								aria-label={$i18n.t('Upload profile image')}
								title={$i18n.t('Change image')}
								on:click={() => {
									filesInputElement.click();
								}}
							>
								{#if info.meta.profile_image_url}
									<img src={info.meta.profile_image_url} alt="model profile" class="size-full object-cover" />
								{:else}
									<img src="{WEBUI_BASE_URL}/static/favicon.png" alt="model profile" class="size-full object-cover" />
								{/if}

								<div
									class="absolute right-0 bottom-0 z-10 opacity-0 transition group-hover:opacity-100 group-focus-within:opacity-100"
								>
									<div class="m-1">
										<div class="rounded-full bg-gray-900 p-1 text-white shadow-sm dark:bg-white dark:text-black">
											<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="size-3">
												<path
													fill-rule="evenodd"
													d="M2 4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4Zm10.5 5.707a.5.5 0 0 0-.146-.353l-1-1a.5.5 0 0 0-.708 0L9.354 9.646a.5.5 0 0 1-.708 0L6.354 7.354a.5.5 0 0 0-.708 0l-2 2a.5.5 0 0 0-.146.353V12a.5.5 0 0 0 .5.5h8a.5.5 0 0 0 .5-.5V9.707ZM12 5a1 1 0 1 1-2 0 1 1 0 0 1 2 0Z"
													clip-rule="evenodd"
												/>
											</svg>
										</div>
									</div>
								</div>
							</button>

							{#if info.meta.profile_image_url && info.meta.profile_image_url !== `${WEBUI_BASE_URL}/static/favicon.png`}
								<button
									class="absolute top-full left-1/2 mt-1 -translate-x-1/2 text-[0.625rem] leading-none text-gray-500 hover:text-gray-800 hover:underline dark:hover:text-gray-200"
									on:click={() => {
										info.meta.profile_image_url = `${WEBUI_BASE_URL}/static/favicon.png`;
									}}
									type="button"
								>
									{$i18n.t('Reset')}
								</button>
							{/if}
						</div>

						<div class="grid min-w-0 flex-1 gap-3 sm:grid-cols-2">
							<div class="flex flex-col gap-1.5">
								<label for="model-name" class="text-sm font-semibold">{$i18n.t('Name')}</label>
								<input
									id="model-name"
									class={fieldClass}
									placeholder={$i18n.t('e.g. CHOn Standard')}
									bind:value={name}
									required
								/>
							</div>
							<div class="flex flex-col gap-1.5">
								<label for="model-id" class="text-sm font-semibold">{$i18n.t('Model ID')}</label>
								<input
									id="model-id"
									class="{fieldClass} font-mono"
									placeholder={$i18n.t('e.g. chon-standard')}
									bind:value={id}
									disabled={edit}
									required
								/>
								{#if !edit}
									<p class="text-xs text-gray-500">{$i18n.t('Cannot be changed later.')}</p>
								{/if}
							</div>
						</div>
					</div>

					<!-- Basics -->
					<section class={sectionClass}>
						<div>
							<h2 class="text-sm font-semibold">{$i18n.t('Basics')}</h2>
							<p class="mt-0.5 text-xs text-gray-500">
								{$i18n.t('What this model is built on and how it is described to users.')}
							</p>
						</div>

						{#if preset}
							<div class="flex flex-col gap-1.5">
								<label for="workspace-base-model" class="text-sm font-semibold">
									{$i18n.t('Base model')}
								</label>
								<div
									class="rounded-lg border border-gray-300 bg-white px-3 py-1.5 focus-within:border-gray-500 dark:border-gray-700 dark:bg-gray-900"
								>
									<ModelSelector
										id="workspace-base-model"
										placeholder={$i18n.t('Select a base model (e.g. llama3, gpt-4o)')}
										searchPlaceholder={$i18n.t('Search a model')}
										items={getBaseModelItems($models)}
										triggerClassName="text-sm"
										selectionOnly
										includeHidden={$user?.role === 'admin'}
										bind:value={info.base_model_id}
									/>
								</div>
								<p class="text-xs text-gray-500">
									{$i18n.t('The model that actually answers. Everything below is added on top of it.')}
								</p>
							</div>
						{/if}

						<div class="flex flex-col gap-1.5">
							<div class="flex items-center justify-between gap-2">
								<label for="model-description" class="text-sm font-semibold">
									{$i18n.t('Description')}
								</label>
								<label class="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400">
									<input
										type="checkbox"
										class="size-3.5 rounded border-gray-300"
										bind:checked={enableDescription}
									/>
									{$i18n.t('Write a custom description')}
								</label>
							</div>
							{#if enableDescription}
								<Textarea
									id="model-description"
									className="{fieldClass} resize-none overflow-y-hidden"
									placeholder={$i18n.t('e.g. Fast. Best for emails, summaries, translations and everyday questions.')}
									minSize={40}
									bind:value={info.meta.description}
								/>
								<p class="text-xs text-gray-500">
									{$i18n.t('One line on what it is good for. Shown in the model picker.')}
								</p>
							{:else}
								<p class="text-xs text-gray-500">
									{$i18n.t("Uses the base model's description.")}
								</p>
							{/if}
						</div>

						<div class="flex flex-col gap-1.5">
							<label for="model-topics" class="text-sm font-semibold">
								{$i18n.t('Topics')}
								<span class="font-normal text-gray-500">({$i18n.t('optional')})</span>
							</label>
							<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
							<div
								class="flex min-h-[2.375rem] cursor-text items-center rounded-lg border border-gray-300 bg-white px-3 py-1.5 focus-within:border-gray-500 dark:border-gray-700 dark:bg-gray-900 dark:focus-within:border-gray-500"
								on:click={() => document.getElementById('model-topics')?.focus()}
							>
								<Tags
									id="model-topics"
									tags={info?.meta?.tags ?? []}
									{suggestionTags}
									splitOnSpace={false}
									inputClassName="text-sm py-0.5"
									placeholder={$i18n.t('e.g. Sales, Quality')}
									on:delete={(e) => {
										const tagName = e.detail;
										info.meta.tags = info.meta.tags.filter((tag) => tag.name !== tagName);
									}}
									on:add={(e) => {
										const tagName = e.detail;
										if (!(info?.meta?.tags ?? null)) {
											info.meta.tags = [{ name: tagName }];
										} else {
											info.meta.tags = [...info.meta.tags, { name: tagName }];
										}
									}}
								/>
							</div>
							<p class="text-xs text-gray-500">{$i18n.t('Press Enter after each topic.')}</p>
						</div>
					</section>

					<!-- Behaviour -->
					<section class={sectionClass}>
						<div>
							<h2 class="text-sm font-semibold">{$i18n.t('Behaviour')}</h2>
							<p class="mt-0.5 text-xs text-gray-500">
								{$i18n.t('Instructions the model follows in every chat.')}
							</p>
						</div>

						<div class="flex flex-col gap-1.5">
							<label for="model-system-prompt" class="text-sm font-semibold">
								{$i18n.t('System prompt')}
							</label>
							<Textarea
								id="model-system-prompt"
								className="{fieldClass} resize-none overflow-y-hidden"
								placeholder={$i18n.t(
									'e.g. You are CHOn Standard, an assistant for Weidmann employees. Answer briefly and use metric units.'
								)}
								rows={4}
								bind:value={system}
							/>
						</div>

						<div class="flex flex-col gap-1.5">
							<label for="model-information" class="text-sm font-semibold">
								{$i18n.t('Model Information badge')}
								<span class="font-normal text-gray-500">({$i18n.t('optional')})</span>
							</label>
							<Textarea
								id="model-information"
								className="{fieldClass} resize-none overflow-y-hidden"
								placeholder={$i18n.t('e.g. New: answers now include links to the source documents.')}
								rows={2}
								bind:value={news}
							/>
							<p class="text-xs text-gray-500">
								{$i18n.t(
									'Shown when users hover the red "Model Information" badge below the message box on a new chat. Leave empty to hide the badge.'
								)}
							</p>
						</div>

						{#if chatVariablesPreview.fields.length > 0 || chatVariablesPreview.userFields.length > 0 || chatVariablesPreview.warnings.length > 0}
							<div class="rounded-lg bg-gray-50 px-3 py-2 dark:bg-gray-850">
								{#if chatVariablesPreview.fields.length > 0}
									<div class="mb-1 text-xs font-semibold">{$i18n.t('Chat Variables')}</div>
									<div class="flex flex-wrap gap-x-3 gap-y-1.5 text-xs">
										{#each chatVariablesPreview.fields as field}
											<div class="flex items-center gap-1 text-gray-600 dark:text-gray-300">
												<span class="font-medium">{field.key}</span>
												<span class="text-gray-400 dark:text-gray-500">{field.type}</span>
												{#if field.required}
													<span class="text-amber-600 dark:text-amber-400">required</span>
												{/if}
											</div>
										{/each}
									</div>
								{/if}

								{#if chatVariablesPreview.userFields.length > 0}
									<div class="mt-2 mb-1 text-xs font-semibold">{$i18n.t('User Variables')}</div>
									<div class="flex flex-wrap gap-x-3 gap-y-1.5 text-xs">
										{#each chatVariablesPreview.userFields as field}
											<span class="font-medium text-gray-600 dark:text-gray-300">{field.key}</span>
										{/each}
									</div>
								{/if}

								{#if chatVariablesPreview.warnings.length > 0}
									<div class="mt-2 flex flex-col gap-1 text-xs text-amber-600 dark:text-amber-400">
										{#each chatVariablesPreview.warnings as warning}
											<div>{warning}</div>
										{/each}
									</div>
								{/if}
							</div>
						{/if}

						<div class="border-t border-gray-100 pt-3 dark:border-gray-800">
							<button
								class="flex w-full items-center justify-between text-left"
								type="button"
								aria-expanded={showAdvanced}
								on:click={() => {
									showAdvanced = !showAdvanced;
								}}
							>
								<span>
									<span class="block text-sm font-semibold">{$i18n.t('Advanced parameters')}</span>
									<span class="block text-xs text-gray-500">
										{$i18n.t('Temperature, context length and other fine-tuning. Usually not needed.')}
									</span>
								</span>
								<span class="shrink-0 text-xs text-gray-600 underline dark:text-gray-400">
									{showAdvanced ? $i18n.t('Hide') : $i18n.t('Show')}
								</span>
							</button>

							{#if showAdvanced}
								<div class="mt-3">
									<AdvancedParams admin={true} custom={true} layout="grid" bind:params />
								</div>
							{/if}
						</div>
					</section>

					<!-- New chat screen -->
					<section class={sectionClass}>
						<div>
							<h2 class="text-sm font-semibold">{$i18n.t('New chat screen')}</h2>
							<p class="mt-0.5 text-xs text-gray-500">
								{$i18n.t('What users see before they type, when this model is selected.')}
							</p>
						</div>

						<div class="flex flex-col gap-1.5">
							<div class="text-sm font-semibold">{$i18n.t('Task cards')}</div>
							<TaskPrompts bind:promptIds={info.meta.task_prompt_ids} />
						</div>

						<div class="flex flex-col gap-1.5">
							<div class="flex items-center justify-between gap-2">
								<div class="text-sm font-semibold">{$i18n.t('Prompt suggestions')}</div>
								<label class="flex items-center gap-1.5 text-xs text-gray-600 dark:text-gray-400">
									<input
										type="checkbox"
										class="size-3.5 rounded border-gray-300"
										checked={(info?.meta?.suggestion_prompts ?? null) !== null}
										on:change={(e) => {
											(info.meta as any).suggestion_prompts = e.currentTarget.checked
												? [{ content: '', title: ['', ''] }]
												: null;
										}}
									/>
									{$i18n.t('Customize')}
								</label>
							</div>
							{#if info?.meta?.suggestion_prompts}
								<PromptSuggestions bind:promptSuggestions={info.meta.suggestion_prompts} />
							{:else}
								<p class="text-xs text-gray-500">
									{$i18n.t('Uses the default suggestions. Hidden when the model has task cards.')}
								</p>
							{/if}
						</div>
					</section>

					<!-- Knowledge, tools & skills -->
					<section class={sectionClass}>
						<div>
							<h2 class="text-sm font-semibold">{$i18n.t('Knowledge, tools & skills')}</h2>
							<p class="mt-0.5 text-xs text-gray-500">
								{$i18n.t('Attached here, they are available in every chat with this model.')}
							</p>
						</div>

						<Knowledge bind:selectedItems={knowledge} />
						<ToolsSelector bind:selectedToolIds={toolIds} tools={$tools ?? []} />
						<SkillsSelector bind:selectedSkillIds={skillIds} skills={skillsList} />

						{#if ($functions ?? []).filter((func) => func.type === 'filter').length > 0}
							<FiltersSelector
								bind:selectedFilterIds={filterIds}
								filters={($functions ?? []).filter((func) => func.type === 'filter')}
							/>

							{@const toggleableFilters = $functions.filter(
								(func) =>
									func.type === 'filter' &&
									(filterIds.includes(func.id) || func?.is_global) &&
									func?.meta?.toggle
							)}

							{#if toggleableFilters.length > 0}
								<DefaultFiltersSelector
									bind:selectedFilterIds={defaultFilterIds}
									filters={toggleableFilters}
								/>
							{/if}
						{/if}

						{#if ($functions ?? []).filter((func) => func.type === 'action').length > 0}
							<ActionsSelector
								bind:selectedActionIds={actionIds}
								actions={($functions ?? []).filter((func) => func.type === 'action')}
							/>
						{/if}
					</section>

					<!-- Capabilities -->
					<section class={sectionClass}>
						<div>
							<h2 class="text-sm font-semibold">{$i18n.t('Capabilities')}</h2>
							<p class="mt-0.5 text-xs text-gray-500">
								{$i18n.t('What users can do with this model, and what is switched on by default.')}
							</p>
						</div>

						<!-- Default features and built-in tool choices live inside the matching rows. -->
						<Capabilities bind:capabilities bind:defaultFeatureIds bind:builtinTools />

						{#if capabilities.terminal}
							<TerminalSelector bind:terminalId />
						{/if}
					</section>

					<!-- Voice -->
					<section class={sectionClass}>
						<div>
							<h2 class="text-sm font-semibold">{$i18n.t('Voice')}</h2>
							<p class="mt-0.5 text-xs text-gray-500">
								{$i18n.t('Voice used when answers are read aloud. Leave empty for the default.')}
							</p>
						</div>
						<TTSVoiceInput
							bind:value={tts.voice}
							{voices}
							placeholder={$i18n.t('e.g. alloy, echo, shimmer')}
						/>
					</section>

					<!-- JSON preview (for admins / debugging) -->
					<div class="px-1">
						<button
							class="text-xs text-gray-500 underline hover:text-gray-800 dark:hover:text-gray-200"
							type="button"
							on:click={() => {
								showPreview = !showPreview;
							}}
						>
							{showPreview ? $i18n.t('Hide JSON preview') : $i18n.t('Show JSON preview')}
						</button>

						{#if showPreview}
							<textarea
								class="mt-2 w-full resize-none rounded-lg bg-gray-50 p-3 font-mono text-xs text-gray-600 outline-hidden dark:bg-gray-850 dark:text-gray-400"
								rows="10"
								value={JSON.stringify(info, null, 2)}
								disabled
								readonly
							/>
						{/if}
					</div>
				</form>
			{/if}
		</div>

		<!-- Always-visible actions -->
		{#if !edit || (edit && model)}
			<div
				class="shrink-0 border-t border-gray-200 bg-white px-1 py-3 dark:border-gray-800 dark:bg-gray-900"
			>
				<div class="mx-auto flex w-full max-w-4xl flex-wrap items-center justify-between gap-3">
					<button
						type="button"
						class="flex min-w-0 items-center gap-1.5 text-xs text-gray-500 hover:text-gray-800 dark:hover:text-gray-200"
						title={$i18n.t('Change who can use this model')}
						on:click={() => (showAccessControlModal = true)}
					>
						<span class="truncate">{accessSummary}</span>
						<span class="shrink-0 underline">{$i18n.t('Change')}</span>
					</button>

					<div class="ml-auto flex items-center gap-2">
						{#if onBack}
							<button
								class="rounded-lg border border-gray-300 px-3.5 py-2 text-sm font-medium transition hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800"
								type="button"
								on:click={() => onBack()}
							>
								{$i18n.t('Cancel')}
							</button>
						{/if}
						<button
							class="flex items-center rounded-lg bg-black px-4 py-2 text-sm font-semibold text-white transition hover:bg-gray-800 disabled:opacity-60 dark:bg-white dark:text-black dark:hover:bg-gray-200"
							type="submit"
							form="model-editor-form"
							disabled={loading}
						>
							{edit ? $i18n.t('Save changes') : $i18n.t('Create model')}
							{#if loading}
								<div class="ml-1.5"><Spinner /></div>
							{/if}
						</button>
					</div>
				</div>
			</div>
		{/if}
	</div>
{/if}
