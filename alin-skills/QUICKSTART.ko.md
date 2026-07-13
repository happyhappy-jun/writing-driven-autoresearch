# alin-skills 퀵스타트

ALIN 연구실의 Claude Code 공유 스킬 레포. 전체 가이드: [GUIDE.ko.md](GUIDE.ko.md) · English: [QUICKSTART.md](QUICKSTART.md)

## 1. 접근 권한 받기

Woomin에게 본인의 GitHub 사용자명을 알려주세요. GitHub이 보내는 collaborator 초대 이메일을 수락하면 끝입니다.

## 2. 설치

alin-skills는 `alin`이라는 이름의 **Claude Code 플러그인**입니다. 클론이나 복사 없이, Claude Code 세션 안에서 바로 설치하세요:

```text
/plugin marketplace add alinlab/alin-skills
/plugin install alin@alin-skills
```

레포가 비공개이므로 두 명령 모두 본인 GitHub 계정에 접근 권한이 있어야 동작합니다 (Step 1). Claude Code는 기존 git 자격증명으로 마켓플레이스를 클론하므로, `git clone`이 되는 환경이면 설치도 됩니다. 그 다음 `/reload-plugins`를 실행(또는 세션 새로 시작)하면 스킬이 활성화됩니다.

모든 스킬은 `/alin:<skill-name>` 형태로 네임스페이스가 붙고(예: `/alin:hwpx`), Claude가 description을 보고 알아서 라우팅합니다. `/alin:`까지 입력하면 자동완성이 전체 목록을 보여줍니다. 이 머신에서 필요 없는 스킬(예: Linux에서 macOS 전용 `kakaotalk-mac`)은 그냥 호출하지 않으면 됩니다 — 스킬별 설치 단계가 따로 없습니다.

## 3. 업데이트

```text
/plugin marketplace update alin-skills
```

GitHub에서 최신 카탈로그와 플러그인을 받아옵니다. 이후 `/reload-plugins` 실행. **시작 시 자동 업데이트**(비공개 레포는 기본적으로 건너뜀)를 원하면, repo 읽기 권한이 있는 토큰을 셸 설정에 추가하세요:

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

## 4. 내가 만든 스킬 공유하기

기여는 여전히 클론 + PR 방식입니다 (단순 사용이 아니라 레포를 편집하는 것이니까요). 한 번만 클론하세요:

```bash
git clone https://github.com/alinlab/alin-skills.git ~/code/alin-skills
```

그 다음 프로젝트가 열린 Claude Code 세션에서:

> 이 프로젝트의 `<스킬 이름>` 스킬을 `~/code/alin-skills`의 alin-skills에 추가해줘. CONTRIBUTING.md의 "Add a new skill" 가이드를 따라줘. 브랜치에 커밋하되 아직 푸시는 하지 마.

Claude Code가 스킬을 다듬고, `skills/` 아래에 추가하고, README 표를 업데이트하고, `claude --plugin-dir`로 클론을 로드해 테스트한 뒤, 브랜치에 커밋합니다. 게시를 마무리하려면:

> 브랜치 푸시하고 main 대상으로 pull request 열어줘.
