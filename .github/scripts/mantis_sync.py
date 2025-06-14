#!/usr/bin/env python3
"""
GitHub Projects V2 RSS Issue Creator
RSS 피드에서 새로운 이슈를 GitHub 프로젝트에 자동으로 생성하는 스크립트
"""

import os
import logging
import hashlib
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import feedparser
import requests
from urllib.parse import urlparse


@dataclass
class RSSItem:
    """RSS 피드 아이템을 나타내는 데이터 클래스"""
    title: str
    link: str
    description: str
    category: str = ""
    
    def get_hash(self) -> str:
        """이슈의 고유 해시값 생성 (중복 체크용)"""
        content = f"{self.title}{self.link}".encode('utf-8')
        return hashlib.md5(content).hexdigest()[:8]


@dataclass
class ProjectConfig:
    """프로젝트 설정을 관리하는 데이터 클래스"""
    owner: str
    repo: str
    project_number: int
    default_status: str = ""
    default_milestone: str = ""


class GitHubAPI:
    """GitHub API 클라이언트"""
    
    def __init__(self, token: str):
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.github+json'
        })
        self.graphql_url = 'https://api.github.com/graphql'
        self.rest_url = 'https://api.github.com/repos'
    
    def execute_graphql(self, query: str, variables: Dict = None) -> Dict:
        """GraphQL 쿼리 실행"""
        payload = {'query': query}
        if variables:
            payload['variables'] = variables
            
        response = self.session.post(self.graphql_url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        if 'errors' in data:
            raise Exception(f"GraphQL 오류: {data['errors']}")
        
        return data['data']
    
    def create_issue(self, owner: str, repo: str, title: str, body: str, labels: List[str] = None) -> Dict:
        """REST API로 이슈 생성"""
        url = f"{self.rest_url}/{owner}/{repo}/issues"
        payload = {
            'title': title,
            'body': body,
            'labels': labels or []
        }
        
        response = self.session.post(url, json=payload)
        response.raise_for_status()
        return response.json()


class GitHubProjectManager:
    """GitHub Projects V2 관리자"""
    
    def __init__(self, api: GitHubAPI, config: ProjectConfig):
        self.api = api
        self.config = config
        self.project_id = None
        self.status_field_id = None
        self.milestone_field_id = None
        self.status_options = {}
        self.milestone_options = {}
    
    def initialize(self):
        """프로젝트 정보 및 필드 정보 초기화"""
        self._get_project_info()
        self._get_project_fields()
    
    def _get_project_info(self):
        """프로젝트 정보 조회"""
        query = """
        query($owner: String!, $number: Int!) {
            user(login: $owner) {
                projectV2(number: $number) {
                    id
                    title
                }
            }
        }
        """
        
        variables = {
            'owner': self.config.owner,
            'number': self.config.project_number
        }
        
        data = self.api.execute_graphql(query, variables)
        
        # 사용자 또는 조직 프로젝트 확인
        project = data.get('user', {}).get('projectV2') or data.get('organization', {}).get('projectV2')
        
        if not project:
            raise Exception(f"프로젝트를 찾을 수 없습니다: {self.config.owner}/#{self.config.project_number}")
        
        self.project_id = project['id']
        logging.info(f"프로젝트 발견: {project['title']} (ID: {self.project_id})")
    
    def _get_project_fields(self):
        """프로젝트 필드 정보 조회"""
        query = """
        query($projectId: ID!) {
            node(id: $projectId) {
                ... on ProjectV2 {
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
        """
        
        data = self.api.execute_graphql(query, {'projectId': self.project_id})
        fields = data['node']['fields']['nodes']
        
        for field in fields:
            field_name = field['name'].lower()
            
            if 'status' in field_name and 'options' in field:
                self.status_field_id = field['id']
                self.status_options = {opt['name']: opt['id'] for opt in field['options']}
                logging.info(f"상태 필드 발견: {field['name']} (옵션: {list(self.status_options.keys())})")
            
            elif 'milestone' in field_name and 'options' in field:
                self.milestone_field_id = field['id']
                self.milestone_options = {opt['name']: opt['id'] for opt in field['options']}
                logging.info(f"마일스톤 필드 발견: {field['name']} (옵션: {list(self.milestone_options.keys())})")
    
    def get_existing_issues(self) -> Set[str]:
        """기존 이슈의 해시값 조회"""
        query = """
        query($owner: String!, $repo: String!) {
            repository(owner: $owner, name: $repo) {
                issues(first: 100, states: [OPEN, CLOSED]) {
                    nodes {
                        title
                        body
                        url
                    }
                }
            }
        }
        """
        
        variables = {
            'owner': self.config.owner,
            'repo': self.config.repo
        }
        
        data = self.api.execute_graphql(query, variables)
        issues = data['repository']['issues']['nodes']
        
        existing_hashes = set()
        for issue in issues:
            # 이슈 본문에서 RSS 링크 추출하여 해시 생성
            body = issue.get('body', '')
            if '**Link:** ' in body:
                link_line = [line for line in body.split('\n') if line.startswith('**Link:** ')]
                if link_line:
                    link = link_line[0].replace('**Link:** ', '').strip()
                    content = f"{issue['title']}{link}".encode('utf-8')
                    hash_value = hashlib.md5(content).hexdigest()[:8]
                    existing_hashes.add(hash_value)
        
        logging.info(f"기존 이슈 {len(existing_hashes)}개 발견")
        return existing_hashes
    
    def add_issue_to_project(self, issue_id: str) -> str:
        """이슈를 프로젝트에 추가"""
        mutation = """
        mutation($projectId: ID!, $contentId: ID!) {
            addProjectV2ItemByContentId(input: {
                projectId: $projectId
                contentId: $contentId
            }) {
                item {
                    id
                }
            }
        }
        """
        
        variables = {
            'projectId': self.project_id,
            'contentId': issue_id
        }
        
        data = self.api.execute_graphql(mutation, variables)
        item_id = data['addProjectV2ItemByContentId']['item']['id']
        logging.info(f"이슈가 프로젝트에 추가됨 (Item ID: {item_id})")
        return item_id
    
    def update_project_item_field(self, item_id: str, field_id: str, option_id: str):
        """프로젝트 아이템의 필드 값 업데이트"""
        mutation = """
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
        """
        
        variables = {
            'projectId': self.project_id,
            'itemId': item_id,
            'fieldId': field_id,
            'value': {'singleSelectOptionId': option_id}
        }
        
        self.api.execute_graphql(mutation, variables)
    
    def create_issue_from_rss(self, rss_item: RSSItem) -> Optional[str]:
        """RSS 아이템으로부터 이슈 생성 및 프로젝트 추가"""
        # 이슈 본문 생성
        body_parts = []
        
        if rss_item.category:
            body_parts.append(f"**Category:** {rss_item.category}")
        
        body_parts.extend([
            f"**Link:** {rss_item.link}",
            "",
            "**Description:**",
            rss_item.description
        ])
        
        body = "\n".join(body_parts)
        labels = ['rss-auto-created']
        
        if rss_item.category:
            labels.append(f"category:{rss_item.category}")
        
        try:
            # 이슈 생성
            issue = self.api.create_issue(
                self.config.owner,
                self.config.repo,
                rss_item.title,
                body,
                labels
            )
            
            issue_id = issue['node_id']
            logging.info(f"이슈 생성됨: {issue['title']} (#{issue['number']})")
            
            # 프로젝트에 추가
            item_id = self.add_issue_to_project(issue_id)
            
            # 상태 설정
            if self.config.default_status and self.status_field_id:
                status_option_id = self.status_options.get(self.config.default_status)
                if status_option_id:
                    self.update_project_item_field(item_id, self.status_field_id, status_option_id)
                    logging.info(f"상태 설정: {self.config.default_status}")
            
            # 마일스톤 설정
            if self.config.default_milestone and self.milestone_field_id:
                milestone_option_id = self.milestone_options.get(self.config.default_milestone)
                if milestone_option_id:
                    self.update_project_item_field(item_id, self.milestone_field_id, milestone_option_id)
                    logging.info(f"마일스톤 설정: {self.config.default_milestone}")
            
            return issue['html_url']
            
        except Exception as e:
            logging.error(f"이슈 생성 실패 - {rss_item.title}: {e}")
            return None


class RSSProcessor:
    """RSS 피드 처리기"""
    
    @staticmethod
    def fetch_rss_items(rss_url: str) -> List[RSSItem]:
        """RSS 피드에서 아이템 조회"""
        try:
            feed = feedparser.parse(rss_url)
            
            if feed.bozo:
                logging.warning(f"RSS 피드 파싱 경고: {feed.bozo_exception}")
            
            items = []
            for entry in feed.entries:
                # 카테고리 처리
                category = ""
                if hasattr(entry, 'tags') and entry.tags:
                    category = entry.tags[0].term
                elif hasattr(entry, 'category'):
                    category = entry.category
                
                # 설명 처리
                description = ""
                if hasattr(entry, 'summary'):
                    description = entry.summary
                elif hasattr(entry, 'description'):
                    description = entry.description
                elif hasattr(entry, 'content'):
                    if isinstance(entry.content, list) and entry.content:
                        description = entry.content[0].value
                    else:
                        description = str(entry.content)
                
                item = RSSItem(
                    title=entry.title,
                    link=entry.link,
                    description=description,
                    category=category
                )
                items.append(item)
            
            logging.info(f"RSS에서 {len(items)}개 아이템 조회됨")
            return items
            
        except Exception as e:
            logging.error(f"RSS 피드 처리 실패: {e}")
            return []


def setup_logging(test_mode: bool = False):
    """로깅 설정"""
    level = logging.DEBUG if test_mode else logging.INFO
    format_str = '%(asctime)s - %(levelname)s - %(message)s'
    
    logging.basicConfig(
        level=level,
        format=format_str,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('github_rss_processor.log')
        ]
    )


