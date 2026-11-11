"""Verify the paused site cannot fetch or publish the saved headline snapshot."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]

class RssPauseTests(unittest.TestCase):
    def test_no_schedule_and_dispatch_job_is_disabled(self):
        workflow=(ROOT/'.github/workflows/news.yml').read_text()
        self.assertNotIn('schedule:',workflow)
        self.assertNotIn('cron:',workflow)
        self.assertIn('if: ${{ false }}',workflow)
        self.assertIn('workflow_dispatch:',workflow)
        self.assertTrue((ROOT/'scripts/update_news.py').is_file())
        self.assertIn('function proof',(ROOT/'scripts/rss-ui.fragment.html').read_text())

    def test_paused_source_json_has_no_news(self):
        data=json.loads((ROOT/'data/news.json').read_text())
        self.assertEqual(data['status'],'paused')
        self.assertEqual(data['articles'],[])
        self.assertEqual(data['feed_success'],[])
        self.assertIsNone(data['generated_at'])

    def test_actual_pages_staging_excludes_news_and_cleans_old_artifact(self):
        workflow=(ROOT/'.github/workflows/pages.yml').read_text()
        self.assertNotIn("'Update news RSS'",workflow)
        block=re.search(r'      - name: Stage public files only\n        run: \|\n(.*?)(?=      - uses:)',workflow,re.S)[1]
        command='\n'.join(line[10:] for line in block.splitlines())
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name in ('index.html','about.html','privacy.html','contact.html','sitemap.xml','robots.txt','googleb899a57e1737e8bb.html'):
                shutil.copy(ROOT/name,root/name)
            shutil.copytree(ROOT/'articles',root/'articles')
            (root/'data').mkdir();(root/'data/news.json').write_text('OLD HEADLINE')
            (root/'_site/data').mkdir(parents=True);(root/'_site/data/news.json').write_text('STALE HEADLINE')
            subprocess.run(['bash','-eu','-c',command],cwd=root,check=True)
            self.assertFalse((root/'_site/data/news.json').exists())
            self.assertEqual(len(list((root/'_site/articles').glob('*.html'))),len(list((ROOT/'articles').glob('*.html'))))
            self.assertNotIn('fetch(', (root/'_site/index.html').read_text())
            self.assertFalse((root/'_site/scripts').exists())
