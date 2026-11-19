// Shared wording for file upload status, used by chat attachments and knowledge-base uploads.

export type UploadState = 'queued' | 'uploading' | 'reading' | 'ready' | 'failed';

type Translate = (key: string, options?: Record<string, unknown>) => string;

export type UploadErrorContext = 'chat' | 'knowledge';

// Turns a raw browser/server error into "what happened" and "what to do".
export const describeUploadError = (
	t: Translate,
	raw: string = '',
	{ maxSizeMb = null, context = 'chat' }: { maxSizeMb?: number | null; context?: UploadErrorContext } = {}
): { cause: string; fix: string } => {
	const e = `${raw ?? ''}`.toLowerCase();

	if (e.includes('content provided is empty') || e.includes('no text')) {
		return {
			cause: t('No text found. This looks like a scanned image.'),
			fix: t('Upload a searchable PDF (export it again, or run OCR on it first).')
		};
	}
	if (e.includes('embedding model') || e.includes('embedding_engine')) {
		return {
			cause: t("CHOn can't index documents right now: no embedding model is set up."),
			fix: t(
				'This is a server setting, not a problem with your file. Contact the CHOn team (Admin Settings > Documents).'
			)
		};
	}
	if (e.includes('duplicate content')) {
		return context === 'knowledge'
			? {
					cause: t('This file is already in the knowledge base.'),
					fix: t('Nothing to do. Remove the old copy first if you want to replace it.')
				}
			: {
					cause: t('This file is already attached.'),
					fix: t('Nothing to do. Remove this copy.')
				};
	}
	if (e.includes('vision') || e.includes('image inputs')) {
		return {
			cause: t("The selected model can't read images."),
			fix: t('Pick a model that supports images, or remove the image.')
		};
	}
	if (e.includes('not supported') || e.includes('unsupported')) {
		return {
			cause: t("CHOn can't read this file type."),
			fix: t('Save it as PDF, Word, PowerPoint, Excel or text and upload it again.')
		};
	}
	if (e.includes('empty file') || e.includes('file is empty')) {
		return {
			cause: t('The file is empty.'),
			fix: t('Check that you picked the right file.')
		};
	}
	if (e.includes('size') || e.includes('too large') || e.includes('413')) {
		return {
			cause: t('The file is too large.'),
			fix: maxSizeMb
				? t('Split or compress it to under {{size}} MB.', { size: maxSizeMb })
				: t('Split or compress it, then upload the parts.')
		};
	}
	if (e.includes('timeout') || e.includes('timed out')) {
		return {
			cause: t('Reading the file took too long.'),
			fix: t('Try again, or split it into smaller files.')
		};
	}
	if (e.includes('network') || e.includes('failed to fetch')) {
		return {
			cause: t('The upload was interrupted.'),
			fix: t('Check your connection and try again.')
		};
	}
	if (e.includes('permission') || e.includes('access') || e.includes('401') || e.includes('403')) {
		return context === 'knowledge'
			? {
					cause: t("You don't have permission to add files here."),
					fix: t('Ask the owner of this knowledge base for edit access.')
				}
			: {
					cause: t("You don't have permission to upload files."),
					fix: t('Ask the CHOn team to enable file uploads for your account.')
				};
	}
	if (e.includes('removed while reading') || e.includes('not_found')) {
		return {
			cause: t('The file was removed while it was being read.'),
			fix: t('Upload it again.')
		};
	}
	return {
		cause: raw ? `${raw}` : t('The file could not be read.'),
		fix: t('Try again. If it keeps failing, contact the CHOn team.')
	};
};

// Label and colours for a status badge.
export const uploadStateBadge = (
	t: Translate,
	state: UploadState,
	progress: number | null = null
): { label: string; cls: string } =>
	({
		queued: {
			label: t('Queued'),
			cls: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300'
		},
		uploading: {
			label: `${t('Uploading')} ${progress ?? 0}%`,
			cls: 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300'
		},
		reading: {
			label: t('Reading'),
			cls: 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300'
		},
		ready: {
			label: `✓ ${t('Ready')}`,
			cls: 'bg-green-50 text-green-700 dark:bg-green-950/40 dark:text-green-300'
		},
		failed: {
			label: `✕ ${t('Failed')}`,
			cls: 'bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300'
		}
	})[state];
