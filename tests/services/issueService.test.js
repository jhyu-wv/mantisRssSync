const IssueService = require('../../src/services/issueService');

describe('IssueService', () => {
    let issueService;
    let mockGithubService;
    let mockRssService;

    beforeEach(() => {
        mockGithubService = {
            createIssue: jest.fn(),
            addIssueToProject: jest.fn()
        };
        mockRssService = {};
        issueService = new IssueService(mockGithubService, mockRssService);
    });

    describe('findNewIssues', () => {
        it('should return all items when no existing issues', () => {
            const rssItems = [
                { title: 'New Item 1', category: 'Bug' },
                { title: 'New Item 2', category: 'Feature' }
            ];
            const existingIssues = [];

            const newIssues = issueService.findNewIssues(rssItems, existingIssues);

            expect(newIssues).toHaveLength(2);
            expect(newIssues).toEqual(rssItems);
        });

        it('should filter out existing issues', () => {
            const rssItems = [
                { title: 'Existing Item', category: 'Bug' },
                { title: 'New Item', category: 'Feature' }
            ];
            const existingIssues = [
                { title: 'Existing Item', number: 1 }
            ];

            const newIssues = issueService.findNewIssues(rssItems, existingIssues);

            expect(newIssues).toHaveLength(1);
            expect(newIssues[0].title).toBe('New Item');
        });

        it('should handle title whitespace correctly', () => {
            const rssItems = [
                { title: '  Whitespace Item  ', category: 'Bug' }
            ];
            const existingIssues = [
                { title: 'Whitespace Item', number: 1 }
            ];

            const newIssues = issueService.findNewIssues(rssItems, existingIssues);

            expect(newIssues).toHaveLength(0);
        });
    });

    describe('createNewIssues', () => {
        it('should create issues in normal mode', async () => {
            const newIssues = [
                { title: 'Test Issue', category: 'Bug' }
            ];
            const defaults = { status: 'Todo', milestone: 'v1.0' };

            mockGithubService.createIssue.mockResolvedValue({ number: 1, title: 'Test Issue' });
            mockGithubService.addIssueToProject.mockResolvedValue();

            // sleep 메서드 모킹
            issueService.sleep = jest.fn().mockResolvedValue();

            const result = await issueService.createNewIssues(newIssues, defaults, false);

            expect(mockGithubService.createIssue).toHaveBeenCalledWith(newIssues[0]);
            expect(mockGithubService.addIssueToProject).toHaveBeenCalledWith(1, 'Todo', 'v1.0');
            expect(result).toHaveLength(1);
        });

        it('should not create issues in dry run mode', async () => {
            const newIssues = [
                { title: 'Test Issue', category: 'Bug' }
            ];
            const defaults = { status: 'Todo', milestone: 'v1.0' };

            const result = await issueService.createNewIssues(newIssues, defaults, true);

            expect(mockGithubService.createIssue).not.toHaveBeenCalled();
            expect(result).toHaveLength(0);
        });

        it('should handle empty new issues array', async () => {
            const result = await issueService.createNewIssues([], {}, false);
            expect(result).toHaveLength(0);
        });
    });
});
