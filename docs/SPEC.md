---
title: "AI 동아리 앱 갤러리 GitHub 사이트 제작 명세"
date: 2026-10-13
version: 0.3
type: prd
status: draft
tags:
  - 바이브코딩
  - AI동아리
  - GitHubPages
  - Canva
related:
  - "[[2026-AI동아리-5-6학년-내고민해결앱만들기-계획서]]"
  - "[[2026-AI동아리-5-6학년-내고민해결앱만들기-학습지와자료]]"
---

# AI 동아리 앱 갤러리 GitHub 사이트 제작 명세

> 이 문서는 **별도 폴더(Drive 밖)에서 VS Code와 Claude로 사이트를 만들 때 넘겨줄 명세**다. Edu-Nexus에는 코드를 두지 않고, 완성 후 저장소·배포 링크와 기준 버전만 `03_Project_Notes/`에 기록한다(AGENTS.md 코드와 Git 원칙).

## 1. 목적과 범위

**목적**

- 학교 AI 동아리 4팀이 Canva Code로 만든 앱을 한곳에 모아 보여 준다.
- 각 앱의 **보관본(코드 복제)**을 저장해, Canva 권한 회수나 게시 중단 뒤에도 실행되게 한다.

**하는 것**

- 활동 안내 페이지
- 팀별 작품 갤러리: 앱 실행(보관본), Canva 원본 링크, 기획서 보기
- 교사가 게시 링크로 보관본을 만드는 스크립트

**하지 않는 것**

- 데이터베이스, 로그인, 좋아요, 댓글·피드백 입력. 피드백은 수업에서 종이 카드로 받는다.
- 학생 이름 표시. 팀 이름만 쓴다.
- 사이트에서 직접 제출받기. 제출은 Google Forms로 받는다.

**규모:** 4팀(5·6학년 2인 1팀), 2026년 2학기 1회 운영. 다음 동아리에서 재사용할 수 있게 팀 수와 학기를 데이터로 분리한다.

## 2. 참고 사이트

| 사이트 | 가져올 점 | 다른 점 |
| --- | --- | --- |
| greatsong.github.io/ingu | 워크숍 안내 + `gallery/` 구성, 카드에 바로가기·한 줄 소개 | ingu 갤러리는 Supabase로 제출·좋아요를 받고 앱은 외부 링크만 둔다. 여기서는 DB가 없고 보관본을 저장한다 |
| TCA Creator Camp (Apps Script) | 프로젝트 발표 모드(문제 → 사용자 → 기능 → 흐름 → 완성) | 서버·갤러리 저장이 Apps Script다. 여기서는 정적 JSON을 쓴다 |

## 3. 보관 방법 검증 결과 (2026-10-13)

교사용 예시 앱 `https://xn--o79ay59agzdiwb.my.canva.site/cmzttgv7h6ejhfvy`로 시험했다.

1. **게시 페이지:** 게시 주소의 HTML(약 36KB)은 Canva 사이트 껍데기다. 그 안에 앱이 iframe으로 들어 있다.
   - iframe 주소: `_assets/remote/embed/codelet/<코드ID>/index.html` (게시 주소 경로 기준 상대 경로)
   - 실제 요청 주소: `https://<사이트>/<페이지ID>/_assets/remote/embed/codelet/<코드ID>/index.html`
   - 페이지 데이터 안에 `canva-hosted-embed.com/codelet/DP_…/<코드ID>` 주소도 있다. 직접 열면 404였다.
2. **앱 HTML 받기:** iframe 주소를 그냥 요청하면 `canvacode.com/codelet/<토큰>/…`으로 넘어가 404가 났다.
   - 요청 헤더에 `Referer: <게시 주소>`와 `Sec-Fetch-Dest: iframe`을 넣으면 200으로 앱 HTML(약 20KB)을 받았다.
3. **앱 HTML의 구성**
   - Canva 전용 스크립트 4개: `/codelet/<토큰>/telemetry_sdk.js`, `data_sdk.js`, `editing_sdk.js`, `resizing_sdk.js`. 상대 경로라 Canva 밖에서는 깨진다.
   - 외부 CDN: Tailwind(`cdn.tailwindcss.com/3.4.17`), lucide(`cdn.jsdelivr.net/npm/lucide@0.577.0`), Google Fonts
   - 앱 본문 스크립트(인라인 1개, 약 3.4KB)는 Canva SDK를 쓰지 않았다.
