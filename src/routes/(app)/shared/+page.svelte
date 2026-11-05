<script lang="ts">
	import { onMount, getContext } from 'svelte';

	import { mobile, showSidebar, user } from '$lib/stores';
	import { getModelItems } from '$lib/apis/models';
	import { searchKnowledgeBases } from '$lib/apis/knowledge';
	import { getPromptItems } from '$lib/apis/prompts';
	import { getSkillItems } from '$lib/apis/skills';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';

	const i18n = getContext('i18n');

	type SharedItem = { id: string; name: string; description: string; owner: string; href: string | null };
	type Section = { key: string; title: string; items: SharedItem[] };

	let loaded = false;
	let sections: Section[] = [];

	const can = (perm: string) =>
		$user?.role === 'admin' || ($user?.permissions?.workspace?.[perm] ?? false);

	const ownerName = (item) => item?.user?.name ?? item?.user?.email ?? '';

	onMount(async () => {
		const token = localStorage.token;
		// view_option "shared" = items owned by someone else that this user has access to.
		const [models, knowledge, prompts, skills] = await Promise.all([
			getModelItems(token, null, 'shared', null, null, null, 1).catch(() => null),
			searchKnowledgeBases(token, null, 'shared', 1).catch(() => null),
			getPromptItems(token, null, 'shared', null, null, null, 1).catch(() => null),
			getSkillItems(token, null, 'shared', 1).catch(() => null)
		]);

		sections = [
			{
				key: 'models',
				title: $i18n.t('Models'),
				items: (models?.items ?? []).map((m) => ({
					id: m.id,
					name: m.name ?? m.id,
					description: m.meta?.description ?? '',
					owner: ownerName(m),
					// Any user can start a chat with a model they can access.
					href: `/?models=${encodeURIComponent(m.id)}`
				}))
			},
			{
				key: 'knowledge',
				title: $i18n.t('Knowledge'),
				items: (knowledge?.items ?? []).map((k) => ({
					id: k.id,
					name: k.name,
					description: k.description ?? '',
					owner: ownerName(k),
					href: can('knowledge') ? `/workspace/knowledge/${k.id}` : null
				}))
			},
			{
				key: 'prompts',
				title: $i18n.t('Prompts'),
				items: (prompts?.items ?? []).map((p) => ({
					id: p.id,
					name: p.name,
					description: p.command ? `/${p.command.replace(/^\//, '')}` : '',
					owner: ownerName(p),
					href: can('prompts') ? `/workspace/prompts/${p.id}` : null
				}))
			},
			{
				key: 'skills',
				title: $i18n.t('Skills'),
				items: (skills?.items ?? []).map((s) => ({
					id: s.id,
					name: s.name,
					description: s.description ?? '',
					owner: ownerName(s),
					href: can('skills') ? `/workspace/skills/edit?id=${encodeURIComponent(s.id)}` : null
				}))
			}
		];

		loaded = true;
	});

	$: total = sections.reduce((n, s) => n + s.items.length, 0);
</script>

<svelte:head>
	<title>{$i18n.t('Shared with me')}</title>
</svelte:head>

<div
	class="flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''} max-w-full"
>
	<nav class="pb-1 px-2.5 pt-2 select-none">
		<div class="flex items-center gap-1">
			{#if $mobile}
				<Tooltip content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}>
					<button
						class="flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition p-1.5"
						aria-label={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
						on:click={() => showSidebar.set(!$showSidebar)}
					>
						<Sidebar className="size-4" />
					</button>
				</Tooltip>
			{/if}
			<h1 class="px-1 text-sm text-gray-900 dark:text-gray-100">{$i18n.t('Shared with me')}</h1>
		</div>
	</nav>

	<div class="flex-1 max-h-full overflow-y-auto px-4 pb-8">
		{#if !loaded}
			<div class="w-full h-full flex justify-center items-center">
				<Spinner className="size-5" />
			</div>
		{:else if total === 0}
			<div class="mt-24 text-center text-sm text-gray-500 dark:text-gray-400">
				{$i18n.t('Nothing has been shared with you yet.')}
			</div>
		{:else}
			<div class="mx-auto max-w-4xl">
				{#each sections.filter((s) => s.items.length > 0) as section (section.key)}
					<section class="mt-5">
						<div class="mb-2 flex items-baseline gap-1.5">
							<h2 class="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
								{section.title}
							</h2>
							<span class="text-xs text-gray-400 dark:text-gray-600">{section.items.length}</span>
						</div>

						<div class="grid grid-cols-1 md:grid-cols-2 gap-2">
							{#each section.items as item (item.id)}
								<svelte:element
									this={item.href ? 'a' : 'div'}
									href={item.href}
									class="flex flex-col rounded-2xl border border-gray-100 dark:border-gray-850 px-4 py-3 {item.href
										? 'hover:bg-gray-50 dark:hover:bg-gray-850 transition'
										: ''}"
								>
									<div class="text-sm font-medium text-gray-900 dark:text-gray-100 line-clamp-1">
										{item.name}
									</div>
									{#if item.description}
										<div class="mt-0.5 text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
											{item.description}
										</div>
									{/if}
									{#if item.owner}
										<div class="mt-1.5 text-[0.6875rem] text-gray-400 dark:text-gray-500">
											{$i18n.t('Shared by {{name}}', { name: item.owner })}
										</div>
									{/if}
								</svelte:element>
							{/each}
						</div>
					</section>
				{/each}
			</div>
		{/if}
	</div>
</div>
