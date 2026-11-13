<script lang="ts">
	import Switch from '$lib/components/common/Switch.svelte';

	// One setting: name and plain-language description on the left, switch on the right.
	// Anything in the default slot appears under the description (only while switched on).
	export let id: string;
	export let label: string;
	export let description = '';
	export let checked = false;
	export let onChange: (checked: boolean) => void = () => {};
	export let compact = false;
</script>

<div class="flex items-start justify-between gap-4 {compact ? 'py-2' : 'py-2.5'}">
	<div class="min-w-0">
		<label for={id} id="{id}-label" class="block cursor-pointer text-sm text-gray-900 dark:text-gray-100">
			{label}
		</label>
		{#if description}
			<p class="mt-0.5 text-xs text-gray-500">{description}</p>
		{/if}
		{#if checked}
			<slot />
		{/if}
	</div>
	<div class="shrink-0 pt-0.5">
		<Switch {id} ariaLabelledbyId="{id}-label" state={checked} on:change={(e) => onChange(e.detail)} />
	</div>
</div>
