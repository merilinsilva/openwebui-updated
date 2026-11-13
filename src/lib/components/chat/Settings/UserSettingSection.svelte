<script lang="ts">
	export let title = '';
	export let first = false;
	export let className = '';
</script>

<!-- CHOn: a titled card, like the sections in the model editor. -->
<section class="w-full {first ? '' : 'mt-5'} {className}">
	{#if title}
		<h3 class="mb-1.5 text-[0.6875rem] font-semibold tracking-wide text-gray-500 uppercase dark:text-gray-400">
			{title}
		</h3>
	{/if}

	<div
		class="flex flex-col gap-3 rounded-xl border border-gray-200 px-4 py-3 dark:border-gray-800"
	>
		<slot />
	</div>
</section>
