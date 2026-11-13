<script lang="ts">
	import { getContext, createEventDispatcher, onMount, tick } from 'svelte';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '../icons/XMark.svelte';

	import { toast } from 'svelte-sonner';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { user, config, models } from '$lib/stores';

	import Textarea from '$lib/components/common/Textarea.svelte';
	import Knowledge from '$lib/components/workspace/Models/Knowledge.svelte';
	import { getFolderById } from '$lib/apis/folders';
	const i18n = getContext('i18n');

	export let show = false;
	export let onSubmit: Function = (e) => {};

	export let folderId = null;
	export let parentId = null;
	export let edit = false;

	let folder = null;
	let name = '';
	let meta = {
		background_image_url: null
	};
	let data: Record<string, any> = {
		system_prompt: '',
		files: []
	};

	let loading = false;
	let showExamples = false;

	// CHOn form styles (same as the prompt and knowledge forms).
	const fieldClass =
		'w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm outline-hidden placeholder:text-gray-400 focus:border-gray-500 dark:border-gray-700 dark:bg-gray-900 dark:focus:border-gray-500 dark:scheme-dark';

	const instructionExamples = [
		'Answer as a quality engineer. Use metric units. Keep answers short and list open actions at the end.',
		'This folder is about the Transformer X project. Always say which document a fact comes from.',
		'Write in simple English for colleagues who are not native speakers.'
	];

	// Default model: stored as data.model_ids (new chats in this folder start with it).
	$: canSetSystemPrompt =
		$user?.role === 'admin' || ($user?.permissions.chat?.system_prompt ?? true);
	$: modelOptions = ($models ?? [])
		.filter((m) => !(m?.info?.meta?.hidden ?? false))
		.sort((a, b) => (a.name ?? a.id).localeCompare(b.name ?? b.id));
	$: folderModelIds = (data?.model_ids ?? []).filter(Boolean);
	$: defaultModelValue =
		folderModelIds.length === 0 ? '' : folderModelIds.length === 1 ? folderModelIds[0] : '__keep__';

	const setDefaultModel = (value: string) => {
		if (value === '__keep__') return;
		// null (not []) so the folder falls back to the usual default model.
		data = { ...data, model_ids: value ? [value] : null };
	};

	const submitHandler = async () => {
		loading = true;

		if ((data?.files ?? []).some((file) => file.status === 'uploading')) {
			toast.error($i18n.t('Please wait until all files are uploaded.'));
			loading = false;
			return;
		}

		// Check folder max file count limit
		const maxFileCount = $config?.features?.folder_max_file_count ?? '';
		if (maxFileCount && (data?.files ?? []).length > maxFileCount) {
			toast.error(
				$i18n.t('Maximum number of files per folder is {{max}}.', { max: maxFileCount ?? 0 })
			);
			loading = false;
			return;
		}

		await onSubmit({
			name,
			meta,
			data,
			parent_id: edit ? undefined : parentId
		});
		show = false;
		loading = false;
	};

	const init = async () => {
		if (folderId) {
			folder = await getFolderById(localStorage.token, folderId).catch((error) => {
				toast.error(`${error}`);
				return null;
			});

			name = folder.name;
			meta = folder.meta || {
				background_image_url: null
			};
			data = folder.data || {
				system_prompt: '',
				files: []
			};
		}

		focusInput();
	};

	const focusInput = async () => {
		await tick();
		const input = document.getElementById('folder-name') as HTMLInputElement;
		if (input) {
			input.focus();
			input.select();
		}
	};

	$: if (show) {
		init();
	}

	$: if (!show && !edit) {
		name = '';
		meta = {
			background_image_url: null
		};
		data = {
			system_prompt: '',
			files: []
		};
		showExamples = false;
	}
</script>

