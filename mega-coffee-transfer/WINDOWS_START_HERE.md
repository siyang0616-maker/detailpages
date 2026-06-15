# Windows 작업 시작 메모

이 폴더는 메가커피 양도양수 상세페이지 초안입니다. 현재 구조는 빌드가 필요한 앱이 아니라 정적 HTML 상세페이지입니다.

## 바로 열기

- Windows: `open-preview.bat` 더블클릭
- 직접 열기: `index.html` 더블클릭
- 편집 시작: `index.html`, `README.md`, `images/`

## 현재 포함된 작업물

- `index.html`: 12컷 이미지를 세로로 미리보기 하는 브라우저 페이지
- `images/cut-01.png` ~ `images/cut-12.png`: 상세페이지 컷 이미지
- `README.md`: 제작 기준과 실사용 전 확인할 자료 목록

## Windows에서 확인한 상태

- HTML 문서 인코딩: UTF-8
- 이미지 경로: Windows/macOS 모두 동작하는 상대경로 `images/cut-xx.png`
- 별도 Node/npm 설치: 필요 없음
- 별도 빌드 명령: 필요 없음
- Git 상태 확인: GitHub Desktop 내장 Git 기준 `main...origin/main`

## 새 작업 전 체크리스트

- 실제 매장 사진, 매출 증빙, 권리금/보증금/월세/관리비 자료가 들어오면 README의 확인 필요 항목부터 갱신
- 이미지를 교체할 때는 기존 파일명 `cut-01.png` 형식을 유지하면 `index.html` 수정 없이 반영 가능
- 컷 수를 늘리거나 줄이면 `index.html`의 `<figure>` 목록도 같이 수정
- Git 명령이 PowerShell에서 안 되면 GitHub Desktop을 사용하거나 GitHub Desktop 내장 Git 경로를 사용

