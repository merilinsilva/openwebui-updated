<script lang="ts">
	import { getContext, tick } from 'svelte';
	const i18n = getContext('i18n');

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import AddConnectionModal from '$lib/components/AddConnectionModal.svelte';

	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import Wrench from '$lib/components/icons/Wrench.svelte';
	import ManageOllamaModal from './ManageOllamaModal.svelte';
	import Download from '$lib/components/icons/Download.svelte';

	export let onDelete = () => {};
	export let onSubmit = () => {};

	export let url = '';
	export let idx = 0;
	export let config = {};

	let showManageModal = false;
	let showConfigModal = false;
</script>

<AddConnectionModal
	ollama
	edit
	bind:show={showConfigModal}
	connection={{
		url,
		key: config?.key ?? '',
		config: config
	}}
	onDelete={() => {
		onDelete();
		showConfigModal = false;
	}}
	onSubmit={(connection) => {
		url = connection.url;
		config = { ...connection.config, key: connection.key };
		onSubmit(connection);
	}}
/>

<ManageOllamaModal bind:show={showManageModal} urlIdx={idx} />

<div class="flex items-center gap-1.5">
	<Tooltip
		className="w-full relative"
		content={$i18n.t(`WebUI will make requests to "{{url}}/api/chat"`, {
			url
		})}
		placement="top-start"
	>
		{#if !(config?.enable ?? true)}
			<div
				class="absolute top-0 bottom-0 left-0 right-0 opacity-60 bg-white dark:bg-gray-900 z-10"
			></div>
		{/if}

		<input
			class="w-full truncate bg-transparent font-mono text-[0.8125rem] text-gray-900 outline-hidden dark:text-gray-100"
			placeholder={$i18n.t('Enter URL (e.g. http://localhost:11434)')}
			bind:value={url}
			readonly={true}
		/>
	</Tooltip>

	{#if !(config?.enable ?? true)}
		<span class="shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-[0.625rem] text-gray-600 dark:bg-gray-800 dark:text-gray-300">
			{$i18n.t('Off')}
		</span>
	{/if}

	<div class="flex gap-1 items-center">
		<Tooltip content={$i18n.t('Manage')} className="self-start">
			<button
				class="flex items-center gap-1 rounded-lg px-1.5 py-1 text-xs text-gray-500 transition hover:bg-gray-100 hover:text-gray-900 dark:hover:bg-gray-800 dark:hover:text-gray-100"
				on:click={() => {
					showManageModal = true;
				}}
				type="button"
				aria-label={$i18n.t('Manage models')}
			>
				<Download className="size-3.5" />
				{$i18n.t('Models')}
			</button>
		</Tooltip>

		<Tooltip content={$i18n.t('Configure')} className="self-start">
			<button
				class="flex items-center gap-1 rounded-lg px-1.5 py-1 text-xs text-gray-500 transition hover:bg-gray-100 hover:text-gray-900 dark:hover:bg-gray-800 dark:hover:text-gray-100"
				on:click={() => {
					showConfigModal = true;
				}}
				type="button"
			>
				<Cog6 />
			</button>
		</Tooltip>

		<Tooltip content={(config?.enable ?? true) ? $i18n.t('Enabled') : $i18n.t('Disabled')}>
			<Switch
				bind:state={config.enable}
				on:change={() => {
					config.enable = config.enable ?? false;
					onSubmit({ url, key: config?.key ?? '', config });
				}}
			/>
		</Tooltip>
	</div>
</div>
