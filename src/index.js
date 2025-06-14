const config = require('./config');
const Logger = require('./utils/logger');
const RSSService = require('./services/rssService');
const GitHubService = require('./services/githubService');
const IssueService = require('./services/issueService');

/**
 * 메인 애플리케이션 클래스
 */
class RSSToIssueApp {
    constructor() {
        this.rssService = new RSSService();
        this.githubService = new GitHubService(config);
        this.issueService = new IssueService(this.githubService, this.rssService);
    }

    /**
     * 애플리케이션 실행
     */
    async run() {
        try {
            Logger.info(`Starting RSS to Issue automation ${config.dryRun ? '(DRY RUN MODE)' : ''}`);
            Logger.info('Configuration:', {
                rssUrl: config.rss.url,
                repository: `${config.github.owner}/${config.github.repo}`,
                project: config.github.projectNumber,
                dryRun: config.dryRun
            });

            // RSS 피드 가져오기
            const rssItems = await this.rssService.fetchRSSItems(config.rss.url);

            // 기존 이슈 가져오기
            const existingIssues = await this.githubService.getExistingIssues();

            // 새 이슈 찾기
            const newIssues = this.issueService.findNewIssues(rssItems, existingIssues);

            // 새 이슈 생성
            const createdIssues = await this.issueService.createNewIssues(
                newIssues,
                config.defaults,
                config.dryRun
            );

            Logger.info('Automation completed successfully');
            Logger.info('Summary:', {
                totalRSSItems: rssItems.length,
                existingIssues: existingIssues.length,
                newIssuesFound: newIssues.length,
                issuesCreated: createdIssues.length
            });

        } catch (error) {
            Logger.error('Application failed', error);
            process.exit(1);
        }
    }
}

// 스크립트 직접 실행 시
if (require.main === module) {
    const app = new RSSToIssueApp();
    app.run();
}

module.exports = RSSToIssueApp;
