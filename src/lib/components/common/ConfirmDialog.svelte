<script lang="ts">
	import DOMPurify from 'dompurify';

	import { onMount, getContext, createEventDispatcher, onDestroy, tick } from 'svelte';
	import * as FocusTrap from 'focus-trap';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import { fade } from 'svelte/transition';
	import { flyAndScale } from '$lib/utils/transitions';
	import { marked } from 'marked';
	import SensitiveInput from './SensitiveInput.svelte';
	import NativeSelect from './NativeSelect.svelte';

	export let title = '';
	export let message = '';

	export let cancelLabel = $i18n.t('Cancel');
	export let confirmLabel = $i18n.t('Confirm');

	export let onConfirm = () => {};

	export let input = false;
	export let inputPlaceholder = '';
	export let inputValue = '';
	export let inputType = '';
	export let inputOptions: ({ label?: string; value: string } | string)[] = [];

	let _inputValue = inputValue;

	export let show = false;

	// CHOn: 'danger' shows a warning icon and a red action button. 'auto' (default) treats
	// titles starting with Delete / Remove / Clear / Reset as dangerous.
	export let variant: 'auto' | 'default' | 'danger' = 'auto';

	const DEFAULT_CONFIRM_LABEL = $i18n.t('Confirm');
	$: isDanger =
		variant === 'danger' ||
		(variant === 'auto' && /^\s*(delete|remove|clear|reset)\b/i.test(title ?? ''));
	// A dangerous dialog that kept the generic "Confirm" label says what it does instead.
	$: actionLabel =
		isDanger && confirmLabel === DEFAULT_CONFIRM_LABEL
			? /^\s*reset/i.test(title ?? '')
				? $i18n.t('Reset')
				: /^\s*clear/i.test(title ?? '')
					? $i18n.t('Clear')
					: $i18n.t('Delete')
			: confirmLabel;

	$: if (show) {
		init();
	}

	let modalElement = null;
	let mounted = false;

	let focusTrap: FocusTrap.FocusTrap | null = null;

	const init = () => {
		_inputValue = inputValue;
	};

	const handleKeyDown = (event: KeyboardEvent) => {
		if (event.key === 'Escape') {
			cancelHandler();
		}

		if (event.key === 'Enter') {
			// let the focused control act on Enter itself
			const target = event.target;
			if (target instanceof Element && target.closest('a, button, textarea')) {
				return;
			}

			event.preventDefault();
			event.stopPropagation();
			confirmHandler();
		}
	};

	const confirmHandler = async () => {
		show = false;
		await tick();
		await onConfirm();
		dispatch('confirm', _inputValue);
	};

	const cancelHandler = () => {
		show = false;
		dispatch('cancel');
	};

	onMount(() => {
		mounted = true;
	});

	$: if (mounted) {
		if (show && modalElement) {
			document.body.appendChild(modalElement);
			focusTrap = FocusTrap.createFocusTrap(modalElement);
			focusTrap.activate();

			window.addEventListener('keydown', handleKeyDown);
			document.body.style.overflow = 'hidden';
		} else if (modalElement) {
			focusTrap.deactivate();

			window.removeEventListener('keydown', handleKeyDown);
			document.body.removeChild(modalElement);

			document.body.style.overflow = 'unset';
		}
	}

	onDestroy(() => {
		show = false;
		window.removeEventListener('keydown', handleKeyDown);
		if (focusTrap) {
			focusTrap.deactivate();
		}
		if (modalElement) {
			document.body.removeChild(modalElement);
		}
	});
</script>


{#if show}
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		bind:this={modalElement}
		class=" fixed top-0 right-0 left-0 bottom-0 bg-black/45 dark:bg-black/60 w-full h-screen max-h-[100dvh] flex justify-center z-99999999 overflow-hidden overscroll-contain"
		in:fade={{ duration: 10 }}
		on:mousedown={() => {
			cancelHandler();
		}}
	>
		<div
			role="alertdialog"
			aria-modal="true"
			aria-label={title !== '' ? title : $i18n.t('Confirm your action')}
			tabindex="-1"
			class="m-auto mx-2 w-[28rem] max-w-full max-h-[100dvh] rounded-2xl border border-white bg-white shadow-3xl dark:border-gray-850 dark:bg-gray-900"
			in:flyAndScale
			on:mousedown={(e) => {
				e.stopPropagation();
			}}
		>
			<div class="flex flex-col px-5 pt-5 pb-4 text-gray-900 dark:text-gray-100">
				<div class="flex items-start gap-3">
					{#if isDanger}
						<div
							class="flex size-9 shrink-0 items-center justify-center rounded-full bg-red-50 text-red-600 dark:bg-red-950/40 dark:text-red-400"
							aria-hidden="true"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="2"
								stroke="currentColor"
								class="size-5"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
								/>
							</svg>
						</div>
					{/if}

					<div class="min-w-0 flex-1">
						<h2 class="text-base font-semibold">
							{#if title !== ''}
								{title}
							{:else}
								{$i18n.t('Confirm your action')}
							{/if}
						</h2>

						<div class="mt-1.5">
							<slot>
								<div class="flex-1 text-sm text-gray-600 dark:text-gray-400">
									{#if message !== ''}
										{@const html = DOMPurify.sanitize(marked.parse(message))}
										{@html html}
									{:else}
										{$i18n.t('This action cannot be undone. Do you wish to continue?')}
									{/if}

									{#if input}
										{#if inputType === 'password'}
											<div
												class="mt-3 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus-within:border-gray-500 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
											>
												<SensitiveInput
													id="event-confirm-input"
													placeholder={inputPlaceholder
														? inputPlaceholder
														: $i18n.t('Enter your message')}
													bind:value={_inputValue}
													required={true}
												/>
											</div>
										{:else if inputType === 'select' && inputOptions.length}
											<NativeSelect
												className="mt-3 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-hidden focus:border-gray-500 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
												bind:value={_inputValue}
												options={inputOptions}
												placeholder={inputPlaceholder ? inputPlaceholder : $i18n.t('Select an option')}
												required
											/>
										{:else}
											<textarea
												bind:value={_inputValue}
												aria-label={inputPlaceholder ? inputPlaceholder : $i18n.t('Enter your message')}
												placeholder={inputPlaceholder ? inputPlaceholder : $i18n.t('Enter your message')}
												class="mt-3 w-full resize-none rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-hidden placeholder:text-gray-400 focus:border-gray-500 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
												rows="3"
												required
											/>
										{/if}
									{/if}
								</div>
							</slot>
						</div>
					</div>
				</div>

				<div class="mt-5 flex justify-end gap-2">
					<button
						class="rounded-lg border border-gray-300 px-3.5 py-2 text-sm font-medium transition hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800"
						on:click={() => {
							cancelHandler();
						}}
						type="button"
					>
						{cancelLabel}
					</button>
					<button
						class="rounded-lg px-4 py-2 text-sm font-semibold transition {isDanger
							? 'bg-red-600 text-white hover:bg-red-700 dark:bg-red-600 dark:hover:bg-red-500'
							: 'bg-black text-white hover:bg-gray-800 dark:bg-white dark:text-black dark:hover:bg-gray-200'}"
						on:click={() => {
							confirmHandler();
						}}
						type="button"
					>
						{actionLabel}
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}

<style>
	.modal-content {
		animation: scaleUp 0.1s ease-out forwards;
	}

	@keyframes scaleUp {
		from {
			transform: scale(0.985);
			opacity: 0;
		}
		to {
			transform: scale(1);
			opacity: 1;
		}
	}
</style>