4. **단독 실행:** `/codelet/`로 시작하는 스크립트 태그 4개를 지운 파일을 Edge 헤드리스(820×1180, iPad 세로 비율)로 열었다. 기획서 앱 1단계 화면이 정상으로 그려졌다.

**주의**

- 이 방법은 Canva가 공식으로 안내한 내보내기가 아니다. Canva 쪽 구조가 바뀌면 작동하지 않을 수 있다. 실패하면 링크와 화면 캡처만 보관한다(5절 대안).
- 학생 앱이 Canva 저장 기능(`data_sdk`)을 쓰면 보관본에서 그 기능이 작동하지 않는다. 스크립트가 감지해 표시한다(5절).
- 제목 글자 굵기 등 일부 스타일이 원본과 다를 수 있다(`canva-text` 클래스). 보관 후 원본과 나란히 비교한다.
- 동아리 학생이 만든 앱만 보관한다. 다른 사람의 Canva 사이트에는 쓰지 않는다.

## 4. 사이트 구조

```text
ai-club-2026/                      GitHub 저장소 (Drive 밖 로컬 폴더)
├─ index.html                      활동 안내
├─ gallery/
│   ├─ index.html                  팀 카드 4개
│   └─ project.html?team=team1     기획서 보기(발표 모드)
├─ apps/
│   ├─ team1/
│   │   ├─ index.html              보관본 (Canva SDK 제거)
│   │   ├─ original.html           받은 원본 그대로 (기록용, 링크하지 않음)
│   │   └─ thumb.png               썸네일 (820×1180 캡처)
│   └─ team2/ team3/ team4/
├─ data/
│   └─ projects.json               팀·작품 정보 (사이트가 읽는 유일한 데이터)
├─ tools/
│   ├─ archive_canva.py            보관 스크립트 (교사 PC에서 실행)
│   └─ README.md                   교사용 실행 방법
└─ assets/ (style.css, app.js)
```

- 폴더 이름은 `team1`~`team4`처럼 영문으로 쓴다. 한글 팀 이름은 `projects.json`에만 둔다(경로 문제 방지).
- 모든 페이지에 `<meta name="robots" content="noindex">`를 넣는다. 공개 사이트지만 검색 노출은 줄인다.
- 순수 HTML·CSS·JS만 쓴다. 빌드 도구와 서버는 쓰지 않는다. GitHub Pages(main 브랜치 루트)로 배포한다.

### 4-1. 활동 안내 (`index.html`)

ingu의 워크숍 안내처럼 학생이 보는 페이지다.

- 상단 메뉴: 1주차 · 사이 작업 · 2주차 · 갤러리
- 1주차: 팀 이름 정하기 → 문제 찾기 → 기획서 앱(링크·QR) → 요청문 복사 방법(전체 선택 → 길게 누르기) → Canva Code 만들기
- 요청 카드 내용(학습지 문서 D절)과 만들기 체크리스트(E절)
- 2주차: 게시 전 안전 점검(I절) → 웹사이트로 게시 → 제출 양식(Google Forms 링크) → 발표
- 맨 아래 출처: TCA Creator Camp(박오종 교사), 참고 구조 greatsong.github.io/ingu

### 4-2. 갤러리 (`gallery/index.html`)

- `data/projects.json`을 읽어 팀 카드 4개를 그린다.
- 카드 구성: 썸네일, 팀 이름, 앱 이름, 한 줄 소개, 버튼 3개
  - **[앱 실행]** → `apps/teamN/index.html` (새 탭)
  - **[Canva 원본]** → 게시 링크 (새 탭). 원본이 닫힌 뒤에는 "원본 종료" 표시
  - **[기획서 보기]** → `project.html?team=teamN`
- 상태별 표시

| status | 카드 표시 |
| --- | --- |
| `waiting` | 팀 이름만, "준비 중" (1주차 뒤 팀 이름만 들어간 상태) |
| `archived` | 버튼 3개 모두 |
| `archived-partial` | 버튼 3개와 "일부 기능은 원본에서만 작동" 배지 |
| `link-only` | 썸네일과 [Canva 원본]·[기획서 보기]만 |

### 4-3. 기획서 보기 (`gallery/project.html`)

- 원 워크숍 발표 모드를 줄인 4단계 화면이다: 01 문제 → 02 쓰는 사람 → 03 기능 3개 → 04 시험 문장과 앱 열기
- 04 화면에는 시험 문장("친구가 ① … ② … ③ …이 나오면 완성!")을 크게 보여 주고 [앱 실행] 버튼을 둔다. 발표 때 이 문장 순서대로 시연한다.
- 2주차 발표 때 화면에 띄워 쓸 수 있게 큰 글자와 [이전]/[다음] 버튼을 둔다.

