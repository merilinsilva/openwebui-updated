<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';

	import { onMount, getContext, tick, createEventDispatcher } from 'svelte';
	import { blur, fade } from 'svelte/transition';

	const dispatch = createEventDispatcher();

	import { updateFolderById } from '$lib/apis/folders';
	import { getPrompts } from '$lib/apis/prompts';

	import {
		config,
		user,
		models as _models,
		temporaryChatEnabled,
		selectedFolder,
		skills
	} from '$lib/stores';
	import { refreshChatList, refreshFolderChatLists } from '$lib/stores/chatList';
	import { sanitizeResponseContent, extractCurlyBraceWords } from '$lib/utils';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';

	import Suggestions from './Suggestions.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import EyeSlash from '$lib/components/icons/EyeSlash.svelte';
	import MessageInput from './MessageInput.svelte';
	import FolderPlaceholder from './Placeholder/FolderPlaceholder.svelte';
	import FolderTitle from './Placeholder/FolderTitle.svelte';
	import ModelValveSelect from './Placeholder/ModelValveSelect.svelte';

	const i18n = getContext('i18n');

	export let createMessagePair: Function;
	export let stopResponse: Function;

	export let autoScroll = false;

	export let atSelectedModel: Model | undefined;
	export let selectedModels: [''];

	export let history;

	export let prompt = '';
	export let files = [];
	export let messageInput = null;

	export let selectedToolIds = [];
	export let selectedSkillIds = [];
	export let selectedFilterIds = [];
	export let pendingOAuthTools = [];

	export let showCommands = false;

	export let imageGenerationEnabled = false;
	export let codeInterpreterEnabled = false;
	export let webSearchEnabled = false;
	export let toolApprovalMode = 'full';
	export let onToolApprovalModeChange: Function = () => {};
	export let oauthRedirectHandler: Function = () => {};

	export let onUpload: Function = (e) => {};
	export let onUpdate: (data?: { file?: any }) => void = () => {};
	export let onSelect = (e) => {};
	export let onChange = (e) => {};
	export let onWebSearchToggle: Function = () => {};
	export let messageQueue: { id: string; prompt: string; files: any[] }[] = [];
	export let onQueueSendNow: (id: string) => void = () => {};
	export let onQueueEdit: (id: string) => void = () => {};
	export let onQueueDelete: (id: string) => void = () => {};
	export let askUser = {
		show: false,
		questions: [],
		allowOther: true,
		timeoutMs: null,
		onConfirm: (_value: any) => {},
		onCancel: () => {}
	};

	export let dragged = false;

	let models = [];
	let selectedModelIdx = 0;

	$: if (selectedModels.length > 0) {
		selectedModelIdx = models.length - 1;
	}

	$: models = selectedModels.map((id) => $_models.find((m) => m.id === id));

	// Skills the user can use (store is loaded by Chat.svelte), most recently updated first.
	const QUICK_SKILL_COUNT = 6;
	$: quickSkills = ($skills ?? [])
		.filter((skill) => skill?.is_active !== false)
		.sort((a, b) => (b.updated_at ?? 0) - (a.updated_at ?? 0))
		.slice(0, QUICK_SKILL_COUNT);

	$: activeModel = atSelectedModel ?? models[selectedModelIdx];

	$: modelInfo = (activeModel?.info?.meta?.news ?? '').trim();

	// Task cards come from the prompt library (only prompts this user can read).
	let libraryPrompts = [];
	onMount(async () => {
		const res = await getPrompts(localStorage.token).catch(() => null);
		libraryPrompts = (res ?? []).filter(
			(p) => p?.is_active !== false && (p?.content ?? '').trim()
		);
	});

	const toTask = (p) => ({
		title: p.name,
		// Prompts have no description field: preview the prompt text instead.
		description: (p.content ?? '').replace(/\s+/g, ' ').trim(),
		label: p.tags?.[0] ?? `/${(p.command ?? '').replace(/^\//, '')}`,
		prompt: p.content
	});

	// The model's picked prompts, in order; otherwise the 4 most recently updated.
	$: taskPromptIds = activeModel?.info?.meta?.task_prompt_ids ?? [];
	$: tasks = (
		taskPromptIds.length > 0
			? taskPromptIds.map((id) => libraryPrompts.find((p) => p.id === id)).filter(Boolean)
			: [...libraryPrompts].sort((a, b) => (b.updated_at ?? 0) - (a.updated_at ?? 0))
	)
		.slice(0, 4)
		.map(toTask);

	$: canViewSkills =
		$user?.role === 'admin' || ($user?.permissions?.workspace?.skills ?? false);

	const insertPrompt = (text: string) => {
		if (!text?.trim()) return;
		messageInput?.setText(text);
	};

	// Same mention tag the "/" menu produces; the backend loads the skill's full
	// instructions for any <$id|label> in the message. Appended so typed text is kept.
	const insertSkill = (skill) => {
		if (!skill?.id) return;
		if ((prompt ?? '').includes(`<$${skill.id}`)) {
			messageInput?.focus();
			return;
		}
		// The input's mention parser stops at these characters.
		const label = (skill.name ?? skill.id).replace(/[<>&|]/g, '').trim() || skill.id;
		const current = (prompt ?? '').trimEnd();
		messageInput?.setText(`${current ? `${current} ` : ''}<$${skill.id}|${label}> `);
	};

	// True when viewing a shared folder the current user doesn't own AND lacks write access
	$: folderReadOnly =
		$selectedFolder != null &&
		$selectedFolder.user_id !== $user?.id &&
		$selectedFolder.permission !== 'write';