<Modal size="md" bind:show className="bg-white dark:bg-gray-900 rounded-2xl">
	<div class="text-gray-900 dark:text-gray-100">
		<div class="flex items-center justify-between px-5 pt-4">
			<h2 class="text-base font-semibold">
				{edit ? $i18n.t('Edit folder') : $i18n.t('New project folder')}
			</h2>
			<button
				aria-label={$i18n.t('Close')}
				class="rounded-lg p-1 text-gray-500 transition hover:bg-gray-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200"
				type="button"
				on:click={() => {
					show = false;
				}}
			>
				<XMark className="size-4" />
			</button>
		</div>

		<form
			class="flex flex-col gap-4 px-5 pt-4 pb-4"
			on:submit|preventDefault={() => {
				submitHandler();
			}}
		>
			<div class="flex flex-col gap-1.5">
				<label for="folder-name" class="text-sm font-semibold">{$i18n.t('Folder name')}</label>
				<input
					id="folder-name"
					class={fieldClass}
					type="text"
					bind:value={name}
					placeholder={$i18n.t('e.g. Project Transformer X')}
					autocomplete="off"
					required
				/>
			</div>

			{#if canSetSystemPrompt}
				<div class="flex flex-col gap-1.5">
					<label for="folder-instructions" class="text-sm font-semibold">
						{$i18n.t('Instructions for CHOn in this folder')}
						<span class="font-normal text-gray-500">({$i18n.t('optional')})</span>
					</label>
					<Textarea
						id="folder-instructions"
						className="{fieldClass} resize-none overflow-y-hidden"
						placeholder={$i18n.t(
							'e.g. "Answer as a quality engineer. Use metric units. Keep answers short and list open actions at the end."'
						)}
						rows={3}
						maxSize={200}
						bind:value={data.system_prompt}
					/>
					<p class="text-xs text-gray-500">
						{$i18n.t('Applies to every chat in this folder.')}
						<button
							type="button"
							class="underline hover:text-gray-800 dark:hover:text-gray-200"
							aria-expanded={showExamples}
							on:click={() => (showExamples = !showExamples)}
						>
							{showExamples ? $i18n.t('Hide examples') : $i18n.t('See examples')}
						</button>
					</p>
					{#if showExamples}
						<ul class="flex flex-col gap-1">
							{#each instructionExamples as example}
								<li>
									<button
										type="button"
										class="w-full rounded-lg border border-dashed border-gray-300 px-3 py-1.5 text-left text-xs text-gray-700 transition hover:border-gray-500 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-850"
										title={$i18n.t('Use this example')}
										on:click={() => {
											data.system_prompt = $i18n.t(example);
											showExamples = false;
										}}
									>
										{$i18n.t(example)}
									</button>
								</li>
							{/each}
						</ul>
					{/if}
				</div>
			{/if}

			<div class="flex flex-col gap-1.5">
				<Knowledge
					bind:selectedItems={data.files}
					addLabel={$i18n.t('Add existing')}
					uploadLabel={$i18n.t('Upload files to new knowledge base')}
					uploadToNewKnowledgeBase={{ name: () => name }}
					chipTone="brand"
				>
					<div slot="label" class="text-sm font-semibold">
						{$i18n.t('Knowledge for this folder')}
						<span class="font-normal text-gray-500">({$i18n.t('optional')})</span>
					</div>
					<p slot="help" class="mt-1.5 text-xs text-gray-500">
						{$i18n.t('CHOn searches these documents in every chat of this folder.')}
					</p>
				</Knowledge>
			</div>

			<div class="flex flex-col gap-1.5">
				<label for="folder-default-model" class="text-sm font-semibold">
					{$i18n.t('Default model')}
				</label>
				<select
					id="folder-default-model"
					class="{fieldClass} cursor-pointer"
					value={defaultModelValue}
					on:change={(e) => setDefaultModel(e.currentTarget.value)}
				>
					<option value="">{$i18n.t('Use the usual default')}</option>
					{#if defaultModelValue === '__keep__'}
						<option value="__keep__">
							{$i18n.t('Keep current selection ({{count}} models)', {
								count: folderModelIds.length
							})}
						</option>
					{/if}
					{#each modelOptions as m (m.id)}
						<option value={m.id}>{m.name ?? m.id}</option>
					{/each}
				</select>
			</div>

			<input
				id="folder-background-image-input"
				type="file"
				hidden
				accept="image/*"
				on:change={(e) => {
					const inputFiles = e.target.files;

					let reader = new FileReader();
					reader.onload = (event) => {
						let originalImageUrl = `${event.target.result}`;
						meta.background_image_url = originalImageUrl;
					};

					if (
						inputFiles &&
						inputFiles.length > 0 &&
						['image/gif', 'image/webp', 'image/jpeg', 'image/png'].includes(inputFiles[0]['type'])
					) {
						reader.readAsDataURL(inputFiles[0]);
					} else {
						console.log(`Unsupported File Type '${inputFiles[0]['type']}'.`);

						// clear the input
						e.target.value = '';
					}
				}}
			/>

			<!-- Not in the create mockup; kept for editing (creating a folder doesn't save it anyway). -->
			{#if edit}
			<div class="flex items-center justify-between gap-3">
				<div>
					<div class="text-sm font-semibold" id="folder-background-label">
						{$i18n.t('Background image')}
						<span class="font-normal text-gray-500">({$i18n.t('optional')})</span>
					</div>
					<p class="text-xs text-gray-500">{$i18n.t('Shown behind chats in this folder.')}</p>
				</div>
				<button
					aria-labelledby="folder-background-label background-image-url-state"
					class="shrink-0 rounded-lg border border-gray-300 bg-white px-2.5 py-1 text-xs text-gray-800 transition hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200 dark:hover:bg-gray-800"
					on:click={() => {
						if (meta?.background_image_url !== null) {
							meta.background_image_url = null;
						} else {
							const input = document.getElementById('folder-background-image-input');
							if (input) {
								input.click();
							}
						}
					}}
					type="button"
				>
					<span id="background-image-url-state">
						{(meta?.background_image_url ?? null) === null
							? `↑ ${$i18n.t('Upload')}`
							: $i18n.t('Remove')}
					</span>
				</button>
			</div>
			{/if}

			<div class="flex flex-wrap items-center justify-between gap-3 pt-1">
				{#if !edit || !folder?.user_id || folder.user_id === $user?.id}
					<p class="text-xs text-gray-500">{$i18n.t('Only you can see this folder.')}</p>
				{/if}

				<div class="ml-auto flex items-center gap-2">
					<button
						class="rounded-lg border border-gray-300 px-3.5 py-2 text-sm font-medium transition hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800"
						type="button"
						on:click={() => {
							show = false;
						}}
					>
						{$i18n.t('Cancel')}
					</button>
					<button
						class="flex items-center rounded-lg bg-black px-4 py-2 text-sm font-semibold text-white transition hover:bg-gray-800 disabled:opacity-60 dark:bg-white dark:text-black dark:hover:bg-gray-200"
						type="submit"
						disabled={loading}
					>
						{edit ? $i18n.t('Save changes') : $i18n.t('Create folder')}
						{#if loading}
							<div class="ml-1.5"><Spinner /></div>
						{/if}
					</button>
				</div>
			</div>
		</form>
	</div>
</Modal>
