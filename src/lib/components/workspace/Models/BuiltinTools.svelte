<script lang="ts" context="module">
	// Keep in sync with the tool list below (used for "12 of 16 tools on").
	export const BUILTIN_TOOL_COUNT = 16;
</script>

<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import Switch from '$lib/components/common/Switch.svelte';

	const i18n: Writable<i18nType> = getContext('i18n');

	const toolLabels = {
		time: {
			label: $i18n.t('Time & Calculation'),
			description: $i18n.t('Get current time and perform date/time calculations')
		},
		user_input: {
			label: $i18n.t('Ask User'),
			description: $i18n.t('Pause a response to ask the user a clarifying question')
		},
		memory: {
			label: $i18n.t('Memory'),
			description: $i18n.t('Search and manage user memories')
		},
		chats: {
			label: $i18n.t('Chat History'),
			description: $i18n.t('Search and view user chat history')
		},
		notes: {
			label: $i18n.t('Notes'),
			description: $i18n.t('Search, view, and manage user notes')
		},
		knowledge: {
			label: $i18n.t('Knowledge Base'),
			description: $i18n.t('Browse and query knowledge bases')
		},
		files: {
			label: $i18n.t('Files'),
			description: $i18n.t('List, search, and read files attached to the current chat')
		},
		channels: {
			label: $i18n.t('Channels'),
			description: $i18n.t('Search channels and channel messages')
		},
		notifications: {
			label: $i18n.t('Notifications'),
			description: $i18n.t('Send notifications to configured webhook targets')
		},
		web_search: {
			label: $i18n.t('Web Search'),
			description: $i18n.t('Search the web and fetch URLs')
		},
		image_generation: {
			label: $i18n.t('Image Generation'),
			description: $i18n.t('Generate and edit images')
		},
		code_interpreter: {
			label: $i18n.t('Code Interpreter'),
			description: $i18n.t('Execute code')
		},
		tasks: {
			label: $i18n.t('Task Management'),
			description: $i18n.t('Break down complex requests into trackable steps')
		},
		automations: {
			label: $i18n.t('Automations'),
			description: $i18n.t('Create and manage scheduled automations')
		},
		calendar: {
			label: $i18n.t('Calendar'),
			description: $i18n.t('List calendars, search, create, update, and delete calendar events')
		},
		subagents: {
			label: $i18n.t('Sub-agents'),
			description: $i18n.t('Delegate focused work to parallel sub-agents')
		}
	};

	type Tool = keyof typeof toolLabels;

	const groups: { title: string; tools: Tool[] }[] = [
		{
			title: $i18n.t('Look things up'),
			tools: ['time', 'web_search', 'knowledge', 'files', 'chats', 'memory', 'notes', 'channels']
		},
		{
			title: $i18n.t('Take actions'),
			tools: ['image_generation', 'code_interpreter', 'calendar', 'automations', 'notifications', 'tasks']
		},
		{ title: $i18n.t('Work with the user'), tools: ['user_input', 'subagents'] }
	];

	// Stored as { tool: false } for switched-off tools; everything else is on.
	export let builtinTools: Record<string, boolean> = {};

	const setBuiltinTool = (tool: Tool, checked: boolean) => {
		if (checked) {
			delete builtinTools[tool];
		} else {
			builtinTools[tool] = false;
		}
		builtinTools = builtinTools;
	};
</script>

<div class="flex flex-col gap-3">
	{#each groups as group (group.title)}
		<div>
			<div class="mb-1 text-xs font-semibold text-gray-700 dark:text-gray-300">{group.title}</div>
			<div class="grid gap-x-6 sm:grid-cols-2">
				{#each group.tools as tool (tool)}
					<div class="flex items-center justify-between gap-3 py-1" title={toolLabels[tool].description}>
						<label
							for="builtin-tool-{tool}"
							id="builtin-tool-{tool}-label"
							class="min-w-0 cursor-pointer truncate text-xs text-gray-700 dark:text-gray-300"
						>
							{toolLabels[tool].label}
						</label>
						<Switch
							id="builtin-tool-{tool}"
							ariaLabelledbyId="builtin-tool-{tool}-label"
							state={builtinTools[tool] !== false}
							on:change={(e) => setBuiltinTool(tool, e.detail)}
						/>
					</div>
				{/each}
			</div>
		</div>
	{/each}
</div>