</script>

<div class="m-auto w-full max-w-[58rem] px-1 @2xl:px-20 translate-y-6 py-24 text-center">
	{#if $temporaryChatEnabled}
		<Tooltip
			content={$i18n.t("This chat won't appear in history and your messages will not be saved.")}
			className="w-full flex justify-center mb-0.5"
			placement="top"
		>
			<div class="flex items-center gap-1.5 text-gray-500 text-xs my-1 w-fit">
				<EyeSlash strokeWidth="2" className="size-3.5" />{$i18n.t('Temporary Chat')}
			</div>
		</Tooltip>
	{/if}

	<div class="w-full text-3xl text-gray-800 dark:text-gray-100 text-center flex items-center gap-4">
		<div class="w-full flex flex-col justify-center items-center">
			{#if $selectedFolder}
				<FolderTitle
					folder={$selectedFolder}
					readOnly={folderReadOnly}
					onUpdate={async () => {
						await Promise.all([refreshChatList(localStorage.token), refreshFolderChatLists(null)]);
					}}
					onDelete={async () => {
						await Promise.all([refreshChatList(localStorage.token), refreshFolderChatLists(null)]);

						selectedFolder.set(null);
					}}
				/>
			{:else}
				<div class="flex flex-row justify-center gap-2.5 @sm:gap-3 w-fit px-5 max-w-xl">
					<div class="flex shrink-0 justify-center">
						<div class="flex -space-x-4 mb-0.5" in:fade={{ duration: 100 }}>
							{#each models as model, modelIdx}
								<Tooltip
									content={(models[modelIdx]?.info?.meta?.tags ?? [])
										.map((tag) => tag.name.toUpperCase())
										.join(', ')}
									placement="top"
								>
									<button
										aria-hidden={models.length <= 1}
										aria-label={$i18n.t('Get information on {{name}} in the UI', {
											name: models[modelIdx]?.name
										})}
										on:click={() => {
											selectedModelIdx = modelIdx;
										}}
									>
										<img
											src={`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${model?.id}&lang=${$i18n.language}`}
											class=" size-9 @sm:size-10 rounded-2xl"
											aria-hidden="true"
											draggable="false"
											on:error={(e) => {
												// LICENSE covers this Open WebUI fallback logo.
												// Do not alter, remove, obscure, or replace it except as LICENSE permits:
												// https://docs.openwebui.com/license.
												e.currentTarget.src = '/favicon.png';
											}}
										/>
									</button>
								</Tooltip>
							{/each}
						</div>
					</div>

					<div
						class=" text-2xl @sm:text-2xl line-clamp-1 flex items-center"
						in:fade={{ duration: 100 }}
					>
						{#if models[selectedModelIdx]?.name}
							<Tooltip
								content={models[selectedModelIdx]?.name}
								placement="top"
								className=" flex items-center "
							>
								<span class="line-clamp-1">
									{models[selectedModelIdx]?.name}
								</span>
							</Tooltip>
						{:else}
							{$i18n.t('Hello, {{name}}', { name: $user?.name })}
						{/if}
					</div>

				</div>

				<div class="flex mt-1 mb-2">
					<div in:fade={{ duration: 100, delay: 50 }}>
						{#if models[selectedModelIdx]?.info?.meta?.description ?? null}
							<Tooltip
								className=" w-fit"
								content={DOMPurify.sanitize(
									marked.parse(
										sanitizeResponseContent(
											models[selectedModelIdx]?.info?.meta?.description ?? ''
										).replaceAll('\n', '<br>')
									)
								)}
								placement="top"
							>
								<div
									class="mt-0.5 px-2 text-sm font-normal text-gray-500 dark:text-gray-400 line-clamp-2 max-w-xl markdown"
								>
									{@html DOMPurify.sanitize(
										marked.parse(
											sanitizeResponseContent(
												models[selectedModelIdx]?.info?.meta?.description ?? ''
											).replaceAll('\n', '<br>')
										)
									)}
								</div>
							</Tooltip>

							{#if models[selectedModelIdx]?.info?.meta?.user}
								<div class="mt-0.5 text-sm font-normal text-gray-400 dark:text-gray-500">
									By
									{#if models[selectedModelIdx]?.info?.meta?.user.community}
										<a
											href="https://openwebui.com/m/{models[selectedModelIdx]?.info?.meta?.user
												.username}"
											>{models[selectedModelIdx]?.info?.meta?.user.name
												? models[selectedModelIdx]?.info?.meta?.user.name
												: `@${models[selectedModelIdx]?.info?.meta?.user.username}`}</a
										>
									{:else}
										{models[selectedModelIdx]?.info?.meta?.user.name}
									{/if}
								</div>
							{/if}
						{/if}
					</div>
				</div>

				<!-- e.g. "Base Model" from the Base Model Router filter attached to this model. -->
				<ModelValveSelect model={activeModel} />
			{/if}

			{#if !$selectedFolder && (tasks.length > 0 || quickSkills.length > 0)}
				<div class="@md:max-w-3xl w-full mt-3 text-left" in:fade={{ duration: 150, delay: 50 }}>
					{#if tasks.length > 0}
						<div class="grid grid-cols-1 @md:grid-cols-2 gap-2">
							{#each tasks as task, taskIdx}
								<button
									type="button"
									class="group flex flex-col text-left rounded-2xl border border-gray-100 dark:border-gray-850 bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-850 px-4 py-3 transition"
									on:click={() => insertPrompt(task.prompt || task.title)}
								>
									<div class="flex w-full items-center justify-between gap-2">
										<span
											class="text-[0.6875rem] font-medium tracking-wide uppercase text-gray-400 dark:text-gray-500"
										>
											{$i18n.t('Task {{number}}', {
												number: String(taskIdx + 1).padStart(2, '0')
											})}
										</span>
										{#if task.icon}
											<span class="text-base leading-none text-gray-500 dark:text-gray-400"
												>{task.icon}</span
											>
										{/if}
									</div>
									<div
										class="mt-1.5 text-sm font-semibold text-gray-900 dark:text-gray-100 line-clamp-1"
									>
										{task.title}
									</div>
									{#if task.description}
										<div class="mt-0.5 text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
											{task.description}
										</div>
									{/if}
									{#if task.label}
										<div class="mt-2 text-[0.6875rem] text-gray-400 dark:text-gray-500">
											{task.label}
										</div>
									{/if}
								</button>
							{/each}
						</div>
					{/if}

					{#if quickSkills.length > 0}
						<div class="flex flex-wrap items-center gap-2 {tasks.length > 0 ? 'mt-3' : ''}">
							<span
								class="text-[0.6875rem] font-medium tracking-wide uppercase text-gray-400 dark:text-gray-500 mr-1"
							>
								{$i18n.t('Skills')}
							</span>
							{#each quickSkills as skill (skill.id)}
								<!-- Skill text is user content: render it as plain text, never HTML. -->
								<Tooltip
									content={skill.description || skill.name}
									allowHTML={false}
									placement="top"
								>
									<button
										type="button"
										class="flex items-center gap-1.5 rounded-full bg-gray-50 dark:bg-gray-850 hover:bg-gray-100 dark:hover:bg-gray-800 px-3 py-1 text-xs text-gray-800 dark:text-gray-200 transition"
										on:click={() => insertSkill(skill)}
									>
										<span class="line-clamp-1">{skill.name}</span>
									</button>
								</Tooltip>
							{/each}
							{#if canViewSkills}
								<a
									href="/workspace/skills"
									class="ml-auto text-xs underline underline-offset-2 text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
								>
									{$i18n.t('View all')} →
								</a>
							{/if}
						</div>
					{/if}
				</div>
			{/if}

			<div class="text-base font-normal @md:max-w-3xl w-full py-3 {atSelectedModel ? 'mt-2' : ''}">
				{#if !($selectedFolder && folderReadOnly)}
					<MessageInput
						bind:this={messageInput}
						{history}
						bind:selectedModels
						bind:files
						bind:prompt
						bind:autoScroll
						bind:selectedToolIds
						bind:selectedSkillIds
						bind:selectedFilterIds
						bind:imageGenerationEnabled
						bind:codeInterpreterEnabled
						bind:webSearchEnabled
						bind:atSelectedModel
						bind:showCommands
						bind:dragged
						{pendingOAuthTools}
						{oauthRedirectHandler}
						{toolApprovalMode}
						{onToolApprovalModeChange}
						{stopResponse}
						{createMessagePair}
						placeholder={$i18n.t('How can I help you today?')}
						{onChange}
						{onUpload}
						{onUpdate}
						{messageQueue}
						{onQueueSendNow}
						{onQueueEdit}
						{onQueueDelete}
						{askUser}
						{onWebSearchToggle}
						on:chatVariables
						on:submit={(e) => {
							dispatch('submit', e.detail);
						}}
					/>
				{/if}
			</div>
		</div>
	</div>

	{#if $selectedFolder}
		<div class="mx-auto px-4 md:max-w-3xl md:px-6 min-h-62" in:fade={{ duration: 200, delay: 200 }}>
			<FolderPlaceholder folder={$selectedFolder} />
		</div>
	{:else}
		<div class="mx-auto max-w-2xl mt-2" in:fade={{ duration: 200, delay: 200 }}>
			<div class="mx-5">
				{#if modelInfo}
					<!-- Long text would overflow the viewport: cap the height and scroll;
					     interactive so the pointer can move in to scroll. -->
					<Tooltip
						content={`<div class="max-h-[60vh] overflow-y-auto pr-1">${DOMPurify.sanitize(
							marked.parse(sanitizeResponseContent(modelInfo).replaceAll('\n', '<br>'))
						)}</div>`}
						placement="top"
						theme="news"
						interactive
						tippyOptions={{ appendTo: () => document.body, maxWidth: 420 }}
						className="flex justify-center mb-3"
					>
						<div
							class="flex items-center gap-1.5 rounded-full bg-red-600 hover:bg-red-700 px-3 py-1.5 text-xs font-medium text-white shadow-sm cursor-default select-none transition"
							role="note"
							aria-label={$i18n.t('Model Information')}
							in:fade={{ duration: 100 }}
						>
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
								<path d="M3 11v2a1 1 0 0 0 1 1h2l5 4V6L6 10H4a1 1 0 0 0-1 1Z" />
								<path d="M15.5 8.5a5 5 0 0 1 0 7" />
								<path d="M18.5 5.5a9 9 0 0 1 0 13" />
							</svg>
							{$i18n.t('Model Information')}
						</div>
					</Tooltip>
				{/if}

				<div class="mb-3 text-xs text-gray-500 dark:text-gray-400 text-center">
					{$i18n.t(
						'CHOn can make mistakes. Review content carefully and do not input information that is confidential to you.'
					)}
				</div>

				<!-- Tasks replace the suggestion list for this model; pass none so only the footer shows. -->
				<Suggestions
					suggestionPrompts={tasks.length > 0
						? []
						: atSelectedModel?.info?.meta?.suggestion_prompts ??
							models[selectedModelIdx]?.info?.meta?.suggestion_prompts ??
							$config?.default_prompt_suggestions ??
							[]}
					inputValue={prompt}
					{onSelect}
				/>
			</div>
		</div>
	{/if}
</div>
