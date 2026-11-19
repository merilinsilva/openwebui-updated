<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import { config, models as _models, settings } from '$lib/stores';
	import { getModels } from '$lib/apis';
	import { getModelsConfig, setModelsConfig } from '$lib/apis/configs';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';

	const i18n = getContext('i18n');

	// Order of the workspace models in the new-chat model picker. Saved into the global
	// model order (Admin Settings > Models), so the model selector follows it too.
	export let show = false;

	let order = [];
	let saving = false;

	const workspaceModels = () =>
		($_models ?? []).filter((m) => m?.info?.base_model_id && !(m?.info?.meta?.hidden ?? false));

	$: if (show) order = workspaceModels(); // $models is already in the saved order

	const move = (idx: number, delta: number) => {
		const target = idx + delta;
		if (target < 0 || target >= order.length) return;
		const next = [...order];
		[next[idx], next[target]] = [next[target], next[idx]];
		order = next;
	};

	const save = async () => {
		saving = true;
		try {
			const current = await getModelsConfig(localStorage.token);
			const ids = order.map((m) => m.id);
			// Workspace models first in the chosen order, then everything else as it was.
			const rest = (current?.MODEL_ORDER_LIST ?? []).filter((id) => !ids.includes(id));
			await setModelsConfig(localStorage.token, { ...current, MODEL_ORDER_LIST: [...ids, ...rest] });

			_models.set(
				await getModels(
					localStorage.token,
					$config?.features?.enable_direct_connections && ($settings?.directConnections ?? null)
				)
			);
			toast.success($i18n.t('Model order saved'));
			show = false;
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			saving = false;
		}
	};
</script>

<Modal bind:show size="md" className="bg-white dark:bg-gray-900 rounded-3xl overflow-hidden">
	<div class="flex max-h-[80vh] flex-col">
		<div class="flex shrink-0 items-center justify-between gap-4 px-5 pt-4 pb-1">
			<h2 class="m-0 text-lg font-medium text-gray-900 dark:text-white">
				{$i18n.t('Order on new chat')}
			</h2>
			<button
				class="flex size-8 items-center justify-center rounded-xl text-gray-400 transition hover:bg-gray-100 hover:text-gray-700 dark:text-gray-500 dark:hover:bg-white/10 dark:hover:text-gray-200"
				on:click={() => (show = false)}
				aria-label={$i18n.t('Close')}
			>
				<XMark className="size-4" />
			</button>
		</div>
		<p class="px-5 pb-3 text-xs text-gray-500 dark:text-gray-400">
			{$i18n.t(
				'The order in which workspace models appear in the model picker on the new chat screen and in the model selector.'
			)}
		</p>

		<div class="min-h-0 flex-1 overflow-y-auto px-5">
			{#if order.length === 0}
				<div class="py-8 text-center text-sm text-gray-500">{$i18n.t('No workspace models yet.')}</div>
			{:else}
				<ol class="flex flex-col gap-1">
					{#each order as model, idx (model.id)}
						<li
							class="flex items-center gap-2.5 rounded-xl border border-gray-100 dark:border-gray-850 px-3 py-2"
						>
							<span class="w-5 shrink-0 text-xs text-gray-400">{idx + 1}</span>
							<img
								src={`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${encodeURIComponent(model.id)}`}
								class="size-7 shrink-0 rounded-lg"
								alt=""
								on:error={(e) => {
									// LICENSE covers this Open WebUI fallback logo.
									// Do not alter, remove, obscure, or replace it except as LICENSE permits:
									// https://docs.openwebui.com/license.
									e.currentTarget.src = '/favicon.png';
								}}
							/>
							<span class="min-w-0 flex-1 truncate text-sm text-gray-900 dark:text-gray-100">
								{model.name}
							</span>
							<button
								type="button"
								class="p-1 text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 disabled:opacity-30"
								aria-label={$i18n.t('Move up')}
								disabled={idx === 0}
								on:click={() => move(idx, -1)}
							>
								<ChevronUp className="size-3.5" />
							</button>
							<button
								type="button"
								class="p-1 text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 disabled:opacity-30"
								aria-label={$i18n.t('Move down')}
								disabled={idx === order.length - 1}
								on:click={() => move(idx, 1)}
							>
								<ChevronDown className="size-3.5" />
							</button>
						</li>
					{/each}
				</ol>
			{/if}
		</div>

		<div class="flex shrink-0 justify-end px-5 py-4">
			<button
				class="flex items-center gap-2 rounded-full bg-black px-3.5 py-1.5 text-sm font-medium text-white transition hover:bg-gray-900 disabled:opacity-60 dark:bg-white dark:text-black dark:hover:bg-gray-100"
				type="button"
				disabled={saving || order.length === 0}
				on:click={save}
			>
				{$i18n.t('Save')}
				{#if saving}
					<Spinner className="size-4" />
				{/if}
			</button>
		</div>
	</div>
</Modal>
