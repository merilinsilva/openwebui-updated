<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';

	import Modal from '$lib/components/common/Modal.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let announcement: { title?: string | null; content: string } = { content: '' };

	// Modal also closes on Escape and on outside click, so acknowledge on any
	// close rather than only the button — otherwise those paths would leave it
	// undismissed and it would reappear on every page load.
	let wasShown = false;
	$: if (show) {
		wasShown = true;
	} else if (wasShown) {
		wasShown = false;
		dispatch('acknowledge');
	}
</script>

<Modal bind:show size="sm">
	<div class="px-5 py-4">
		{#if announcement?.title}
			<div class="text-lg font-medium mb-2">
				{announcement.title}
			</div>
		{/if}

		<div class="text-sm text-gray-700 dark:text-gray-200">
			{@html DOMPurify.sanitize(
				marked.parse((announcement?.content ?? '').replace(/\n/g, '<br>'))
			)}
		</div>

		<div class="flex justify-end mt-5">
			<button
				class="px-4 py-2 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:hover:bg-gray-100 dark:text-black rounded-full transition"
				type="button"
				on:click={() => {
					show = false;
				}}
			>
				{$i18n.t('Got it')}
			</button>
		</div>
	</div>
</Modal>
