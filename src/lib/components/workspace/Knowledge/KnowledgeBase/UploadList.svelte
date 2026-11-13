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

	const i18n = getContext('i18n');

	export let uploads: UploadEntry[] = [];
	export let onRetry: (entry: UploadEntry) => void = () => {};
	export let onDismiss: (entry: UploadEntry) => void = () => {};
	export let onClearFinished: () => void = () => {};

	$: finishedCount = uploads.filter((u) => u.state === 'ready' || u.state === 'failed').length;

	// Turns the server's technical error into "what happened" and "what to do".
	const describeError = (raw = ''): { cause: string; fix: string } => {
		const e = raw.toLowerCase();
		if (e.includes('content provided is empty') || e.includes('no text')) {
			return {
				cause: $i18n.t('No text found. This looks like a scanned image.'),
				fix: $i18n.t('Upload a searchable PDF (export it again, or run OCR on it first).')
			};
		}
		if (e.includes('embedding model') || e.includes('embedding_engine')) {
			return {
				cause: $i18n.t("CHOn can't index documents right now: no embedding model is set up."),
				fix: $i18n.t(
					'This is a server setting, not a problem with your file. Contact the CHOn team (Admin Settings > Documents).'
				)
			};
		}
		if (e.includes('duplicate content')) {
			return {
				cause: $i18n.t('This file is already in the knowledge base.'),
				fix: $i18n.t('Nothing to do. Remove the old copy first if you want to replace it.')
			};
		}
		if (e.includes('not supported')) {
			return {
				cause: $i18n.t("CHOn can't read this file type."),
				fix: $i18n.t('Save it as PDF, Word, PowerPoint, Excel or text and upload it again.')
			};
		}
		if (e.includes('empty file')) {
			return {
				cause: $i18n.t('The file is empty.'),
				fix: $i18n.t('Check that you picked the right file.')
			};
		}
		if (e.includes('size') || e.includes('too large') || e.includes('413')) {
			return {
				cause: $i18n.t('The file is too large.'),
				fix: $config?.file?.max_size
					? $i18n.t('Split or compress it to under {{size}} MB.', { size: $config.file.max_size })
					: $i18n.t('Split or compress it, then upload the parts.')
			};
		}
		if (e.includes('timeout') || e.includes('timed out')) {
			return {
				cause: $i18n.t('Reading the file took too long.'),
				fix: $i18n.t('Try again, or split it into smaller files.')
			};
		}
		if (e.includes('network')) {
			return {
				cause: $i18n.t('The upload was interrupted.'),
				fix: $i18n.t('Check your connection and try again.')
			};
		}
		if (e.includes('permission') || e.includes('access')) {
			return {
				cause: $i18n.t("You don't have permission to add files here."),
				fix: $i18n.t('Ask the owner of this knowledge base for edit access.')
			};
		}
		return {
			cause: raw ? raw : $i18n.t('The file could not be read.'),
			fix: $i18n.t('Try again. If it keeps failing, contact the CHOn team.')
		};
	};

	const badge = (u: UploadEntry) =>
		({
			queued: {
				label: $i18n.t('Queued'),
				cls: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300'
			},
			uploading: {
				label: `${$i18n.t('Uploading')} ${u.progress ?? 0}%`,
				cls: 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300'
			},
			reading: {
				label: $i18n.t('Reading'),
				cls: 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300'
			},
			ready: {
				label: `✓ ${$i18n.t('Ready')}`,
				cls: 'bg-green-50 text-green-700 dark:bg-green-950/40 dark:text-green-300'
			},
			failed: {
				label: `✕ ${$i18n.t('Failed')}`,
				cls: 'bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300'
			}
		})[u.state];
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
