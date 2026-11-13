<script lang="ts">
	import { getContext, tick } from 'svelte';
	const i18n = getContext('i18n');

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import Cog6 from '$lib/components/icons/Cog6.svelte';
	import AddConnectionModal from '$lib/components/AddConnectionModal.svelte';

	import { connect } from 'socket.io-client';

	export let onDelete = () => {};
	export let onSubmit = () => {};

	export let pipeline = false;

	export let url = '';
	export let key = '';
	export let config = {};

	let showConfigModal = false;
</script>

<AddConnectionModal
	edit
	bind:show={showConfigModal}
	connection={{
		url,
		key,
		config
	}}
	onDelete={() => {
		onDelete();
		showConfigModal = false;
	}}
	onSubmit={(connection) => {
		url = connection.url;
		key = connection.key;
		config = connection.config;
		onSubmit(connection);
	}}
/>

<div class="flex w-full gap-2 items-center">
	<Tooltip
		className="w-full relative"
		content={$i18n.t(`WebUI will make requests to "{{url}}/chat/completions"`, {
			url
		})}
		placement="top-start"
	>
		{#if !(config?.enable ?? true)}
			<div
				class="absolute top-0 bottom-0 left-0 right-0 opacity-60 bg-white dark:bg-gray-900 z-10"
			></div>
		{/if}
		<div class="flex w-full gap-2">
			<div class="flex-1 relative">
				<input
					class="w-full truncate bg-transparent font-mono text-[0.8125rem] text-gray-900 outline-hidden dark:text-gray-100 {pipeline ? 'pr-20' : ''}"
					placeholder={$i18n.t('API Base URL')}
					bind:value={url}
					autocomplete="off"
					readonly={true}
				/>

				{#if pipeline}
					<div class="absolute top-0 right-0 flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-[0.625rem] text-blue-700 dark:bg-blue-950/40 dark:text-blue-300">
						<Tooltip content="Pipelines">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 24 24"
								fill="currentColor"
								class="size-3"
							>
								<path
									d="M11.644 1.59a.75.75 0 0 1 .712 0l9.75 5.25a.75.75 0 0 1 0 1.32l-9.75 5.25a.75.75 0 0 1-.712 0l-9.75-5.25a.75.75 0 0 1 0-1.32l9.75-5.25Z"
								/>
								<path
									d="m3.265 10.602 7.668 4.129a2.25 2.25 0 0 0 2.134 0l7.668-4.13 1.37.739a.75.75 0 0 1 0 1.32l-9.75 5.25a.75.75 0 0 1-.71 0l-9.75-5.25a.75.75 0 0 1 0-1.32l1.37-.738Z"
								/>
								<path
									d="m10.933 19.231-7.668-4.13-1.37.739a.75.75 0 0 0 0 1.32l9.75 5.25c.221.12.489.12.71 0l9.75-5.25a.75.75 0 0 0 0-1.32l-1.37-.738-7.668 4.13a2.25 2.25 0 0 1-2.134-.001Z"
								/>
							</svg>
						</Tooltip>
						Pipelines
					</div>
				{/if}
			</div>
		</div>
	</Tooltip>

	{#if !(config?.enable ?? true)}
		<span class="shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-[0.625rem] text-gray-600 dark:bg-gray-800 dark:text-gray-300">
			{$i18n.t('Off')}
		</span>
	{/if}

	<div class="flex gap-1 items-center">
		<Tooltip content={$i18n.t('Configure')} className="self-start">
			<button
				class="flex items-center gap-1 rounded-lg px-1.5 py-1 text-xs text-gray-500 transition hover:bg-gray-100 hover:text-gray-900 dark:hover:bg-gray-800 dark:hover:text-gray-100"
				aria-label={$i18n.t('Configure')}
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
					onSubmit({ url, key, config });
				}}
			/>
		</Tooltip>
	</div>
</div>
