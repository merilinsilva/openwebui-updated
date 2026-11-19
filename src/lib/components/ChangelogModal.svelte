<script lang="ts">
	import DOMPurify from 'dompurify';

	import { getContext } from 'svelte';

	import { WEBUI_NAME, config, settings } from '$lib/stores';

	import { WEBUI_VERSION } from '$lib/constants';
	import { getChangelog } from '$lib/apis';

	import Modal from './common/Modal.svelte';
	import { updateUserSettings } from '$lib/apis/users';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	export let show = false;

	type ChangelogEntry = {
		raw?: string;
	};
	type ChangelogVersion = {
		date: string;
		[section: string]: string | ChangelogEntry[];
	};

	let changelog: Record<string, ChangelogVersion> | null = null;
	let error = false;

	const init = async () => {
		if (changelog || error) {
			return;
		}

		changelog = await getChangelog().catch(() => {
			error = true;
			return null;
		});
	};

	const closeModal = async () => {
		localStorage.version = $config.version;
		await settings.set({ ...$settings, ...{ version: $config.version } });
		await updateUserSettings(localStorage.token, { ui: $settings });
		show = false;
	};

	$: if (show) {
		init();
	}

	const formatDate = (date: string) => {
		if (!date) {
			return '';
		}

		const [year, month, day] = date.split('-');
		const months = [
			'Jan',
			'Feb',
			'Mar',
			'Apr',
			'May',
			'Jun',
			'Jul',
			'Aug',
			'Sep',
			'Oct',
			'Nov',
			'Dec'
		];
		const monthIndex = Number(month) - 1;

		return year && monthIndex >= 0 && monthIndex < months.length && day
			? `${months[monthIndex]} ${Number(day)}, ${year}`
			: date;
	};

	const getSectionEntries = (version: string, section: string) => {
		const entries = changelog?.[version]?.[section];
		return Array.isArray(entries) ? entries : [];
	};

	// Section labels stay neutral like the other dialogs; a small dot carries the type colour.
	const sectionDotClass = (section: string) =>
		section === 'added'
			? 'bg-blue-500'
			: section === 'fixed'
				? 'bg-green-500'
				: section === 'changed'
					? 'bg-amber-500'
					: section === 'removed'
						? 'bg-red-500'
						: 'bg-gray-400';
</script>

<Modal bind:show size="lg" className="bg-white dark:bg-gray-900 rounded-2xl overflow-hidden">
	<div class="flex max-h-[80dvh] flex-col text-gray-900 dark:text-gray-100">
		<div class="flex shrink-0 items-start justify-between gap-3 px-5 pt-4 pb-3">
			<div class="min-w-0">
				<!-- LICENSE covers this Open WebUI release identifier.
				Do not alter, remove, obscure, or replace it except as LICENSE permits:
				https://docs.openwebui.com/license. -->
				<h2 class="truncate text-base font-semibold">
					{$i18n.t("What's New in")}
					{$WEBUI_NAME}
				</h2>
				<p class="mt-0.5 text-xs text-gray-500">
					{$i18n.t('Release Notes')} · v{WEBUI_VERSION}
				</p>
			</div>

			<button
				class="shrink-0 rounded-lg p-1 text-gray-500 transition hover:bg-gray-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200"
				type="button"
				on:click={closeModal}
				aria-label={$i18n.t('Close')}
			>
				<XMark className="size-4" />
			</button>
		</div>

		<div
			class="min-h-0 flex-1 overflow-y-auto border-t border-gray-200 px-5 scrollbar-hidden dark:border-gray-800"
		>
			{#if changelog}
				<div class="divide-y divide-gray-200 dark:divide-gray-800">
					{#each Object.keys(changelog) as version}
						<section class="py-4">
							<div class="mb-3 flex items-baseline gap-2">
								<h3 class="text-sm font-semibold">v{version}</h3>
								{#if version === WEBUI_VERSION}
									<span
										class="rounded-md border border-gray-300 px-1.5 py-px text-[0.6875rem] font-medium text-gray-600 dark:border-gray-700 dark:text-gray-300"
									>
										{$i18n.t('Current')}
									</span>
								{/if}
								<span class="ml-auto shrink-0 text-xs text-gray-500">
									{formatDate(changelog[version].date)}
								</span>
							</div>

							{#each Object.keys(changelog[version]).filter((section) => section !== 'date') as section}
								<div class="mb-4 last:mb-0">
									<div
										class="mb-1.5 flex items-center gap-1.5 text-[0.6875rem] font-semibold tracking-wide uppercase text-gray-500 dark:text-gray-400"
									>
										<span
											class="size-1.5 rounded-full {sectionDotClass(section)}"
											aria-hidden="true"
										></span>
										{section}
									</div>

									<ul class="space-y-2 text-sm leading-relaxed">
										{#each getSectionEntries(version, section) as entry}
											<li
												class="markdown-prose-sm !max-w-none !text-sm text-gray-600 dark:text-gray-400 [&_*]:!my-0 [&_a]:text-gray-700 dark:[&_a]:text-gray-300 [&_a:hover]:text-gray-900 dark:[&_a:hover]:text-gray-100 [&_b]:font-semibold [&_b]:text-gray-900 dark:[&_b]:text-gray-100 [&_strong]:font-semibold [&_strong]:text-gray-900 dark:[&_strong]:text-gray-100"
											>
												<!-- eslint-disable-next-line svelte/no-at-html-tags -->
												{@html DOMPurify.sanitize(entry?.raw)}
											</li>
										{/each}
									</ul>
								</div>
							{/each}
						</section>
					{/each}
				</div>
			{:else if error}
				<div class="flex flex-col items-center justify-center gap-3 py-16 text-center">
					<p class="text-sm text-gray-600 dark:text-gray-400">
						{$i18n.t('Could not load release notes.')}
					</p>
					<button
						type="button"
						on:click={() => {
							error = false;
							init();
						}}
						class="rounded-lg border border-gray-300 px-3.5 py-2 text-sm font-medium transition hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800"
					>
						{$i18n.t('Retry')}
					</button>
				</div>
			{:else}
				<div class="flex flex-col items-center justify-center gap-2 py-16 text-sm text-gray-500">
					<Spinner className="size-5" />
					{$i18n.t('Loading release notes...')}
				</div>
			{/if}
		</div>

		<div class="flex shrink-0 justify-end border-t border-gray-200 px-5 py-3 dark:border-gray-800">
			<button
				type="button"
				on:click={closeModal}
				class="rounded-lg bg-black px-4 py-2 text-sm font-semibold text-white transition hover:bg-gray-800 dark:bg-white dark:text-black dark:hover:bg-gray-200"
			>
				{$i18n.t("Okay, Let's Go!")}
			</button>
		</div>
	</div>
</Modal>
