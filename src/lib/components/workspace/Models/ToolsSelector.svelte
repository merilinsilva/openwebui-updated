<script lang="ts">
	import XMark from '$lib/components/icons/XMark.svelte';
	import TypeaheadSelector from './TypeaheadSelector.svelte';
	import { getContext } from 'svelte';

	type Tool = {
		id: string;
		name?: string;
		meta?: {
			description?: string;
		};
	};

	export let tools: Tool[] = [];
	export let selectedToolIds: string[] = [];

	const i18n = getContext('i18n') as any;

	$: selectedTools = tools.filter((tool) => selectedToolIds.includes(tool.id));

	const toggleTool = (tool: Tool) => {
		selectedToolIds = selectedToolIds.includes(tool.id)
			? selectedToolIds.filter((id) => id !== tool.id)
			: [...selectedToolIds, tool.id];
	};
</script>

<div>
	<div class="mb-2 flex w-full items-start justify-between gap-3">
		<div class="min-w-0">
			<div class="text-sm font-semibold text-gray-900 dark:text-gray-100">{$i18n.t('Tools')}</div>
			<p class="text-xs text-gray-500">{$i18n.t('Let the model call tools, e.g. to look something up in another system.')}</p>
		</div>

		{#if tools.length > 0}
			<TypeaheadSelector
				id="model-tools-selector"
				items={tools}
				selectedIds={selectedToolIds}
				placeholder={$i18n.t('Search tools')}
				triggerLabel={$i18n.t('Add tool')}
				emptyLabel={$i18n.t('No tools found')}
				variant="dropdown"
				on:select={(e) => {
					toggleTool(e.detail);
				}}
				on:enableall={(e) => {
					selectedToolIds = [...new Set([...selectedToolIds, ...e.detail.map((tool) => tool.id)])];
				}}
			/>
		{/if}
	</div>

	<div class="flex flex-col mb-1">
		{#if tools.length > 0}
			<div class="flex flex-wrap items-center gap-1.5">
				{#each selectedTools as tool (tool.id)}
					<span class="inline-flex max-w-full items-center gap-1 rounded-full border border-gray-300 py-0.5 pr-1 pl-2.5 text-xs text-gray-800 dark:border-gray-700 dark:text-gray-200" title={tool.meta?.description ?? tool.id}>
						<span class="truncate">{tool.name}</span>
						<button
							type="button"
							class="rounded-full p-0.5 text-gray-400 hover:bg-gray-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200"
							aria-label={$i18n.t('Remove {{name}}', { name: tool.name })}
							on:click={() => {
								selectedToolIds = selectedToolIds.filter((id) => id !== tool.id);
							}}
						>
							<XMark className="size-3" />
						</button>
					</span>
				{/each}

				{#if selectedTools.length > 0}
					<button
						type="button"
						class="text-xs text-gray-500 underline hover:text-gray-800 dark:hover:text-gray-200"
						on:click={() => {
							selectedToolIds = [];
						}}
					>
						{$i18n.t('Remove all')}
					</button>
				{/if}
			</div>
		{/if}
	</div>

	{#if tools.length === 0}
		<div class="text-xs text-gray-500">{$i18n.t('No tools available yet. Add them in Workspace > Tools first.')}</div>
	{/if}
</div>
