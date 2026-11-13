<script lang="ts">
	export let title = '';
	export let description = '';
	export let first = false;
	export let className = '';
</script>

<!-- CHOn: a titled card, same as the personal settings sections. -->
<section class="{first ? '' : 'mt-5'} {className}">
	{#if title}
		<h3 class="text-[0.6875rem] font-semibold tracking-wide text-gray-500 uppercase dark:text-gray-400">
			{title}
		</h3>
	{/if}
	{#if description}
		<p class="mt-0.5 text-xs text-gray-500 dark:text-gray-400">{description}</p>
	{/if}

	<div
		class="{title || description
			? 'mt-1.5'
			: ''} flex flex-col gap-3 rounded-xl border border-gray-200 px-4 py-3 dark:border-gray-800"
	>
		<slot />
	</div>
</section>
