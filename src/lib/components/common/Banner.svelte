<script lang="ts">
	import type { Banner } from '$lib/types';
	import { onMount, createEventDispatcher, getContext } from 'svelte';
	import { fade } from 'svelte/transition';
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import InfoCircle from '$lib/components/icons/InfoCircle.svelte';
	import CheckCircle from '$lib/components/icons/CheckCircle.svelte';
	import ExclamationTriangle from '$lib/components/icons/ExclamationTriangle.svelte';
	import XCircle from '$lib/components/icons/XCircle.svelte';

	const dispatch = createEventDispatcher();
	const i18n = getContext<Writable<i18nType>>('i18n');

	export let banner: Banner = {
		id: '',
		type: 'info',
		title: '',
		content: '',
		url: '',
		dismissible: true,
		timestamp: Math.floor(Date.now() / 1000)
	};
	export let className = 'mx-2';

	export let dismissed = false;

	let mounted = false;

	// Container (background + border) and icon colours per banner type
	const styles: Record<string, { container: string; icon: string }> = {
		info: {
			container: 'bg-blue-50/90 border-blue-200 dark:bg-blue-950/70 dark:border-blue-800/60',
			icon: 'text-blue-600 dark:text-blue-300'
		},
		success: {
			container: 'bg-green-50/90 border-green-200 dark:bg-green-950/70 dark:border-green-800/60',
			icon: 'text-green-600 dark:text-green-300'
		},
		warning: {
			container:
				'bg-yellow-50/90 border-yellow-200 dark:bg-yellow-950/70 dark:border-yellow-800/60',
			icon: 'text-yellow-600 dark:text-yellow-300'
		},
		error: {
			container: 'bg-red-50/90 border-red-200 dark:bg-red-950/70 dark:border-red-800/60',
			icon: 'text-red-600 dark:text-red-300'
		}
	};

	const icons: Record<string, typeof InfoCircle> = {
		info: InfoCircle,
		success: CheckCircle,
		warning: ExclamationTriangle,
		error: XCircle
	};

	$: bannerType = (banner?.type ?? 'info').toLowerCase();
	$: style = styles[bannerType] ?? styles.info;
	$: icon = icons[bannerType] ?? InfoCircle;
	$: typeLabel =
		bannerType === 'info'
			? $i18n.t('Info')
			: bannerType === 'warning'
				? $i18n.t('Warning')
				: bannerType === 'error'
					? $i18n.t('Error')
					: bannerType === 'success'
						? $i18n.t('Success')
						: banner.type;

	const dismiss = (id: string) => {
		dismissed = true;
		dispatch('dismiss', id);
	};

	onMount(() => {
		mounted = true;

		console.log('Banner mounted:', banner);
	});
</script>

{#if !dismissed}
	{#if mounted}
		<div
			class="{className} {style.container} relative z-30 flex items-start gap-2 rounded-md border px-3 py-2 text-gray-800 backdrop-blur-xl dark:text-gray-100"
			role={bannerType === 'error' || bannerType === 'warning' ? 'alert' : 'status'}
			transition:fade={{ delay: 100, duration: 300 }}
		>
			<div class="flex shrink-0 pt-px {style.icon}" title={typeLabel}>
				<svelte:component this={icon} className="size-4" strokeWidth="2" />
				<span class="sr-only">{typeLabel}</span>
			</div>

			<div class="flex min-w-0 flex-1 flex-col gap-1 md:flex-row md:items-center">
				<div class="max-h-60 flex-1 overflow-y-auto text-xs text-gray-700 dark:text-white">
					{@html DOMPurify.sanitize(marked.parse((banner?.content ?? '').replace(/\n/g, '<br>')))}
				</div>

				{#if banner.url}
					<div class="group flex w-fit items-center">
						<a
							class="text-xs font-normal text-gray-700 underline dark:text-white"
							href={banner.url}
							target="_blank"
							rel="noopener noreferrer"
						>
							{$i18n.t('Learn More')}
						</a>

						<div class="ml-1 text-gray-400 group-hover:text-gray-600 dark:group-hover:text-white">
							<svg
								aria-hidden="true"
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 16 16"
								fill="currentColor"
								class="size-4"
							>
								<path
									fill-rule="evenodd"
									d="M4.22 11.78a.75.75 0 0 1 0-1.06L9.44 5.5H5.75a.75.75 0 0 1 0-1.5h5.5a.75.75 0 0 1 .75.75v5.5a.75.75 0 0 1-1.5 0V6.56l-5.22 5.22a.75.75 0 0 1-1.06 0Z"
									clip-rule="evenodd"
								/>
							</svg>
						</div>
					</div>
				{/if}
			</div>

			<button
				aria-label={$i18n.t('Close Banner')}
				on:click={() => {
					dismiss(banner.id);
				}}
				class="-mt-0.5 shrink-0 leading-none text-gray-400 hover:text-gray-700 dark:hover:text-white"
				>&times;</button
			>
		</div>
	{/if}
{/if}
