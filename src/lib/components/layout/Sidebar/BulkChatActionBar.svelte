<script lang="ts">
	// CHOn (T16): action bar shown while the sidebar is in "Select chats" mode.
	// Archive, move to folder, export and delete several chats at once.
	import { getContext, tick } from 'svelte';
	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { goto } from '$app/navigation';
	import {
		archiveChatById,
		deleteChatById,
		getAllTags,
		getChatById,
		updateChatFolderIdById
	} from '$lib/apis/chats';
	import { chatId, folders, tags, user } from '$lib/stores';
	import {
		chatSelectMode,
		selectedChatIds,
		setChatSelection,
		exitChatSelectMode,
		getSelectedChatIds
	} from '$lib/stores/chatSelection';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ArchiveBoxIcon from '$lib/components/icons/ArchiveBox.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import FolderIcon from './icons/Folder.svelte';
	import DownloadIcon from './icons/Download.svelte';
	import TrashIcon from './icons/Trash.svelte';

	const i18n = getContext('i18n');

	/** Ids of all chats currently loaded in the main list (pinned + recent). */
	export let selectableIds: string[] = [];
	/** Called after an action so the sidebar reloads its lists. */
	export let onDone: () => void | Promise<void> = () => {};

	type FolderItem = { id: string; name?: string };
	$: folderList = [...($folders as FolderItem[])].sort((a, b) =>
		(a?.name ?? '').localeCompare(b?.name ?? '')
	);

	let busy = false;
	let showDeleteConfirm = false;
	let showMoveMenu = false;

	$: count = $selectedChatIds.size;
	$: allSelected = selectableIds.length > 0 && selectableIds.every((id) => $selectedChatIds.has(id));
	$: canDelete = $user?.role === 'admin' || ($user?.permissions?.chat?.delete ?? true);
	$: canExport = $user?.role === 'admin' || ($user?.permissions?.chat?.export ?? true);
	// The Dropdown trigger wrapper still opens when the button is disabled.
	$: if (showMoveMenu && (busy || count === 0)) showMoveMenu = false;

	// Run a per-chat API call for every selected id, a few at a time.
	const runForSelected = async (fn: (id: string) => Promise<unknown>) => {
		const ids = getSelectedChatIds();
		const failed: string[] = [];
		const queue = [...ids];
		const worker = async () => {
			while (queue.length) {
				const id = queue.shift() as string;
				try {
					const res = await fn(id);
					if (res === null || res === undefined || res === false) failed.push(id);
				} catch (e) {
					console.error(e);
					failed.push(id);
				}
			}
		};
		await Promise.all(Array.from({ length: Math.min(5, ids.length) }, worker));
		return { ids, ok: ids.length - failed.length, failed };
	};

	const finish = async (ids: string[], leftCurrentChat: boolean) => {
		if (leftCurrentChat && ids.includes($chatId)) {
			await goto('/');
			chatId.set('');
			await tick();
		}
		exitChatSelectMode();
		await onDone();
	};

	const report = (ok: number, failed: string[], success: string) => {
		if (ok > 0) toast.success(success);
		if (failed.length > 0) {
			toast.error(
				$i18n.t('{{COUNT}} chat(s) could not be processed. Please try again.', {
					COUNT: failed.length
				})
			);
		}
	};

	const archiveHandler = async () => {
		if (busy || count === 0) return;
		busy = true;
		const { ids, ok, failed } = await runForSelected((id) =>
			archiveChatById(localStorage.token, id)
		);
		report(ok, failed, $i18n.t('{{COUNT}} chat(s) archived.', { COUNT: ok }));
		await finish(ids, true);
		busy = false;
	};

	const moveHandler = async (folderId: string | null, folderName: string) => {
		showMoveMenu = false;
		if (busy || count === 0) return;
		busy = true;
		// null removes the chat from its folder (same as the sidebar's drop-to-root handler)
		const { ids, ok, failed } = await runForSelected((id) =>
			updateChatFolderIdById(localStorage.token, id, folderId as string)
		);
		report(
			ok,
			failed,
			folderId
				? $i18n.t('{{COUNT}} chat(s) moved to {{FOLDER}}.', { COUNT: ok, FOLDER: folderName })
				: $i18n.t('{{COUNT}} chat(s) removed from their folder.', { COUNT: ok })
		);
		await finish(ids, false);
		busy = false;
	};

	const exportHandler = async () => {
		if (busy || count === 0) return;
		busy = true;
		const exported: unknown[] = [];
		const { ok, failed } = await runForSelected(async (id) => {
			const chat = await getChatById(localStorage.token, id);
			if (chat) exported.push(chat);
			return chat;
		});
		if (exported.length > 0) {
			const blob = new Blob([JSON.stringify(exported)], { type: 'application/json' });
			saveAs(blob, `chon-chats-export-${new Date().toISOString().slice(0, 10)}.json`);
		}
		report(ok, failed, $i18n.t('{{COUNT}} chat(s) exported.', { COUNT: ok }));
		busy = false;
	};

	const deleteHandler = async () => {
		if (busy || count === 0) return;
		busy = true;
		const { ids, ok, failed } = await runForSelected((id) =>
			deleteChatById(localStorage.token, id)
		);
		if (ok > 0) tags.set(await getAllTags(localStorage.token));
		report(ok, failed, $i18n.t('{{COUNT}} chat(s) deleted.', { COUNT: ok }));
		await finish(ids, true);
		busy = false;
	};

	const toggleAll = () => {
		setChatSelection(allSelected ? [] : selectableIds);
	};

	const buttonClass =
		'flex flex-col items-center justify-center gap-0.5 flex-1 min-w-0 rounded-lg py-1.5 text-[0.6875rem] text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-850 transition outline-hidden focus-visible:ring-2 focus-visible:ring-red-700/40 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent';
