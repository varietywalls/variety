#!/usr/bin/python
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (c) 2012, Peter Levi <peterlevi@peterlevi.com>
# This program is free software: you can redistribute it and/or modify it 
# under the terms of the GNU General Public License version 3, as published 
# by the Free Software Foundation.
# 
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranties of 
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along 
# with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

import sys
import os.path
import unittest
from variety.QuotesEngine import QuotesEngine

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

xml1 = """
<rss xmlns:content="http://purl.org/rss/1.0/modules/content/" version="2.0">
    <channel>
        <title>Quotes Daddy - Random quote by Albert Einstein</title>
        <link>http://www.quotesdaddy.com/</link>
        <description/>
        <pubDate>Mon, 12 Nov 2012 13:23:57 +0000</pubDate>
        <language>en</language>
        <item>
            <title>
                "We can't solve problems by using the same kind of thinking we used when we created them." - Albert Einstein
            </title>
            <link>
                http://www.quotesdaddy.com/quote/17473/albert-einstein/we-cant-solve-problems-by-using-the-same-kind-of-thinking
            </link>
            <description>
                "We can't solve problems by using the same kind of thinking we used when we created them." - Albert Einstein
            </description>
            <guid isPermalink="false">17473</guid>
            <pubDate>Mon, 12 Nov 2012 13:23:57 +0000</pubDate>
        </item>
    </channel>
</rss>
"""

class TestQuotesEngine(unittest.TestCase):
    def test_extract_quote(self):
        self.assertEqual({"quote" : u"\u201C%s\u201D" % "We can't solve problems by using the same kind of thinking we used when we created them.",
                          "author" : "Albert Einstein",
                          "link" : "http://www.quotesdaddy.com/quote/17473/albert-einstein/we-cant-solve-problems-by-using-the-same-kind-of-thinking"},
                         QuotesEngine.extract_quote(xml1))

    def test_choose_random_feed_url(self):
        class Opt:
            def __init__(self, tags, authors):
                self.quotes_tags = tags
                self.quotes_authors = authors

        skip = set()
        url = QuotesEngine.choose_random_feed_url(Opt("a,b", ""), skip)
        self.assertTrue(url.startswith("http://www.quotesdaddy.com/feed/tagged/"))
        skip.add(url)
        url = QuotesEngine.choose_random_feed_url(Opt("a,b", ""), skip)
        self.assertTrue(url.startswith("http://www.quotesdaddy.com/feed/tagged/"))
        skip.add(url)
        url = QuotesEngine.choose_random_feed_url(Opt("a,b", ""), skip)
        self.assertEquals("http://www.quotesdaddy.com/feed", url)

        skip = set()
        url = QuotesEngine.choose_random_feed_url(Opt("", "a,b"), skip)
        self.assertTrue(url.startswith("http://www.quotesdaddy.com/feed/author/"))
        skip.add(url)
        url = QuotesEngine.choose_random_feed_url(Opt("", "a,b"), skip)
        self.assertTrue(url.startswith("http://www.quotesdaddy.com/feed/author/"))
        skip.add(url)
        url = QuotesEngine.choose_random_feed_url(Opt("", "a,b"), skip)
        self.assertEquals("http://www.quotesdaddy.com/feed", url)

if __name__ == '__main__':
    unittest.main()
