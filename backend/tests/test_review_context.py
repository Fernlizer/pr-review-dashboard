import re
import unittest
from services.review_context import build_focused_context


class FocusedContextTests(unittest.TestCase):
    def file(self,path,source):return {'path':path,'change_type':'edit','src_content':source}

    def test_small_pr_retains_complete_source_and_existing_markers(self):
        text=build_focused_context([self.file('/a.ts','const a=1;\nreturn a;')],{'/a.ts':{2}})
        self.assertIn('L   1:       const a=1;',text)
        self.assertIn('L   2:[NEW] return a;',text)
        self.assertNotIn('omitted',text)

    def test_large_file_includes_late_changed_lines_instead_of_only_prefix(self):
        source='\n'.join(f'const item{i} = "'+('x'*70)+'";' for i in range(1500))
        files=[self.file('/large.ts',source)];lines={'/large.ts':{4,750,1499}}
        text=build_focused_context(files,lines)
        self.assertLessEqual(len(text),28000)
        for number in lines['/large.ts']:self.assertIn(f'L{number:4d}:[NEW]',text)
        self.assertIn('omitted; full source available via dashboard_context',text)
        self.assertEqual(files[0]['src_content'],source)

    def test_all_changed_files_keep_their_changed_lines(self):
        files=[self.file(f'/{i}.ts','\n'.join('unchanged '+('x'*100) for _ in range(400))) for i in range(24)]
        text=build_focused_context(files,{f['path']:{300} for f in files})
        self.assertEqual(text.count('L 300:[NEW]'),24)
        for f in files:self.assertIn('FILE: '+f['path'],text)

    def test_adjacent_guard_is_included_and_large_omissions_are_explicit(self):
        source=['// '+('x'*80) for _ in range(1000)]
        source[499]='if (!user) return null;';source[500]='return user.name;'
        text=build_focused_context([self.file('/a.ts','\n'.join(source))],{'/a.ts':{501}})
        self.assertIn('if (!user) return null;',text)
        self.assertIn('L 501:[NEW] return user.name;',text)
        self.assertIn('full source available',text)

    def test_oversized_essential_changes_use_original_renderer_fallback(self):
        source='\n'.join('changed '+('x'*500) for _ in range(100))
        self.assertIsNone(build_focused_context([self.file('/a.ts',source)],{'/a.ts':set(range(1,101))}))

    def test_empty_and_removed_head_lines_are_handled_without_invented_markers(self):
        self.assertEqual(build_focused_context([],{}),'')
        text=build_focused_context([self.file('/a.ts','const safe=1;')],{'/a.ts':set()})
        self.assertNotIn('[NEW]',text)
        self.assertIn('const safe=1;',text)


class PromptCompatibilityTests(unittest.IsolatedAsyncioTestCase):
    async def compare_modes(self,source,changed):
        from unittest.mock import AsyncMock,patch
        from config import settings
        from services import llm_reviewer as reviewer
        prompts=[]
        for mode in (False,True):
            with patch.multiple(settings,LLM_BACKEND='hermes',HERMES_REQUIRE_TOOLS=True,HERMES_BATCH_WORKFLOW=mode), patch.object(
                reviewer,'_call_llm',new=AsyncMock(return_value='[]')
            ) as call:
                await reviewer.review_pr_with_llm('test','author','feature','main',
                    [{'path':'/a.ts','change_type':'edit','src_content':source,'tgt_content':source}],{'/a.ts':changed})
            prompts.append(call.call_args.args[0])
        return prompts

    async def test_small_pr_prompt_is_identical_to_original(self):
        old,new=await self.compare_modes('if (!user) return null;\nreturn user.name;', {2})
        self.assertEqual(old,new)

    async def test_essential_changes_over_budget_keep_original_prompt(self):
        source='\n'.join('changed '+('x'*500) for _ in range(100))
        old,new=await self.compare_modes(source,set(range(1,101)))
        self.assertEqual(old,new)
