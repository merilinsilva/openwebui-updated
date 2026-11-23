import { describe, expect, it } from 'vitest';
import JSZip from 'jszip';
import { readSkillHeader, skillFromMarkdown, skillsFromZip } from './skillFiles';

const SKILL_MD = `---
name: sharepoint-search
description: "Find and read Weidmann SharePoint documents: policies, forms, manuals."
---

# SharePoint document search

One empty search result is not an answer.
`;

describe('skill files (CHOn T12)', () => {
	it('reads the YAML header, including colons in quoted values', () => {
		expect(readSkillHeader(SKILL_MD)).toEqual({
			name: 'sharepoint-search',
			description: 'Find and read Weidmann SharePoint documents: policies, forms, manuals.'
		});
	});

	it('builds id, display name and keeps the whole file as content', () => {
		const skill = skillFromMarkdown(SKILL_MD, 'fallback', 'SKILL.md');
		expect(skill.id).toBe('sharepoint-search');
		expect(skill.name.length).toBeGreaterThan(0);
		expect(skill.content).toBe(SKILL_MD);
	});

	it('falls back to the file name when there is no header', () => {
		const skill = skillFromMarkdown('# Just text', 'meeting-prep');
		expect(skill.id).toBe('meeting-prep');
		expect(skill.description).toBe('');
	});

	it('reads one skill per SKILL.md in a zip and lists ignored files', async () => {
		const zip = new JSZip();
		zip.file('sharepoint-search/SKILL.md', SKILL_MD);
		zip.file('sharepoint-search/reference/rules.md', '# rules');
		zip.file('kata-coach/SKILL.md', '---\nname: kata-coach\ndescription: Toyota Kata coach\n---\nBody');
		zip.file('__MACOSX/sharepoint-search/._SKILL.md', 'junk');
		const data = await zip.generateAsync({ type: 'uint8array' });

		const skills = await skillsFromZip(data, 'skills.zip');
		expect(skills.map((s) => s.id).sort()).toEqual(['kata-coach', 'sharepoint-search']);
		const sp = skills.find((s) => s.id === 'sharepoint-search')!;
		expect(sp.ignoredFiles).toEqual(['sharepoint-search/reference/rules.md']);
	});

	it('uses the folder name when SKILL.md has no name', async () => {
		const zip = new JSZip();
		zip.file('bee360-review/SKILL.md', 'No header here');
		const skills = await skillsFromZip(await zip.generateAsync({ type: 'uint8array' }));
		expect(skills[0].id).toBe('bee360-review');
	});
});