</script>

<svelte:window
	on:keydown={(e) => {
		if (e.key === 'Escape' && $chatSelectMode && !showDeleteConfirm && !busy) {
			exitChatSelectMode();
		}
	}}
/>

<ConfirmDialog
	bind:show={showDeleteConfirm}
	variant="danger"
	title={$i18n.t('Delete {{COUNT}} chat(s)?', { COUNT: count })}
	confirmLabel={$i18n.t('Delete')}
	on:confirm={deleteHandler}
>
	<div class="text-sm text-gray-500 flex-1">
		{$i18n.t('The selected chats will be deleted permanently. This cannot be undone.')}
	</div>
</ConfirmDialog>

<div
	id="sidebar-bulk-actions"
	class="mb-1.5 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-sm p-1.5"
	role="toolbar"
	aria-label={$i18n.t('Bulk chat actions')}
>
	<div class="flex items-center justify-between gap-2 px-1 pb-1">
		<div class="flex items-center gap-1.5 min-w-0 text-[0.8125rem] font-semibold text-gray-900 dark:text-gray-100">
			{#if busy}
				<Spinner className="size-3.5" />
			{/if}
			<span class="truncate" aria-live="polite">
				{$i18n.t('{{COUNT}} selected', { COUNT: count })}
			</span>
		</div>
		<div class="flex items-center gap-1 shrink-0">
			<button
				type="button"
				class="text-xs text-red-700 dark:text-red-400 hover:underline rounded outline-hidden focus-visible:ring-2 focus-visible:ring-red-700/40 disabled:opacity-40"
				disabled={busy || selectableIds.length === 0}
				on:click={toggleAll}
			>
				{allSelected ? $i18n.t('Clear') : $i18n.t('Select all')}
			</button>
			<Tooltip content={$i18n.t('Done (Esc)')}>
				<button
					type="button"
					class="flex size-6 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-850 outline-hidden focus-visible:ring-2 focus-visible:ring-red-700/40"
					aria-label={$i18n.t('Exit selection')}
					disabled={busy}
					on:click={exitChatSelectMode}
				>
					<XMark className="size-3.5" strokeWidth="2" />
				</button>
			</Tooltip>
		</div>
	</div>

	<div class="flex items-stretch gap-0.5">
		<button type="button" class={buttonClass} disabled={busy || count === 0} on:click={archiveHandler}>
			<ArchiveBoxIcon className="size-4" strokeWidth="1.6" />
			<span>{$i18n.t('Archive')}</span>
		</button>

		<Dropdown bind:show={showMoveMenu} align="start" side="top">
			<button type="button" class={buttonClass} disabled={busy || count === 0}>
				<FolderIcon className="size-4" />
				<span>{$i18n.t('Move')}</span>
			</button>
			<div slot="content">
				<DropdownMenu className="min-w-[12rem] max-h-60 overflow-y-auto scrollbar-hidden">
					{#if folderList.length === 0}
						<div class="px-2 py-1.5 text-xs text-gray-500">
							{$i18n.t('No folders yet. Create one in the sidebar first.')}
						</div>
					{:else}
						{#each folderList as folder (folder.id)}
							<button
								type="button"
								class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[0.8125rem] hover:bg-gray-100 dark:hover:bg-gray-900"
								on:click={() => moveHandler(folder.id, folder?.name ?? '')}
							>
								<FolderIcon className="size-3.5 shrink-0" />
								<span class="truncate">{folder?.name ?? $i18n.t('Folder')}</span>
							</button>
						{/each}
						<hr class="my-1 border-gray-100 dark:border-gray-800" />
					{/if}
					<button
						type="button"
						class="flex h-[1.6875rem] w-full items-center gap-2 rounded-xl px-2 text-[0.8125rem] hover:bg-gray-100 dark:hover:bg-gray-900"
						on:click={() => moveHandler(null, '')}
					>
						<XMark className="size-3.5 shrink-0" strokeWidth="2" />
						<span class="truncate">{$i18n.t('Remove from folder')}</span>
					</button>
				</DropdownMenu>
			</div>
		</Dropdown>

		{#if canExport}
			<button type="button" class={buttonClass} disabled={busy || count === 0} on:click={exportHandler}>
				<DownloadIcon className="size-4" />
				<span>{$i18n.t('Export')}</span>
			</button>
		{/if}

		{#if canDelete}
			<button
				type="button"
				class="{buttonClass} !text-red-700 dark:!text-red-400"
				disabled={busy || count === 0}
				on:click={() => (showDeleteConfirm = true)}
			>
				<TrashIcon className="size-4" />
				<span>{$i18n.t('Delete')}</span>
			</button>
		{/if}
	</div>
</div>
