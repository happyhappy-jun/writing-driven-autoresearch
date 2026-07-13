# alin-skills 가이드

*English version: [GUIDE.md](GUIDE.md)*

alin-skills가 무엇이고, 왜 만들었으며, Claude Code로 어떻게 사용하는지 친절하게 안내하는 문서입니다.

---

## alin-skills란?

alin-skills는 ALIN 연구실 구성원들이 함께 만들고 공유하는 **Claude Code 스킬 모음집**입니다.

"Claude Code 스킬"이란, 특정 작업을 처음부터 끝까지 수행하도록 Claude Code에게 가르치는 작고 독립적인 레시피입니다. 예를 들면 HWP 파일을 Markdown으로 변환하기, 국립국어원 맞춤법 검사기로 한국어 문장 교정하기, macOS에서 카카오톡 메시지 조회하기 같은 작업들이죠. 각 스킬은 `SKILL.md` 파일 하나(와 선택적으로 helper 스크립트)로 이루어져 있습니다. alin-skills는 이 스킬들을 전부 묶어 `alin`이라는 단일 **Claude Code 플러그인**으로 제공하며, 마켓플레이스에서 한 번 설치하면 됩니다. Claude Code는 모든 스킬을 자동으로 찾아내 요청에 맞는 것을 골라 쓰고, `/alin:hwpx`처럼 네임스페이스가 붙은 이름으로 직접 호출할 수도 있습니다.

스킬은 곧 **재사용 가능한 자동화**라고 생각하면 됩니다. 연구실 구성원 중 누군가가 Claude에게 어떤 작업을 안정적으로 시키는 방법을 알아내면, 그걸 스킬로 포장해서 공유할 수 있고, 나머지 사람들은 그걸 공짜로 받아 쓸 수 있습니다.

---

## 왜 이 레포를 만들었나

모든 연구실 구성원은 Claude Code를 쓰면서 각자만의 작은 노하우를 쌓아갑니다. 참고문헌 포맷팅하는 법, 국가 데이터 포털에서 데이터 긁는 법, 논문 초고를 교정하는 법, 리뷰어가 보낸 한글(HWP) 문서를 변환하는 법 같은 것들요. 문제는 이런 지식의 대부분이 개인 머릿속에만 남아 있다는 점입니다. 같은 작업이 반복해서 재발명되고, 3개월 전에 적어두었던 기발한 우회 방법도 시간이 지나면 잊어버리게 됩니다.

alin-skills는 이런 개인적이고 흩어져 있는 노하우를 **공유되는 집단 지성**으로 바꾸기 위해 만들어졌습니다:

- 유용한 워크플로우를 찾았다면 **스킬로 게시**하세요. 연구실 전체가 혜택을 봅니다.
- 다른 사람의 스킬이 여러분의 필요에 *거의* 맞는다면, **수정하고 개선**하세요. 다음 사람은 개선된 버전을 받게 됩니다.
- 시간이 지나면 이 레포는 연구실의 **에이전트 워크플로우에 대한 제도적 기억**이 됩니다.

설계 원칙은 단순합니다. **스킬을 공유하는 것이 혼자 간직하는 것보다 확실히 덜 번거롭도록** 만드는 것.

---

## alin-skills 사용법

### Step 0: 레포 접근 권한 받기

