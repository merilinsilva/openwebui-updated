<script lang="ts">
	import { getContext, tick } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { config, settings, showMemoryPanel, memoryCount, showSettings } from '$lib/stores';
	import { addNewMemory, deleteMemoryById, getMemories, updateMemoryById } from '$lib/apis/memories';
	import { updateUserSettings } from '$lib/apis/users';

	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import Trash from '$lib/components/icons/Trash.svelte';
	import Search from '$lib/components/icons/Search.svelte';

	const i18n = getContext('i18n');

	type Memory = {
		id: string;
		content: string;
		type?: string;
		path?: string | null;
		created_at?: number;
		updated_at?: number;
	};

	const NEW_FOR_SECONDS = 24 * 60 * 60;
	const SEARCH_FROM = 8; // show a search box once there are this many memories

	let memories: Memory[] = [];
	let loading = false;
	let query = '';

	let adding = false;
	let newContent = '';
	let saving = false;

	let editingId: string | null = null;
	let editContent = '';

	$: memoryOn = $settings?.memory ?? $config?.features?.enable_memories ?? false;

	const load = async () => {
		loading = true;
		memories = ((await getMemories(localStorage.token).catch((e) => {
			toast.error(`${e}`);
			return [];
		})) ?? []) as Memory[];
		memories.sort((a, b) => (b.created_at ?? 0) - (a.created_at ?? 0));
		memoryCount.set(memories.length);
		loading = false;
	};

	$: if ($showMemoryPanel) {
		load();
	}

	$: if (!$showMemoryPanel) {
		adding = false;
		newContent = '';
		editingId = null;
		query = '';
	}

	const setMemoryOn = async (on: boolean) => {
		await settings.set({ ...$settings, memory: on });
		await updateUserSettings(localStorage.token, { ui: $settings }).catch((e) => {
			toast.error(`${e}`);
		});
	};

	const isNew = (m: Memory) =>
		!!m.created_at && Date.now() / 1000 - m.created_at < NEW_FOR_SECONDS;

	$: visible = query.trim()
		? memories.filter((m) =>
				`${m.content} ${m.path ?? ''}`.toLowerCase().includes(query.trim().toLowerCase())
			)
		: memories;

	const startAdding = async () => {
		adding = true;
		editingId = null;
		await tick();
		document.getElementById('memory-new-input')?.focus();
	};

	const saveNew = async () => {
		const content = newContent.trim();
		if (!content) return;
		saving = true;
		const res = await addNewMemory(localStorage.token, content).catch((e) => {
			toast.error(`${e}`);
			return null;
		});
		saving = false;
		if (res) {
			newContent = '';
			adding = false;
			await load();
		}
	};

	const startEditing = async (m: Memory) => {
		editingId = m.id;
		editContent = m.content;
		adding = false;
		await tick();
		document.getElementById(`memory-edit-${m.id}`)?.focus();
	};

	const saveEdit = async (m: Memory) => {
		const content = editContent.trim();
		if (!content || content === m.content) {
			editingId = null;
			return;
		}
		saving = true;
		const res = await updateMemoryById(localStorage.token, m.id, content).catch((e) => {
			toast.error(`${e}`);
			return null;
		});
		saving = false;
		if (res) {
			editingId = null;
			await load();
		}
	};

	const remove = async (m: Memory) => {
		const res = await deleteMemoryById(localStorage.token, m.id).catch((e) => {
			toast.error(`${e}`);
			return null;
		});
		if (!res) return;

		memories = memories.filter((x) => x.id !== m.id);
		memoryCount.set(memories.length);

		toast.success($i18n.t('Deleted from memory: "{{content}}"', { content: m.content }), {
			action: {
				label: $i18n.t('Undo'),
				onClick: async () => {
					await addNewMemory(
						localStorage.token,
						m.content,
						m.type ?? 'user',
						m.path ?? ''
					).catch((e) => toast.error(`${e}`));
					if ($showMemoryPanel) await load();
					else {
						const all = await getMemories(localStorage.token).catch(() => null);
						if (Array.isArray(all)) memoryCount.set(all.length);
					}
				}
			}
		});
	};

	// Enter adds a line; Ctrl/Cmd+Enter saves.
	const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform);
	$: shortcutHint = $i18n.t('{{key}}+Enter to save', { key: isMac ? '⌘' : 'Ctrl' });

	const inputClass =
		'w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm outline-hidden placeholder:text-gray-400 focus:border-gray-500 dark:border-gray-700 dark:bg-gray-900 dark:focus:border-gray-500';
	const iconButtonClass =
		'rounded-md p-1 text-gray-400 transition hover:bg-gray-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200';
