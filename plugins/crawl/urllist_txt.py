'''
urllist_txt.py

Copyright 2006 Andres Riancho

This file is part of w3af, http://w3af.org/ .

w3af is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

w3af is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with w3af; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

'''
import core.controllers.output_manager as om
import core.data.kb.knowledge_base as kb

from core.controllers.plugins.crawl_plugin import CrawlPlugin
from core.controllers.exceptions import w3afRunOnce, w3afException
from core.controllers.core_helpers.fingerprint_404 import is_404
from core.controllers.misc.decorators import runonce
from core.data.kb.info import Info


class urllist_txt(CrawlPlugin):
    '''
    Analyze the urllist.txt file and find new URLs
    :author: Andres Riancho (andres.riancho@gmail.com)
    '''

    def __init__(self):
        CrawlPlugin.__init__(self)

    @runonce(exc_class=w3afRunOnce)
    def crawl(self, fuzzable_request):
        '''
        Get the urllist.txt file and parse it.

        :param fuzzable_request: A fuzzable_request instance that contains
                                    (among other things) the URL to test.
        '''
        base_url = fuzzable_request.get_url().base_url()
        urllist_url = base_url.url_join('urllist.txt')
        http_response = self._uri_opener.GET(urllist_url, cache=True)

        if not is_404(http_response):
            if self._is_urllist_txt(base_url, http_response.get_body()):
                # Save it to the kb!
                desc = 'A urllist.txt file was found at: "%s", this file might'\
                       ' expose private URLs and requires a manual review. The'\
                       ' scanner will add all URLs listed in this files to the'\
                       ' analysis queue.'
                desc = desc % urllist_url
                
                i = Info('urllist.txt file', desc, http_response.id,
                         self.get_name())
                i.set_url(urllist_url)
                
                kb.kb.append(self, 'urllist.txt', i)
                om.out.information(i.get_desc())

            # Even in the case where it is NOT a valid urllist.txt it might be
            # the case where some URLs are present, so I'm going to extract them
            # from the file as if it is a valid urllist.txt

            url_generator = self._extract_urls_generator(base_url,
                                                         http_response.get_body())

            # Send the requests using threads:
            self.worker_pool.map(self.http_get_and_parse, url_generator)

    def _is_urllist_txt(self, base_url, body):
        '''
        :return: True if the body is a urllist.txt
        '''
        is_urllist = 5
        for line in body.split('\n'):

            line = line.strip()

            if not line.startswith('#') and line:
                try:
                    base_url.url_join(line)
                except:
                    is_urllist -= 1

        return bool(is_urllist)

    def _extract_urls_generator(self, base_url, body):
        '''
        :param body: The urllist.txt body
        @yield: a URL object from the urllist.txt body
        '''
        for line in body.split('\n'):

            line = line.strip()

            if not line.startswith('#') and line:
                try:
                    url = base_url.url_join(line)
                except:
                    pass
                else:
                    yield url

    def get_long_desc(self):
        '''
        :return: A DETAILED description of the plugin functions and features.
        '''
        return '''
        This plugin searches for the urllist.txt file, and parses it. The
        urllist.txt file is/was used by Yahoo's search engine.
        '''
