<script lang="ts">
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import DocumentArrowDown from '$lib/components/icons/DocumentArrowDown.svelte';
	import DocumentArrowUp from '$lib/components/icons/DocumentArrowUp.svelte';
	import Link from '$lib/components/icons/Link.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';

	// CHOn style: white fill, Weidmann-red outline and text.
	const shellClass =
		'ml-1 rounded-lg border border-red-600 bg-white text-[0.8125rem] font-medium text-red-600 transition dark:border-red-500 dark:bg-gray-900 dark:text-red-400';
	const hoverClass = 'hover:bg-red-50 dark:hover:bg-red-950/40';

	type SplitCreateAction = {
		id: string;
		label: string;
		href?: string;
		onClick?: () => void | Promise<void>;
		visible?: boolean;
	};

	export let actions: SplitCreateAction[] = [];
	export let label = 'Create';

	const i18n = getContext<Writable<i18nType>>('i18n');

	let showMenu = false;
	$: visibleActions = actions.filter((action) => action.visible ?? true);
	$: primaryAction =
		visibleActions.find((action) => action.id.endsWith('-new')) ?? visibleActions[0] ?? null;

	const runAction = async (action: SplitCreateAction | null) => {
		if (!action) return;
		if (action.href) {
			await goto(action.href);
		} else {
			await action.onClick?.();
		}
	};

	const getActionIcon = (id: string) => {
		if (id.endsWith('-new')) return Pencil;
		if (id.includes('-import-link')) return Link;
		if (id.includes('-import')) return DocumentArrowUp;
		if (id.includes('-export')) return DocumentArrowDown;
		return Pencil;
	};
</script>

{#if visibleActions.length === 1}
	<button
		class="focus-ring flex items-center gap-1.5 px-5 py-1.5 {shellClass} {hoverClass}"
		type="button"
		on:click={() => {
			runAction(primaryAction);
		}}
	>
		<Plus className="size-3.5" strokeWidth="2.5" />
		{$i18n.t(label)}
	</button>
{:else if visibleActions.length > 1}
	<!-- items-stretch: the arrow half (inside Dropdown's display:contents span) must fill the height. -->
	<div class="flex items-stretch overflow-hidden {shellClass}">
		<button
			class="focus-ring flex items-center gap-1.5 py-1.5 pr-4 pl-5 transition {hoverClass}"
			on:click={() => {
				runAction(primaryAction);
			}}
		>
			<Plus className="size-3.5" strokeWidth="2.5" />
			{$i18n.t(label)}
		</button>

		<Dropdown bind:show={showMenu} align="end" sideOffset={6}>
			<button
				class="focus-ring flex items-center self-stretch border-l border-red-600 px-2.5 transition dark:border-red-500 {hoverClass}"
				aria-label={$i18n.t('Open create menu')}
			>
				<ChevronDown className="size-3" strokeWidth="2.5" />
			</button>

			<div slot="content">
				<DropdownMenu className="min-w-[10.625rem]">
					{#each visibleActions as action (action.id)}
						{@const Icon = getActionIcon(action.id)}
						{#if action.href}
							<a
								href={action.href}
								on:click={() => {
									showMenu = false;
								}}
							>
								<Icon className="size-3.5" />
								<span class="self-center truncate">{action.label}</span>
							</a>
						{:else}
							<button
								on:click={async () => {
									await action.onClick?.();
									showMenu = false;
								}}
							>
								<Icon className="size-3.5" />
								<span class="self-center truncate">{action.label}</span>
							</button>
						{/if}
					{/each}
				</DropdownMenu>
			</div>
		</Dropdown>
	</div>
{/if}
