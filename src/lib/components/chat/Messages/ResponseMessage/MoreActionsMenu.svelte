<script lang="ts">
	// CHOn (T08): rarely used answer actions grouped under a labelled "More" menu
	// (WG-AI-PLA-00002, section 8 "Labelled controls").
	import { getContext } from 'svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';

	const i18n = getContext('i18n');

	type MessageAction = { id: string; name: string; icon?: string };

	export let buttonClass = '';

	export let showReadAloud = false;
	export let speaking = false;
	export let loadingSpeech = false;
	export let onReadAloud: () => void = () => {};

	export let showContinue = false;
	export let onContinue: () => void = () => {};

	export let actions: MessageAction[] = [];
	export let onAction: (id: string) => void = () => {};

	export let showFork = false;
	export let onFork: () => void = () => {};

	export let showDelete = false;
	export let deleteDisabled = false;
	export let onDelete: () => void = () => {};

	let show = false;

	$: hasItems = showReadAloud || showContinue || actions.length > 0 || showFork || showDelete;

	const run = (fn: () => void) => {
		show = false;
		fn();
	};

	const itemClass =
		'flex w-full items-center gap-2.5 rounded-xl px-2.5 py-1.5 text-left text-[0.8125rem] text-gray-800 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-850 transition disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent';
</script>

{#if hasItems}
	<Dropdown bind:show align="start" side="bottom">
		<Tooltip content={$i18n.t('More actions')} placement="bottom">
			<button
				type="button"
				aria-label={$i18n.t('More actions')}
				aria-haspopup="menu"
				class={buttonClass}
			>
				<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" class="w-4 h-4">
					<circle cx="5" cy="12" r="1.8" />
					<circle cx="12" cy="12" r="1.8" />
					<circle cx="19" cy="12" r="1.8" />
				</svg>
			</button>
		</Tooltip>

		<div slot="content">
			<DropdownMenu className="min-w-[13rem] max-w-[18rem]">
				{#if showReadAloud}
					<button
						type="button"
						class={itemClass}
						disabled={loadingSpeech}
						on:click={() => run(onReadAloud)}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="2"
							stroke="currentColor"
							aria-hidden="true"
							class="size-4 shrink-0"
						>
							{#if speaking}
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M17.25 9.75 19.5 12m0 0 2.25 2.25M19.5 12l2.25-2.25M19.5 12l-2.25 2.25m-10.5-6 4.72-4.72a.75.75 0 0 1 1.28.53v15.88a.75.75 0 0 1-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.009 9.009 0 0 1 2.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75Z"
								/>
							{:else}
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M19.114 5.636a9 9 0 010 12.728M16.463 8.288a5.25 5.25 0 010 7.424M6.75 8.25l4.72-4.72a.75.75 0 011.28.53v15.88a.75.75 0 01-1.28.53l-4.72-4.72H4.51c-.88 0-1.704-.507-1.938-1.354A9.01 9.01 0 012.25 12c0-.83.112-1.633.322-2.396C2.806 8.756 3.63 8.25 4.51 8.25H6.75z"
								/>
							{/if}
						</svg>
						<span class="truncate">
							{loadingSpeech
								? $i18n.t('Preparing audio…')
								: speaking
									? $i18n.t('Stop reading aloud')
									: $i18n.t('Read aloud')}
						</span>
					</button>
				{/if}

				{#if showContinue}
					<button type="button" class={itemClass} on:click={() => run(onContinue)}>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							fill="none"
							viewBox="0 0 24 24"
							stroke-width="2"
							stroke="currentColor"
							aria-hidden="true"
							class="size-4 shrink-0"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
							/>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M15.91 11.672a.375.375 0 0 1 0 .656l-5.603 3.113a.375.375 0 0 1-.557-.328V8.887c0-.286.307-.466.557-.327l5.603 3.112Z"
							/>
						</svg>
						<span class="truncate">{$i18n.t('Continue response')}</span>
					</button>
				{/if}

				{#if actions.length > 0}
					{#if showReadAloud || showContinue}
						<hr class="my-1 border-gray-100 dark:border-gray-800" />
					{/if}
					{#each actions as action (action.id)}
						<button type="button" class={itemClass} on:click={() => run(() => onAction(action.id))}>
							{#if action?.icon}
								<img
									src={action.icon}
									class="size-4 shrink-0 {action.icon.includes('data:image/svg')
										? 'dark:invert-[80%]'
										: ''}"
									alt=""
									draggable="false"
								/>
							{:else}
								<Sparkles strokeWidth="2" className="size-4 shrink-0" />
							{/if}
							<span class="truncate">{action.name}</span>
						</button>
					{/each}
				{/if}

				{#if showFork || showDelete}
					{#if showReadAloud || showContinue || actions.length > 0}
						<hr class="my-1 border-gray-100 dark:border-gray-800" />
					{/if}
					{#if showFork}
						<button type="button" class={itemClass} on:click={() => run(onFork)}>
							<svg
								class="size-4 shrink-0"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="1.8"
								stroke-linecap="round"
								stroke-linejoin="round"
								aria-hidden="true"
							>
								<path d="M4 12H9" />
								<path d="M9 12C12.5 12 12.5 7 16 7H20" />
								<path d="M17 4L20 7L17 10" />
								<path d="M9 12C12.5 12 12.5 17 16 17H20" />
								<path d="M17 14L20 17L17 20" />
							</svg>
							<span class="truncate">{$i18n.t('Fork into new chat')}</span>
						</button>
					{/if}
					{#if showDelete}
						<button
							type="button"
							class="{itemClass} !text-red-700 dark:!text-red-400"
							disabled={deleteDisabled}
							on:click={() => run(onDelete)}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="2"
								stroke="currentColor"
								aria-hidden="true"
								class="size-4 shrink-0"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
								/>
							</svg>
							<span class="truncate">{$i18n.t('Delete this version')}</span>
						</button>
					{/if}
				{/if}
			</DropdownMenu>
		</div>
	</Dropdown>
{/if}