## 5. 데이터와 보관 작업

### 5-1. `data/projects.json`

```json
{
  "club": "2026 AI 동아리",
  "term": "2026-2",
  "projects": [
    {
      "id": "team1",
      "teamName": "반짝반짝 팀",
      "status": "archived",
      "appName": "발표왕 뽑기",
      "tagline": "발표할 사람을 공평하게 뽑아 주는 앱",
      "problem": "발표할 사람을 정할 때 시간이 오래 걸린다",
      "features": ["번호 입력", "무작위 뽑기", "뽑힌 번호 빼기"],
      "testSentence": "친구가 ① 24를 입력하고 ② [뽑기]를 세 번 누르면 ③ 서로 다른 번호 3개가 나오면 완성!",
      "sourceUrl": "https://….my.canva.site/…",
      "sourceOpen": true,
      "archivedAt": "2026-11-03",
      "usesCanvaData": false
    }
  ]
}
```

- 1주차 뒤에는 `id`, `teamName`, `status: "waiting"`만 채운다.
- 학생 이름 필드는 두지 않는다.

### 5-2. 보관 스크립트 `tools/archive_canva.py`

**입력:** Google Forms 응답 시트를 내보낸 CSV(팀 이름, 앱 이름, 한 줄 소개, 불편, 기능 3개, 시험 문장, 게시 링크, 공개 동의)와 팀 이름 → `teamN` 대응표

**처리 (팀마다)**

1. 공개 동의가 없으면 건너뛴다.
2. 게시 링크 HTML을 받아 `_assets/remote/embed/codelet/<코드ID>/index.html` 경로를 찾는다.
3. `Referer: <게시 링크>`, `Sec-Fetch-Dest: iframe` 헤더로 앱 HTML을 받는다. 받은 그대로 `original.html`에 저장한다.
4. `src="/codelet/…"` 스크립트 태그를 지운다. `<meta name="robots" content="noindex">`와 출처 주석(원본 주소·보관 날짜)을 넣어 `index.html`로 저장한다.
5. 원본 스크립트에 `dataSdk`·`elementSdk` 같은 Canva SDK 사용 흔적이 있으면 `usesCanvaData: true`, `status: "archived-partial"`로 기록한다.
6. 헤드리스 브라우저(Playwright 또는 Edge)로 820×1180 캡처를 떠 `thumb.png`로 저장한다.
7. `projects.json`을 갱신한다.

**실패 대안:** 2~3단계가 실패하면 게시 페이지 화면만 캡처하고 `status: "link-only"`로 둔다. 로그에 실패 이유를 남긴다.

**실행 환경**

- Windows 교사 PC 기준이다.
- Windows curl·Python에서 인증서 폐기 확인 오류(`CRYPT_E_NO_REVOCATION_CHECK`)가 났다. curl은 `--ssl-no-revoke` 옵션을 쓰고, Python은 `requests`로 처리한다.
- 의존성은 `requests`와 선택 항목 `playwright`이다.

### 5-3. 교사 작업 순서

| 시점 | 작업 |
| --- | --- |
| 1주차 전 | 저장소 생성, 사이트 뼈대, 활동 안내 완성, `projects.json`에 `team1~4` waiting |
| 1주차 뒤 | 4팀 이름을 `projects.json`과 Google Forms 드롭다운에 입력 → 커밋·푸시 |
| 2주차 뒤 | 응답 CSV 내보내기 → 실명 여부 확인 → `archive_canva.py` 실행 → 로컬에서 4팀 보관본과 원본 비교 → 커밋·푸시 → 갤러리 주소 안내 |
| 권한 회수 전 | 보관본이 GitHub Pages에서 열리는지 다시 확인 |

## 6. 디자인·접근성 기준

- iPad 9세대(세로 810×1080, 가로 1080×810)에서 가로 스크롤이 없어야 한다.
- 본문 글자 18px 이상, 버튼은 손가락으로 누르기 쉬운 크기(높이 48px 이상)로 한다.
- 밝은 바탕에 강조색 1개를 쓴다. 색만으로 상태를 구분하지 않고 글자 배지를 함께 쓴다.
- 이미지에 대체 텍스트(앱 이름 + "첫 화면")를 넣는다.
- 필요하면 Edu-Nexus `DESIGN.md`의 색과 글꼴 기준을 따른다.

