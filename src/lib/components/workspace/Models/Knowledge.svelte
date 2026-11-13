<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { config, knowledge, settings, user } from '$lib/stores';

	import KnowledgeSelector from './Knowledge/KnowledgeSelector.svelte';
	import FileItemModal from '$lib/components/common/FileItemModal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ChatBubble from '$lib/components/icons/ChatBubble.svelte';
	import Database from '$lib/components/icons/Database.svelte';
	import DocumentPage from '$lib/components/icons/DocumentPage.svelte';
	import Folder from '$lib/components/icons/Folder.svelte';
	import PageEdit from '$lib/components/icons/PageEdit.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	import { getKnowledgeBases, createNewKnowledge } from '$lib/apis/knowledge';
	import { uploadFile } from '$lib/apis/files';

	import { toast } from 'svelte-sonner';
	import { v4 as uuidv4 } from 'uuid';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	export let selectedItems = [];

	// Optional wording / look (e.g. the project folder dialog).
	export let addLabel = '';
	export let uploadLabel = '';
	export let chipTone: 'neutral' | 'brand' = 'neutral';
	// When set, "Upload" puts the files into a new knowledge base (named after `name()`) and
	// attaches that knowledge base, instead of attaching the loose files.
	export let uploadToNewKnowledgeBase: { name: () => string } | null = null;

	// The knowledge base created by this picker, reused for later uploads.
	let createdKnowledgeBase: any = null;

	const setItem = (id: string, patch: Record<string, any>) => {
		selectedItems = selectedItems.map((item) => (item.id === id ? { ...item, ...patch } : item));
	};

	const uploadIntoNewKnowledgeBase = async (files: File[]) => {
		if ($user?.role !== 'admin' && !($user?.permissions?.chat?.file_upload ?? true)) {
			toast.error($i18n.t('You do not have permission to upload files.'));
			return;
		}

		const maxSize = $config?.file?.max_size ?? null;
		const valid = files.filter((file) => {
			if (file.size === 0) {
				toast.error($i18n.t('"{{name}}" is empty.', { name: file.name }));
				return false;
			}
			if (maxSize !== null && file.size > maxSize * 1024 * 1024) {
				toast.error(
					$i18n.t('"{{name}}" is larger than {{maxSize}} MB.', { name: file.name, maxSize })
				);
				return false;
			}
			return true;
		});
		if (valid.length === 0) return;

		// Create the knowledge base on first upload; afterwards keep adding to it.
		if (!createdKnowledgeBase) {
			const base = uploadToNewKnowledgeBase?.name()?.trim() || $i18n.t('Project folder');
			const kb = await createNewKnowledge(
				localStorage.token,
				$i18n.t('{{name}} files', { name: base }),
				$i18n.t('Files uploaded for the "{{name}}" project folder.', { name: base }),
				[]
			).catch((e) => {
				toast.error(`${e}`);
				return null;
			});
			if (!kb) return;
			createdKnowledgeBase = { ...kb, type: 'collection' };
		}

		const kbId = createdKnowledgeBase.id;
		if (!selectedItems.find((item) => item.id === kbId)) {
			selectedItems = [...selectedItems, createdKnowledgeBase];
		}

		// While uploading, the chip shows progress and the folder can't be saved yet.
		const total = valid.length;
		setItem(kbId, { status: 'uploading', uploadProgress: `0/${total}` });

		const failed: string[] = [];
		for (const [idx, file] of valid.entries()) {
			try {
				// The server reads the file and adds it to the knowledge base itself.
				const res = await uploadFile(localStorage.token, file, { knowledge_id: kbId });
				if (!res || res.error) failed.push(file.name);
			} catch (e) {
				failed.push(file.name);
			}
			setItem(kbId, { uploadProgress: `${idx + 1}/${total}` });
		}

		selectedItems = selectedItems.map((item) => {
			if (item.id !== kbId) return item;
			const { status, uploadProgress, ...rest } = item;
			return rest;
		});

		if (failed.length > 0) {
			toast.error(
				$i18n.t('{{count}} of {{total}} files could not be added: {{names}}', {
					count: failed.length,
					total,
					names: failed.join(', ')
				})
			);
		} else {
			toast.success(
				$i18n.t('Added {{count}} files to "{{name}}".', {
					count: total,
					name: createdKnowledgeBase.name
				})
			);
		}
	};

	const addButtonClass =
		'flex min-w-0 items-center rounded-lg border border-gray-300 bg-white px-2.5 py-1 text-xs text-gray-800 outline-hidden transition hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200 dark:hover:bg-gray-800';
	const i18n = getContext('i18n');

	let loaded = false;

	let filesInputElement = null;
	let inputFiles = null;

	let showItemModal = false;
	let selectedItemIdx = null;

	$: if (selectedItems == null) {
		selectedItems = [];
	}

	const uploadFileHandler = async (file, fullContext: boolean = false) => {
		if ($user?.role !== 'admin' && !($user?.permissions?.chat?.file_upload ?? true)) {
			toast.error($i18n.t('You do not have permission to upload files.'));
			return null;
		}

		const tempItemId = uuidv4();
		const fileItem = {
			type: 'file',
			file: '',
			id: null,
			url: '',
			name: file.name,
			collection_name: '',
			status: 'uploading',
			size: file.size,
			error: '',
			itemId: tempItemId,
			...(fullContext ? { context: 'full' } : {})
		};

		if (fileItem.size == 0) {
			toast.error($i18n.t('You cannot upload an empty file.'));
			return null;
		}

		selectedItems = [...selectedItems, fileItem];

		try {
			// If the file is an audio file, provide the language for STT.
			let metadata = null;
			if (
				(file.type.startsWith('audio/') || file.type.startsWith('video/')) &&
				$settings?.audio?.stt?.language
			) {
				metadata = {
					language: $settings?.audio?.stt?.language
				};
			}

			// During the file upload, file content is automatically extracted.
			const uploadedFile = await uploadFile(localStorage.token, file, metadata);

			if (uploadedFile) {
				console.log('File upload completed:', {
					id: uploadedFile.id,
					name: fileItem.name,
					collection: uploadedFile?.meta?.collection_name
				});

				if (uploadedFile.error) {
					console.warn('File upload warning:', uploadedFile.error);
					toast.warning(uploadedFile.error);
				}

				fileItem.status = 'uploaded';
				fileItem.file = uploadedFile;
				fileItem.id = uploadedFile.id;
				fileItem.collection_name =
					uploadedFile?.meta?.collection_name || uploadedFile?.collection_name;
				fileItem.url = `${uploadedFile.id}`;

				selectedItems = selectedItems;
			} else {
				selectedItems = selectedItems.filter((item) => item?.itemId !== tempItemId);
			}
		} catch (e) {
			toast.error(`${e}`);
			selectedItems = selectedItems.filter((item) => item?.itemId !== tempItemId);
		}
	};

	const inputFilesHandler = async (inputFiles) => {
		console.log('Input files handler called with:', inputFiles);

		inputFiles.forEach(async (file) => {
			console.log('Processing file:', {
				name: file.name,
				type: file.type,
				size: file.size,
				extension: file.name.split('.').at(-1)
			});

			if (
				($config?.file?.max_size ?? null) !== null &&
				file.size > ($config?.file?.max_size ?? 0) * 1024 * 1024
			) {
				console.log('File exceeds max size limit:', {
					fileSize: file.size,
					maxSize: ($config?.file?.max_size ?? 0) * 1024 * 1024
				});
				toast.error(
					$i18n.t(`File size should not exceed {{maxSize}} MB.`, {
						maxSize: $config?.file?.max_size
					})
				);
				return;
			}

			if (!file['type'].startsWith('image/')) {
				uploadFileHandler(file);
			} else {
				toast.error($i18n.t(`Unsupported file type.`));
			}
		});
	};

	onMount(async () => {
		loaded = true;
	});
