<script lang="ts">
	export let label = '';
	export let description = '';
	export let forId = '';
	export let className = '';
</script>

<!-- CHOn: bold label above the control, explanation below. -->
<div class={className}>
	{#if label}
		<label class="text-sm font-semibold text-gray-900 dark:text-gray-100" for={forId || undefined}>
			{label}
		</label>
	{/if}

	<div class={label ? 'mt-1.5' : ''}>
		<slot />
	</div>

	{#if description}
		<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
			{description}
		</p>
	{/if}
</div>
