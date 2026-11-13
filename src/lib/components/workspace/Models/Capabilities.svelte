<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import ToggleRow from './ToggleRow.svelte';
	import BuiltinTools, { BUILTIN_TOOL_COUNT } from './BuiltinTools.svelte';

	const i18n: Writable<i18nType> = getContext('i18n');

	const capabilityLabels = {
		vision: {
			label: $i18n.t('Images'),
			description: $i18n.t('Users can attach images, and the model can read them.')
		},
		file_upload: {
			label: $i18n.t('File upload'),
			description: $i18n.t('Users can attach documents to a message.')
		},
		file_context: {
			label: $i18n.t('Add file content to the chat'),
			description: $i18n.t(
				'Puts the text of attached files into the conversation. Turn off if the model should look files up with tools instead.'
			)
		},
		web_search: {
			label: $i18n.t('Web search'),
			description: $i18n.t('Can search the internet for current information.')
		},
		image_generation: {
			label: $i18n.t('Image generation'),
			description: $i18n.t('Can create images from a description.')
		},
		code_interpreter: {
			label: $i18n.t('Code interpreter'),
			description: $i18n.t('Can run code, e.g. for calculations, charts and data analysis.')
		},
		terminal: {
			label: $i18n.t('Terminal'),
			description: $i18n.t('Can run commands and manage files in Open Terminal.')
		},
		citations: {
			label: $i18n.t('Citations'),
			description: $i18n.t('Shows which sources an answer is based on.')
		},
		status_updates: {
			label: $i18n.t('Progress updates'),
			description: $i18n.t('Shows what the model is doing, e.g. "Searching the web…".')
		},
		memory: {
			label: $i18n.t('Memory'),
			description: $i18n.t('Uses the facts users saved in "My memory".')
		},
		usage: {
			label: $i18n.t('Usage reporting'),
			description: $i18n.t('Asks the provider to report token usage for each answer, where supported.')
		},
		builtin_tools: {
			label: $i18n.t('Built-in tools'),
			description: $i18n.t(
				'Helpers like time, notes and chat history the model can call by itself. Needs native function calling.'
			)
		}
	};

	type Capability = keyof typeof capabilityLabels;

	const groups: { title: string; items: Capability[] }[] = [
		{ title: $i18n.t('What users can send'), items: ['vision', 'file_upload'] },
		{
			title: $i18n.t('What it can do'),
			items: ['web_search', 'image_generation', 'code_interpreter', 'terminal']
		},
		{ title: $i18n.t('In the answer'), items: ['citations', 'status_updates', 'memory'] },
		{ title: $i18n.t('Technical'), items: ['usage', 'builtin_tools'] }
	];

	// These can also be switched on by default for new chats.
	const DEFAULTABLE: Capability[] = ['web_search', 'image_generation', 'code_interpreter'];

	export let capabilities: Partial<Record<Capability, boolean>> = {};
	// Optional: pass to show "On by default" inside the matching rows (null hides it).
	export let defaultFeatureIds: string[] | null = null;
	// Optional: pass to choose individual built-in tools inside the "Built-in tools" row.
	export let builtinTools: Record<string, any> | null = null;

	let showBuiltinTools = false;

	const setCapability = (capability: Capability, checked: boolean) => {
		capabilities[capability] = checked;
		capabilities = capabilities;
	};

	const setDefaultFeature = (feature: string, on: boolean) => {
		const ids = defaultFeatureIds ?? [];
		defaultFeatureIds = on ? [...new Set([...ids, feature])] : ids.filter((id) => id !== feature);
	};

	$: enabledBuiltinCount =
		BUILTIN_TOOL_COUNT - Object.values(builtinTools ?? {}).filter((v) => v === false).length;
</script>

<div class="flex flex-col gap-4">
	{#each groups as group (group.title)}
		<div>
			<div class="mb-1 text-[0.6875rem] font-semibold tracking-wide text-gray-500 uppercase">
				{group.title}
			</div>
			<div
				class="divide-y divide-gray-100 rounded-lg border border-gray-200 px-3 dark:divide-gray-800 dark:border-gray-800"
			>
				{#each group.items as capability (capability)}
					<ToggleRow
						id="capability-{capability}"
						label={capabilityLabels[capability].label}
						description={capabilityLabels[capability].description}
						checked={!!capabilities[capability]}
						onChange={(on) => setCapability(capability, on)}
					>
						{#if defaultFeatureIds !== null && DEFAULTABLE.includes(capability)}
							<label class="mt-1.5 flex w-fit items-center gap-1.5 text-xs text-gray-700 dark:text-gray-300">
								<input
									type="checkbox"
									class="size-3.5 rounded border-gray-300"
									checked={defaultFeatureIds.includes(capability)}
									on:change={(e) => setDefaultFeature(capability, e.currentTarget.checked)}
								/>
								{$i18n.t('On by default in new chats')}
							</label>
						{/if}

						{#if capability === 'builtin_tools' && builtinTools !== null}
							<div class="mt-1.5 text-xs text-gray-700 dark:text-gray-300">
								{$i18n.t('{{count}} of {{total}} tools on', {
									count: enabledBuiltinCount,
									total: BUILTIN_TOOL_COUNT
								})}
								·
								<button
									type="button"
									class="underline hover:text-gray-900 dark:hover:text-gray-100"
									aria-expanded={showBuiltinTools}
									on:click={() => (showBuiltinTools = !showBuiltinTools)}
								>
									{showBuiltinTools ? $i18n.t('Done') : $i18n.t('Choose')}
								</button>
							</div>
						{/if}
					</ToggleRow>

					{#if capability === 'file_upload' && capabilities.file_upload}
						<div class="pl-4">
							<ToggleRow
								id="capability-file_context"
								label={capabilityLabels.file_context.label}
								description={capabilityLabels.file_context.description}
								checked={!!capabilities.file_context}
								onChange={(on) => setCapability('file_context', on)}
								compact
							/>
						</div>
					{/if}

					{#if capability === 'builtin_tools' && builtinTools !== null && capabilities.builtin_tools && showBuiltinTools}
						<div class="py-3">
							<BuiltinTools bind:builtinTools />
						</div>
					{/if}
				{/each}
			</div>
		</div>
	{/each}
</div>
