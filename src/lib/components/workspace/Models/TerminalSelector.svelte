<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { getTerminalServers, type TerminalServer } from '$lib/apis/terminal';

	const i18n = getContext('i18n');

	export let terminalId: string = '';

	let terminals: TerminalServer[] = [];

	onMount(async () => {
		terminals = await getTerminalServers(localStorage.token);
	});
</script>

{#if terminals.length > 0}
	<div class="mb-1.5">
		<label for="model-terminal" class="text-sm font-semibold text-gray-900 dark:text-gray-100">
			{$i18n.t('Terminal server')}
		</label>
		<p class="text-xs text-gray-500">{$i18n.t('Where the model runs commands when Terminal is on.')}</p>
	</div>

	<select
		id="model-terminal"
		class="w-full cursor-pointer rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm outline-hidden focus:border-gray-500 dark:border-gray-700 dark:bg-gray-900 dark:scheme-dark"
		bind:value={terminalId}
	>
		<option value="">{$i18n.t('None')}</option>
		{#each terminals as terminal (terminal.id)}
			<option value={terminal.id}>{terminal.name || terminal.id}</option>
		{/each}
	</select>
{/if}
