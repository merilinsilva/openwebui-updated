<script>
	import { toast } from 'svelte-sonner';

	import { goto } from '$app/navigation';
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { user, config, pendingKnowledgeUploads } from '$lib/stores';
	import { createNewKnowledge } from '$lib/apis/knowledge';

	import AccessControlModal from '../common/AccessControlModal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let modal = false;
	/** @type {() => void | Promise<void>} */
	export let onBack = () => goto('/workspace/knowledge');
	/** @type {(knowledge: { id: string }) => void | Promise<void>} */
	export let onCreated = (knowledge) => goto(`/workspace/knowledge/${knowledge.id}`);

	let loading = false;

	let name = '';
	let description = '';
	/** @type {{ id?: string; principal_type: 'user' | 'group'; principal_id: string; permission: 'read' | 'write' }[]} */
	let accessGrants = [];
	let showAccessControlModal = false;

	// Files picked here are uploaded on the new knowledge base's page (with per-file status).
	/** @type {File[]} */
	let files = [];
	let draggingOver = false;
	/** @type {HTMLInputElement} */
	let fileInput;

	/** @param {FileList | File[] | null | undefined} list */
	const addFiles = (list) => {
		const incoming = Array.from(list ?? []);
		const key = (/** @type {File} */ f) => `${f.name}:${f.size}:${f.lastModified}`;
		const existing = new Set(files.map(key));
		files = [...files, ...incoming.filter((f) => !existing.has(key(f)))];
	};

	/** @param {File} f */
	const tooLarge = (f) =>
		($config?.file?.max_size ?? null) !== null && f.size > $config.file.max_size * 1024 * 1024;

	/** @param {number} bytes */
	const formatSize = (bytes) =>
		bytes < 1024 * 1024
			? `${Math.max(1, Math.round(bytes / 1024))} KB`
			: `${(bytes / 1024 / 1024).toFixed(1)} MB`;

	const fieldClass =
		'w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm outline-hidden placeholder:text-gray-400 focus:border-gray-500 dark:border-gray-700 dark:bg-gray-900 dark:focus:border-gray-500';

	// One-line "who can see this" next to the create button.
	$: accessSummary =
		accessGrants.length === 0
			? $i18n.t('Only you can see this knowledge base.')
			: accessGrants.some((g) => g.principal_id === '*')
				? $i18n.t('Everyone at Weidmann can use it.')
				: $i18n.t('Shared with selected people or teams.');

	const submitHandler = async () => {
		loading = true;

		if (name.trim() === '' || description.trim() === '') {
			toast.error($i18n.t('Please fill in all fields.'));
			name = '';
			description = '';
			loading = false;
			return;
		}

		const res = await createNewKnowledge(localStorage.token, name, description, accessGrants).catch(
			(e) => {
				toast.error(`${e}`);
			}
		);

		if (res) {
			toast.success($i18n.t('Knowledge created successfully.'));
			if (files.length > 0) {
				pendingKnowledgeUploads.set({ knowledgeId: res.id, files });
			}
			await onCreated(res);
		}

		loading = false;
	};
</script>

<AccessControlModal
	bind:show={showAccessControlModal}
	bind:accessGrants
	accessRoles={['read', 'write']}
	share={$user?.permissions?.sharing?.knowledge || $user?.role === 'admin'}
	sharePublic={$user?.permissions?.sharing?.public_knowledge || $user?.role === 'admin'}
	shareUsers={($user?.permissions?.access_grants?.allow_users ?? true) || $user?.role === 'admin'}
/>

