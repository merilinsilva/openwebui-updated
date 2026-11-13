<script lang="ts">
	export let label = '';
	export let description = '';
	export let className = '';
	export let labelClassName = '';
</script>

<!-- CHOn: label and its explanation on the left, the control on the right. -->
<div class="flex items-center justify-between gap-4 {className}">
	<div class="min-w-0 {labelClassName}">
		<div class="text-sm text-gray-900 dark:text-gray-100">
			<slot name="label">{label}</slot>
		</div>
		{#if description}
			<p class="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
				{description}
			</p>
		{/if}
	</div>

	<div class="min-w-0 shrink-0">
		<slot />
	</div>
</div>
