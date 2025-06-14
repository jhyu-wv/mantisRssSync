const RSSToIssueApp = require('../../src/index');
const config = require('../../src/config');
const nock = require('nock');

// 환경 변수 모킹
process.env.GITHUB_TOKEN = 'test-token';
process.env.GITHUB_OWNER = 'test-owner';
process.env.GITHUB_REPO = 'test-repo';
process.env.PROJECT_NUMBER = '1';
process.env.MANTIS_RSS_URL = 'https://example.com/rss.xml';
process.env.DRY_RUN = 'true';

describe('RSSToIssueApp Integration', () => {
    let app;

    beforeEach(() => {
        app = new RSSToIssueApp();
        nock.disableNetConnect();
    });

    afterEach(() => {
        nock.cleanAll();
        nock.enableNetConnect();
    });

    it('should run complete workflow in dry run mode', async () => {
        // Mock RSS feed
        const mockRSSXML = `<?xml version="1.0" encoding="UTF-8"?>
      <rss version="2.0">
        <channel>
          <title>Test RSS</title>
          <item>
            <title>Test Issue</title>
            <description>Test description</description>
            <link>https://example.com/issue</link>
            <category>Bug</category>
          </item>
        </channel>
      </rss>`;

        nock('https://example.com')
            .get('/rss.xml')
            .reply(200, mockRSSXML);

        // Mock GitHub API
        nock('https://api.github.com')
            .get('/repos/test-owner/test-repo/issues')
            .query({ state: 'all', per_page: 100 })
            .reply(200, []);

        // 실행 시 오류가 발생하지 않고 완료되는지 확인
        await expect(app.run()).resolves.not.toThrow();
    });
});
