<script lang="ts">
	// CHOn (T17): specific error card with Retry and Report
	// (WG-AI-PLA-00002, section 8 / PP-05; error red #B3261E, always icon + text label).
	import { getContext, tick } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Info from '$lib/components/icons/Info.svelte';
	import ExclamationTriangle from '$lib/components/icons/ExclamationTriangle.svelte';
	import { explainChatError, type ChatErrorInput } from '$lib/utils/chatErrors';
	import { copyToClipboard } from '$lib/utils';

	const i18n = getContext('i18n');

	/** Full error object ({ content, status?, code?, finish_reason? }). */
	export let error: ChatErrorInput | null = null;
	/** Legacy: raw error content only. */
	export let content: unknown = '';
	/** The user stopped the answer (neutral notice instead of an error). */
	export let stopped = false;

	export let canRetry = true;
	export let onRetry: (() => void) | null = null;
	/** Returns true when the report was saved. */
	export let onReport:
		| ((details: { kind: string; title: string; details: string; comment?: string }) => Promise<boolean>)
		| null = null;

	let showDetails = false;
	let reporting = false;
	let reported = false;
	// Report asks "what happened?" first; the text goes to the feedback's Comment.
	let showReportForm = false;
	let reportComment = '';
	let reportInput: HTMLTextAreaElement;

	$: input = error ?? (content ? { content } : null);
	$: explained = explainChatError((key, opts) => $i18n.t(key, opts), input, { stopped });
	$: retryVisible = !!onRetry && canRetry && explained.canRetry;
	$: reportVisible = !!onReport && !explained.neutral;

	const openReportForm = async () => {
		if (reported) return;
		showReportForm = true;
		await tick();
		reportInput?.focus();
	};

	const report = async () => {
		if (!onReport || reporting || reported) return;
		reporting = true;
		const ok = await onReport({
			kind: explained.kind,
			title: explained.title,
			details: explained.details,
			comment: reportComment.trim()
		}).catch(() => false);
		reporting = false;
		if (ok) {
			reported = true;
			showReportForm = false;
			toast.success($i18n.t('Thanks. The CHOn team has received your report.'));
		}
	};
</script>

<div
	role={explained.neutral ? 'status' : 'alert'}
	class="my-1.5 w-full rounded-2xl border px-3.5 py-3 text-[0.8125rem] leading-5 {explained.neutral
		? 'border-gray-200 bg-gray-50 text-gray-600 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-400'
		: 'chon-error-card'}"
>
	<div class="flex items-start gap-2.5">
		{#if explained.neutral}
			<Info className="mt-0.5 size-4 shrink-0" strokeWidth="1.8" />
		{:else}
			<span class="chon-error-icon mt-0.5 shrink-0" aria-hidden="true">
				<ExclamationTriangle className="size-4" strokeWidth="2" />
			</span>
		{/if}

		<div class="min-w-0 flex-1">
			{#if !explained.neutral}
				<div class="chon-error-label text-[0.6875rem] font-semibold uppercase tracking-wide">
					{$i18n.t('Error')}
				</div>
			{/if}
			<div class="font-semibold text-gray-900 dark:text-gray-100 break-words">
				{explained.title}
			</div>
			<div class="mt-0.5 text-gray-700 dark:text-gray-300 break-words">
				{explained.nextStep}
			</div>

			{#if retryVisible || reportVisible || explained.details}
				<div class="mt-2.5 flex flex-wrap items-center gap-2">
					{#if retryVisible}
						<button
							type="button"
							class="rounded-lg bg-black px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100"
							on:click={() => onRetry?.()}
						>
							{$i18n.t('Retry')}
						</button>
					{/if}

					{#if reportVisible}
						<button
							type="button"
							class="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-800 transition hover:bg-gray-100 disabled:opacity-60 dark:border-gray-700 dark:text-gray-200 dark:hover:bg-gray-850"
							disabled={reporting || reported || showReportForm}
							on:click={openReportForm}
						>
							{reported ? $i18n.t('Reported') : $i18n.t('Report')}
						</button>
					{/if}

					{#if explained.details}
						<button
							type="button"
							class="ml-auto text-xs text-gray-500 underline underline-offset-2 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200"
							aria-expanded={showDetails}
							on:click={() => (showDetails = !showDetails)}
						>
							{showDetails ? $i18n.t('Hide technical details') : $i18n.t('Technical details')}
						</button>
					{/if}
				</div>
			{/if}

			{#if showReportForm && !reported}
				<!-- CHOn (T17): the user describes what happened (saved as the report's comment) -->
				<form class="mt-2.5" on:submit|preventDefault={report}>
					<label class="mb-1 block text-xs font-medium text-gray-800 dark:text-gray-200" for="report-{explained.kind}">
						{$i18n.t('What happened? (optional)')}
					</label>
					<textarea
						id="report-{explained.kind}"
						bind:this={reportInput}
						bind:value={reportComment}
						rows="3"
						maxlength="2000"
						class="w-full resize-y rounded-lg border border-gray-300 bg-white px-2.5 py-1.5 text-xs text-gray-900 outline-hidden focus:border-gray-500 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
						placeholder={$i18n.t('E.g. what you asked for, which file or connector you used, what you expected.')}
						on:keydown={(e) => {
							if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) report();
							if (e.key === 'Escape') showReportForm = false;
						}}
					></textarea>
					<div class="mt-1.5 flex items-center gap-2">
						<button
							type="submit"
							class="rounded-lg bg-black px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-gray-900 disabled:opacity-60 dark:bg-white dark:text-black dark:hover:bg-gray-100"
							disabled={reporting}
						>
							{$i18n.t('Send report')}
						</button>
						<button
							type="button"
							class="rounded-lg px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-850"
							on:click={() => (showReportForm = false)}
						>
							{$i18n.t('Cancel')}
						</button>
						<span class="ml-auto text-[0.6875rem] text-gray-500">
							{$i18n.t('The technical details are attached automatically.')}
						</span>
					</div>
				</form>
			{/if}

			{#if showDetails && explained.details}
				<div class="mt-2 rounded-lg bg-black/[0.04] p-2 dark:bg-white/[0.05]">
					<pre
						class="max-h-48 overflow-auto whitespace-pre-wrap break-words font-mono text-[0.6875rem] leading-4 text-gray-700 dark:text-gray-300">{explained.details}</pre>
					<button
						type="button"
						class="mt-1 text-[0.6875rem] text-gray-500 underline underline-offset-2 hover:text-gray-800 dark:hover:text-gray-200"
						on:click={async () => {
							if (await copyToClipboard(explained.details)) {
								toast.success($i18n.t('Copied to clipboard'));
							}
						}}
					>
						{$i18n.t('Copy details')}
					</button>
				</div>
			{/if}
		</div>
	</div>
</div>

<style>
	/* CHOn error token (WG-AI-PLA-00002 4.4): Error Red #B3261E, ~6.5:1 on white. */
	.chon-error-card {
		border-color: rgb(179 38 30 / 0.35);
		background-color: rgb(179 38 30 / 0.05);
		border-left: 3px solid #b3261e;
	}
	.chon-error-icon,
	.chon-error-label {
		color: #b3261e;
	}
	:global(.dark) .chon-error-card {
		border-color: rgb(242 184 181 / 0.25);
		background-color: rgb(242 184 181 / 0.06);
		border-left-color: #f2b8b5;
	}
	:global(.dark) .chon-error-icon,
	:global(.dark) .chon-error-label {
		color: #f2b8b5;
	}
</style>
