const Logger = require('../utils/logger');

/**
 * 이슈 관리 서비스
 */
class IssueService {
    constructor(githubService, rssService) {
        this.github = githubService;
        this.rss = rssService;
    }

    /**
     * RSS 아이템과 기존 이슈 비교하여 새 이슈 찾기
     * @param {Array} rssItems - RSS 아이템 배열
     * @param {Array} existingIssues - 기존 이슈 배열
     * @returns {Array} 새로운 이슈 배열
     */
    findNewIssues(rssItems, existingIssues) {
        Logger.info('Comparing RSS items with existing issues');

        if (existingIssues.length === 0) {
            Logger.warn('No existing issues found. All RSS items will be created as new issues.');
            return rssItems;
        }

        const existingTitles = new Set(existingIssues.map(issue => issue.title.trim()));
        const newIssues = rssItems.filter(item => !existingTitles.has(item.title.trim()));

        Logger.info(`Found ${newIssues.length} new issues out of ${rssItems.length} RSS items`);
        return newIssues;
    }

    /**
     * 새 이슈들을 일괄 생성
     * @param {Array} newIssues - 새 이슈 배열
     * @param {Object} defaults - 기본 설정
     * @param {boolean} dryRun - 테스트 모드
     */
    async createNewIssues(newIssues, defaults, dryRun = false) {
        if (newIssues.length === 0) {
            Logger.info('No new issues to create');
            return [];
        }

        Logger.info(`${dryRun ? '[DRY RUN] ' : ''}Creating ${newIssues.length} new issues`);
        const createdIssues = [];

        for (const issueData of newIssues) {
            try {
                if (dryRun) {
                    Logger.info(`[DRY RUN] Would create issue: ${issueData.title}`);
                    Logger.debug('[DRY RUN] Issue data:', issueData);
                    continue;
                }

                const issue = await this.github.createIssue(issueData);
                createdIssues.push(issue);

                // 칸반보드에 추가
                await this.github.addIssueToProject(
                    issue.number,
                    defaults.status,
                    defaults.milestone
                );

                // API 레이트 리미트 고려하여 잠시 대기
                await this.sleep(1000);
            } catch (error) {
                Logger.error(`Failed to create issue: ${issueData.title}`, error);
                // 개별 이슈 생성 실패 시에도 계속 진행
            }
        }

        Logger.info(`${dryRun ? '[DRY RUN] ' : ''}Successfully processed ${createdIssues.length} issues`);
        return createdIssues;
    }

    /**
     * 지연 함수
     * @param {number} ms - 밀리초
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

module.exports = IssueService;
