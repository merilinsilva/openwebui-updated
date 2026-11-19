<script lang="ts" context="module">
	export type UploadState = 'queued' | 'uploading' | 'reading' | 'ready' | 'failed';
	export type UploadEntry = {
		itemId: string;
		name: string;
		size: number;
		state: UploadState;
		progress?: number; // upload percent while state === 'uploading'
		error?: string; // raw error from the browser or the server
		fileId?: string | null;
		file?: File; // kept so a failed upload can be retried
	};
</script>

<script lang="ts">
	import { getContext } from 'svelte';
	import { config } from '$lib/stores';
	import { describeUploadError, uploadStateBadge } from '$lib/utils/uploadStatus';

	const i18n = getContext('i18n');

	export let uploads: UploadEntry[] = [];
	export let onRetry: (entry: UploadEntry) => void = () => {};
	export let onDismiss: (entry: UploadEntry) => void = () => {};
	export let onClearFinished: () => void = () => {};

	$: finishedCount = uploads.filter((u) => u.state === 'ready' || u.state === 'failed').length;

	// Shared with chat uploads so both explain failures the same way.
	const describeError = (raw = '') =>
		describeUploadError((k, o) => $i18n.t(k, o), raw, {
			maxSizeMb: $config?.file?.max_size ?? null,
			context: 'knowledge'
		});

	const badge = (u: UploadEntry) => uploadStateBadge((k, o) => $i18n.t(k, o), u.state, u.progress ?? null);
</script>

{#if uploads.length > 0}
	<div class="text-gray-900 dark:text-gray-100" aria-live="polite">
		<div class="flex items-center justify-between">
			<div class="text-[0.6875rem] font-semibold tracking-wide text-gray-500 uppercase">
				{$i18n.t('Uploads')}
			</div>
			{#if finishedCount > 0}
				<button
					type="button"
					class="text-xs text-gray-500 hover:text-gray-800 hover:underline dark:hover:text-gray-200"
					on:click={onClearFinished}
				>
					{$i18n.t('Clear finished')}
				</button>
			{/if}
		</div>

		<ul class="mt-1.5 flex flex-col gap-2">
			{#each uploads as u (u.itemId)}
				{@const b = badge(u)}
				<li class="text-sm">
					<div class="flex items-center gap-2">
						<span class="min-w-0 flex-1 truncate font-medium" title={u.name}>{u.name}</span>
						<span class="shrink-0 rounded-full px-2 py-0.5 text-[0.6875rem] {b.cls}">{b.label}</span>
					</div>

					{#if u.state === 'uploading'}
						<div class="mt-1 h-1 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-800">
							<div
								class="h-full rounded-full bg-gray-700 transition-[width] dark:bg-gray-300"
								style="width: {u.progress ?? 0}%"
							></div>
						</div>
					{:else if u.state === 'reading'}
						<!-- The server doesn't report reading progress, so show activity rather than a fake %. -->
						<div class="mt-1 h-1 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-800">
							<div class="upload-indeterminate h-full w-1/3 rounded-full bg-gray-700 dark:bg-gray-300"></div>
						</div>
					{:else if u.state === 'failed'}
						{@const d = describeError(u.error)}
						<div class="mt-0.5 text-xs text-red-700 dark:text-red-400">
							{d.cause}
							<span class="text-gray-600 dark:text-gray-400">{d.fix}</span>
						</div>
						<div class="mt-1 flex gap-3 text-xs">
							{#if u.file}
								<button
									type="button"
									class="font-medium underline hover:text-gray-600 dark:hover:text-gray-300"
									on:click={() => onRetry(u)}
								>
									{$i18n.t('Retry')}
								</button>
							{/if}
							<button
								type="button"
								class="text-gray-500 underline hover:text-gray-800 dark:hover:text-gray-200"
								on:click={() => onDismiss(u)}
							>
								{$i18n.t('Dismiss')}
							</button>
						</div>
					{/if}
				</li>
			{/each}
		</ul>
	</div>
{/if}

<style>
	.upload-indeterminate {
		animation: upload-slide 1.2s ease-in-out infinite;
	}
	@keyframes upload-slide {
		from {
			transform: translateX(-100%);
		}
		to {
			transform: translateX(300%);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.upload-indeterminate {
			animation: none;
			width: 100%;
			opacity: 0.4;
		}
	}
</style>
