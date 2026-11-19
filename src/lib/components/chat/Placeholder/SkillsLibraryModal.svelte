<script lang="ts">
	import { getContext, tick } from 'svelte';

	import { user } from '$lib/stores';

	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');

	// All skills the user can use, as boxes with title and short description.
	export let show = false;
	export let skills = [];
	export let onSelect: (skill) => void = () => {};

	let query = '';
	let searchInput: HTMLInputElement;

	$: canManageSkills =
		$user?.role === 'admin' || ($user?.permissions?.workspace?.skills ?? false);

	$: filtered = skills
		.filter((s) => {
			const q = query.trim().toLowerCase();
			return !q || `${s.name} ${s.description ?? ''}`.toLowerCase().includes(q);
		})
		.sort((a, b) => a.name.localeCompare(b.name));

	$: if (show) {
		query = '';
		tick().then(() => searchInput?.focus());
	}
</script>

<Modal bind:show size="xl" className="bg-white dark:bg-gray-900 rounded-3xl overflow-hidden">
	<div class="flex max-h-[80vh] flex-col">
		<div class="flex shrink-0 items-center justify-between gap-4 px-5 pt-4 pb-2">
			<h2 class="m-0 text-lg font-medium text-gray-900 dark:text-white">{$i18n.t('Skills')}</h2>
			<button
				class="flex size-8 items-center justify-center rounded-xl text-gray-400 transition hover:bg-gray-100 hover:text-gray-700 dark:text-gray-500 dark:hover:bg-white/10 dark:hover:text-gray-200"
				on:click={() => (show = false)}
				aria-label={$i18n.t('Close')}
			>
				<XMark className="size-4" />
			</button>
		</div>

		<div class="px-5 pb-3">
			<input
				bind:this={searchInput}
				class="w-full rounded-xl bg-gray-50 dark:bg-gray-850 px-3 py-2 text-sm outline-hidden"
				placeholder={$i18n.t('Search skills')}
				aria-label={$i18n.t('Search skills')}
				bind:value={query}
			/>
		</div>

		<div class="min-h-0 flex-1 overflow-y-auto px-5 pb-5">
			{#if filtered.length === 0}
				<div class="py-10 text-center text-sm text-gray-500 dark:text-gray-400">
					{skills.length === 0 ? $i18n.t('No skills available.') : $i18n.t('No matches')}
				</div>
			{:else}
				<div class="grid grid-cols-1 md:grid-cols-2 gap-2">
					{#each filtered as skill (skill.id)}
						<button
							type="button"
							class="flex flex-col text-left rounded-2xl border border-gray-100 dark:border-gray-850 hover:bg-gray-50 dark:hover:bg-gray-850 px-4 py-3 transition"
							on:click={() => {
								onSelect(skill);
								show = false;
							}}
						>
							<div class="text-sm font-semibold text-gray-900 dark:text-gray-100 line-clamp-1">
								{skill.name}
							</div>
							<div class="mt-0.5 text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
								{skill.description || $i18n.t('No description')}
							</div>
						</button>
					{/each}
				</div>
			{/if}
		</div>

		{#if canManageSkills}
			<div class="shrink-0 border-t border-gray-100 dark:border-gray-850 px-5 py-2.5 text-right">
				<a
					href="/workspace/skills"
					class="text-xs underline underline-offset-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
				>
					{$i18n.t('Manage skills')} →
				</a>
			</div>
		{/if}
	</div>
</Modal>
