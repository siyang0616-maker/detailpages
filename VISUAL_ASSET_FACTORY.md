# Visual Asset Factory

이 저장소의 새 기준은 “AI가 상상한 가짜 매장 이미지 생성”이 아니라, 실제 사진 자산을 안전하게 관리하고 블로그용 이미지로 재가공하는 내부 생산 시스템입니다.

## 핵심 원칙

- 원본 사진은 절대 덮어쓰지 않습니다.
- 출처·권리·위험·승인 상태가 없는 사진은 최종 렌더링에 쓰지 않습니다.
- `review_required` 또는 `disallowed` 자산은 자동 출력에서 차단됩니다.
- 마스킹이 필요한 자산은 마스킹 결과가 기록되어야 렌더링에 들어갑니다.
- 생성형 이미지 프롬프트보다 실사진 변환과 템플릿 렌더링을 우선합니다.

## 기본 폴더

```text
data/
asset_library/
raw/
reviewed/
approved/
rejected/
transformed/
manifests/
asset-index.jsonl
projects/
{project_slug}/manifest.json
```

## 사용 흐름

1. 사진을 `data/asset_library/raw/브랜드명/카테고리/` 아래에 넣습니다.
2. 자산을 인식하고 `asset_id`를 부여합니다.

```bash
python -m detailpages.cli ingest-assets \
  --input ./data/asset_library/raw \
  --output ./data/asset_library/manifests/asset-index.jsonl
```

3. 리뷰표를 만듭니다.

```bash
python -m detailpages.cli make-review-sheet \
  --asset-index ./data/asset_library/manifests/asset-index.jsonl
```

4. `data/asset_library/review-sheet.csv`에서 권리 상태, 승인 여부, 위험도를 수정합니다.
5. 리뷰표를 반영합니다.

```bash
python -m detailpages.cli approve-assets \
  --review-sheet ./data/asset_library/review-sheet.csv
```

6. 마스킹이 필요한 자산을 처리합니다.

```bash
python -m detailpages.cli mask-assets \
  --asset-index ./data/asset_library/manifests/asset-index.jsonl
```

7. 프로젝트 manifest를 수정합니다.

```text
data/projects/example-compose-transfer/manifest.json
```

8. 미리보기를 만듭니다.

```bash
python -m detailpages.cli render-preview \
  --manifest ./data/projects/example-compose-transfer/manifest.json
```

9. 전체 이미지를 만듭니다.

```bash
python -m detailpages.cli render-full \
  --manifest ./data/projects/example-compose-transfer/manifest.json
```

10. QA를 실행합니다.

```bash
python -m detailpages.cli qa \
  --output ./outputs/example-compose-transfer/latest
```

## 출력물

`render-full`은 아래 파일을 생성합니다.

- `cut-01.jpg`부터 `cut-10.jpg` 또는 `cut-12.jpg`
- `contact-sheet.jpg`
- `blog-caption-copy.md`
- `naver-upload-draft.md`
- `qa-report.json`
- `asset-usage-report.json`

`asset-usage-report.json`에는 어떤 원본 자산을 썼는지, 변환 파일 경로, 마스킹 기록, 위험도, 권리 상태, QA 통과 여부가 남습니다.

## 현재 한계

얼굴, 번호판, 전화번호, 워터마크 감지는 아직 완전한 컴퓨터비전/OCR이 아니라 보수적인 메타데이터와 영역 마스킹 중심입니다. 확신이 낮은 이미지는 `review_required`로 남겨 사람이 확인하는 방식이 안전합니다.
