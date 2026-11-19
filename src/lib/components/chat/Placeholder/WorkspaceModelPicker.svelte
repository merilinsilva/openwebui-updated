<script lang="ts">
	import { getContext } from 'svelte';
	import { slide } from 'svelte/transition';

	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { modelDescription } from '$lib/utils/modelNames';

	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';

	const i18n = getContext('i18n');

	// Header of the new-chat screen: the current model, which expands into boxes of the
	// workspace models (icon, name, description) in the order set in Workspace > Models.
	export let models = [];
	export let current = null;
	export let onSelect: (modelId: string) => void = () => {};

	let open = false;

	const imageUrl = (id: string) =>
		`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${encodeURIComponent(id)}&lang=${$i18n.language}`;

	const fallbackImage = (e) => {
		// LICENSE covers this Open WebUI fallback logo.
		// Do not alter, remove, obscure, or replace it except as LICENSE permits:
		// https://docs.openwebui.com/license.
		e.currentTarget.src = '/favicon.png';
	};
</script>

<div class="flex w-full flex-col items-center px-5">
	<button
		type="button"
		class="flex flex-col items-center rounded-3xl border border-gray-200 dark:border-gray-800 px-6 pt-2.5 pb-3 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
		aria-expanded={open}
		aria-controls="workspace-model-picker"
		on:click={() => (open = !open)}
	>
		<span
			class="flex items-center gap-1.5 text-xs font-medium tracking-wide uppercase text-gray-500 dark:text-gray-400"
		>
			{$i18n.t('Weidmann Models')}
			<ChevronDown className="size-3.5 transition {open ? 'rotate-180' : ''}" strokeWidth="2" />
		</span>
		<span class="mt-1.5 flex items-center gap-2.5">
			{#if current}
				<img
					src={imageUrl(current.id)}
					class="size-9 @sm:size-10 rounded-2xl"
					alt=""
					draggable="false"
					on:error={fallbackImage}
				/>
			{/if}
			<span class="text-2xl text-gray-800 dark:text-gray-100 line-clamp-1">
				{current?.name ?? $i18n.t('Select a model')}
			</span>
		</span>
	</button>

	{#if open}
		<div
			id="workspace-model-picker"
			class="mt-3 grid w-full max-w-3xl grid-cols-1 @md:grid-cols-2 gap-2 text-left"
			transition:slide={{ duration: 150 }}
		>
			{#each models as model (model.id)}
				{@const selected = model.id === current?.id}
				<button
					type="button"
					class="flex items-start gap-3 rounded-2xl border px-4 py-3 transition {selected
						? 'border-gray-900 dark:border-gray-100 bg-gray-50 dark:bg-gray-850'
						: 'border-gray-100 dark:border-gray-850 hover:bg-gray-50 dark:hover:bg-gray-850'}"
					aria-pressed={selected}
					on:click={() => {
						onSelect(model.id);
						open = false;
					}}
				>
					<img
						src={imageUrl(model.id)}
						class="size-9 shrink-0 rounded-xl"
						alt=""
						draggable="false"
						on:error={fallbackImage}
					/>
					<span class="min-w-0 flex-1">
						<span class="block text-sm font-semibold text-gray-900 dark:text-gray-100 line-clamp-1">
							{model.name}
						</span>
						{#if modelDescription(model)}
							<span class="mt-0.5 block text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
								{modelDescription(model)}
							</span>
						{/if}
					</span>
				</button>
			{/each}
		</div>
	{/if}
</div>