<div class="w-full max-h-full text-gray-900 dark:text-gray-100">
	{#if modal}
		<div class="flex items-center justify-between px-5 pt-4">
			<h2 class="text-base font-semibold">{$i18n.t('New knowledge base')}</h2>
			<button
				class="rounded-lg p-1 text-gray-500 transition hover:bg-gray-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200"
				aria-label={$i18n.t('Close')}
				type="button"
				on:click={() => {
					onBack();
				}}
			>
				<XMark className="size-4" />
			</button>
		</div>
	{:else}
		<button
			class="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800 dark:hover:text-gray-200"
			type="button"
			on:click={() => {
				onBack();
			}}
		>
			← {$i18n.t('Back')}
		</button>
	{/if}

	<form
		class="flex flex-col gap-4 {modal ? 'px-5 pt-4 pb-4' : 'mx-auto mt-10 mb-10 max-w-lg'}"
		on:submit|preventDefault={() => {
			submitHandler();
		}}
	>
		{#if !modal}
			<h1 class="text-xl font-semibold">{$i18n.t('New knowledge base')}</h1>
		{/if}

		<div class="flex flex-col gap-1.5">
			<label for="knowledge-name" class="text-sm font-semibold">{$i18n.t('Name')}</label>
			<input
				id="knowledge-name"
				class={fieldClass}
				type="text"
				bind:value={name}
				placeholder={$i18n.t('e.g. Transformer X specs')}
				required
			/>
		</div>

		<div class="flex flex-col gap-1.5">
			<label for="knowledge-description" class="text-sm font-semibold">
				{$i18n.t('What is it for?')}
			</label>
			<textarea
				id="knowledge-description"
				class="{fieldClass} resize-y"
				rows="3"
				bind:value={description}
				placeholder={$i18n.t(
					'e.g. Design specs and test reports for Transformer X, used to answer questions about ratings and limits.'
				)}
				required
			></textarea>
			<p class="text-xs text-gray-500">
				{$i18n.t('Helps colleagues pick the right knowledge base. CHOn also uses it when searching.')}
			</p>
		</div>

		<div class="flex flex-col gap-1.5">
			<div class="text-sm font-semibold">
				{$i18n.t('Documents')}
				<span class="font-normal text-gray-500">({$i18n.t('optional')})</span>
			</div>

			<input
				bind:this={fileInput}
				type="file"
				multiple
				hidden
				on:change={(e) => {
					addFiles(e.currentTarget.files);
					e.currentTarget.value = '';
				}}
			/>
			<button
				type="button"
				class="flex w-full flex-col items-center gap-0.5 rounded-xl border border-dashed px-4 py-4 text-center transition {draggingOver
					? 'border-gray-700 bg-gray-50 dark:border-gray-300 dark:bg-gray-850'
					: 'border-gray-300 hover:border-gray-500 hover:bg-gray-50 dark:border-gray-700 dark:hover:border-gray-500 dark:hover:bg-gray-850'}"
				on:click={() => fileInput?.click()}
				on:dragover|preventDefault|stopPropagation={() => (draggingOver = true)}
				on:dragleave|preventDefault|stopPropagation={() => (draggingOver = false)}
				on:drop|preventDefault|stopPropagation={(e) => {
					draggingOver = false;
					addFiles(e.dataTransfer?.files);
				}}
			>
				<span class="text-sm text-gray-800 dark:text-gray-200">
					↑ {$i18n.t('Drop files here or')}
					<span class="underline">{$i18n.t('browse')}</span>
				</span>
				<span class="text-xs text-gray-500">
					{$i18n.t('PDF, Word, PowerPoint, Excel, text')}{#if $config?.file?.max_size}
						· {$i18n.t('max {{size}} MB per file', { size: $config.file.max_size })}{/if}
				</span>
			</button>

			{#if files.length > 0}
				<ul class="flex max-h-40 flex-col gap-1 overflow-y-auto">
					{#each files as f, idx (`${f.name}:${f.size}:${f.lastModified}`)}
						<li class="flex items-center gap-2 text-sm">
							<span class="min-w-0 flex-1 truncate" title={f.name}>{f.name}</span>
							{#if tooLarge(f)}
								<span class="shrink-0 text-xs text-red-700 dark:text-red-400">
									{$i18n.t('Too large (max {{size}} MB)', { size: $config.file.max_size })}
								</span>
							{:else}
								<span class="shrink-0 text-xs text-gray-500">{formatSize(f.size)}</span>
							{/if}
							<button
								type="button"
								class="shrink-0 rounded p-0.5 text-gray-400 hover:bg-gray-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200"
								aria-label={$i18n.t('Remove {{name}}', { name: f.name })}
								on:click={() => (files = files.filter((_, i) => i !== idx))}
							>
								<XMark className="size-3.5" />
							</button>
						</li>
					{/each}
				</ul>
			{/if}
			<p class="text-xs text-gray-500">
				{$i18n.t('Uploads start when you create the knowledge base. You can add more later.')}
			</p>
		</div>

		<div class="flex flex-wrap items-center justify-between gap-3 pt-1">
			<button
				type="button"
				class="flex min-w-0 items-center gap-1.5 text-xs text-gray-500 hover:text-gray-800 dark:hover:text-gray-200"
				title={$i18n.t('Change who can use this knowledge base')}
				on:click={() => (showAccessControlModal = true)}
			>
				<span class="truncate">{accessSummary}</span>
				<span class="shrink-0 underline">{$i18n.t('Change')}</span>
			</button>

			<div class="ml-auto flex items-center gap-2">
				{#if modal}
					<button
						class="rounded-lg border border-gray-300 px-3.5 py-2 text-sm font-medium transition hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800"
						type="button"
						on:click={() => {
							onBack();
						}}
					>
						{$i18n.t('Cancel')}
					</button>
				{/if}

				<button
					class="flex items-center rounded-lg bg-black px-4 py-2 text-sm font-semibold text-white transition hover:bg-gray-800 disabled:opacity-60 dark:bg-white dark:text-black dark:hover:bg-gray-200"
					type="submit"
					disabled={loading}
				>
					{$i18n.t('Create knowledge base')}
					{#if loading}
						<div class="ml-1.5">
							<Spinner />
						</div>
					{/if}
				</button>
			</div>
		</div>
	</form>
</div>
