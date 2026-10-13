# 교사용 도구: 보관 스크립트

`archive_canva.py`는 학생이 Canva Code로 게시한 앱을 받아 갤러리 보관본(`apps/teamN/`)을 만들고 `data/projects.json`을 고친다. 자세한 규칙은 `docs/SPEC.md` 3절, 5-2절, 5-4절에 있다.

## 준비 (한 번만)

- Python 3.12, `requests`, `truststore`가 필요하다. 없으면 `python -m pip install requests truststore`로 설치한다.
- Microsoft Edge가 있어야 썸네일을 만든다. 따로 설치할 것은 없다.

## 2주차 뒤: 4팀 보관하기

1. Google Forms 응답 시트에서 **파일 → 다운로드 → CSV**로 받는다.
2. 받은 파일을 `tools/input/responses.csv`로 옮긴다. 이 폴더와 `*.csv`는 저장소에 올라가지 않는다.
3. CSV를 열어 **실명·전화번호 같은 개인정보가 없는지** 확인한다.
4. 저장소 폴더(`D:\Projects\ai-club-2026`)에서 실행한다.

   ```powershell
   python tools/archive_canva.py --csv tools/input/responses.csv
   ```

5. 마지막 결과 표를 확인한다.

   | 상태 | 뜻 | 할 일 |
   | --- | --- | --- |
   | `archived` | 보관 성공 | 보관본과 원본을 나란히 열어 비교 |
   | `archived-partial` | 보관했지만 Canva 저장 기능을 씀 | 그 기능이 보관본에서 안 되는지 확인 |
   | `link-only` | 보관 실패, 링크만 남김 | 이유를 보고 학생에게 링크를 다시 받아 한 팀만 다시 실행 |

6. 로컬에서 확인한다: `python -m http.server 8000` → http://localhost:8000/gallery/
7. 문제가 없으면 커밋·푸시한다.

## 한 팀만 다시 보관하기

```powershell
python tools/archive_canva.py --url <게시 링크> --team team2
```

- 기존 보관본은 `tools/backup/<날짜시간>/team2/`로 옮겨진 뒤 새로 만든다.
- 새로 받기에 실패하면 이전 보관본을 그대로 둔다.
- 이 방법은 Forms 내용(앱 이름·소개 등)을 바꾸지 않는다. 앱 이름이 비어 있을 때만 앱 제목으로 채운다.

## 시험하기 (저장소를 건드리지 않음)

```powershell
python tools/archive_canva.py --url https://xn--o79ay59agzdiwb.my.canva.site/cmzttgv7h6ejhfvy --team team1 --out C:/Temp/archive-test
```

`--out` 폴더 안에 `apps/`, `data/projects.json`, `tools/logs/`가 만들어진다. 썸네일이 필요 없으면 `--no-thumb`을 붙인다.

## Canva 게시를 닫은 뒤

`data/projects.json`에서 그 팀의 `"sourceOpen"`을 `false`로 바꾸고 푸시한다. 갤러리의 [Canva 원본] 버튼이 [원본 종료]로 바뀐다.

## 문제가 생기면

- 로그: `tools/logs/archive-<날짜시간>.log` (저장소에 올라가지 않음)
- `CERTIFICATE_VERIFY_FAILED`: `truststore`가 설치되어 있는지 확인한다(학교망 인증서 문제).
- "필요한 열이 없습니다": Forms 질문 제목이 바뀌었는지 확인한다. 열 이름은 `docs/SPEC.md` 5-4절에 있다.
- 썸네일이 비어 있음: 앱이 늦게 그려지면 스크립트의 `WAIT_ARCHIVE`·`WAIT_PUBLISHED`(초)를 늘린다.
