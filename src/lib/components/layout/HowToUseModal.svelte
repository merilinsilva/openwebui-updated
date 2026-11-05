<script lang="ts">
	import DOMPurify from 'dompurify';
	import { getContext } from 'svelte';

	import { howToUseContent, showHowToUse } from '$lib/stores';

	import Modal from '$lib/components/common/Modal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');

	// Admin-written HTML: sanitize before rendering (DOMPurify keeps data: image URIs).
	$: safeContent = DOMPurify.sanitize($howToUseContent?.content ?? '');
	$: title = ($howToUseContent?.title ?? '').trim() || $i18n.t('How to use CHOn');
</script>

<Modal
	bind:show={$showHowToUse}
	size="xl"
	className="bg-white dark:bg-gray-900 rounded-3xl overflow-hidden"
	containerClassName="p-3"
>
	<div class="flex max-h-[85vh] flex-col">
		<div
			class="flex shrink-0 items-center justify-between gap-4 px-5 pb-2 pt-4 dark:text-white text-black"
		>
			<h2 class="m-0 truncate text-lg font-medium">{title}</h2>

			<button
				class="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl text-gray-400 transition hover:bg-gray-100 hover:text-gray-700 dark:text-gray-500 dark:hover:bg-white/10 dark:hover:text-gray-200"
				on:click={() => showHowToUse.set(false)}
				aria-label={$i18n.t('Close')}
			>
				<XMark className="size-4" />
			</button>
		</div>

		<div class="min-h-0 flex-1 overflow-y-auto px-5 pb-5 pt-1">
			<div class="markdown-prose prose-img:rounded-xl prose-img:max-w-full">
				{@html safeContent}
			</div>
		</div>
	</div>
</Modal>
