<script lang="ts">
	import { getContext } from 'svelte';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';

	import { models } from '$lib/stores';
	import { sanitizeResponseContent } from '$lib/utils';

	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	// Red "Model Information" badge: hover shows the model's "Model Information" text
	// (meta.news, set in Workspace > Models). Hidden when the model has none.
	export let modelId = '';
	export let compact = false;

	$: text = (($models ?? []).find((m) => m.id === modelId)?.info?.meta?.news ?? '').trim();
</script>

{#if text}
	<!-- Long text would overflow the viewport: cap the height and scroll;
	     interactive so the pointer can move in to scroll. -->
	<Tooltip
		content={`<div class="max-h-[60vh] overflow-y-auto pr-1">${DOMPurify.sanitize(
			marked.parse(sanitizeResponseContent(text).replaceAll('\n', '<br>'))
		)}</div>`}
		placement="bottom-end"
		theme="news"
		interactive
		tippyOptions={{ appendTo: () => document.body, maxWidth: 420 }}
		className="flex shrink-0"
	>
		<div
			class="flex items-center gap-1.5 rounded-full bg-red-600 hover:bg-red-700 {compact
				? 'p-1.5'
				: 'px-3 py-1'} text-xs font-medium text-white shadow-sm cursor-default select-none transition no-drag-region"
			role="note"
			aria-label={$i18n.t('Model Information')}
		>
			<svg
				class="size-4 shrink-0"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="1.8"
				stroke-linecap="round"
				stroke-linejoin="round"
				aria-hidden="true"
			>
				<path d="M3 11v2a1 1 0 0 0 1 1h2l5 4V6L6 10H4a1 1 0 0 0-1 1Z" />
				<path d="M15.5 8.5a5 5 0 0 1 0 7" />
				<path d="M18.5 5.5a9 9 0 0 1 0 13" />
			</svg>
			{#if !compact}
				<span class="whitespace-nowrap">{$i18n.t('Model Information')}</span>
			{/if}
		</div>
	</Tooltip>
{/if}
