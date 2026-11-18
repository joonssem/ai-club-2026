# ai-club-2026

2026년 AI 동아리 활동 안내와 작품 갤러리. 첫 화면은 SPIKE Prime 라인트레이서 활동이며, 이전 앱 만들기 안내는 `app-making.html`에 보관한다.
순수 HTML·CSS·JS로 만들고 GitHub Pages(main 브랜치 루트)로 배포한다.

- 명세: [docs/SPEC.md](docs/SPEC.md)
- 데이터: `data/projects.json` (학생 이름은 넣지 않는다. 팀 이름만)
- 로컬 미리보기: `python -m http.server 8000` 후 http://localhost:8000/
  (갤러리는 `fetch`로 JSON을 읽으므로 파일을 직접 열면 동작하지 않는다)
