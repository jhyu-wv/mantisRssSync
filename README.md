# mantisRssSync

# GitHub RSS Issue Creator

RSS 피드에서 자동으로 GitHub Issues를 생성하고 Projects V2 칸반보드에 추가하는 Python 스크립트입니다.

## 주요 기능

- RSS 피드 모니터링 및 새 아이템 감지
- GitHub Issues 자동 생성 (제목, 링크, 설명, 카테고리 포함)
- GitHub Projects V2 칸반보드 자동 등록
- 이슈 상태 및 마일스톤 자동 설정
- 중복 이슈 방지 (해시 기반 중복 체크)
- 테스트 모드 지원
- 상세 로깅 및 오류 처리

## 설치 및 설정

### 1. 필수 라이브러리 설치

```bash
pip install feedparser requests
```

### 2. 환경 변수 설정

GitHub Actions에서 사용할 경우 다음 환경 변수들을 설정해야 합니다:

#### Secrets (GitHub Repository Settings > Secrets and variables > Actions)

- `GITHUB_TOKEN`: GitHub Personal Access Token (필수)
  - 권한: `repo`, `project`, `write:org` (조직 프로젝트의 경우)

#### Variables (GitHub Repository Settings > Secrets and variables > Actions)

- `PROJECT_NUMBER`: GitHub Project V2 번호 (필수)
- `MANTIS_RSS_URL`: 모니터링할 RSS 피드 URL (필수)
- `DEFAULT_STATUS`: 기본 이슈 상태 (선택사항)
- `DEFAULT_MILESTONE`: 기본 마일스톤 (선택사항)

### 3. 파일 배치

리포지토리 루트에 다음 파일들을 배치합니다:

```
repository/
├── .github/
│   └── workflows/
│       └── rss-to-issues.yml
├── github_rss_processor.py
├── test_github_rss.py
└── README.md
```

## 사용 방법

### 로컬 실행

#### 환경 변수 설정 (로컬 테스트)

```bash
export GITHUB_TOKEN="your_github_token"
export GITHUB_OWNER="your_github_username_or_org"
export GITHUB_REPO="your_repository_name"
export PROJECT_NUMBER="1"
export MANTIS_RSS_URL="https://example.com/rss.xml"
export DEFAULT_STATUS="Todo"
export DEFAULT_MILESTONE="v1.0"
```

#### 테스트 모드 실행

```bash
python github_rss_processor.py test
```

#### 실제 실행

```bash
python github_rss_processor.py
```

### GitHub Actions 실행

#### 자동 실행 (스케줄)

워크플로우는 매시간 자동으로 실행됩니다. 필요에 따라 `.github/workflows/rss-to-issues.yml`의 cron 설정을 수정하세요.

```yaml
schedule:
  # 매 시간마다 실행
  - cron: '0 * * * *'
  # 매일 오전 9시 실행
  # - cron: '0 9 * * *'
  # 매주 월요일 오전 9시 실행
  # - cron: '0 9 * * 1'
```

#### 수동 실행

1. GitHub 리포지토리 페이지에서 **Actions** 탭 클릭
2. **RSS to GitHub Issues** 워크플로우 선택
3. **Run workflow** 버튼 클릭
4. 테스트 모드 여부 선택 후 실행

## 테스트

### 단위 테스트 실행

```bash
python test_github_rss.py
```

### 통합 테스트 (실제 API 호출)

```bash
python github_rss_processor.py test
```

테스트 모드에서는 실제 이슈를 생성하지 않고 RSS 피드 파싱과 GitHub API 연결만 확인합니다.

## 설정 상세

### GitHub Project V2 설정

1. GitHub에서 새 Project V2 생성
2. 프로젝트 번호 확인 (URL에서 확인 가능: `/projects/{number}`)
3. 필요한 상태 필드 및 마일스톤 필드 생성
4. 상태 옵션 및 마일스톤 옵션 설정

### RSS 피드 요구사항

RSS 피드는 다음 요소들을 포함해야 합니다:

- `title`: 이슈 제목으로 사용
- `link`: 이슈 본문에 포함
- `description` 또는 `summary`: 이슈 설명으로 사용
- `category` 또는 `tags`: 이슈 라벨로 사용 (선택사항)

### 이슈 형식

생성되는 이슈는 다음과 같은 형식을 가집니다:

```markdown
**Category:** [RSS 카테고리]
**Link:** [RSS 링크]

**Description:**
[RSS 설명 내용]
```

이슈 라벨:
- `rss-auto-created`: 자동 생성된 이슈임을 표시
- `category:[카테고리명]`: RSS 카테고리가 있는 경우 추가

## 로그 및 모니터링

### 로그 파일

스크립트는 `github_rss_processor.log` 파일에 상세한 로그를 기록합니다.

### GitHub Actions 로그

Actions 실행 로그는 GitHub Actions 페이지에서 확인할 수 있으며, 로그 파일은 아티팩트로 저장됩니다.

### 모니터링 항목

- RSS 피드 파싱 성공/실패
- 신규 이슈 생성 개수
- GitHub API 호출 성공/실패
- 프로젝트 필드 설정 성공/실패

## 문제 해결

### 일반적인 문제

#### 1. "프로젝트를 찾을 수 없습니다" 오류

- `PROJECT_NUMBER`가 올바른지 확인
- GitHub Token이 프로젝트 접근 권한을 가지는지 확인
- 조직 프로젝트의 경우 `write:org` 권한 필요

#### 2. "필수 환경 변수가 누락됨" 오류

- 모든 필수 환경 변수가 설정되었는지 확인
- GitHub Actions Variables/Secrets 설정 확인

#### 3. RSS 피드 파싱 실패

- RSS URL이 올바른지 확인
- RSS 피드가 표준 형식을 따르는지 확인
- 네트워크 연결 상태 확인

#### 4. GitHub API 호출 실패

- GitHub Token이 유효한지 확인
- Token 권한이 충분한지 확인
- API 호출 한도 확인

### 디버깅 방법

1. 테스트 모드로 실행하여 설정 확인
2. 로그 파일 확인
3. GitHub Actions 상세 로그 확인
4. 단위 테스트 실행

## 보안 고려사항

- GitHub Token은 반드시 Secret으로 저장
- 최소 권한 원칙에 따라 Token 권한 설정
- RSS URL이 신뢰할 수 있는 소스인지 확인
- 정기적인 Token 갱신 권장

## 기여 방법

1. 이슈 생성 또는 기능 요청
2. 포크 후 브랜치 생성
3. 코드 수정 및 테스트
4. Pull Request 생성

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.