</script>

{#if showItemModal && selectedItemIdx !== null && selectedItems[selectedItemIdx]}
	<FileItemModal bind:show={showItemModal} bind:item={selectedItems[selectedItemIdx]} edit={true} />
{/if}

<input
	bind:this={filesInputElement}
	bind:files={inputFiles}
	type="file"
	hidden
	multiple
	on:change={async () => {
		if (inputFiles && inputFiles.length > 0) {
			const _inputFiles = Array.from(inputFiles) as File[];
			if (uploadToNewKnowledgeBase) {
				uploadIntoNewKnowledgeBase(_inputFiles);
			} else {
				inputFilesHandler(_inputFiles);
			}
		} else {
			toast.error($i18n.t(`File not found.`));
		}

		filesInputElement.value = '';
	}}
/>

<div>
	<div class="mb-1.5 min-w-0">
		<slot name="label">
			<div class="text-sm font-semibold text-gray-900 dark:text-gray-100">{$i18n.t('Knowledge')}</div>
			<p class="text-xs text-gray-500">
				{$i18n.t('Knowledge bases and files the model searches in every chat.')}
			</p>
		</slot>
	</div>

	<!-- Chosen items and the add/upload buttons share one wrapping row. -->
	<div class="flex flex-wrap items-center gap-1.5">
		{#each selectedItems ?? [] as file, fileIdx}
			<Tooltip content={file.description || file.name || file.id}>
				<div
					class="flex max-w-56 items-center gap-1.5 rounded-full border py-0.5 pr-1 pl-2.5 text-xs {chipTone ===
					'brand'
						? 'border-red-400 bg-red-50 text-gray-900 dark:border-red-500 dark:bg-red-950/40 dark:text-gray-100'
						: 'border-gray-300 text-gray-800 dark:border-gray-700 dark:text-gray-200'}"
				>
					<button
						type="button"
						class="flex min-w-0 items-center gap-1.5"
						aria-label={$i18n.t('Edit')}
						on:click={() => {
							selectedItemIdx = fileIdx;
							showItemModal = true;
						}}
					>
						<div class="shrink-0 text-gray-500 dark:text-gray-400">
							{#if file.status === 'uploading'}
								<Spinner className="size-3.5" />
							{:else if file.type === 'collection'}
								<Database className="size-3.5" />
							{:else if file.type === 'note'}
								<PageEdit className="size-3.5" />
							{:else if file.type === 'chat'}
								<ChatBubble className="size-3.5" />
							{:else if file.type === 'folder'}
								<Folder className="size-3.5" />
							{:else}
								<DocumentPage className="size-3.5" />
							{/if}
						</div>

						<div class="min-w-0 truncate">
							{file.name || file.id}
						</div>
					</button>

					{#if file.status === 'uploading'}
						<div class="shrink-0 text-gray-400 dark:text-gray-500">
							{$i18n.t('Uploading')}{file.uploadProgress ? ` ${file.uploadProgress}` : ''}
						</div>
					{/if}

					<button
						type="button"
						class="flex shrink-0 items-center justify-center rounded-full p-0.5 text-gray-400 hover:bg-gray-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200"
						aria-label={$i18n.t('Remove {{name}}', { name: file.name || file.id })}
						on:click={() => {
							selectedItems = selectedItems.filter((_, idx) => idx !== fileIdx);
						}}
					>
						<XMark className="size-3" />
					</button>
				</div>
			</Tooltip>
		{/each}

		{#if loaded}
			<KnowledgeSelector
				on:select={(e) => {
					const item = e.detail;

					if (!selectedItems.find((k) => k.id === item.id)) {
						selectedItems = [
							...selectedItems,
							{
								...item
							}
						];
					}
				}}
			>
				<div class={addButtonClass}>
					<span class="truncate">+ {addLabel || $i18n.t('Add knowledge')}</span>
				</div>
			</KnowledgeSelector>

			{#if $user?.role === 'admin' || $user?.permissions?.chat?.file_upload}
				<button
					class={addButtonClass}
					type="button"
					aria-label={$i18n.t('Upload Files')}
					on:click={() => {
						filesInputElement.click();
					}}
				>
					↑ {uploadLabel || $i18n.t('Upload files')}
				</button>
			{/if}
		{/if}

		{#if (selectedItems ?? []).length > 1}
			<button
				type="button"
				class="text-xs text-gray-500 underline hover:text-gray-800 dark:hover:text-gray-200"
				on:click={() => {
					selectedItems = [];
				}}
			>
				{$i18n.t('Remove all')}
			</button>
		{/if}
	</div>

	<slot name="help" />
</div>
