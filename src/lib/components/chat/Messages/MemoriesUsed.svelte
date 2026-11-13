<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { getMemories } from '$lib/apis/memories';
	import { showMemoryPanel } from '$lib/stores';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	// Ids recorded by the server for this answer. The text is looked up from the user's own
	// memories (only the owner can read them), so shared chats never expose it.
	export let memoryIds: string[] = [];

	let loading = true;
	let contents: (string | null)[] = [];

	onMount(async () => {
		const all = (await getMemories(localStorage.token).catch(() => null)) ?? [];
		const byId = new Map<string, string>(all.map((m: any) => [m.id, m.content]));
		contents = memoryIds.map((id) => byId.get(id) ?? null);
		loading = false;
	});

	$: deletedCount = contents.filter((c) => c === null).length;
</script>

<div
	class="my-2 w-full max-w-xl rounded-lg border border-gray-200 px-3 py-2 text-xs dark:border-gray-800"
	dir="auto"
>
	<div class="text-[0.6875rem] font-semibold tracking-wide text-gray-500 uppercase">
		{$i18n.t('Memories used in this reply')}
	</div>

	{#if loading}
		<div class="py-2"><Spinner className="size-3.5" /></div>
	{:else}
		<ul class="mt-1 list-disc space-y-0.5 pl-4 text-gray-700 dark:text-gray-300">
			{#each contents.filter((c) => c !== null) as content}
				<li class="whitespace-pre-line">{content}</li>
			{/each}
		</ul>
		{#if deletedCount > 0}
			<p class="mt-1 text-gray-500">
				{deletedCount === 1
					? $i18n.t("+ 1 memory you've since deleted")
					: $i18n.t("+ {{count}} memories you've since deleted", { count: deletedCount })}
			</p>
		{/if}
		<button
			type="button"
			class="mt-1.5 text-gray-500 underline hover:text-gray-800 dark:hover:text-gray-200"
			on:click={() => showMemoryPanel.set(true)}
		>
			{$i18n.t('Manage my memory')}
		</button>
	{/if}
</div>