## 7. 완료 기준 (인수 테스트)

- [ ] `projects.json`에 waiting 팀만 있을 때 갤러리에 "준비 중" 카드 4개가 보인다.
- [ ] 예시 링크(교사 기획서 앱)로 `archive_canva.py`를 실행하면 `apps/teamN/index.html`이 만들어진다. 이 파일을 Canva에 접속하지 않고 열어도 1~3단계가 작동한다.
- [ ] 잘못된 링크를 넣으면 스크립트가 멈추지 않고 그 팀을 `link-only`로 남긴다.
- [ ] 갤러리 카드 버튼 3개가 각각 보관본, 원본, 기획서 보기를 연다.
- [ ] 기획서 보기 4단계를 [이전]/[다음]으로 넘길 수 있다.
- [ ] 모든 페이지에 noindex 메타가 있다. 어떤 화면에도 학생 이름이 없다.
- [ ] iPad 크기(810×1080) 캡처에서 잘림·겹침이 없다.

## 8. 남은 확인

- [ ] 학생 계정으로 게시한 앱도 같은 주소 구조(`*.my.canva.site/…/_assets/remote/embed/codelet/…`)인지 확인한다.
- [ ] 학생 앱이 Canva 저장 기능을 쓰는 경우가 있는지 확인한다(기능에 '저장'이 들어간 팀).
- [ ] GitHub 계정과 저장소 이름(`ai-club-2026` 제안)을 정한다.

## 9. 제작 준비 (2026-10-13 정리)

### 9-1. 이 PC 환경 점검 결과

| 항목 | 상태 | 할 일 |
| --- | --- | --- |
| Git | 2.55 설치됨 | **`user.name`·`user.email` 미설정** → 9-3에서 설정 |
| GitHub CLI(gh) | 2.100, `joonssem` 계정으로 로그인됨 | 이 계정을 쓸지 확인 |
| Python | 3.12 + `requests` 있음 | 보관 스크립트에 그대로 사용 |
| 썸네일 캡처 | Playwright 없음, Microsoft Edge 있음 | 새로 설치하지 않고 Edge 헤드리스로 캡처(이번 작업에서 검증) |
| Node.js / VS Code | 24 / 1.141 | 사이트는 빌드 도구 없이 순수 HTML이라 Node는 필수 아님 |

**Windows에서 이번에 겪은 문제 (스크립트에 반영할 것)**

- curl이 인증서 폐기 확인 오류(`CRYPT_E_NO_REVOCATION_CHECK`)로 실패했다 → curl은 `--ssl-no-revoke`를 쓰고, Python은 `requests`로 받는다.
- Edge 헤드리스 캡처를 연달아 실행하면 결과 파일이 갱신되지 않을 때가 있었다 → 실행마다 `--user-data-dir`을 따로 준다.
- 저장 경로에 역슬래시와 `$변수`를 섞으면 경로가 깨졌다 → 경로는 슬래시(`C:/…/thumb.png`)로 넘긴다.
- 한글 경로를 콘솔에 출력하면 깨진다(cp949) → 스크립트 출력은 UTF-8로 설정하거나 로그 파일로 남긴다.

### 9-2. 정할 것

| 항목 | 제안 | 비고 |
| --- | --- | --- |
| GitHub 계정 | `joonssem` (현재 로그인) | 사이트 주소: `https://joonssem.github.io/ai-club-2026/` |
| 저장소 이름 | `ai-club-2026` | 다음 학기 재사용 시 `ai-club-2027-1`처럼 새로 만든다 |
| 로컬 폴더 | `D:\Projects\ai-club-2026` (확정, 이미 만들어 둠) | **Google Drive 밖**(AGENTS.md: Drive 루트를 Git 저장소로 쓰지 않음) |
| 공개 범위 | public | 학생 이름 없음, 팀 이름만 |
| 커밋 작성자 이메일 | GitHub noreply 주소 | 공개 저장소에 학교 이메일이 남지 않게 한다 |

### 9-3. 시작 명령 (PowerShell, 한 번만)

```powershell
# 1) 커밋 작성자 설정 (joonssem의 noreply 주소)
git config --global user.name "joonssem"
git config --global user.email "187607730+joonssem@users.noreply.github.com"

# 2) Drive 밖 로컬 폴더(이미 있음)를 VS Code로 열기
code D:\Projects\ai-club-2026
```

