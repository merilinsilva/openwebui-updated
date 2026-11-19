<script lang="ts">
	import { getContext } from 'svelte';

	import XMark from '$lib/components/icons/XMark.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';

	const i18n = getContext('i18n');

	// Ordered pick of up to `max` items from a library (prompts, skills, ...), stored as IDs.
	export let ids: string[] = [];
	export let items: { id: string; name: string; detail?: string }[] = [];
	export let loaded = false;
	export let max = 4;
	export let rowLabel: (idx: number) => string = (idx) => `${idx + 1}`;
	export let description = '';
	export let searchPlaceholder = '';
	export let emptyLibraryText = '';
	export let notFoundText = '';

	$: if (!Array.isArray(ids)) ids = [];

	let query = '';

	$: itemById = new Map(items.map((item) => [item.id, item]));

	$: candidates = items
		.filter((item) => !ids.includes(item.id))
		.filter((item) => {
			const q = query.trim().toLowerCase();
			return !q || `${item.name} ${item.detail ?? ''}`.toLowerCase().includes(q);
		})
		.sort((a, b) => a.name.localeCompare(b.name));

	const add = (id: string) => {
		if (ids.length >= max) return;
		ids = [...ids, id];
		query = '';
	};

	const remove = (idx: number) => {
		ids = ids.filter((_, i) => i !== idx);
	};

	const move = (idx: number, delta: number) => {
		const next = [...ids];
		const target = idx + delta;
		if (target < 0 || target >= next.length) return;
		[next[idx], next[target]] = [next[target], next[idx]];
		ids = next;
	};
</script>

<div class="space-y-2">
	{#if description}
		<div class="text-xs text-gray-500 dark:text-gray-400">{description}</div>
	{/if}

	{#if ids.length > 0}
		<div class="flex flex-col gap-1">
			{#each ids as id, idx (id)}
				{@const item = itemById.get(id)}
				<div
					class="flex items-center gap-2 rounded-lg border border-gray-100/40 dark:border-gray-850/50 px-2 py-1"
				>
					<span class="text-[0.6875rem] text-gray-400 dark:text-gray-600 shrink-0">
						{rowLabel(idx)}
					</span>
					<div class="flex min-w-0 flex-1 items-baseline gap-1.5 text-[0.8125rem]">
						{#if item}
							<span class="truncate text-gray-700 dark:text-gray-200">{item.name}</span>
							{#if item.detail}
								<span class="truncate text-xs text-gray-400 dark:text-gray-500">{item.detail}</span>
							{/if}
						{:else if loaded}
							<!-- Deleted, or not visible to you; users without access won't see it either. -->
							<span class="truncate text-xs text-gray-400 italic">{notFoundText}</span>
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
							disabled={idx === ids.length - 1}
							on:click={() => move(idx, 1)}
						>
							<ChevronDown className="size-3" />
						</button>
						<button
							type="button"
							class="p-1 text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
							aria-label={$i18n.t('Remove')}
							on:click={() => remove(idx)}
						>
							<XMark className="size-3.5" />
						</button>
					</div>
				</div>
			{/each}
		</div>
	{/if}

	{#if ids.length < max}
		<div class="rounded-lg border border-gray-100/40 dark:border-gray-850/50">
			<input
				class="w-full bg-transparent px-2 py-1.5 text-[0.8125rem] outline-hidden placeholder:text-gray-300 dark:placeholder:text-gray-700"
				placeholder={searchPlaceholder}
				aria-label={searchPlaceholder}
				bind:value={query}
			/>
			<div class="max-h-40 overflow-y-auto border-t border-gray-100/40 dark:border-gray-850/50">
				{#if !loaded}
					<div class="px-2 py-1.5 text-xs text-gray-400">{$i18n.t('Loading...')}</div>
				{:else if candidates.length === 0}
					<div class="px-2 py-1.5 text-xs text-gray-400">
						{items.length === 0 ? emptyLibraryText : $i18n.t('No matches')}
					</div>
				{:else}
					{#each candidates as item (item.id)}
						<button
							type="button"
							class="flex w-full items-baseline gap-1.5 px-2 py-1 text-left text-[0.8125rem] hover:bg-gray-50 dark:hover:bg-gray-850 transition"
							on:click={() => add(item.id)}
						>
							<span class="truncate text-gray-700 dark:text-gray-200">{item.name}</span>
							{#if item.detail}
								<span class="truncate text-xs text-gray-400 dark:text-gray-500">{item.detail}</span>
							{/if}
						</button>
					{/each}
				{/if}
			</div>
		</div>
	{/if}
</div>
