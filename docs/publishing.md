# Publishing to Zenodo (DOI 받기)

연구 메타데이터에 박을 영구 DOI를 발급받는 표준 절차.
GitHub repo와 Zenodo를 한 번만 연동하면, 이후 release 만들 때마다 자동으로 새 DOI가 발급됨.

## 사전 준비 (한 번만)

### 1. CITATION.cff 채우기
[`../CITATION.cff`](../CITATION.cff)에서 `TODO:` 표시 부분 채워넣기.
- `authors.family-names`, `given-names`, `affiliation`
- ORCID 있으면 `orcid:` 라인 주석 해제 후 ID 입력
- `repository-code`, `url`의 `USERNAME` 부분을 실제 GitHub 사용자명으로

### 2. ORCID 발급 (없다면)
- https://orcid.org/register — 1분, 무료
- 학술 활동에서 저자 영구 식별자. Zenodo 가입 시 연동하면 향후 release도 자동으로 본인 명의

## GitHub repo 생성

```bash
cd C:\Users\USER\Firic_regular

git init
git add .
git commit -m "Initial release: firic-rotation-counter v0.1.0"

# GitHub에서 빈 repo 생성 후 (예: firic-rotation-counter)
git remote add origin https://github.com/USERNAME/firic-rotation-counter.git
git branch -M main
git push -u origin main
```

## Zenodo 연동 (한 번만)

1. https://zenodo.org/login 접속
2. **Log in with GitHub** 클릭 → GitHub 권한 승인
3. Profile (우상단) → **GitHub** 메뉴
4. 목록에서 `firic-rotation-counter` 찾아 토글을 **ON**
   → Zenodo가 GitHub에 webhook 등록 완료

## Release 만들기 → DOI 자동 발급

GitHub repo 페이지에서:

1. 우측 **Releases** → **Create a new release**
2. **Choose a tag** → `v0.1.0` 입력 (없으니까 새로 만든다고 선택)
3. **Release title**: `v0.1.0 — Initial release`
4. **Describe this release** (예시):
   ```
   First public release.
   - Two-stage ROI pipeline (manual coarse + automatic flicker-based fine ROI)
   - HSV peak detection with smoke-aware interpolation
   - Validated on 227 manually-counted rows across 10 ROV dive videos
     (96.5% rotation match, 0.00% median RPM error)
   ```
5. **Publish release** 클릭

→ 1분 안에 Zenodo에서 자동으로:
- repo 전체를 archive (zip)
- DOI 발급 (예: `10.5281/zenodo.12345678`)
- 메타데이터를 CITATION.cff에서 읽어 채움

## DOI 확인 & 메타데이터 보완

1. https://zenodo.org/account/settings/github/ 의 repo 옆 DOI 클릭
2. 발급된 deposit 페이지에서:
   - Authors의 ORCID 확인
   - Keywords, License (MIT) 확인
   - **Communities** 등록 (선택): 관련 학술 community에 묶기
3. **Edit** → 필요한 메타데이터 보완 → **Publish**

## DOI를 어디에 박을지

### CITATION.cff 업데이트
```yaml
doi: "10.5281/zenodo.12345678"   # 주석 해제 + 실제 DOI 입력
```
커밋해서 push.

### README.md 업데이트
파일 상단:
```markdown
[![DOI](https://zenodo.org/badge/123456789.svg)](https://doi.org/10.5281/zenodo.12345678)
```
(badge URL은 Zenodo deposit 페이지에서 그대로 복사 가능)

"How to cite" 섹션의 `DOI_HERE`도 실제 DOI로 교체.

### 부서 연구결과 메타데이터
> 결과 도출 방법: 영상 기반 자동 회전수 측정 파이프라인을 사용함.
> 코드 및 알고리즘: https://doi.org/10.5281/zenodo.12345678
> (또는 인용 형식으로) AUTHOR (2026). firic-rotation-counter (v0.1.0).
> Zenodo. https://doi.org/10.5281/zenodo.12345678

## 향후 업데이트

코드 수정 후 새 버전 release 만들면:
- 새 DOI 발급 (예: `10.5281/zenodo.12345679`)
- **Concept DOI** (`10.5281/zenodo.12345677`)는 모든 버전을 포함 — 항상 최신 버전을 가리킴
- 보통 논문 인용에는 concept DOI를 권장 (Zenodo deposit 페이지에 둘 다 표시됨)

## 자주 묻는 것들

**Q. 코드 수정하면 DOI 다시 받아야 하나?**
A. 의미 있는 업데이트 시 release 만들면 새 DOI 자동 발급. 일반 commit은 무관.

**Q. private repo도 가능?**
A. Zenodo는 release 시점에 archive 만들므로 archive는 public이 됨.
   향후 repo를 private 전환해도 archive와 DOI는 영구 유지.

**Q. 데이터(영상)도 같이 올려야 하나?**
A. 코드만 올리면 됨. 영상 데이터를 공개 archive에 올리는 건 별도 결정.
   영상까지 공개할 거면 같은 Zenodo deposit에 묶거나, Pangaea(해양 데이터 전문) 같은 곳을 고려.

**Q. Software Heritage도 같이?**
A. Zenodo로 충분. SWH는 자동으로 GitHub repo snapshot도 만들기 때문에
   별도 작업 없이도 SWHID는 발급되고 있음 (https://archive.softwareheritage.org/).