alin-skills는 **[github.com/alinlab/alin-skills](https://github.com/alinlab/alin-skills)**에 호스팅된 **비공개 레포지토리**입니다. 클론이나 기여 그 무엇이든 하기 전에 먼저 collaborator로 등록되어야 합니다.

**접근 권한을 요청하려면** Woomin에게 메시지를 보내세요 (Slack, 카카오톡, 이메일, 직접 만나서 — 가장 빠른 방법 아무거나):

- 본인의 GitHub 사용자명 (예: `@your-handle`)
- alin-skills에 합류하고 싶다는 한 줄 메모

Woomin이 여러분을 collaborator로 추가하면 GitHub에서 초대 이메일을 보내줍니다. 초대를 수락하면 클론할 준비가 끝난 것입니다. 클론 URL은 다음과 같습니다:

```
https://github.com/alinlab/alin-skills.git
```

> 클론할 때 "repository not found" 또는 "permission denied" 에러가 난다면, 보통 초대를 아직 수락하지 않았거나 로컬 git이 GitHub에 인증되어 있지 않은 경우입니다. 초대를 수락하고, GitHub CLI를 쓴다면 `gh auth login`을 실행한 다음 다시 시도해 보세요.

### (선택 사항) 매끄러운 PR 플로우를 위한 GitHub CLI 설치

기여 워크플로우는 대부분 pull request를 여는 것으로 마무리됩니다. 두 가지 선택지:

1. **아무것도 추가로 설치하지 않기** — Claude Code가 브랜치를 푸시하게 두고, PR은 본인이 GitHub 웹페이지에서 여는 방법 (푸시 직후 뜨는 "Compare & pull request" 배너 한 번 클릭).
2. **[GitHub CLI (`gh`)](https://cli.github.com/) 설치** — Claude Code가 `gh pr create`까지 직접 실행. 기여를 한두 번 이상 할 계획이라면 더 매끄럽습니다.

```bash
# macOS + Homebrew
brew install gh

# conda (크로스 플랫폼)
conda install -c conda-forge gh
```

설치 후 `gh auth login`을 한 번 실행하세요. 이후부터는 *"푸시하고 PR 열어줘"*로 한 번에 끝납니다.

---

## alin-skills 사용하기

설치와 업데이트는 전부 Claude Code 안에서 `/plugin` 명령으로 처리합니다 — 클론도, 파일 복사도 없습니다. 스킬을 공유하거나 개선하는 기여 작업은 레포 자체를 편집하는 것이라 여전히 클론 + PR 방식을 씁니다.

### A1. 최초 설치 (새 머신에 깔기)

Claude Code 세션에서 실행하세요:

```text
/plugin marketplace add alinlab/alin-skills
/plugin install alin@alin-skills
```

첫 번째 명령은 이 레포를 마켓플레이스로 등록하고, 두 번째 명령은 거기서 `alin` 플러그인을 설치합니다. 레포가 **비공개**이므로 둘 다 본인 GitHub 계정에 접근 권한이 있어야 동작합니다 (Step 0). Claude Code는 평소 git 자격증명(`git clone`에 쓰는 SSH 키나 HTTPS 토큰 / `gh auth login`)으로 마켓플레이스를 클론하므로, 씨름할 대화형 프롬프트가 없습니다.

끝나면 `/reload-plugins`를 실행(또는 세션 새로 시작)하면 모든 스킬이 `/alin:<skill-name>` 네임스페이스로 활성화됩니다.

**어떤 스킬을 설치할지 골라야 하나요?** 아니요. 플러그인이 전부 한 번에 설치하지만, 호출되기 전까지는 비용이 거의 없고, Claude는 요청이 description과 맞을 때만 해당 스킬로 라우팅합니다. `kakaotalk-mac` 같은 macOS 전용 스킬은 Linux에서는 그냥 안 불릴 뿐입니다. 스킬별 설치 단계는 이제 없습니다.

### A2. 최신 버전으로 업데이트

```text
/plugin marketplace update alin-skills
```

그 다음 `/reload-plugins`. 끝입니다 — GitHub에서 최신 버전을 바로 받아옵니다.

**선택: 시작 시 자동 업데이트.** Claude Code는 시작할 때 마켓플레이스를 갱신할 수 있지만, *비공개* 레포는 비대화형으로 인증할 수 있을 때만 이걸 수행합니다. 켜려면 repo 읽기 권한이 있는 GitHub 토큰을 셸 설정(`~/.zshrc`)에 넣으세요:

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
```

토큰이 없어도 문제 없습니다 — 위 명령으로 수동 업데이트하면 됩니다.

### A3. 새 스킬을 연구실에 공유하기

본인 프로젝트에서 helper 스크립트와 `SKILL.md`로 된 워크플로우를 만들었고, 이걸 게시하고 싶을 때의 시나리오입니다. 기여는 레포를 편집하므로 먼저 클론하세요 (경로는 자유, 이 가이드는 `~/code/alin-skills` 기준):

```bash
git clone https://github.com/alinlab/alin-skills.git ~/code/alin-skills
```

그 다음 원본 프로젝트가 열린 Claude Code 세션에서:

> 이 프로젝트의 `<원본 스킬 경로>`에 스킬이 하나 있어. `~/code/alin-skills`의 alin-skills 레포에 이 스킬을 추가해줘. 클론된 `CONTRIBUTING.md`의 "Add a new skill" 가이드를 따라줘 — `skills/<skill-name>/`에 복사하고, `SKILL.md`를 레포 컨벤션에 맞게 다듬고(프로젝트별 경로 제거, 번들 스크립트는 `${CLAUDE_SKILL_DIR}`로 참조), README 스킬 표에 행을 추가하고, `claude --plugin-dir ~/code/alin-skills`로 클론을 로드해 테스트해줘. 브랜치에 커밋하되 아직 푸시는 하지 마.

Claude Code가 작업을 마치고 요약을 보여주면, 푸시 전에 멈춥니다. 마무리하려면:

> 브랜치 푸시하고 main 대상으로 pull request 열어줘.

또는 터미널에서 직접 `git push -u origin <branch>`하고 GitHub 웹페이지에서 PR을 열어도 됩니다.

### A4. 기존 스킬 개선하기

> alin-skills의 `<스킬 이름>` 스킬에 `<바꾸거나 추가하고 싶은 내용>`이 필요해. `~/code/alin-skills`에서 CONTRIBUTING.md의 "Update an existing skill" 가이드를 따라 업데이트해줘. 편집 전에 merge plan을 먼저 보여주고, 폴더 이름이나 `name:` frontmatter는 절대 바꾸지 말고, `update-<skill-name>` 브랜치에 커밋하되 푸시는 하지 마.

Claude Code가 merge plan을 보여주고, 여러분의 확인을 기다린 뒤 수정을 적용하고 테스트하고(`claude --plugin-dir ~/code/alin-skills`) 커밋합니다. 준비되면 푸시하세요.

---

## 팁과 흔한 실수들

- **설치/업데이트 후 reload.** `/reload-plugins`를 실행(또는 세션 새로 시작)하면 새로 설치/업데이트된 스킬이 인식됩니다.
- **스킬은 description으로 라우팅됩니다.** Claude Code는 `SKILL.md`의 frontmatter에 있는 `description:` 필드를 보고 어떤 스킬을 쓸지 결정합니다. 파일명이 아닙니다. 스킬이 자동으로 불리지 않는다면 description을 다시 읽고 여러분의 요청과 맞는지 확인하세요. `/alin:hwpx`처럼 네임스페이스가 붙은 이름으로 강제 호출할 수도 있습니다.
- **충돌 걱정이 없습니다.** 플러그인 스킬은 항상 네임스페이스(`alin:<name>`)가 붙으므로, `~/.claude/skills/`의 개인 스킬이나 다른 플러그인의 스킬과 절대 충돌하지 않습니다. 예전의 "이 디렉토리 덮어쓸까요?" 위험은 사라졌습니다.
- **설치된 복사본은 편집하지 마세요.** 플러그인은 업데이트 시 교체되는 관리형 버전 캐시(`~/.claude/plugins/cache/…`)에 위치합니다. 스킬을 바꾸려면 클론에서 편집하고 PR을 여세요 (A3/A4 참고). 캐시에 직접 편집한 내용은 다음 업데이트 때 사라집니다.
- **한국어와 영어 모두 가능합니다.** 스킬의 `description` 필드는 안정적인 라우팅을 위해 영어로 작성되지만, `SKILL.md`의 본문은 작업에 어울리는 언어(한국어든 영어든) 아무거나 써도 됩니다.

---

## 도움 받기

- **접근 권한 / 권한 문제**: Woomin에게 직접 연락하세요.
- **스킬이 망가졌거나 예상대로 동작하지 않을 때**: GitHub 레포에 이슈를 열거나 연구실 채널에 알려주세요.
- **좋은 스킬을 어떻게 써야 할지 모르겠을 때**: `CONTRIBUTING.md`를 읽고 `skills/` 안에 있는 기존 스킬들을 예시로 참고하세요.
- **이 가이드나 기여 절차 자체를 바꾸고 싶을 때**: `GUIDE.md` 또는 `CONTRIBUTING.md`에 대한 PR을 여세요.

기억할 철학은 단 하나입니다. **워크플로우가 나에게 시간을 아껴줬다면, 다른 사람에게도 시간을 아껴줄 가능성이 높습니다.** 너무 깊이 고민하지 마세요. 일단 스킬을 공유하고, 피드백을 받으며 개선하세요. 연구실의 집단 지성은 그렇게 자라납니다.
