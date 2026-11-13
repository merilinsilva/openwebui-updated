<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';

	import { goto } from '$app/navigation';
	import { mobile, showSidebar, user, chatInputInsert } from '$lib/stores';
	import { getModelItems } from '$lib/apis/models';
	import { searchKnowledgeBases } from '$lib/apis/knowledge';
	import { getPromptItems } from '$lib/apis/prompts';
	import { getSkillItems } from '$lib/apis/skills';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';

	dayjs.extend(relativeTime);

	const i18n = getContext('i18n');

	type Kind = 'knowledge' | 'prompt' | 'skill' | 'assistant';
	type SharedItem = {
		key: string;
		kind: Kind;
		id: string;
		name: string;
		description: string;
		owner: string;
		updatedAt: number;
		open: (() => void) | null;
	};

	let loaded = false;
	let items: SharedItem[] = [];
	let filter: Kind | '' = '';
	// Items not seen on an earlier visit get a "New" marker (remembered in this browser).
	let newKeys = new Set<string>();

	const can = (perm: string) =>
		$user?.role === 'admin' || ($user?.permissions?.workspace?.[perm] ?? false);

	const ownerName = (item) => item?.user?.name ?? item?.user?.email ?? '';

	const kindLabel = (kind: Kind) =>
		({
			knowledge: $i18n.t('Knowledge'),
			prompt: $i18n.t('Prompt'),
			skill: $i18n.t('Skill'),
			assistant: $i18n.t('Assistant')
		})[kind];

	const kindClass = (kind: Kind) =>
		({
			knowledge: 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300',
			prompt: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
			skill: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
			assistant: 'bg-amber-50 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300'
		})[kind];

	const useInChat = async (insert) => {
		chatInputInsert.set(insert);
		await goto('/');
	};

	const seenStorageKey = () => `chon.sharedWithMe.seen.${$user?.id ?? 'anon'}`;

	const markNew = (all: SharedItem[]) => {
		let seen: string[] | null = null;
		try {
			seen = JSON.parse(localStorage.getItem(seenStorageKey()) ?? 'null');
		} catch {
			seen = null;
		}
		// First visit: remember everything, mark nothing as new.
		newKeys = Array.isArray(seen)
			? new Set(all.map((i) => i.key).filter((k) => !seen.includes(k)))
			: new Set();
		try {
			localStorage.setItem(seenStorageKey(), JSON.stringify(all.map((i) => i.key)));
		} catch {
			// storage unavailable: just no "New" markers next time
		}
	};

	onMount(async () => {
		const token = localStorage.token;
		// view_option "shared" = items owned by someone else that this user has access to.
		const [models, knowledge, prompts, skills] = await Promise.all([
			getModelItems(token, null, 'shared', null, null, null, 1).catch(() => null),
			searchKnowledgeBases(token, null, 'shared', 1).catch(() => null),
			getPromptItems(token, null, 'shared', null, null, null, 1).catch(() => null),
			getSkillItems(token, null, 'shared', 1).catch(() => null)
		]);

		const all: SharedItem[] = [
			...(knowledge?.items ?? []).map((k) => ({
				key: `knowledge:${k.id}`,
				kind: 'knowledge' as Kind,
				id: k.id,
				name: k.name,
				description: k.description ?? '',
				owner: ownerName(k),
				updatedAt: k.updated_at ?? 0,
				open: can('knowledge') ? () => goto(`/workspace/knowledge/${k.id}`) : null
			})),
			...(prompts?.items ?? []).map((p) => ({
				key: `prompt:${p.id}`,
				kind: 'prompt' as Kind,
				id: p.id,
				name: p.name,
				description: p.command ? `/${p.command.replace(/^\//, '')}` : '',
				owner: ownerName(p),
				updatedAt: p.updated_at ?? p.created_at ?? 0,
				// Anyone can use a prompt shared with them: open it in a new chat.
				open: () => useInChat({ type: 'prompt', name: p.name, content: p.content ?? '' })
			})),
			...(skills?.items ?? []).map((s) => ({
				key: `skill:${s.id}`,
				kind: 'skill' as Kind,
				id: s.id,
				name: s.name,
				description: s.description ?? '',
				owner: ownerName(s),
				updatedAt: s.updated_at ?? 0,
				open: () => useInChat({ type: 'skill', id: s.id, name: s.name })
			})),
			...(models?.items ?? []).map((m) => ({
				key: `assistant:${m.id}`,
				kind: 'assistant' as Kind,
				id: m.id,
				name: m.name ?? m.id,
				description: m.meta?.description ?? '',
				owner: ownerName(m),
				updatedAt: m.updated_at ?? 0,
				// Any user can start a chat with a model they can access.
				open: () => goto(`/?models=${encodeURIComponent(m.id)}`)
			}))
		].sort((a, b) => b.updatedAt - a.updatedAt);

		markNew(all);
		items = all;
		loaded = true;
	});

	$: counts = items.reduce(
		(acc, i) => ({ ...acc, [i.kind]: (acc[i.kind] ?? 0) + 1 }),
		{} as Record<Kind, number>
	);
	$: chips = [
		{ value: '' as Kind | '', label: $i18n.t('All') },
		...(['knowledge', 'prompt', 'skill', 'assistant'] as Kind[])
			.filter((k) => counts[k])
			.map((k) => ({ value: k, label: `${kindLabel(k)} (${counts[k]})` }))
	];
	$: visible = filter ? items.filter((i) => i.kind === filter) : items;

	const chipClass = (active: boolean) =>
		`shrink-0 rounded-full border px-3 py-1 text-xs transition ${
			active
				? 'border-red-500 bg-red-50 text-red-700 dark:border-red-500 dark:bg-red-950/40 dark:text-red-300'
				: 'border-gray-200 text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-850'
		}`;
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
		</div>
	</nav>

	<div class="flex-1 max-h-full overflow-y-auto px-4 pb-8">
		<div class="mx-auto max-w-3xl pt-2 text-gray-900 dark:text-gray-100">
			<h1 class="text-lg font-semibold">{$i18n.t('Shared with me')}</h1>
			<p class="mt-0.5 text-sm text-gray-500">
				{$i18n.t('Knowledge, prompts, skills and assistants colleagues have shared with you. Newest first.')}
			</p>

			{#if !loaded}
				<div class="flex justify-center py-16"><Spinner className="size-5" /></div>
			{:else if items.length === 0}
				<div class="py-16 text-center">
					<div class="text-sm">{$i18n.t('Nothing has been shared with you yet.')}</div>
					<p class="mt-1 text-xs text-gray-500">
						{$i18n.t('When a colleague shares something with you or your team, it shows up here.')}
					</p>
				</div>
			{:else}
				{#if chips.length > 2}
					<div class="mt-4 flex flex-wrap gap-1.5">
						{#each chips as chip (chip.value)}
							<button
								type="button"
								class={chipClass(filter === chip.value)}
								aria-pressed={filter === chip.value}
								on:click={() => (filter = chip.value)}
							>
								{chip.label}
							</button>
						{/each}
					</div>
				{/if}

				<ul class="mt-4 flex flex-col gap-2.5">
					{#each visible as item (item.key)}
						<li>
							<svelte:element
								this={item.open ? 'button' : 'div'}
								type={item.open ? 'button' : undefined}
								class="flex w-full flex-col rounded-xl border border-gray-200 px-4 py-3 text-left dark:border-gray-800 {item.open
									? 'transition hover:border-gray-400 hover:bg-gray-50 focus-visible:border-gray-500 dark:hover:border-gray-600 dark:hover:bg-gray-850'
									: ''}"
								on:click={() => item.open?.()}
							>
								<div class="flex w-full items-center gap-2">
									<span class="shrink-0 rounded-full px-2 py-0.5 text-[0.6875rem] {kindClass(item.kind)}">
										{kindLabel(item.kind)}
									</span>
									{#if newKeys.has(item.key)}
										<span
											class="ml-auto shrink-0 rounded-full bg-red-50 px-2 py-0.5 text-[0.6875rem] font-medium text-red-700 dark:bg-red-950/40 dark:text-red-300"
										>
											{$i18n.t('New')}
										</span>
									{/if}
								</div>
								<div class="mt-1.5 truncate text-sm font-semibold">{item.name}</div>
								{#if item.description}
									<div class="mt-0.5 line-clamp-2 text-xs text-gray-600 dark:text-gray-400">
										{item.description}
									</div>
								{/if}
								<div class="mt-1 text-[0.6875rem] text-gray-500">
									{#if item.owner}
										{$i18n.t('from {{name}}', { name: item.owner })}
										·
									{/if}
									<span title={dayjs(item.updatedAt * 1000).format('LLLL')}>
										{$i18n.t('updated {{time}}', { time: dayjs(item.updatedAt * 1000).fromNow() })}
									</span>
								</div>
							</svelte:element>
						</li>
					{/each}
				</ul>
			{/if}
		</div>
	</div>
</div>