저장소 생성(`gh repo create`)과 GitHub Pages 켜기는 뼈대가 만들어진 뒤 Claude에게 맡긴다(9-5 1단계).

### 9-4. 새 폴더로 가져갈 자료

| 자료 | 위치 | 쓰임 |
| --- | --- | --- |
| 이 명세 | `00_Obsidian_Vault/20_Lessons_Training/2026-AI동아리-5-6학년-내고민해결앱만들기-깃허브갤러리-명세.md` | 새 폴더에 `docs/SPEC.md`로 복사 |
| 학습지와 자료 | 같은 폴더 `…-학습지와자료.md` (C·D·E·I·H절) | 활동 안내 페이지 내용, Forms 열 이름 |
| 시험용 게시 링크 | `https://xn--o79ay59agzdiwb.my.canva.site/cmzttgv7h6ejhfvy` (교사 기획서 앱) | 보관 스크립트 인수 테스트 |
| 예시 화면 4장 | `03_Outputs/Slides/2026-AI동아리-내고민해결앱/compare_*.png`, `template_*.png` | 갤러리 화면을 미리 채워 볼 가짜 데이터 썸네일 |
| 디자인 기준(선택) | 루트 `DESIGN.md`, `scripts/design/tokens.css` | 색·서체 토큰 |

- 학습지·카드 PDF와 Forms 응답 CSV는 **저장소에 넣지 않는다**. 응답 CSV는 `tools/input/`에 두고 `.gitignore`로 제외한다(공개 저장소).

### 9-5. 작업 순서와 완료 기준

| 단계 | 시점 | 할 일 | 완료 기준 |
| --- | --- | --- | --- |
| 1 | 1주차 전 | 뼈대 생성(4절 구조), `projects.json`에 team1~4 waiting, noindex, `.gitignore`, 저장소 생성·Pages 켜기 | 공개 주소에서 "준비 중" 카드 4개가 보인다 |
| 2 | 1주차 전 | 활동 안내 페이지(`index.html`) 내용 채우기 | iPad 크기(810×1080) 캡처에 잘림 없음 |
| 3 | 1주차 전 | `archive_canva.py` 작성, 시험용 게시 링크로 인수 테스트 | 7절 두 번째·세 번째 항목 통과 |
| 4 | 1주차 전 | 가짜 데이터 4팀으로 갤러리·기획서 보기 시험 후 원래대로 되돌리기 | 7절 나머지 항목 통과 |
| 5 | 1주차 뒤 | 팀 이름 4개 입력 → 커밋·푸시 | 갤러리에 팀 이름 표시 |
| 6 | 2주차 뒤 | 응답 CSV로 보관 실행 → 원본과 비교 → 푸시 → 주소 안내 | 4팀 보관본이 공개 주소에서 열린다 |
| 7 | 권한 회수 전 | 보관본 재확인 → Edu-Nexus `03_Project_Notes/`에 저장소·배포 링크와 커밋 기준 기록 | 기록 노트 작성 |

### 9-6. 새 폴더에서 Claude에게 처음 줄 요청 (복사용)

```text
docs/SPEC.md는 학교 AI 동아리(5·6학년 4팀) 앱 갤러리 GitHub Pages 사이트의 명세야.
먼저 SPEC.md 전체를 읽고, 4절 구조대로 뼈대를 만들어 줘.

- 순수 HTML·CSS·JS, 빌드 도구 없음. 모든 페이지에 noindex 메타.
- data/projects.json에는 team1~team4를 status "waiting"으로만 넣어 줘. 학생 이름 필드는 만들지 마.
- .gitignore에 tools/input/, *.csv를 넣어 줘(Forms 응답이 공개 저장소에 올라가지 않게).
- 아직 archive_canva.py는 만들지 말고, 뼈대를 만든 뒤 브라우저(iPad 세로 810×1080) 캡처로 갤러리의 "준비 중" 카드 4개를 확인해 줘.
- 확인되면 gh로 public 저장소 ai-club-2026을 만들고 GitHub Pages(main 브랜치 루트)를 켜기 전에 나에게 물어봐 줘.
- SPEC.md 9-1의 Windows 주의사항을 따라 줘.
```

다음 단계(3단계 보관 스크립트)는 같은 대화에서 "SPEC.md 5-2절대로 tools/archive_canva.py를 만들고, 9-4의 시험용 링크로 7절 인수 테스트를 해 줘"라고 요청한다.
