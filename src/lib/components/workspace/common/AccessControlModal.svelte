<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import Modal from '$lib/components/common/Modal.svelte';
	import AccessControl from './AccessControl.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	type AccessGrant = {
		id?: string;
		principal_type: 'user' | 'group' | 'anyone';
		principal_id: string;
		permission: 'read' | 'write';
	};

	export let show = false;
	export let accessGrants: AccessGrant[] = [];
	export let accessControl: any = undefined;
	export let accessRoles = ['read'];

	export let share = true;
	export let sharePublic = true;
	export let shareOpen = false;
	export let shareUsers = true;

	// Optional: what is being shared, e.g. itemName="Transformer X specs",
	// subtitle="Knowledge base · 24 documents".
	export let itemName = '';
	export let subtitle = '';

	export let onChange = () => {};
</script>

<Modal size="sm" bind:show className="bg-white dark:bg-gray-900 rounded-2xl">
	<div class="px-5 pt-4 pb-4 text-gray-900 dark:text-gray-100">
		<div class="flex items-start justify-between gap-3">
			<div class="min-w-0">
				<h2 class="truncate text-base font-semibold">
					{itemName ? $i18n.t('Share "{{name}}"', { name: itemName }) : $i18n.t('Share')}
				</h2>
				{#if subtitle}
					<p class="mt-0.5 truncate text-xs text-gray-500">{subtitle}</p>
				{/if}
			</div>
			<button
				class="shrink-0 rounded-lg p-1 text-gray-500 transition hover:bg-gray-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200"
				type="button"
				aria-label={$i18n.t('Close')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark className="size-4" />
			</button>
		</div>

		<div class="mt-4">
			<AccessControl
				bind:accessGrants
				bind:accessControl
				{onChange}
				{accessRoles}
				{share}
				{sharePublic}
				{shareOpen}
				{shareUsers}
			/>
		</div>

		<div class="mt-4 flex items-center justify-between gap-3">
			<p class="text-xs text-gray-500">
				{$i18n.t('People find it under "Shared with me".')}
			</p>
			<button
				type="button"
				class="shrink-0 rounded-lg bg-black px-4 py-2 text-sm font-semibold text-white transition hover:bg-gray-800 dark:bg-white dark:text-black dark:hover:bg-gray-200"
				on:click={() => {
					show = false;
				}}
			>
				{$i18n.t('Done')}
			</button>
		</div>
	</div>
</Modal>
