<script lang="ts">
	import { getContext } from 'svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import TypeaheadSelector from './TypeaheadSelector.svelte';

	type Filter = {
		id: string;
		name?: string;
		is_global?: boolean;
		meta?: {
			description?: string;
		};
	};

	const i18n = getContext('i18n') as any;

	export let filters: Filter[] = [];
	export let selectedFilterIds: string[] = [];

	$: selectableFilters = filters.filter((filter) => !filter.is_global);
	$: selectedFilters = filters.filter(
		(filter) => filter.is_global || selectedFilterIds.includes(filter.id)
	);

	const toggleFilter = (filter: Filter) => {
		selectedFilterIds = selectedFilterIds.includes(filter.id)
			? selectedFilterIds.filter((id) => id !== filter.id)
			: [...selectedFilterIds, filter.id];
	};
</script>

{#if filters.length > 0}
	<div>
		<div class="mb-2 flex w-full items-start justify-between gap-3">
		<div class="min-w-0">
			<div class="text-sm font-semibold text-gray-900 dark:text-gray-100">{$i18n.t('Filters')}</div>
			<p class="text-xs text-gray-500">{$i18n.t('Run before or after each message, e.g. to remove personal data.')}</p>
		</div>

			{#if selectableFilters.length > 0}
				<TypeaheadSelector
					id="model-filters-selector"
					items={selectableFilters.map((filter) => ({
						...filter,
						description: filter.meta?.description
					}))}
					selectedIds={selectedFilterIds}
					placeholder={$i18n.t('Search filters')}
					triggerLabel={$i18n.t('Add filter')}
					emptyLabel={$i18n.t('No filters found')}
					variant="dropdown"
					on:select={(e) => {
						toggleFilter(e.detail);
					}}
					on:enableall={(e) => {
						selectedFilterIds = [
							...new Set([...selectedFilterIds, ...e.detail.map((filter) => filter.id)])
						];
					}}
				/>
			{/if}
		</div>

		<!-- TODO: Filter order matters -->
		<div class="flex flex-col">
			<div class="flex flex-wrap items-center gap-1.5">
				{#each selectedFilters as filter (filter.id)}
					<span class="inline-flex max-w-full items-center gap-1 rounded-full border border-gray-300 py-0.5 pr-1 pl-2.5 text-xs text-gray-800 dark:border-gray-700 dark:text-gray-200 {filter.is_global ? 'pr-2.5' : ''}" title={filter.meta?.description ?? filter.id}>
						<span class="truncate">{filter.name}</span>
						{#if filter.is_global}
							<span class="text-gray-500">· {$i18n.t('always on')}</span>
						{:else}
							<button
								type="button"
								class="rounded-full p-0.5 text-gray-400 hover:bg-gray-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200"
								aria-label={$i18n.t('Remove {{name}}', { name: filter.name })}
								on:click={() => {
									selectedFilterIds = selectedFilterIds.filter((id) => id !== filter.id);
								}}
							>
								<XMark className="size-3" />
							</button>
						{/if}
					</span>
				{/each}

				{#if selectedFilterIds.length > 0}
					<button
						type="button"
						class="text-xs text-gray-500 underline hover:text-gray-800 dark:hover:text-gray-200"
						on:click={() => {
							selectedFilterIds = [];
						}}
					>
						{$i18n.t('Remove all')}
					</button>
				{/if}
			</div>
		</div>

		
	</div>
{/if}
