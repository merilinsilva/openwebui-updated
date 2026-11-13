<script lang="ts">
	import { getContext, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';

	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import {
		user,
		showPromptLibrary,
		chatInputInsert,
		mobile,
		showSidebar
	} from '$lib/stores';
	import { createNewPrompt, getPromptItems } from '$lib/apis/prompts';
	import { getSkills } from '$lib/apis/skills';
	import { getGroups } from '$lib/apis/groups';
	import { slugify, parseFrontmatter, formatSkillName } from '$lib/utils';
	import { getOwnership, ownershipToneClass, type Ownership } from '$lib/utils/ownership';

	import Modal from '$lib/components/common/Modal.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import PromptEditor from '$lib/components/workspace/Prompts/PromptEditor.svelte';

	dayjs.extend(relativeTime);

	const i18n = getContext('i18n');

	// The prompt list endpoint pages in 30s; stop after this many pages.
	const MAX_PROMPT_PAGES = 20;

	type LibraryItem = {
		key: string;
		type: 'prompt' | 'skill';
		raw: any;
		name: string;
		description: string;
		handle: string;
		tags: string[];
		mine: boolean;
		canEdit: boolean;
		ownership: Ownership;
		ownerNote: string;
		updatedAt: number;
	};

	let loading = false;
	let loadedOnce = false;
	let prompts: any[] = [];
	let skills: any[] = [];
	let groupNames: Record<string, string> = {};

	let query = '';
	let tab: 'all' | 'prompt' | 'skill' = 'all';
	let topic = ''; // '' = all topics, '__mine__' = only mine, otherwise a tag
	let showCreatePrompt = false;
	let skillFileInput: HTMLInputElement;

	$: canCreatePrompt =
		$user?.role === 'admin' || ($user?.permissions?.workspace?.prompts ?? false);
	$: canCreateSkill = $user?.role === 'admin' || ($user?.permissions?.workspace?.skills ?? false);

	const loadAllPrompts = async () => {
		const all = [];
		for (let p = 1; p <= MAX_PROMPT_PAGES; p++) {
			const res = await getPromptItems(localStorage.token, '', '', '', 'name', 'asc', p);
			all.push(...(res?.items ?? []));
			if (!res || all.length >= (res.total ?? 0) || (res.items ?? []).length === 0) break;
		}
		return all;
	};

	const load = async () => {
		loading = true;
		try {
			const [promptRes, skillRes, groupRes] = await Promise.all([
				loadAllPrompts().catch((error) => {
					toast.error(`${error}`);
					return [];
				}),
				getSkills(localStorage.token).catch(() => []),
				getGroups(localStorage.token).catch(() => [])
			]);
			prompts = (promptRes ?? []).filter((p) => p?.is_active !== false);
			skills = (skillRes ?? []).filter((s) => s?.is_active !== false);
			groupNames = Object.fromEntries((groupRes ?? []).map((g) => [g.id, g.name]));
			loadedOnce = true;
		} finally {
			loading = false;
		}
	};

	// Reload every time the dialog opens so new and shared items show up.
	$: if ($showPromptLibrary) {
		load();
	}

	$: if (!$showPromptLibrary) {
		query = '';
		showCreatePrompt = false;
	}

	const ownershipOf = (item: any): Ownership =>
		getOwnership(item, $user?.id, groupNames, (k, o) => $i18n.t(k, o));

	const ownerNoteOf = (item: any, ownership: Ownership) => {
		if (item?.user_id === $user?.id) {
			return ownership.tone === 'mine' ? $i18n.t('private') : $i18n.t('shared by you');
		}
		const owner = item?.user?.name ?? item?.user?.email;
		if (owner) return $i18n.t('shared by {{name}}', { name: owner });
		return $i18n.t('updated {{time}}', {
			time: dayjs((item?.updated_at ?? item?.created_at ?? 0) * 1000).fromNow()
		});
	};

	const oneLine = (text: string) => (text ?? '').replace(/\s+/g, ' ').trim();

	const toItem = (raw: any, type: 'prompt' | 'skill'): LibraryItem => {
		const ownership = ownershipOf(raw);
		const mine = raw?.user_id === $user?.id;
		return {
			key: `${type}:${raw.id}`,
			type,
			raw,
			name: raw.name ?? raw.command ?? raw.id,
			// Prompts have no description field: preview the prompt text instead.
			description: oneLine(type === 'prompt' ? raw.content : (raw.description ?? raw.content)),
			handle: type === 'prompt' ? `/${(raw.command ?? '').replace(/^\//, '')}` : raw.id,
			tags: (type === 'prompt' ? raw.tags : raw.meta?.tags) ?? [],
			mine,
			canEdit: $user?.role === 'admin' || mine || raw?.write_access === true,
			ownership,
			ownerNote: ownerNoteOf(raw, ownership),
			updatedAt: raw?.updated_at ?? raw?.created_at ?? 0
		};
	};

	$: allItems = [
		...prompts.map((p) => toItem(p, 'prompt')),
		...skills.map((s) => toItem(s, 'skill'))
	].sort((a, b) => a.name.localeCompare(b.name));

	$: promptCount = allItems.filter((i) => i.type === 'prompt').length;
	$: skillCount = allItems.filter((i) => i.type === 'skill').length;

	$: topics = [...new Set(allItems.flatMap((i) => i.tags).filter(Boolean))].sort((a, b) =>
		a.localeCompare(b)
	);

	$: if (topic && topic !== '__mine__' && !topics.includes(topic)) {
		topic = '';
	}

	$: visibleItems = allItems.filter((item) => {
		if (tab !== 'all' && item.type !== tab) return false;
		if (topic === '__mine__' && !item.mine) return false;
		if (topic && topic !== '__mine__' && !item.tags.includes(topic)) return false;

		const q = query.trim().toLowerCase();
		if (!q) return true;
		return [item.name, item.handle, item.description, ...item.tags]
			.join(' ')
			.toLowerCase()
			.includes(q);
	});

	const isChatRoute = (pathname: string) => pathname === '/' || pathname.startsWith('/c/');

	const useItem = async (item: LibraryItem) => {
		chatInputInsert.set(
			item.type === 'prompt'
				? { type: 'prompt', name: item.name, content: item.raw.content ?? '' }
				: { type: 'skill', id: item.raw.id, name: item.name }
		);
		showPromptLibrary.set(false);

		if (!isChatRoute($page.url.pathname)) {
			await goto('/');
		}
		if ($mobile) {
			showSidebar.set(false);
		}
	};

	const editItem = async (item: LibraryItem) => {
		showPromptLibrary.set(false);
		await goto(
			item.type === 'prompt'
				? `/workspace/prompts/${item.raw.id}`
				: `/workspace/skills/edit?id=${encodeURIComponent(item.raw.id)}`
		);
	};

	const createPromptHandler = async (prompt) => {
		const res = await createNewPrompt(localStorage.token, prompt).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (res) {
			toast.success($i18n.t('Prompt created successfully'));
			showCreatePrompt = false;
			tab = 'prompt';
			await load();
		}
	};

	// Same Markdown import as Workspace > Skills: open the file in the skill editor for review.
	const uploadSkillHandler = (event: Event) => {
		const input = event.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;

		const reader = new FileReader();
		reader.onload = async (e) => {
			const mdContent = e.target?.result;
			if (typeof mdContent !== 'string') return;

			const fm: any = parseFrontmatter(mdContent);
			const rawName = fm.name || file.name.replace(/\.md$/i, '');
			sessionStorage.skill = JSON.stringify({
				name: formatSkillName(rawName),
				id: slugify(rawName),
				description: fm.description || '',
				content: mdContent,
				is_active: true,
				access_grants: []
			});
			showPromptLibrary.set(false);
			await tick();
			goto('/workspace/skills/create');
		};
		reader.readAsText(file);
		input.value = '';
	};

	const toneClass = ownershipToneClass;

	const chipClass = (active: boolean) =>
		`shrink-0 rounded-full border px-3 py-1 text-xs transition ${
			active
				? 'border-red-500 bg-red-50 text-red-700 dark:border-red-500 dark:bg-red-950/40 dark:text-red-300'
				: 'border-gray-200 text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-850'
		}`;
</script>

<input
	bind:this={skillFileInput}
	type="file"
	accept=".md"
	hidden
	on:change={uploadSkillHandler}
/>

<Modal
	bind:show={$showPromptLibrary}
	size="md"
	className="bg-white dark:bg-gray-900 rounded-2xl"
>
	<div class="flex max-h-[calc(100dvh-3rem)] flex-col px-5 pt-4 pb-4 text-gray-900 dark:text-gray-100">
		<div class="flex items-center justify-between">
			<h2 class="text-base font-semibold">{$i18n.t('Prompts & skills')}</h2>
			<button
				class="rounded-lg p-1 text-gray-500 transition hover:bg-gray-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200"
				type="button"
				aria-label={$i18n.t('Close')}
				on:click={() => showPromptLibrary.set(false)}
			>
				<XMark className="size-4" />
			</button>
		</div>

		<label
			class="mt-3 flex items-center gap-2 rounded-lg border border-gray-300 px-3 py-2 focus-within:border-gray-500 dark:border-gray-700 dark:focus-within:border-gray-500"
		>
			<Search className="size-3.5 shrink-0 text-gray-500" />
			<input
				class="w-full bg-transparent text-sm outline-hidden placeholder:text-gray-400"
				bind:value={query}
				placeholder={$i18n.t('Search prompts and skills, e.g. "meeting minutes"')}
				aria-label={$i18n.t('Search prompts and skills')}
			/>
			{#if query}
				<button
					type="button"
					class="rounded-full p-0.5 text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
					aria-label={$i18n.t('Clear search')}
					on:click={() => (query = '')}
				>
					<XMark className="size-3" strokeWidth="2" />
				</button>
			{/if}
		</label>

		<div class="mt-3 flex w-fit rounded-lg border border-gray-200 p-0.5 text-xs dark:border-gray-700" role="tablist">
			{#each [{ id: 'all', label: $i18n.t('All') }, { id: 'prompt', label: `${$i18n.t('Prompts')} (${promptCount})` }, { id: 'skill', label: `${$i18n.t('Skills')} (${skillCount})` }] as t (t.id)}
				<button
					type="button"
					role="tab"
					aria-selected={tab === t.id}
					class="rounded-md px-3 py-1 transition {tab === t.id
						? 'bg-black text-white dark:bg-white dark:text-black'
						: 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800'}"
					on:click={() => (tab = t.id as typeof tab)}
				>
					{t.label}
				</button>
			{/each}
		</div>

		<div class="mt-2.5 flex flex-wrap gap-1.5">
			<button type="button" class={chipClass(topic === '')} on:click={() => (topic = '')}>
				{$i18n.t('All topics')}
			</button>
			{#each topics as t (t)}
				<button type="button" class={chipClass(topic === t)} on:click={() => (topic = t)}>
					{t}
				</button>
			{/each}
			<button
				type="button"
				class={chipClass(topic === '__mine__')}
				on:click={() => (topic = topic === '__mine__' ? '' : '__mine__')}
			>
				★ {$i18n.t('Mine')}
			</button>
		</div>

		<div class="mt-3 -mx-1 min-h-[8rem] flex-1 overflow-y-auto px-1">
			{#if loading && !loadedOnce}
				<div class="flex justify-center py-12"><Spinner className="size-5" /></div>
			{:else if visibleItems.length === 0}
				<div class="py-12 text-center">
					<div class="text-sm">
						{allItems.length === 0
							? $i18n.t('No prompts or skills yet')
							: $i18n.t('Nothing matches your search')}
					</div>
					<div class="mt-1 text-xs text-gray-500">
						{allItems.length === 0
							? $i18n.t('Create a prompt to reuse instructions you type often.')
							: $i18n.t('Try another word or topic.')}
					</div>
				</div>
			{:else}
				<ul class="flex flex-col gap-2">
					{#each visibleItems as item (item.key)}
						<li class="group relative">
							<button
								type="button"
								class="w-full rounded-xl border border-gray-200 px-3 py-2.5 text-left transition hover:border-gray-400 hover:bg-gray-50 focus-visible:border-gray-500 dark:border-gray-800 dark:hover:border-gray-600 dark:hover:bg-gray-850"
								on:click={() => useItem(item)}
							>
								<div class="flex items-center gap-2 {item.canEdit ? 'pr-7' : ''}">
									<span
										class="shrink-0 rounded border px-1.5 text-[0.6875rem] leading-4 {item.type ===
										'skill'
											? 'border-gray-800 font-semibold text-gray-900 dark:border-gray-300 dark:text-gray-100'
											: 'border-gray-300 text-gray-600 dark:border-gray-600 dark:text-gray-400'}"
									>
										{item.type === 'skill' ? $i18n.t('Skill') : $i18n.t('Prompt')}
									</span>
									<span class="min-w-0 flex-1 truncate text-sm font-semibold">{item.name}</span>
									<span
										class="max-w-[40%] shrink-0 truncate rounded-full px-2 py-0.5 text-[0.6875rem] {toneClass(
											item.ownership.tone
										)}"
									>
										{item.ownership.label}
									</span>
								</div>
								{#if item.description}
									<div class="mt-1 line-clamp-2 text-xs text-gray-600 dark:text-gray-400">
										{item.description}
									</div>
								{/if}
								<div class="mt-1 truncate text-[0.6875rem] text-gray-500">
									{item.handle} · {item.ownerNote}
								</div>
							</button>

							{#if item.canEdit}
								<button
									type="button"
									class="absolute top-2 right-2 rounded-lg p-1 text-gray-400 opacity-0 transition group-hover:opacity-100 focus-visible:opacity-100 hover:bg-gray-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200"
									aria-label={$i18n.t('Edit {{name}}', { name: item.name })}
									title={$i18n.t('Edit')}
									on:click|stopPropagation={() => editItem(item)}
								>
									<Pencil className="size-3.5" />
								</button>
							{/if}
						</li>
					{/each}
				</ul>
			{/if}
		</div>

		<div class="mt-3 flex flex-wrap items-center gap-2">
			{#if canCreatePrompt}
				<button
					type="button"
					class="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium transition hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800"
					on:click={() => (showCreatePrompt = true)}
				>
					+ {$i18n.t('New prompt')}
				</button>
			{/if}
			{#if canCreateSkill}
				<button
					type="button"
					class="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium transition hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800"
					title={$i18n.t('Upload a SKILL.md file')}
					on:click={() => skillFileInput?.click()}
				>
					↑ {$i18n.t('Upload skill')}
				</button>
			{/if}
			<div class="ml-auto text-xs text-gray-500">
				{$i18n.t('Tip: type / in the message input')}
			</div>
		</div>
	</div>
</Modal>

<Modal bind:show={showCreatePrompt} size="md" className="bg-white dark:bg-gray-900 rounded-2xl">
	{#if showCreatePrompt}
		<PromptEditor
			modal={true}
			onSubmit={createPromptHandler}
			onCancel={() => (showCreatePrompt = false)}
		/>
	{/if}
</Modal>