def load_config() -> tuple[ProjectConfig, str, str]:
    """환경 변수에서 설정 로드"""
    required_vars = [
        'GITHUB_TOKEN',
        'GITHUB_OWNER',
        'GITHUB_REPO',
        'PROJECT_NUMBER',
        'MANTIS_RSS_URL'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise Exception(f"필수 환경 변수가 누락됨: {', '.join(missing_vars)}")
    
    config = ProjectConfig(
        owner=os.getenv('GITHUB_OWNER'),
        repo=os.getenv('GITHUB_REPO'),
        project_number=int(os.getenv('PROJECT_NUMBER')),
        default_status=os.getenv('DEFAULT_STATUS', ''),
        default_milestone=os.getenv('DEFAULT_MILESTONE', '')
    )
    
    return config, os.getenv('GITHUB_TOKEN'), os.getenv('MANTIS_RSS_URL')


def test_mode():
    """테스트 모드 실행"""
    setup_logging(test_mode=True)
    logging.info("=== 테스트 모드 시작 ===")
    
    try:
        config, token, rss_url = load_config()
        
        # RSS 피드 테스트
        logging.info("RSS 피드 테스트 중...")
        rss_items = RSSProcessor.fetch_rss_items(rss_url)
        
        if not rss_items:
            logging.warning("RSS 아이템이 없습니다.")
            return
        
        logging.info(f"첫 번째 RSS 아이템 샘플:")
        sample_item = rss_items[0]
        logging.info(f"  제목: {sample_item.title}")
        logging.info(f"  링크: {sample_item.link}")
        logging.info(f"  카테고리: {sample_item.category}")
        logging.info(f"  해시: {sample_item.get_hash()}")
        
        # GitHub API 테스트
        logging.info("GitHub API 테스트 중...")
        api = GitHubAPI(token)
        project_manager = GitHubProjectManager(api, config)
        project_manager.initialize()
        
        # 기존 이슈 확인
        existing_hashes = project_manager.get_existing_issues()
        
        # 신규 이슈 확인
        new_items = [item for item in rss_items if item.get_hash() not in existing_hashes]
        logging.info(f"신규 이슈 {len(new_items)}개 발견")
        
        if new_items:
            logging.info("신규 이슈 샘플 (실제 생성하지 않음):")
            for i, item in enumerate(new_items[:3], 1):
                logging.info(f"  {i}. {item.title}")
        
        logging.info("=== 테스트 완료 ===")
        
    except Exception as e:
        logging.error(f"테스트 실패: {e}")
        raise


def main():
    """메인 실행 함수"""
    setup_logging()
    logging.info("=== GitHub RSS Issue Creator 시작 ===")
    
    try:
        config, token, rss_url = load_config()
        
        # RSS 아이템 조회
        rss_items = RSSProcessor.fetch_rss_items(rss_url)
        if not rss_items:
            logging.info("처리할 RSS 아이템이 없습니다.")
            return
        
        # GitHub 프로젝트 관리자 초기화
        api = GitHubAPI(token)
        project_manager = GitHubProjectManager(api, config)
        project_manager.initialize()
        
        # 기존 이슈 해시 조회
        existing_hashes = project_manager.get_existing_issues()
        
        # 신규 이슈만 필터링
        new_items = [item for item in rss_items if item.get_hash() not in existing_hashes]
        
        if not new_items:
            logging.info("신규 이슈가 없습니다.")
            return
        
        logging.info(f"{len(new_items)}개의 신규 이슈를 생성합니다.")
        
        # 신규 이슈 생성
        created_count = 0
        for item in new_items:
            issue_url = project_manager.create_issue_from_rss(item)
            if issue_url:
                created_count += 1
                logging.info(f"생성됨: {issue_url}")
        
        logging.info(f"=== 완료: {created_count}개 이슈 생성 ===")
        
    except Exception as e:
        logging.error(f"실행 실패: {e}")
        raise


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        test_mode()
    else:
        main()