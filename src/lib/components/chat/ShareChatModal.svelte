<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { models, config, user } from '$lib/stores';

	import { toast } from 'svelte-sonner';
	import {
		deleteSharedChatById,
		getChatById,
		shareChatById,
		getChatAccessGrants,
		updateChatAccessGrants
	} from '$lib/apis/chats';
	import { copyToClipboard } from '$lib/utils';

	import Modal from '../common/Modal.svelte';
	import Link from '../icons/Link.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import AccessControl from '$lib/components/workspace/common/AccessControl.svelte';

	export let chatId;

	let chat = null;
	let shareUrl = null;
	let accessGrants: any[] = [];
	const i18n = getContext('i18n');

	const shareLocalChat = async () => {
		const _chat = chat;

		const sharedChat = await shareChatById(localStorage.token, chatId);
		shareUrl = `${window.location.origin}/s/${sharedChat.share_id}`;
		console.log(shareUrl);
		chat = await getChatById(localStorage.token, chatId);

		return shareUrl;
	};

	const shareChat = async () => {
		const _chat = chat.chat;
		console.log('share', _chat);

		// LICENSE covers this Open WebUI Community wordmark.
		// Do not alter, remove, obscure, or replace it except as LICENSE permits:
		// https://docs.openwebui.com/license.
		toast.success($i18n.t('Redirecting you to Open WebUI Community'));
		const url = 'https://openwebui.com';
		// const url = 'http://localhost:5173';

		const tab = await window.open(`${url}/chats/upload`, '_blank');
		window.addEventListener(
			'message',
			(event) => {
				if (event.origin !== url) return;
				if (event.data === 'loaded') {
					tab.postMessage(
						JSON.stringify({
							chat: _chat,
							models: $models.filter((m) => _chat.models.includes(m.id))
						}),
						'*'
					);
				}
			},
			false
		);
	};

	const loadAccessGrants = async () => {
		if (!chatId) return;
		try {
			accessGrants = (await getChatAccessGrants(localStorage.token, chatId)) ?? [];
		} catch (e) {
			console.error('Failed to load access grants', e);
			accessGrants = [];
		}
	};

	const saveAccessGrants = async () => {
		try {
			await updateChatAccessGrants(localStorage.token, chatId, accessGrants);
			toast.success($i18n.t('Access updated'));
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	export let show = false;

	$: linkUrl = chat?.share_id ? `${window.location.origin}/s/${chat.share_id}` : '';

	const copyExistingLink = async () => {
		if (await copyToClipboard(linkUrl)) {
			toast.success($i18n.t('Link copied'));
		}
	};

	// Creates the link, or refreshes the snapshot to the latest messages, then copies it.
	const createOrUpdateLink = async () => {
		const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);

		if (isSafari) {
			// Safari only allows clipboard writes started directly by the click.
			const getUrlPromise = async () => {
				const url = await shareLocalChat();
				return new Blob([url], { type: 'text/plain' });
			};

			navigator.clipboard
				.write([
					new ClipboardItem({
						'text/plain': getUrlPromise()
					})
				])
				.catch((error) => {
					console.error('Could not copy text: ', error);
				});
		} else {
			copyToClipboard(await shareLocalChat());
		}

		toast.success($i18n.t('Copied shared chat URL to clipboard!'));
	};

	const stopSharing = async () => {
		const res = await deleteSharedChatById(localStorage.token, chatId).catch((e) => {
			toast.error(`${e}`);
			return null;
		});
		if (res) {
			chat = await getChatById(localStorage.token, chatId);
			toast.success($i18n.t('Link removed. People with the old link can no longer open it.'));
		}
	};

	const isDifferentChat = (_chat) => {
		if (!chat) {
			return true;
		}
		if (!_chat) {
			return false;
		}
		return chat.id !== _chat.id || chat.share_id !== _chat.share_id;
	};

	$: if (show) {
		(async () => {
			if (chatId) {
				const _chat = await getChatById(localStorage.token, chatId);
				if (isDifferentChat(_chat)) {
					chat = _chat;
				}
				await loadAccessGrants();
			} else {
				chat = null;
				accessGrants = [];
			}
		})();
	}
</script>

<Modal bind:show size="sm" className="bg-white dark:bg-gray-900 rounded-2xl">
	<div class="px-5 pt-4 pb-4 text-gray-900 dark:text-gray-100">
		<div class="flex items-start justify-between gap-3">
			<div class="min-w-0">
				<h2 class="text-base font-semibold">{$i18n.t('Share chat')}</h2>
				{#if chat?.chat?.title}
					<p class="mt-0.5 truncate text-xs text-gray-500">{chat.chat.title}</p>
				{/if}
			</div>
			<button
				class="shrink-0 rounded-lg p-1 text-gray-500 transition hover:bg-gray-100 hover:text-gray-800 dark:hover:bg-gray-800 dark:hover:text-gray-200"
				aria-label={$i18n.t('Close')}
				on:click={() => {
					show = false;
				}}
			>
				<XMark className="size-4" />
			</button>
		</div>

		{#if chat}
			{#if !chat.share_id}
				<p class="mt-3 text-sm text-gray-600 dark:text-gray-400">
					{$i18n.t(
						"Creates a link to a snapshot of this chat. Messages you send afterwards aren't included."
					)}
				</p>
			{:else}
				<div class="mt-4 flex flex-col gap-1.5">
					<label for="share-chat-link" class="text-sm font-semibold">{$i18n.t('Link')}</label>
					<div class="flex gap-2">
						<input
							id="share-chat-link"
							class="min-w-0 flex-1 truncate rounded-lg border border-gray-300 bg-gray-50 px-3 py-2 font-mono text-xs text-gray-700 outline-hidden dark:border-gray-700 dark:bg-white/[0.03] dark:text-gray-300"
							value={linkUrl}
							readonly
							on:focus={(e) => e.currentTarget.select()}
						/>
						<button
							type="button"
							class="flex shrink-0 items-center gap-1.5 rounded-lg bg-black px-3.5 py-2 text-sm font-semibold text-white transition hover:bg-gray-800 dark:bg-white dark:text-black dark:hover:bg-gray-200"
							on:click={copyExistingLink}
						>
							<Link className="size-3.5" />
							{$i18n.t('Copy')}
						</button>
					</div>
					<p class="text-xs text-gray-500">
						{$i18n.t('The link shows the chat as it was when the link was last updated.')}
					</p>
					<div class="flex flex-wrap gap-x-4 gap-y-1 text-xs">
						<button
							type="button"
							class="text-gray-700 underline hover:text-gray-900 dark:text-gray-300 dark:hover:text-gray-100"
							on:click={() => createOrUpdateLink()}
						>
							{$i18n.t('Update to latest messages')}
						</button>
						<button
							type="button"
							class="text-red-600 underline hover:text-red-700 dark:text-red-400"
							on:click={stopSharing}
						>
							{$i18n.t('Stop sharing')}
						</button>
					</div>
				</div>

				<div class="mt-4">
					<AccessControl
						bind:accessGrants
						accessRoles={['read']}
						sharePublic={$user?.permissions?.sharing?.public_chats || $user?.role === 'admin'}
						shareOpen={$user?.permissions?.sharing?.open_chats || $user?.role === 'admin'}
						shareUsers={($user?.permissions?.access_grants?.allow_users ?? true) ||
							$user?.role === 'admin'}
						onChange={saveAccessGrants}
					/>
				</div>
			{/if}

			<div class="mt-5 flex flex-wrap items-center justify-end gap-2">
				{#if $config?.features.enable_community_sharing}
					<button
						class="mr-auto rounded-lg border border-gray-300 px-3.5 py-2 text-sm font-medium transition hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800"
						type="button"
						on:click={() => {
							shareChat();
						}}
					>
						<!-- LICENSE covers this Open WebUI Community wordmark.
						Do not alter, remove, obscure, or replace it except as LICENSE permits:
						https://docs.openwebui.com/license. -->
						{$i18n.t('Share to Open WebUI Community')}
					</button>
				{/if}

				{#if chat.share_id}
					<button
						type="button"
						class="rounded-lg bg-black px-4 py-2 text-sm font-semibold text-white transition hover:bg-gray-800 dark:bg-white dark:text-black dark:hover:bg-gray-200"
						on:click={() => (show = false)}
					>
						{$i18n.t('Done')}
					</button>
				{:else}
					<button
						type="button"
						class="rounded-lg border border-gray-300 px-3.5 py-2 text-sm font-medium transition hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800"
						on:click={() => (show = false)}
					>
						{$i18n.t('Cancel')}
					</button>
					<button
						class="flex items-center gap-1.5 rounded-lg bg-black px-4 py-2 text-sm font-semibold text-white transition hover:bg-gray-800 dark:bg-white dark:text-black dark:hover:bg-gray-200"
						type="button"
						id="copy-and-share-chat-button"
						on:click={() => createOrUpdateLink()}
					>
						<Link className="size-3.5" />
						{$i18n.t('Create and copy link')}
					</button>
				{/if}
			</div>
		{:else}
			<div class="flex justify-center py-8"><Spinner className="size-5" /></div>
		{/if}
	</div>
</Modal>
