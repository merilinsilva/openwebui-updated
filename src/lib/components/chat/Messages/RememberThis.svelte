<script lang="ts">
	import { getContext, tick } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { memoryCount } from '$lib/stores';
	import { addNewMemory, deleteMemoryById, getMemories } from '$lib/apis/memories';

	import Dropdown from '$lib/components/common/Dropdown.svelte';

	const i18n = getContext('i18n');

	// Text to start from, usually the user's question to this answer.
	export let suggestion = '';
	export let buttonClass = '';

	let show = false;
	let content = '';
	let saving = false;

	const MAX_SUGGESTION = 500;

	const open = async () => {
		// Keep line breaks (memories can be several lines), but tidy up blank runs and spaces.
		const s = (suggestion ?? '')
			.replace(/[ \t]+/g, ' ')
			.replace(/\n{3,}/g, '\n\n')
			.trim();
		content = s.length > MAX_SUGGESTION ? `${s.slice(0, MAX_SUGGESTION)}…` : s;
		await tick();
		const input = document.getElementById('remember-this-input') as HTMLInputElement | null;
		input?.focus();
		input?.select();
	};

	$: if (show) open();

	const refreshCount = async () => {
		const all = await getMemories(localStorage.token).catch(() => null);
		if (Array.isArray(all)) memoryCount.set(all.length);
	};

	const save = async () => {
		const text = content.trim();
		if (!text) return;
		saving = true;
		const res = await addNewMemory(localStorage.token, text).catch((e) => {
			toast.error(`${e}`);
			return null;
		});
		saving = false;
		if (!res) return;

		show = false;
		refreshCount();
		toast.success($i18n.t('Saved to memory: "{{content}}"', { content: text }), {
			action: {
				label: $i18n.t('Undo'),
				onClick: async () => {
					await deleteMemoryById(localStorage.token, res.id).catch((e) => toast.error(`${e}`));
					refreshCount();
				}
			}
		});
	};
</script>

<Dropdown bind:show align="start" sideOffset={6}>
	<button
		type="button"
		class={buttonClass}
		aria-label={$i18n.t('Remember this')}
		title={$i18n.t('Save a fact from this chat to My memory')}
	>
		+ {$i18n.t('Remember this')}
	</button>

	<div slot="content">
		<form
			class="w-80 max-w-[calc(100vw-2rem)] rounded-xl border border-gray-200 bg-white p-3 text-gray-900 shadow-lg dark:border-gray-800 dark:bg-gray-900 dark:text-gray-100"
			on:submit|preventDefault={save}
		>
			<label for="remember-this-input" class="text-sm font-semibold">
				{$i18n.t('Remember for future chats')}
			</label>
			<textarea
				id="remember-this-input"
				class="mt-1.5 min-h-[4.5rem] w-full resize-y rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm outline-hidden placeholder:text-gray-400 focus:border-gray-500 dark:border-gray-700 dark:bg-gray-900 dark:focus:border-gray-500"
				rows="3"
				bind:value={content}
				placeholder={$i18n.t('e.g. Use metric units')}
				on:keydown={(e) => {
					if (e.key === 'Escape') {
						e.stopPropagation();
						show = false;
					} else if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
						e.preventDefault();
						save();
					}
				}}
			></textarea>
			<p class="mt-1 text-xs text-gray-500">
				{$i18n.t('One fact or preference works best. Only you can see it.')}
				{$i18n.t('{{key}}+Enter to save.', {
					key:
						typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform)
							? '⌘'
							: 'Ctrl'
				})}
			</p>
			<div class="mt-2 flex justify-end gap-2">
				<button
					type="button"
					class="rounded-lg px-3 py-1 text-xs text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
					on:click={() => (show = false)}
				>
					{$i18n.t('Cancel')}
				</button>
				<button
					type="submit"
					class="rounded-lg bg-black px-3 py-1 text-xs font-semibold text-white disabled:opacity-60 dark:bg-white dark:text-black"
					disabled={saving || !content.trim()}
				>
					{$i18n.t('Save to memory')}
				</button>
			</div>
		</form>
	</div>
</Dropdown>
