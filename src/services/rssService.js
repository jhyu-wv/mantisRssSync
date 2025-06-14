const Parser = require('rss-parser');
const Logger = require('../utils/logger');

/**
 * RSS 피드 파싱 서비스
 */
class RSSService {
    constructor() {
        this.parser = new Parser({
            customFields: {
                item: ['category', 'link', 'description']
            }
        });
    }

    /**
     * RSS 피드에서 아이템 가져오기
     * @param {string} url - RSS URL
     * @returns {Promise<Array>} RSS 아이템 배열
     */
    async fetchRSSItems(url) {
        try {
            Logger.info(`Fetching RSS feed from: ${url}`);
            const feed = await this.parser.parseURL(url);

            const items = feed.items.map(item => ({
                title: item.title?.trim() || 'No Title',
                category: item.category || 'General',
                link: item.link || '',
                description: item.description || item.content || 'No description available',
                guid: item.guid || item.link || item.title,
                pubDate: item.pubDate || item.isoDate
            }));

            Logger.info(`Found ${items.length} RSS items`);
            return items;
        } catch (error) {
            Logger.error('Failed to fetch RSS feed', error);
            throw new Error(`RSS fetch failed: ${error.message}`);
        }
    }
}

module.exports = RSSService;
