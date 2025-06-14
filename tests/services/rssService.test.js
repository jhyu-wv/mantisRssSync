const RSSService = require('../../src/services/rssService');
const nock = require('nock');

describe('RSSService', () => {
    let rssService;

    beforeEach(() => {
        rssService = new RSSService();
    });

    afterEach(() => {
        nock.cleanAll();
    });

    describe('fetchRSSItems', () => {
        it('should fetch and parse RSS items successfully', async () => {
            const mockRSSXML = `<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <title>Test RSS</title>
            <item>
              <title>Test Item 1</title>
              <description>Test description 1</description>
              <link>https://example.com/1</link>
              <category>Bug</category>
              <guid>item-1</guid>
            </item>
            <item>
              <title>Test Item 2</title>
              <description>Test description 2</description>
              <link>https://example.com/2</link>
              <category>Feature</category>
              <guid>item-2</guid>
            </item>
          </channel>
        </rss>`;

            nock('https://example.com')
                .get('/rss.xml')
                .reply(200, mockRSSXML, { 'Content-Type': 'application/rss+xml' });

            const items = await rssService.fetchRSSItems('https://example.com/rss.xml');

            expect(items).toHaveLength(2);
            expect(items[0]).toEqual({
                title: 'Test Item 1',
                category: 'Bug',
                link: 'https://example.com/1',
                description: 'Test description 1',
                guid: 'item-1',
                pubDate: undefined
            });
        });

        it('should handle RSS fetch errors', async () => {
            nock('https://example.com')
                .get('/rss.xml')
                .reply(404);

            await expect(rssService.fetchRSSItems('https://example.com/rss.xml'))
                .rejects.toThrow('RSS fetch failed');
        });

        it('should handle missing fields gracefully', async () => {
            const mockRSSXML = `<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
          <channel>
            <title>Test RSS</title>
            <item>
              <title>Test Item</title>
            </item>
          </channel>
        </rss>`;

            nock('https://example.com')
                .get('/rss.xml')
                .reply(200, mockRSSXML, { 'Content-Type': 'application/rss+xml' });

            const items = await rssService.fetchRSSItems('https://example.com/rss.xml');

            expect(items[0]).toEqual({
                title: 'Test Item',
                category: 'General',
                link: '',
                description: 'No description available',
                guid: 'Test Item',
                pubDate: undefined
            });
        });
    });
});
