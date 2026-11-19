<script lang="ts">
	import { onMount, getContext } from 'svelte';

	import { getSkills } from '$lib/apis/skills';
	import LibraryPicker from './LibraryPicker.svelte';

	const i18n = getContext('i18n');

	// Skills shown as chips on the new-chat screen before "View all", in order.
	export let skillIds: string[] = [];
	const MAX_QUICK_SKILLS = 6;

	let items = [];
	let loaded = false;

	onMount(async () => {
		const skills = (await getSkills(localStorage.token).catch(() => null)) ?? [];
		items = skills
			.filter((s) => s?.is_active !== false)
			.map((s) => ({ id: s.id, name: s.name, detail: s.description ?? '' }));
		loaded = true;
	});
</script>

<LibraryPicker
	bind:ids={skillIds}
	{items}
	{loaded}
	max={MAX_QUICK_SKILLS}
	rowLabel={(idx) => `${idx + 1}`}
	description={$i18n.t(
		'Pick up to 6 skills to show on the new chat screen before "View all". With none picked, the 6 most recently updated skills are shown.'
	)}
	searchPlaceholder={$i18n.t('Search skills to add…')}
	emptyLibraryText={$i18n.t('No skills available.')}
	notFoundText={$i18n.t('Skill not found or not accessible')}
/>
