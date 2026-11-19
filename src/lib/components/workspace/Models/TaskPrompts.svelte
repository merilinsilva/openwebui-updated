<script lang="ts">
	import { onMount, getContext } from 'svelte';

	import { getPrompts } from '$lib/apis/prompts';
	import LibraryPicker from './LibraryPicker.svelte';

	const i18n = getContext('i18n');

	// Up to 4 prompt-library IDs shown as task cards on the new-chat screen, in order.
	export let promptIds: string[] = [];

	let items = [];
	let loaded = false;

	onMount(async () => {
		const prompts = (await getPrompts(localStorage.token).catch(() => null)) ?? [];
		items = prompts.map((p) => ({
			id: p.id,
			name: p.name,
			detail: `/${(p.command ?? '').replace(/^\//, '')}`
		}));
		loaded = true;
	});
</script>

<LibraryPicker
	bind:ids={promptIds}
	{items}
	{loaded}
	max={4}
	rowLabel={(idx) => $i18n.t('Task {{number}}', { number: String(idx + 1).padStart(2, '0') })}
	description={$i18n.t(
		'Pick up to 4 prompts from the prompt library to show as task cards on the new chat screen. With none picked, the 4 most recently updated prompts are shown.'
	)}
	searchPlaceholder={$i18n.t('Search prompts to add…')}
	emptyLibraryText={$i18n.t('The prompt library is empty.')}
	notFoundText={$i18n.t('Prompt not found or not accessible')}
/>
