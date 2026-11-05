<script lang="ts">
	import { onMount, getContext } from 'svelte';

	import { getPrompts } from '$lib/apis/prompts';

	import XMark from '$lib/components/icons/XMark.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';

	const i18n = getContext('i18n');

	// Up to 4 prompt-library IDs shown as task cards on the new-chat screen, in order.
	export let promptIds: string[] = [];
	const MAX_TASKS = 4;

	$: if (!Array.isArray(promptIds)) promptIds = [];

	let prompts = [];
	let loaded = false;
	let query = '';

	onMount(async () => {
		prompts = (await getPrompts(localStorage.token).catch(() => null)) ?? [];
		loaded = true;
	});

	const commandOf = (p) => `/${(p?.command ?? '').replace(/^\//, '')}`;

	$: promptById = new Map(prompts.map((p) => [p.id, p]));

	$: candidates = prompts
		.filter((p) => !promptIds.includes(p.id))
		.filter((p) => {
			const q = query.trim().toLowerCase();
			return !q || `${p.name} ${p.command}`.toLowerCase().includes(q);
		})
		.sort((a, b) => a.name.localeCompare(b.name));

	const add = (id: string) => {
		if (promptIds.length >= MAX_TASKS) return;
		promptIds = [...promptIds, id];
		query = '';
	};

	const remove = (idx: number) => {
		promptIds = promptIds.filter((_, i) => i !== idx);
	};

	const move = (idx: number, delta: number) => {
		const next = [...promptIds];
		const target = idx + delta;
		if (target < 0 || target >= next.length) return;
		[next[idx], next[target]] = [next[target], next[idx]];
		promptIds = next;
	};
</script>

<div class="space-y-2">
	<div class="text-xs text-gray-500 dark:text-gray-400">
		{$i18n.t(
			'Pick up to 4 prompts from the prompt library to show as task cards on the new chat screen. With none picked, the 4 most recently updated prompts are shown.'
		)}
	</div>

	{#if promptIds.length > 0}
		<div class="flex flex-col gap-1">
			{#each promptIds as id, idx (id)}
				{@const p = promptById.get(id)}
				<div
					class="flex items-center gap-2 rounded-lg border border-gray-100/40 dark:border-gray-850/50 px-2 py-1"
				>
					<span class="text-[0.6875rem] text-gray-400 dark:text-gray-600 shrink-0">
						{$i18n.t('Task {{number}}', { number: String(idx + 1).padStart(2, '0') })}
					</span>
					<div class="flex min-w-0 flex-1 items-baseline gap-1.5 text-[0.8125rem]">
						{#if p}
							<span class="truncate text-gray-700 dark:text-gray-200">{p.name}</span>
							<span class="truncate text-xs text-gray-400 dark:text-gray-500">{commandOf(p)}</span>
						{:else if loaded}
							<!-- Deleted, or not visible to you; users without access won't see it either. -->
							<span class="truncate text-xs text-gray-400 italic">
								{$i18n.t('Prompt not found or not accessible')}
							</span>
						{/if}
					</div>
					<div class="flex shrink-0 items-center">
						<button
							type="button"
							class="p-1 text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 disabled:opacity-30"
							aria-label={$i18n.t('Move up')}
							disabled={idx === 0}
							on:click={() => move(idx, -1)}
						>
							<ChevronUp className="size-3" />
						</button>
						<button
							type="button"
							class="p-1 text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 disabled:opacity-30"
							aria-label={$i18n.t('Move down')}
							disabled={idx === promptIds.length - 1}
							on:click={() => move(idx, 1)}
						>
							<ChevronDown className="size-3" />
						</button>
						<button
							type="button"
							class="p-1 text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
							aria-label={$i18n.t('Remove task')}
							on:click={() => remove(idx)}
						>
							<XMark className="size-3.5" />
						</button>
					</div>
				</div>
			{/each}
		</div>
	{/if}

	{#if promptIds.length < MAX_TASKS}
		<div class="rounded-lg border border-gray-100/40 dark:border-gray-850/50">
			<input
				class="w-full bg-transparent px-2 py-1.5 text-[0.8125rem] outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700"
				placeholder={$i18n.t('Search prompts to add…')}
				aria-label={$i18n.t('Search prompts to add')}
				bind:value={query}
			/>
			<div class="max-h-40 overflow-y-auto border-t border-gray-100/40 dark:border-gray-850/50">
				{#if !loaded}
					<div class="px-2 py-1.5 text-xs text-gray-400">{$i18n.t('Loading...')}</div>
				{:else if candidates.length === 0}
					<div class="px-2 py-1.5 text-xs text-gray-400">
						{prompts.length === 0
							? $i18n.t('The prompt library is empty.')
							: $i18n.t('No matching prompts')}
					</div>
				{:else}
					{#each candidates as p (p.id)}
						<button
							type="button"
							class="flex w-full items-baseline gap-1.5 px-2 py-1 text-left text-[0.8125rem] hover:bg-gray-50 dark:hover:bg-gray-850 transition"
							on:click={() => add(p.id)}
						>
							<span class="truncate text-gray-700 dark:text-gray-200">{p.name}</span>
							<span class="truncate text-xs text-gray-400 dark:text-gray-500">{commandOf(p)}</span>
						</button>
					{/each}
				{/if}
			</div>
		</div>
	{/if}
</div>
