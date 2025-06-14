#!/usr/bin/env python3
"""
GitHub RSS Processor 테스트 스위트
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import tempfile
from github_rss_processor import (
    RSSItem, ProjectConfig, GitHubAPI, GitHubProjectManager, 
    RSSProcessor, load_config
)


class TestRSSItem(unittest.TestCase):
    """RSSItem 클래스 테스트"""
    
    def test_rss_item_creation(self):
        item = RSSItem(
            title="Test Title",
            link="https://example.com",
            description="Test Description",
            category="Test Category"
        )
        
        self.assertEqual(item.title, "Test Title")
        self.assertEqual(item.link, "https://example.com")
        self.assertEqual(item.description, "Test Description")
        self.assertEqual(item.category, "Test Category")
    
    def test_get_hash(self):
        item1 = RSSItem("Title", "https://example.com", "Desc")
        item2 = RSSItem("Title", "https://example.com", "Desc")
        item3 = RSSItem("Different Title", "https://example.com", "Desc")
        
        # 같은 제목과 링크는 같은 해시
        self.assertEqual(item1.get_hash(), item2.get_hash())
        # 다른 제목은 다른 해시
        self.assertNotEqual(item1.get_hash(), item3.get_hash())
        # 해시 길이 체크
        self.assertEqual(len(item1.get_hash()), 8)


class TestProjectConfig(unittest.TestCase):
    """ProjectConfig 클래스 테스트"""
    
    def test_project_config_creation(self):
        config = ProjectConfig(
            owner="testowner",
            repo="testrepo",
            project_number=1,
            default_status="Todo",
            default_milestone="v1.0"
        )
        
        self.assertEqual(config.owner, "testowner")
        self.assertEqual(config.repo, "testrepo")
        self.assertEqual(config.project_number, 1)
        self.assertEqual(config.default_status, "Todo")
        self.assertEqual(config.default_milestone, "v1.0")


class TestGitHubAPI(unittest.TestCase):
    """GitHubAPI 클래스 테스트"""
    
    def setUp(self):
        self.api = GitHubAPI("test_token")
    
    def test_api_initialization(self):
        self.assertEqual(self.api.token, "test_token")
        self.assertIn("Bearer test_token", self.api.session.headers['Authorization'])
    
    @patch('requests.Session.post')
    def test_execute_graphql_success(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {'data': {'test': 'success'}}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = self.api.execute_graphql("query { test }")
        
        self.assertEqual(result, {'test': 'success'})
        mock_post.assert_called_once()
    
    @patch('requests.Session.post')
    def test_execute_graphql_error(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {'errors': [{'message': 'Test error'}]}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        with self.assertRaises(Exception) as context:
            self.api.execute_graphql("query { test }")
        
        self.assertIn("GraphQL 오류", str(context.exception))
    
    @patch('requests.Session.post')
    def test_create_issue(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {
            'id': 1,
            'number': 1,
            'title': 'Test Issue',
            'html_url': 'https://github.com/test/repo/issues/1'
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = self.api.create_issue("owner", "repo", "Test Issue", "Test Body")
        
        self.assertEqual(result['title'], 'Test Issue')
        mock_post.assert_called_once()


class TestRSSProcessor(unittest.TestCase):
    """RSSProcessor 클래스 테스트"""
    
    @patch('feedparser.parse')
    def test_fetch_rss_items_success(self, mock_parse):
        # Mock RSS 피드 데이터
        mock_entry = Mock()
        mock_entry.title = "Test RSS Title"
        mock_entry.link = "https://example.com/rss/1"
        mock_entry.summary = "Test RSS Description"
        mock_entry.tags = [Mock(term="Test Category")]
        
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.entries = [mock_entry]
        mock_parse.return_value = mock_feed
        
        items = RSSProcessor.fetch_rss_items("https://example.com/rss")
        
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "Test RSS Title")
        self.assertEqual(items[0].link, "https://example.com/rss/1")
        self.assertEqual(items[0].description, "Test RSS Description")
        self.assertEqual(items[0].category, "Test Category")
    
    @patch('feedparser.parse')
    def test_fetch_rss_items_empty_feed(self, mock_parse):
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.entries = []
        mock_parse.return_value = mock_feed
        
        items = RSSProcessor.fetch_rss_items("https://example.com/rss")
        
        self.assertEqual(len(items), 0)
    
    @patch('feedparser.parse')
    def test_fetch_rss_items_with_exception(self, mock_parse):
        mock_parse.side_effect = Exception("RSS parsing failed")
        
        items = RSSProcessor.fetch_rss_items("https://example.com/rss")
        
        self.assertEqual(len(items), 0)


class TestGitHubProjectManager(unittest.TestCase):
    """GitHubProjectManager 클래스 테스트"""
    
    def setUp(self):
        self.mock_api = Mock(spec=GitHubAPI)
        self.config = ProjectConfig("owner", "repo", 1)
        self.manager = GitHubProjectManager(self.mock_api, self.config)
    
    def test_initialization(self):
        self.assertEqual(self.manager.api, self.mock_api)
        self.assertEqual(self.manager.config, self.config)
        self.assertIsNone(self.manager.project_id)
    
    def test_get_project_info_user_project(self):
        mock_data = {
            'user': {
                'projectV2': {
                    'id': 'test_project_id',
                    'title': 'Test Project'
                }
            },
            'organization': {
                'projectV2': None
            }
        }
        self.mock_api.execute_graphql.return_value = mock_data
        
        self.manager._get_project_info()
        
        self.assertEqual(self.manager.project_id, 'test_project_id')
    
    def test_get_project_info_org_project(self):
        mock_data = {
            'user': {
                'projectV2': None
            },
            'organization': {
                'projectV2': {
                    'id': 'org_project_id',
                    'title': 'Org Project'
                }
            }
        }
        self.mock_api.execute_graphql.return_value = mock_data
        
        self.manager._get_project_info()
        
        self.assertEqual(self.manager.project_id, 'org_project_id')
    
    def test_get_project_info_not_found(self):
        mock_data = {
            'user': {'projectV2': None},
            'organization': {'projectV2': None}
        }
        self.mock_api.execute_graphql.return_value = mock_data
        
        with self.assertRaises(Exception) as context:
            self.manager._get_project_info()
        
        self.assertIn("프로젝트를 찾을 수 없습니다", str(context.exception))
    
    def test_get_project_fields(self):
        mock_data = {
            'node': {
                'fields': {
                    'nodes': [
                        {
                            'id': 'status_field_id',
                            'name': 'Status',
                            'options': [
                                {'id': 'todo_id', 'name': 'Todo'},
                                {'id': 'done_id', 'name': 'Done'}
                            ]
                        },
                        {
                            'id': 'milestone_field_id',
                            'name': 'Milestone',
                            'options': [
                                {'id': 'v1_id', 'name': 'v1.0'},
                                {'id': 'v2_id', 'name': 'v2.0'}
                            ]
                        }
                    ]
                }
            }
        }
        self.mock_api.execute_graphql.return_value = mock_data
        
        self.manager._get_project_fields()
        
        self.assertEqual(self.manager.status_field_id, 'status_field_id')
        self.assertEqual(self.manager.milestone_field_id, 'milestone_field_id')
        self.assertIn('Todo', self.manager.status_options)
        self.assertIn('v1.0', self.manager.milestone_options)
    
    def test_get_existing_issues(self):
        mock_data = {
            'repository': {
                'issues': {
                    'nodes': [
                        {
                            'title': 'Test Issue 1',
                            'body': '**Link:** https://example.com/1\nContent',
                            'url': 'https://github.com/owner/repo/issues/1'
                        },
                        {
                            'title': 'Test Issue 2',
                            'body': '**Link:** https://example.com/2\nContent',
                            'url': 'https://github.com/owner/repo/issues/2'
                        }
                    ]
                }
            }
        }
        self.mock_api.execute_graphql.return_value = mock_data
        
        existing_hashes = self.manager.get_existing_issues()
        
        self.assertEqual(len(existing_hashes), 2)
        self.assertIsInstance(existing_hashes, set)
        
        # 해시값 검증
        for hash_val in existing_hashes:
            self.assertEqual(len(hash_val), 8)
    
    def test_create_issue_from_rss(self):
        # Mock 설정
        self.manager.project_id = 'test_project_id'
        self.manager.status_field_id = 'status_field_id'
        self.manager.milestone_field_id = 'milestone_field_id'
        self.manager.status_options = {'Todo': 'todo_option_id'}
        self.manager.milestone_options = {'v1.0': 'v1_option_id'}
        self.config.default_status = 'Todo'
        self.config.default_milestone = 'v1.0'
        
        # Mock API 응답
        mock_issue = {
            'node_id': 'issue_node_id',
            'number': 1,
            'title': 'Test RSS Issue',
            'html_url': 'https://github.com/owner/repo/issues/1'
        }
        self.mock_api.create_issue.return_value = mock_issue
        self.mock_api.execute_graphql.side_effect = [
            {'addProjectV2ItemByContentId': {'item': {'id': 'item_id'}}},  # add to project
            {'updateProjectV2ItemFieldValue': {'projectV2Item': {'id': 'item_id'}}},  # status
            {'updateProjectV2ItemFieldValue': {'projectV2Item': {'id': 'item_id'}}}   # milestone
        ]
        
        rss_item = RSSItem(
            title="Test RSS Issue",
            link="https://example.com/rss/1",
            description="Test RSS Description",
            category="Test Category"
        )
        
        result = self.manager.create_issue_from_rss(rss_item)
        
        self.assertEqual(result, 'https://github.com/owner/repo/issues/1')
        self.mock_api.create_issue.assert_called_once()
        # GraphQL 호출 3번 (프로젝트 추가, 상태 설정, 마일스톤 설정)
        self.assertEqual(self.mock_api.execute_graphql.call_count, 3)


class TestConfigLoader(unittest.TestCase):
    """설정 로드 함수 테스트"""
    
    def setUp(self):
        # 기존 환경 변수 백업
        self.original_env = {}
        env_vars = [
            'GITHUB_TOKEN', 'GITHUB_OWNER', 'GITHUB_REPO', 
            'PROJECT_NUMBER', 'MANTIS_RSS_URL', 'DEFAULT_STATUS', 'DEFAULT_MILESTONE'
        ]
        for var in env_vars:
            self.original_env[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]
    
    def tearDown(self):
        # 환경 변수 복원
        for var, value in self.original_env.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]
    
    def test_load_config_success(self):
        # 필수 환경 변수 설정
        os.environ['GITHUB_TOKEN'] = 'test_token'
        os.environ['GITHUB_OWNER'] = 'test_owner'
        os.environ['GITHUB_REPO'] = 'test_repo'
        os.environ['PROJECT_NUMBER'] = '1'
        os.environ['MANTIS_RSS_URL'] = 'https://example.com/rss'
        os.environ['DEFAULT_STATUS'] = 'Todo'
        os.environ['DEFAULT_MILESTONE'] = 'v1.0'
        
        config, token, rss_url = load_config()
        
        self.assertEqual(config.owner, 'test_owner')
        self.assertEqual(config.repo, 'test_repo')
        self.assertEqual(config.project_number, 1)
        self.assertEqual(config.default_status, 'Todo')
        self.assertEqual(config.default_milestone, 'v1.0')
        self.assertEqual(token, 'test_token')
        self.assertEqual(rss_url, 'https://example.com/rss')
    
    def test_load_config_missing_required_vars(self):
        # 일부 필수 변수만 설정
        os.environ['GITHUB_TOKEN'] = 'test_token'
        os.environ['GITHUB_OWNER'] = 'test_owner'
        # GITHUB_REPO, PROJECT_NUMBER, MANTIS_RSS_URL 누락
        
        with self.assertRaises(Exception) as context:
            load_config()
        
        self.assertIn("필수 환경 변수가 누락됨", str(context.exception))
    
    def test_load_config_optional_vars(self):
        # 필수 변수만 설정 (선택 변수 누락)
        os.environ['GITHUB_TOKEN'] = 'test_token'
        os.environ['GITHUB_OWNER'] = 'test_owner'
        os.environ['GITHUB_REPO'] = 'test_repo'
        os.environ['PROJECT_NUMBER'] = '1'
        os.environ['MANTIS_RSS_URL'] = 'https://example.com/rss'
        
        config, token, rss_url = load_config()
        
        self.assertEqual(config.default_status, '')
        self.assertEqual(config.default_milestone, '')


class TestIntegration(unittest.TestCase):
    """통합 테스트"""
    
    @patch('github_rss_processor.RSSProcessor.fetch_rss_items')
    @patch('github_rss_processor.GitHubProjectManager')
    @patch('github_rss_processor.GitHubAPI')
    @patch('github_rss_processor.load_config')
    def test_main_flow_with_new_items(self, mock_load_config, mock_api_class, 
                                     mock_manager_class, mock_fetch_rss):
        """신규 아이템이 있는 경우의 메인 플로우 테스트"""
        
        # Mock 설정
        mock_config = ProjectConfig("owner", "repo", 1, "Todo", "v1.0")
        mock_load_config.return_value = (mock_config, "token", "rss_url")
        
        # RSS 아이템 Mock
        rss_items = [
            RSSItem("Item 1", "https://example.com/1", "Desc 1", "Cat 1"),
            RSSItem("Item 2", "https://example.com/2", "Desc 2", "Cat 2")
        ]
        mock_fetch_rss.return_value = rss_items
        
        # GitHub 관리자 Mock
        mock_manager = Mock()
        mock_manager.get_existing_issues.return_value = set()  # 기존 이슈 없음
        mock_manager.create_issue_from_rss.return_value = "https://github.com/owner/repo/issues/1"
        mock_manager_class.return_value = mock_manager
        
        # API Mock
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        
        # 메인 함수 실행 (import하여 실행)
        from github_rss_processor import main
        
        # 예외 없이 실행되어야 함
        try:
            main()
        except SystemExit:
            pass  # 정상 종료
        
        # 검증
        mock_manager.initialize.assert_called_once()
        mock_manager.get_existing_issues.assert_called_once()
        self.assertEqual(mock_manager.create_issue_from_rss.call_count, 2)
    
    @patch('github_rss_processor.RSSProcessor.fetch_rss_items')
    @patch('github_rss_processor.GitHubProjectManager')
    @patch('github_rss_processor.GitHubAPI')
    @patch('github_rss_processor.load_config')
    def test_main_flow_no_new_items(self, mock_load_config, mock_api_class, 
                                   mock_manager_class, mock_fetch_rss):
        """신규 아이템이 없는 경우의 메인 플로우 테스트"""
        
        # Mock 설정
        mock_config = ProjectConfig("owner", "repo", 1)
        mock_load_config.return_value = (mock_config, "token", "rss_url")
        
        # RSS 아이템 Mock
        rss_item = RSSItem("Existing Item", "https://example.com/1", "Desc")
        mock_fetch_rss.return_value = [rss_item]
        
        # 기존 이슈에 동일한 해시 존재
        existing_hashes = {rss_item.get_hash()}
        
        mock_manager = Mock()
        mock_manager.get_existing_issues.return_value = existing_hashes
        mock_manager_class.return_value = mock_manager
        
        mock_api = Mock()
        mock_api_class.return_value = mock_api
        
        from github_rss_processor import main
        
        try:
            main()
        except SystemExit:
            pass
        
        # create_issue_from_rss가 호출되지 않아야 함
        mock_manager.create_issue_from_rss.assert_not_called()


def run_tests():
    """테스트 실행 함수"""
    # 테스트 로더 생성
    loader = unittest.TestLoader()
    
    # 테스트 스위트 생성
    suite = unittest.TestSuite()
    
    # 테스트 클래스들 추가
    test_classes = [
        TestRSSItem,
        TestProjectConfig,
        TestGitHubAPI,
        TestRSSProcessor,
        TestGitHubProjectManager,
        TestConfigLoader,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # 테스트 실행
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 결과 출력
    print(f"\n테스트 실행 완료:")
    print(f"  실행된 테스트: {result.testsRun}")
    print(f"  실패: {len(result.failures)}")
    print(f"  오류: {len(result.errors)}")
    
    if result.failures:
        print("\n실패한 테스트:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n오류가 발생한 테스트:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    import sys
    
    # 테스트 실행
    success = run_tests()
    
    # 종료 코드 설정
    sys.exit(0 if success else 1)
            