<script lang="ts">
	import { getContext } from 'svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import TypeaheadSelector from './TypeaheadSelector.svelte';

	type Action = {
		id: string;
		name?: string;
		is_global?: boolean;
		meta?: {
			description?: string;
		};
	};

	const i18n = getContext('i18n') as any;

	export let actions: Action[] = [];
	export let selectedActionIds: string[] = [];

	$: selectableActions = actions.filter((action) => !action.is_global);
	$: selectedActions = actions.filter(
		(action) => action.is_global || selectedActionIds.includes(action.id)
	);

	const toggleAction = (action: Action) => {
		selectedActionIds = selectedActionIds.includes(action.id)
			? selectedActionIds.filter((id) => id !== action.id)
			: [...selectedActionIds, action.id];
	};
</script>

{#if actions.length > 0}
	<div>
		<div class="mb-2 flex w-full items-start justify-between gap-3">
		<div class="min-w-0">
			<div class="text-sm font-semibold text-gray-900 dark:text-gray-100">{$i18n.t('Actions')}</div>
			<p class="text-xs text-gray-500">{$i18n.t('Buttons shown under each answer, e.g. "Send to Outlook".')}</p>
		</div>

			{#if selectableActions.length > 0}
				<TypeaheadSelector
					id="model-actions-selector"
					items={selectableActions.map((action) => ({
						...action,
						description: action.meta?.description
					}))}
					selectedIds={selectedActionIds}
					placeholder={$i18n.t('Search actions')}
					triggerLabel={$i18n.t('Add action')}
					emptyLabel={$i18n.t('No actions found')}
					variant="dropdown"
					on:select={(e) => {
						toggleAction(e.detail);
					}}
					on:enableall={(e) => {
						selectedActionIds = [
							...new Set([...selectedActionIds, ...e.detail.map((action) => action.id)])
						];
					}}
				/>
			{/if}
		</div>

		<div class="flex flex-col">
			<div class="flex flex-wrap items-center gap-1.5">
				{#each selectedActions as action (action.id)}
					<span class="inline-flex max-w-full items-center gap-1 rounded-full border border-gray-300 py-0.5 pr-1 pl-2.5 text-xs text-gray-800 dark:border-gray-700 dark:text-gray-200 {action.is_global ? 'pr-2.5' : ''}" title={action.meta?.description ?? action.id}>
						<span class="truncate">{action.name}</span>
						{#if action.is_global}
							<span class="text-gray-500">· {$i18n.t('always on')}</span>
						{:else}
							<button
								type="button"
								class="rounded-full p-0.5 text-gray-400 hover:bg-gray-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200"
								aria-label={$i18n.t('Remove {{name}}', { name: action.name })}
								on:click={() => {
									selectedActionIds = selectedActionIds.filter((id) => id !== action.id);
								}}
							>
								<XMark className="size-3" />
							</button>
						{/if}
					</span>
				{/each}

				{#if selectedActionIds.length > 0}
					<button
						type="button"
						class="text-xs text-gray-500 underline hover:text-gray-800 dark:hover:text-gray-200"
						on:click={() => {
							selectedActionIds = [];
						}}
					>
						{$i18n.t('Remove all')}
					</button>
				{/if}
			</div>
		</div>

		
	</div>
{/if}
