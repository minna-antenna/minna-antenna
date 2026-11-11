"""Publisher provenance and honest scoring, independent of the live network."""
import datetime as dt
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import update_news as news

class PublisherTests(unittest.TestCase):
    now=dt.datetime(2026,11,10,12,tzinfo=dt.timezone.utc)

    def feed(self,name,title='同じ見出し',publisher=None,source_url=None):
        rss=ET.Element('rss');item=ET.SubElement(ET.SubElement(rss,'channel'),'item')
        for key,value in {'title':title,'link':'https://example.com/news','pubDate':'Tue, 10 Nov 2026 11:00:00 GMT','description':'本文を取り込んではいけない','{http://purl.org/rss/1.0/modules/content/}encoded':'本文全体を取り込んではいけない'}.items():ET.SubElement(item,key).text=value
        if publisher:ET.SubElement(item,'source',{'url':source_url} if source_url else {}).text=publisher
        return news.parse_rss(ET.tostring(rss),name,'ニュース',self.now)

    def test_same_publisher_multiple_feeds_has_no_bonus_and_keeps_provenance(self):
        rows=self.feed('NHK総合')+self.feed('NHK社会')
        item=news.build(rows,self.now)[0];r=item['reason']
        self.assertEqual(r['identified_publisher_count'],1)
        self.assertEqual(r['additional_publisher_points'],0)
        self.assertEqual(r['feed_names'],['NHK社会','NHK総合'])
        self.assertEqual(item['score'],r['freshness_points'])

    def test_google_source_maps_to_nhk_without_counting_google_as_publisher(self):
        rows=self.feed('NHK総合')+self.feed('Google ニュース・政治','同じ見出し - NHK NEWS WEB','NHK NEWS WEB','https://news.web.nhk')
        item=news.build(rows,self.now)[0]
        self.assertEqual(item['reason']['identified_publisher_count'],1)
        self.assertEqual(item['reason']['additional_publisher_points'],0)
        self.assertEqual(rows[-1]['provider'],'Google News')
        self.assertEqual(rows[-1]['publisher_id'],'nhk')

    def test_distinct_configured_publishers_get_one_bonus(self):
        item=news.build(self.feed('NHK総合')+self.feed('NHK社会')+self.feed('BBC News 日本語'),self.now)[0]
        self.assertEqual(item['reason']['additional_publisher_points'],15)
        self.assertEqual({p['id'] for p in item['reason']['publishers']},{'nhk','bbc'})

    def test_unknown_sources_never_inflate_identified_publisher_count(self):
        rows=self.feed('Google ニュース・政治','同じ見出し - 未登録A')+self.feed('Google ニュース・株','同じ見出し - 未登録B')
        item=news.build(rows,self.now)[0]
        self.assertEqual(item['reason']['identified_publisher_count'],0)
        self.assertEqual(item['reason']['additional_publisher_points'],0)
        self.assertEqual(item['reason']['unidentified_source_names'],['未登録A','未登録B'])

    def test_unmapped_source_host_cannot_claim_nhk_alias(self):
        row=self.feed('Google ニュース・政治','同じ見出し - NHK','NHK','https://unrelated.example')[0]
        self.assertIsNone(row['publisher_id'])

    def test_snippets_fulltext_and_original_title_not_published(self):
        item=news.build(self.feed('NHK総合'),self.now)[0]
        self.assertFalse({'description','content','body','original_title'} & item.keys())
        self.assertNotIn('本文を取り込んではいけない',str(item))

    def test_long_and_bracketed_headlines_do_not_collide(self):
        self.assertNotEqual(news.normalize('同じ'*70+'A'),news.normalize('同じ'*70+'B'))
        self.assertNotEqual(news.normalize('【速報】市場'),news.normalize('【訂正】市場'))
        self.assertEqual(news.normalize('Ａ Ｂ！'),news.normalize('AB'))

    def test_home_has_all_original_articles_before_external_news(self):
        root=Path(__file__).resolve().parents[1]
        text=(root/'index.html').read_text()
        self.assertLess(text.index('id="original-articles"'),text.index('id="news"'))
        self.assertNotIn('adsbygoogle',text)
        self.assertIn('7 */3 * * *',(root/'.github/workflows/news.yml').read_text())
