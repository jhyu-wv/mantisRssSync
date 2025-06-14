const { Octokit } = require('@octokit/rest');
const Logger = require('../utils/logger');

/**
 * GitHub API 서비스
 */
class GitHubService {
    constructor(config) {
        this.octokit = new Octokit({
            auth: config.github.token,
        });
        this.owner = config.github.owner;
        this.repo = config.github.repo;
        this.projectNumber = config.github.projectNumber;
    }

    /**
     * 기존 이슈 목록 가져오기
     * @returns {Promise<Array>} 기존 이슈 배열
     */
    async getExistingIssues() {
        try {
            Logger.info('Fetching existing issues from repository');

            const { data: issues } = await this.octokit.rest.issues.listForRepo({
                owner: this.owner,
                repo: this.repo,
                state: 'all',
                per_page: 100
            });

            Logger.info(`Found ${issues.length} existing issues`);
            return issues;
        } catch (error) {
            Logger.error('Failed to fetch existing issues', error);
            throw new Error(`GitHub API error: ${error.message}`);
        }
    }

    /**
     * 새 이슈 생성
     * @param {Object} issueData - 이슈 데이터
     * @returns {Promise<Object>} 생성된 이슈
     */
    async createIssue(issueData) {
        try {
            Logger.info(`Creating issue: ${issueData.title}`);

            const { data: issue } = await this.octokit.rest.issues.create({
                owner: this.owner,
                repo: this.repo,
                title: issueData.title,
                body: this.formatIssueBody(issueData),
                labels: issueData.category ? [issueData.category] : []
            });

            Logger.info(`Created issue #${issue.number}: ${issue.title}`);
            return issue;
        } catch (error) {
            Logger.error(`Failed to create issue: ${issueData.title}`, error);
            throw new Error(`Issue creation failed: ${error.message}`);
        }
    }

    /**
     * 이슈 본문 포맷팅
     * @param {Object} data - RSS 아이템 데이터
     * @returns {string} 포맷된 이슈 본문
     */
    formatIssueBody(data) {
        return `## ${data.title}

**Category:** ${data.category}
**Source:** ${data.link}

### Description
${data.description}

---
*Auto-generated from RSS feed*`;
    }

    /**
     * 프로젝트 V2 API를 통한 이슈 칸반보드 추가
     * @param {number} issueNumber - 이슈 번호
     * @param {string} status - 상태
     * @param {string} milestone - 마일스톤
     */
    async addIssueToProject(issueNumber, status, milestone) {
        try {
            Logger.info(`Adding issue #${issueNumber} to project board`);

            // 프로젝트 정보 가져오기
            const project = await this.getProject();

            // 이슈를 프로젝트에 추가
            const projectItem = await this.addItemToProject(project.id, issueNumber);

            // 상태 및 마일스톤 설정
            if (status) {
                await this.updateProjectItemStatus(project.id, projectItem.id, status);
            }

            if (milestone) {
                await this.updateProjectItemMilestone(project.id, projectItem.id, milestone);
            }

            Logger.info(`Successfully added issue #${issueNumber} to project board`);
        } catch (error) {
            Logger.error(`Failed to add issue #${issueNumber} to project`, error);
            throw error;
        }
    }

    /**
     * 프로젝트 정보 가져오기
     */
    async getProject() {
        const query = `
      query($owner: String!, $number: Int!) {
        user(login: $owner) {
          projectV2(number: $number) {
            id
            fields(first: 20) {
              nodes {
                ... on ProjectV2Field {
                  id
                  name
                }
                ... on ProjectV2SingleSelectField {
                  id
                  name
                  options {
                    id
                    name
                  }
                }
              }
            }
          }
        }
      }
    `;

        const { user } = await this.octokit.graphql(query, {
            owner: this.owner,
            number: this.projectNumber
        });

        return user.projectV2;
    }

    /**
     * 프로젝트에 아이템 추가
     */
    async addItemToProject(projectId, issueNumber) {
        const mutation = `
      mutation($projectId: ID!, $contentId: ID!) {
        addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
          item {
            id
          }
        }
      }
    `;

        // 이슈 ID 가져오기
        const { data: issue } = await this.octokit.rest.issues.get({
            owner: this.owner,
            repo: this.repo,
            issue_number: issueNumber
        });

        const { addProjectV2ItemById } = await this.octokit.graphql(mutation, {
            projectId,
            contentId: issue.node_id
        });

        return addProjectV2ItemById.item;
    }

    /**
     * 프로젝트 아이템 상태 업데이트
     */
    async updateProjectItemStatus(projectId, itemId, status) {
        const mutation = `
      mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $value: ProjectV2FieldValue!) {
        updateProjectV2ItemFieldValue(input: {
          projectId: $projectId
          itemId: $itemId
          fieldId: $fieldId
          value: $value
        }) {
          projectV2Item {
            id
          }
        }
      }
    `;

        // 상태 필드 ID와 옵션 ID 찾기 (실제 구현에서는 프로젝트 스키마에 따라 조정 필요)
        Logger.info(`Updating project item status to: ${status}`);
    }

    /**
     * 프로젝트 아이템 마일스톤 업데이트
     */
    async updateProjectItemMilestone(projectId, itemId, milestone) {
        Logger.info(`Updating project item milestone to: ${milestone}`);
        // 마일스톤 필드 업데이트 로직 (실제 구현에서는 프로젝트 스키마에 따라 조정 필요)
    }
}

module.exports = GitHubService;