</script>

<Modal bind:show={$showMemoryPanel} size="sm" className="bg-white dark:bg-gray-900 rounded-2xl">
	<div class="flex max-h-[calc(100dvh-3rem)] flex-col px-5 pt-4 pb-4 text-gray-900 dark:text-gray-100">
		<div class="flex items-center justify-between gap-3">
			<h2 class="text-base font-semibold">{$i18n.t('My memory')}</h2>
			<div class="flex items-center gap-3">
				<label for="memory-enabled" id="memory-enabled-label" class="text-sm">
					{$i18n.t('Memory')}
				</label>
				<Switch
					id="memory-enabled"
					ariaLabelledbyId="memory-enabled-label"
					state={memoryOn}
					on:change={(e) => setMemoryOn(e.detail)}
				/>
				<button
					class="rounded-lg p-1 text-gray-500 transition hover:bg-gray-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200"
					type="button"
					aria-label={$i18n.t('Close')}
					on:click={() => showMemoryPanel.set(false)}
				>
					<XMark className="size-4" />
				</button>
			</div>
		</div>

		<p class="mt-1.5 text-xs text-gray-500">
			{$i18n.t(
				'CHOn remembers these facts about you and uses them in all chats. Only you can see them. Do not store personal data of others.'
			)}
		</p>

		{#if !memoryOn}
			<div
				class="mt-3 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-200"
			>
				{$i18n.t('Memory is off. CHOn keeps these facts but does not use them in chats.')}
			</div>
		{/if}

		{#if memories.length >= SEARCH_FROM}
			<label
				class="mt-3 flex items-center gap-2 rounded-lg border border-gray-300 px-3 py-1.5 focus-within:border-gray-500 dark:border-gray-700"
			>
				<Search className="size-3.5 shrink-0 text-gray-500" />
				<input
					class="w-full bg-transparent text-sm outline-hidden placeholder:text-gray-400"
					bind:value={query}
					placeholder={$i18n.t('Search memories')}
					aria-label={$i18n.t('Search memories')}
				/>
			</label>
		{/if}

		<div class="mt-3 -mx-1 min-h-0 flex-1 overflow-y-auto px-1">
			{#if loading && memories.length === 0}
				<div class="flex justify-center py-8"><Spinner className="size-5" /></div>
			{:else if memories.length === 0 && !adding}
				<div class="py-8 text-center">
					<div class="text-sm">{$i18n.t('Nothing remembered yet')}</div>
					<p class="mt-1 text-xs text-gray-500">
						{$i18n.t(
							'Add facts like your role, site or preferred format, or click "Remember this" under an answer.'
						)}
					</p>
				</div>
			{:else}
				<ul class="flex flex-col gap-2">
					{#each visible as m (m.id)}
						<li class="rounded-lg border border-gray-200 px-3 py-2 dark:border-gray-800">
							{#if editingId === m.id}
								<form class="flex flex-col gap-2" on:submit|preventDefault={() => saveEdit(m)}>
									<textarea
										id="memory-edit-{m.id}"
										class="{inputClass} min-h-[4.5rem] resize-y"
										rows="3"
										bind:value={editContent}
										aria-label={$i18n.t('Edit memory')}
										on:keydown={(e) => {
											if (e.key === 'Escape') {
												e.stopPropagation();
												editingId = null;
											} else if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
												e.preventDefault();
												saveEdit(m);
											}
										}}
									></textarea>
									<p class="text-[0.6875rem] text-gray-500">{shortcutHint}</p>
									<div class="flex justify-end gap-2">
										<button
											type="button"
											class="rounded-lg px-3 py-1 text-xs text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
											on:click={() => (editingId = null)}
										>
											{$i18n.t('Cancel')}
										</button>
										<button
											type="submit"
											class="rounded-lg bg-black px-3 py-1 text-xs font-semibold text-white disabled:opacity-60 dark:bg-white dark:text-black"
											disabled={saving}
										>
											{$i18n.t('Save')}
										</button>
									</div>
								</form>
							{:else}
								<div class="flex items-start gap-2">
									<div class="min-w-0 flex-1">
										{#if m.path}
											<div class="truncate text-[0.6875rem] text-gray-500">{m.path}</div>
										{/if}
										<div class="text-sm break-words whitespace-pre-line">{m.content}</div>
									</div>
									{#if isNew(m)}
										<span
											class="shrink-0 rounded-full bg-green-50 px-2 py-0.5 text-[0.6875rem] text-green-700 dark:bg-green-950/40 dark:text-green-300"
										>
											{$i18n.t('New')}
										</span>
									{/if}
									<button
										type="button"
										class={iconButtonClass}
										aria-label={$i18n.t('Edit memory')}
										title={$i18n.t('Edit')}
										on:click={() => startEditing(m)}
									>
										<Pencil className="size-3.5" />
									</button>
									<button
										type="button"
										class="{iconButtonClass} hover:text-red-600 dark:hover:text-red-400"
										aria-label={$i18n.t('Delete memory')}
										title={$i18n.t('Delete')}
										on:click={() => remove(m)}
									>
										<Trash className="size-3.5" />
									</button>
								</div>
							{/if}
						</li>
					{/each}
				</ul>
			{/if}

			{#if adding}
				<form
					class="mt-2 flex flex-col gap-2 rounded-lg border border-gray-300 p-2 dark:border-gray-700"
					on:submit|preventDefault={saveNew}
				>
					<textarea
						id="memory-new-input"
						class="{inputClass} min-h-[4.5rem] resize-y"
						rows="3"
						bind:value={newContent}
						placeholder={$i18n.t(
							'e.g. Works in Quality Management, Rapperswil site.\nPrefers summaries in English with a table of action items.'
						)}
						aria-label={$i18n.t('New memory')}
						on:keydown={(e) => {
							if (e.key === 'Escape') {
								e.stopPropagation();
								adding = false;
							} else if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
								e.preventDefault();
								saveNew();
							}
						}}
					></textarea>
					<p class="text-[0.6875rem] text-gray-500">{shortcutHint}</p>
					<div class="flex justify-end gap-2">
						<button
							type="button"
							class="rounded-lg px-3 py-1 text-xs text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
							on:click={() => (adding = false)}
						>
							{$i18n.t('Cancel')}
						</button>
						<button
							type="submit"
							class="rounded-lg bg-black px-3 py-1 text-xs font-semibold text-white disabled:opacity-60 dark:bg-white dark:text-black"
							disabled={saving || !newContent.trim()}
						>
							{$i18n.t('Save')}
						</button>
					</div>
				</form>
			{/if}
		</div>

		<div class="mt-3 flex items-center justify-between gap-3">
			<button
				type="button"
				class="rounded-lg border border-gray-300 px-3.5 py-2 text-sm font-medium transition hover:bg-gray-50 disabled:opacity-60 dark:border-gray-700 dark:hover:bg-gray-800"
				disabled={adding}
				on:click={startAdding}
			>
				+ {$i18n.t('Add memory')}
			</button>
			<div class="flex items-center gap-3 text-xs text-gray-500">
				<span>
					{memories.length === 1
						? $i18n.t('1 memory')
						: $i18n.t('{{count}} memories', { count: memories.length })}
				</span>
				<button
					type="button"
					class="underline hover:text-gray-800 dark:hover:text-gray-200"
					title={$i18n.t('Memory settings, including clearing all memories')}
					on:click={() => {
						showMemoryPanel.set(false);
						showSettings.set('personalization');
					}}
				>
					{$i18n.t('More options')}
				</button>
			</div>
		</div>
	</div>
</Modal>
