# FORGE UI 디자인 시스템 Handoff

> 상태: 모든 customer·worker·operator UI의 필수 구현 기준
> 제품 기준: [제품·기술 아키텍처 Handoff](./HANDOFF_PRODUCT_AND_ARCHITECTURE.md)
> 담당 기준: [팀 역할 Handoff](./HANDOFF_TEAM_OWNERSHIP.md)

## 0. 디자인 방향

FORGE UI는 **따뜻한 ivory 배경 위에 선명한 cyan으로 핵심 행동과 상태를 안내하는 현대적이고 신뢰도 높은 B2B 제품**이어야 한다. Toss 제품처럼 사용자가 지금 알아야 할 가치와 다음 행동을 먼저 보여주고, Gemini 계열 UI처럼 긴 본문과 데이터도 편하게 읽혀야 한다.

Toss의 상표·비공개 TDS component를 복제한다는 뜻이 아니다. 다음 공개된 제품 원칙을 FORGE에 맞게 적용한다.

- 한 화면의 핵심을 하나로 분명하게 전달한다.
- 사용자가 치를 비용이나 복잡성 전에 얻는 가치를 설명한다.
- 질문과 선택지는 바로 이해하고 답할 수 있게 쓴다.
- 불필요한 단계를 줄이고 자연스러운 진행감을 만든다.
- 반복되는 UI 판단은 token과 primitive로 통일한다.

## 1. 절대 규칙

1. 전체 page background는 `#F8F5EB`를 사용한다.
2. primary brand/action color는 `#00ABC2`를 사용한다.
3. 기본 본문은 `16px`, 보조 본문과 metadata도 원칙적으로 `14px` 미만으로 만들지 않는다.
4. 모든 content를 각각 box/card로 감싸지 않는다.
5. 모든 section 사이에 `<hr>` 또는 border line을 반복하지 않는다.
6. 구조는 큰 제목, 여백, 정렬, typography, 제한된 background tone으로 만든다.
7. cyan 위 흰 글씨가 작은 text에서 contrast를 충족한다고 가정하지 않는다. primary fill의 text color는 실제 WCAG contrast 측정 후 dark ink를 기본으로 한다.
8. 색만으로 pass/fail/status를 구분하지 않는다. icon, label, reason을 함께 쓴다.
9. 생산 UI에서 simulated data를 실제 결과처럼 보이게 하지 않는다.
10. 지정한 token 없이 임의 hex, shadow, radius, font size를 component 안에 추가하지 않는다.

## 2. Visual principles

### 2.1 가치와 행동 우선

페이지 첫 viewport는 다음 질문에 답해야 한다.

- 지금 무엇을 보고 있는가?
- 사용자에게 어떤 가치가 있는가?
- 상태는 어떤가?
- 다음 핵심 행동은 무엇인가?

페이지 제목 아래에 여러 badge, 설명 card, metric card를 나열하지 않는다. 한 문장의 설명과 하나의 primary action을 우선한다.

### 2.2 Quiet canvas, clear focus

`#F8F5EB` 배경을 넓게 남긴다. 모든 빈 공간을 panel로 채우지 않는다. cyan은 다음에만 쓴다.

- primary action
- 현재 선택/활성 상태
- 핵심 progress
- 중요 interactive focus
- 브랜드를 기억시키는 제한된 강조

긴 본문 전체, 큰 table background, 여러 status에 cyan을 남용하지 않는다.

### 2.3 Group by proximity, not containers

관련 정보는 가까이 두고, 다른 정보는 충분한 vertical spacing으로 분리한다. card가 필요한지 판단하는 순서:

1. 이 영역이 독립적으로 click/tap 되는가?
2. 배경과 다른 interaction boundary가 필요한가?
3. drag, select, compare 대상인가?
4. 위험/권한/업로드처럼 명확한 경계가 필요한가?

모두 아니라면 card를 쓰지 않는다. heading + text + spacing으로 구성한다.

### 2.4 Progressive disclosure

고객에게 raw GPU log부터 보여주지 않는다. 먼저 `무엇이 완료됐는지`, `무엇이 필요한지`, `결과가 믿을 만한 이유`를 보여준다. 상세 metric, provenance, model version, trace는 disclosure 또는 detail route에서 제공한다.

## 3. Color tokens

### 3.1 Core palette

```css
:root {
  --forge-canvas: #F8F5EB;
  --forge-primary: #00ABC2;

  --forge-ink: #152126;
  --forge-ink-muted: #53636A;
  --forge-ink-subtle: #718087;

  --forge-surface: #FFFEF9;
  --forge-surface-soft: #F1EFE6;
  --forge-surface-cyan: #DDF6F8;

  --forge-primary-hover: #0095AA;
  --forge-primary-active: #007F91;
  --forge-primary-ink: #082F35;

  --forge-border: #D8D6CC;
  --forge-border-strong: #B9C0BF;
  --forge-focus: #007F91;

  --forge-success: #177A52;
  --forge-success-soft: #E1F3EA;
  --forge-warning: #9A6512;
  --forge-warning-soft: #FFF0CF;
  --forge-danger: #B33A3A;
  --forge-danger-soft: #FBE5E2;
  --forge-info: #246B8A;
  --forge-info-soft: #E1F1F7;
}
```

위 보조 색은 시작 token이다. 실제 foreground/background 조합은 automated contrast test를 통과해야 한다. 실패하면 brand hex를 바꾸지 말고 text color, tint, border 또는 component 구조를 조정한다.

### 3.2 사용 규칙

- `canvas`: body와 넓은 page 영역
- `surface`: modal, popover, dropdown, 실제 독립 interaction surface
- `surface-soft`: table header, code block, 선택되지 않은 control group
- `surface-cyan`: 현재 단계 또는 핵심 안내 한 곳
- `border`: input/table 구조에 필요한 최소 경계
- `ink-muted`: 보조 설명; 핵심 본문에 과용 금지
- success/warning/danger: status 의미에만 사용; 장식 금지

금지:

- pure white `#FFFFFF` card를 화면 전체에 타일처럼 반복
- primary cyan과 유사한 파랑을 임의 추가
- 검은색 `#000000` 대형 면
- pastel badge를 모든 metadata에 사용
- gradient를 기본 section background로 사용

## 4. Typography

### 4.1 Font family

```css
--font-sans: Inter, "Pretendard Variable", Pretendard,
             "Noto Sans KR", system-ui, -apple-system,
             "Segoe UI", sans-serif;
--font-mono: "JetBrains Mono", "SFMono-Regular", Consolas, monospace;
```

영문과 숫자는 Inter, 한국어는 Pretendard/Noto Sans KR fallback을 사용한다. font load 전후 layout shift를 줄이고 self-host 여부와 license를 확인한다.

### 4.2 Type scale

| Token | Desktop | Mobile | Weight | Line height | 용도 |
|---|---:|---:|---:|---:|---|
| `display` | 48px | 36px | 700 | 1.12 | landing 핵심 한 곳 |
| `h1` | 36px | 30px | 700 | 1.2 | page title |
| `h2` | 28px | 24px | 700 | 1.25 | 큰 section |
| `h3` | 22px | 20px | 650 | 1.35 | subsection |
| `title` | 18px | 18px | 650 | 1.4 | component/row title |
| `body` | 16px | 16px | 400 | 1.65 | 기본 본문 |
| `body-strong` | 16px | 16px | 600 | 1.55 | 중요한 본문 |
| `small` | 14px | 14px | 400 | 1.55 | 보조 설명, metadata |
| `label` | 14px | 14px | 600 | 1.35 | control label |
| `code` | 14px | 14px | 400 | 1.55 | IDs, schema, log |

12px text는 법적 각주라도 기본 사용하지 않는다. 정보가 길면 줄이거나 disclosure로 옮긴다. 14px 미만은 data visualization의 불가피한 축 label처럼 대체 표현이 있고 확대 가능한 경우에만 예외 review를 받는다.

### 4.3 읽기 폭과 문장

- 일반 본문 최대 폭: `68ch`
- 제품 설명/landing copy 최대 폭: `56ch`
- operator table은 page 폭을 사용할 수 있으나 cell text는 적절히 wrap한다.
- 한 문단을 지나치게 길게 쓰지 않는다.
- 기술 용어 뒤에 사용자가 취할 행동을 plain language로 설명한다.
- all caps와 letter spacing을 status 장식으로 남용하지 않는다.

## 5. Spacing, layout, shape

### 5.1 Spacing scale

```css
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-5: 24px;
--space-6: 32px;
--space-7: 48px;
--space-8: 64px;
--space-9: 96px;
```

- label ↔ control: 8px
- title ↔ description: 8–12px
- related rows: 12–16px
- subsection: 32–48px
- major section: 64–96px
- mobile major section: 48–64px

경계선을 추가하기 전에 spacing을 늘려 구분되는지 먼저 확인한다.

### 5.2 Page grid

- max content width: `1200px`
- reading page width: `760px`
- outer gutter: desktop 32–48px, tablet 24px, mobile 20px
- operator detail: 12-column grid
- customer form: 6–8-column 중심 영역 또는 `680px` 안쪽
- fixed sidebar를 쓸 때 main content가 14px 이하로 축소되지 않게 한다.

### 5.3 Radius and shadow

```css
--radius-control: 12px;
--radius-surface: 16px;
--radius-pill: 999px;
--shadow-popover: 0 12px 32px rgba(21, 33, 38, 0.12);
```

- input/button는 10–12px radius
- modal/popover는 16px
- card radius를 큰 화면 전체에 반복하지 않는다.
- shadow는 modal, dropdown, floating action처럼 elevation 의미가 있을 때만 사용한다.
- 일반 section을 shadow box로 만들지 않는다.

## 6. Composition patterns

### 6.1 허용되는 기본 page

```text
[Breadcrumb or compact context]

Page title                         Primary action
One-sentence value/status

        generous vertical space

Section heading
Direct content, list, table, or visualization

        generous vertical space

Section heading
Direct content
```

section 사이에 line/card가 없어도 제목 크기와 64px 안팎의 공간으로 관계가 보여야 한다.

### 6.2 Card가 허용되는 곳

- 클릭 가능한 order/delivery object
- upload dropzone
- 선택 가능한 pricing/coverage option
- modal/dialog/popover
- 하나의 독립적인 alert requiring action
- compare가 필요한 capture/replay media panel

한 화면의 모든 paragraph, metric, status, action을 각각 card로 만들지 않는다. card 안에 card를 중첩하지 않는다.

### 6.3 HR와 border

금지:

- 각 section마다 `<hr>`
- 모든 row의 위아래 border
- label, value, button 사이마다 vertical separator
- page 전체를 dashboard grid border로 분할

허용:

- table row 스캔에 필요한 아주 약한 한 방향 border
- input boundary
- active/focus/selection boundary
- sticky header와 scroll content의 관계를 나타내는 subtle border
- destructive/legal 영역의 명확한 경계

## 7. Components

### 7.1 Buttons

Primary:

- fill `#00ABC2`
- text는 검증된 `--forge-primary-ink` 기본
- height 44–48px
- label 15–16px, weight 600
- page/step당 원칙적으로 하나

Secondary:

- transparent 또는 subtle surface
- dark ink
- 필요한 경우에만 border

Tertiary:

- text action
- hover/focus 영역은 최소 44px 높이

Danger action은 cyan을 쓰지 않는다. 확인 dialog에서 결과와 복구 가능성을 plain language로 쓴다.

### 7.2 Inputs and forms

- label을 placeholder로 대체하지 않는다.
- input text 16px로 mobile zoom과 가독성을 보호한다.
- control height 최소 48px
- help text와 error는 14px 이상
- error는 field 바로 아래에 원인과 해결 행동을 쓴다.
- 한 번에 답할 수 있는 질문 단위로 묶는다.
- 긴 order form은 stepper로 나누되 진행을 숨기지 않는다.
- required/optional 표기를 일관되게 한다.
- 저장/업로드 진행 상태와 실패 복구를 명확히 보인다.

### 7.3 Status

status 표현은 `icon + label + optional detail`이다.

```text
Accepted — physics replay passed
Needs another capture — fingertips were hidden at first contact
Processing — reconstructing object motion
Simulated — GPU result is a test fixture
```

`FAILED`, `ERROR 0x...`만 고객에게 보여주지 않는다. operator detail에서 code와 evidence를 제공한다.

### 7.4 Metrics

모든 metric을 작은 card grid로 만들지 않는다. 우선순위가 높은 1–3개 숫자는 큰 typography로 한 row에 직접 배치하고, 나머지는 table/chart/detail로 보낸다.

metric에는 반드시 다음이 있다.

- 명확한 이름
- numerator/denominator 또는 단위
- 실제/sandbox/simulated source
- 마지막 calculation version 또는 scope
- 빈 값과 0의 구분

### 7.5 Tables

- header 14px 이상, body 14–16px
- 첫 column 또는 핵심 column을 시각적으로 강조
- 모든 cell에 pill badge를 넣지 않는다.
- 행 action은 명확한 button/menu label
- mobile에서는 우선순위 column을 남기고 detail sheet/route로 이동
- horizontal scroll이 있음을 보이게 한다.
- sticky header는 긴 operator table에만 사용한다.

### 7.6 Navigation

Customer portal의 top-level item은 적게 유지한다.

```text
Orders | Datasets | Account
```

Operator console:

```text
Queue | Orders | Collection | Quality | Deliveries
```

현재 위치는 cyan indicator + text weight로 표시한다. navigation item마다 box를 만들지 않는다.

### 7.7 Upload and capture

- capture instruction은 한 번에 하나의 핵심 행동을 먼저 보여준다.
- camera permission이 왜 필요한지 action 전에 설명한다.
- upload progress는 percentage, bytes, 취소/재시도 상태를 제공한다.
- dropzone만 제공하지 말고 file picker button을 함께 둔다.
- 성공한 upload receipt와 checksum verification state를 분리해 보여준다.
- raw 영상은 공개 URL로 preview하지 않는다.

### 7.8 Media and 3D evidence

- original, reconstruction overlay, robot replay를 명확히 label한다.
- sync play, scrub, phase marker, contact marker를 제공한다.
- color-only contact heatmap에는 legend와 numeric/label 대체를 둔다.
- preview가 없는 경우 empty/error state를 보여주며 blank black box로 두지 않는다.
- 기술 metric은 기본 summary와 expandable detail로 나눈다.

### 7.9 Dialogs and notifications

- modal은 사용자가 현재 맥락을 떠나면 안 되는 결정에만 쓴다.
- 성공 toast는 짧게, 실패는 사라지는 toast만 쓰지 말고 복구 action을 남긴다.
- destructive action은 대상, 결과, 복구 가능성을 확인한다.
- 불필요한 confirmation modal을 모든 step에 넣지 않는다.

## 8. 화면별 필수 구조

### 8.1 Landing

Hero는 다음을 한 번에 전달한다.

```text
Human demonstrations in.
Validated robot-ready datasets out.
```

- 한 개 primary CTA: `Define your robot task`
- 품질 loop를 간결한 visual/process로 설명
- 논문 수치를 FORGE 성능으로 표시하지 않음
- platform logo wall을 가치 설명보다 앞에 두지 않음
- 경쟁사 비방 또는 근거 없는 최고/최초 문구 금지

### 8.2 New order

정보 순서:

1. skill과 성공 상태
2. target robot/hand
3. object/coverage
4. validated output
5. rights/export
6. review/payment

각 step의 page title은 질문형 또는 결과형으로 이해하기 쉽게 쓴다. 기술 schema 이름은 help detail에 둔다.

### 8.3 Order detail

상단:

- order/skill 이름
- plain-language status
- 다음 action 또는 기다리는 대상
- 핵심 progress

본문:

- collection coverage
- quality funnel
- latest evidence/decision
- cost/output summary
- delivery readiness

모든 항목을 dashboard card로 만들지 않는다. coverage는 matrix, funnel은 flow/chart, decision은 narrative + evidence, artifact는 table을 사용한다.

### 8.4 Worker capture

- 작업 목적과 보상/권리를 먼저 설명
- consent는 읽을 수 있는 16px 본문
- 촬영 지시는 큰 단계와 visual example
- 현재 viewpoint/object/attempt를 분명히 표시
- permission, recording, preview, upload, receipt 상태를 각각 정확히 표현
- 실패 시 동일 파일 재업로드와 재촬영 중 선택 가능

### 8.5 Operator quality review

- 넓은 media/evidence 영역을 우선
- 오른쪽 또는 아래에 metric/threshold/reason
- decision action은 `Accept source`, `Reprocess`, `Request capture`, `Stop as infeasible`
- manual override에는 이유 입력 필수
- simulated/sandbox evidence banner를 항상 보이게 함
- raw JSON과 logs는 secondary detail

### 8.6 Delivery

- delivered episode 수와 validated 조건
- rights profile
- dataset version/checksum
- known limitations
- export format과 loader test
- signed download action

“완료”만 보여주지 않고 고객이 결과를 신뢰하고 바로 사용할 정보를 준다.

## 9. Responsive behavior

Breakpoints는 content에 맞춰 결정하되 시작 기준은 다음이다.

```css
--bp-sm: 640px;
--bp-md: 768px;
--bp-lg: 1024px;
--bp-xl: 1280px;
```

- mobile에서 body는 계속 16px다.
- touch target 최소 44×44px
- two-column form은 한 column으로 바뀐다.
- primary action은 내용 흐름에 맞춰 full-width 가능
- operator evidence는 media → summary → actions → detail 순서
- 중요한 action을 horizontal scroll 끝에 숨기지 않는다.
- 320px 폭에서도 핵심 journey가 작동한다.

## 10. Accessibility

필수:

- WCAG 2.2 AA를 목표로 한다.
- semantic heading 순서를 지킨다.
- native control을 우선 사용한다.
- keyboard만으로 모든 action 가능
- focus ring을 제거하지 않음
- dialog focus trap/return 정확
- form error summary와 field association
- video caption 또는 동등한 instruction text
- motion 감소 설정 존중
- chart/table의 text 대체
- status live region은 과도하게 announce하지 않음
- loading skeleton에 screen reader label 제공

Contrast CI:

- token pair automated test
- Storybook/a11y 또는 동등한 component scan
- 핵심 route Playwright axe scan
- cyan primary의 text/hover/disabled 조합 별도 검사

## 11. Motion

- motion은 상태 변화와 공간 관계 설명에만 사용한다.
- 기본 transition 150–220ms 범위의 짧고 자연스러운 움직임
- progress는 실제 state와 연결
- 무한 decorative animation 금지
- heavy blur/parallax/scroll-jacking 금지
- `prefers-reduced-motion`에서 transform animation 제거 또는 단순화
- GPU processing을 fake progress percentage로 표현하지 않는다. stage와 last update를 보여준다.

## 12. Content and UX writing

문구는 짧고 정직하고 행동 가능해야 한다.

권장:

```text
첫 접촉에서 손가락과 뚜껑 가장자리가 가려졌어요.
오른쪽 앞에서 한 번 더 촬영하면 복원 가능성이 높아져요.
```

금지:

```text
Processing failed.
Unknown error.
AI가 완벽한 데이터를 생성했습니다.
```

규칙:

- 내부 provider 이름보다 사용자 결과를 먼저 말한다.
- `AI-powered`, `4D`를 설명 없이 남용하지 않는다.
- blame language를 쓰지 않는다.
- 성공은 무엇이 검증됐는지 구체적으로 쓴다.
- 예상 시간 대신 현재 stage와 사용자가 할 수 있는 행동을 보여준다.
- 모든 technical claim은 실제 artifact/metric과 연결된다.

## 13. 구현 구조

```text
packages/ui/
├── tokens.css
├── theme.ts
├── primitives/
│   ├── Button
│   ├── Field
│   ├── Select
│   ├── Dialog
│   ├── Status
│   ├── Table
│   └── Disclosure
├── patterns/
│   ├── PageHeader
│   ├── ProgressNarrative
│   ├── CoverageMatrix
│   ├── QualityFunnel
│   ├── EvidenceViewer
│   └── EmptyState
└── stories/
```

구현 규칙:

- token은 CSS custom property와 typed theme에서 같은 source로 생성
- component는 임의 margin으로 page layout을 소유하지 않음
- page가 section spacing을 결정
- primitive와 product pattern을 분리
- variant 이름은 appearance보다 의미를 우선: `primary`, `danger`, `quiet`
- Storybook 또는 동등한 isolated preview에 default/hover/focus/disabled/error/loading을 둠

## 14. 금지 패턴 checklist

PR reviewer는 다음이 보이면 변경을 요청한다.

- [ ] page의 모든 section이 white rounded card인가
- [ ] card 안에 card가 중첩되는가
- [ ] heading 없이 HR만으로 구분하는가
- [ ] row마다 진한 border가 있는가
- [ ] 12px 이하 text가 있는가
- [ ] body가 14px로 축소되어 긴 문장을 담는가
- [ ] primary cyan 위 흰 작은 글씨를 contrast 확인 없이 쓰는가
- [ ] badge가 metadata 대부분을 차지하는가
- [ ] shadow가 일반 layout element마다 있는가
- [ ] 동일 화면에 primary button이 여러 개인가
- [ ] status가 색만으로 전달되는가
- [ ] simulated metric이 실제 metric처럼 보이는가
- [ ] raw provider error가 고객에게 그대로 노출되는가
- [ ] mobile에서 action이나 table 내용이 잘리는가

## 15. UI Definition of Done

한 화면은 다음을 모두 만족해야 완료다.

- `#F8F5EB` canvas와 `#00ABC2` primary token 사용
- 본문 16px, 보조/metadata 14px 이상
- card/HR 금지 원칙을 구조적으로 지킴
- 한 화면의 핵심 가치와 primary action이 분명함
- desktop/mobile/keyboard journey 동작
- loading, empty, error, partial, permission-denied 상태 존재
- 실제/sandbox/simulated truth 표시
- contrast, axe, focus, semantic heading QA 통과
- 한국어/영어 긴 문자열과 큰 숫자에서도 layout 유지
- 고객 데이터/PII가 screenshot fixture 또는 public story에 없음
- reviewer가 기능과 함께 visual hierarchy를 확인할 수 있는 screenshot/video evidence 제공

## 16. 에이전트용 UI 작업 지시

```text
FORGE UI를 구현하기 전에 HANDOFF_UI_DESIGN_SYSTEM.md 전체를 읽어라.
packages/ui의 token과 primitive를 먼저 확인하고 임의 색·font·radius를 추가하지 마라.

배경 #F8F5EB, primary #00ABC2, 기본 본문 16px와 최소 14px 보조 글자를
지켜라. 모든 내용을 card에 넣거나 HR로 section을 반복 분리하지 마라.
heading, 여백, 정렬, typography로 위계를 만든 뒤 interaction boundary가 실제로
필요할 때만 surface/card/border를 써라.

각 화면은 loading/empty/error/partial/simulated/mobile/keyboard 상태까지 구현하고,
primary cyan의 contrast와 전체 접근성을 자동 및 시각 QA하라. PR에는 desktop과
mobile screenshot, 접근성 결과, 사용한 token, 금지 패턴 self-check를 첨부하라.
```

## 17. 공개 참고 원칙

- Toss Design 글 모음: <https://toss.tech/category/design>
- Value first, cost later: <https://toss.tech/article/value-first-cost-later>
- Easy to answer: <https://toss.tech/article/insurance-claim-process>
- 디자인 시스템 다시 생각해보기: <https://toss.tech/article/44097>

이 자료는 방향과 제품 사고의 참고다. FORGE token과 component는 이 문서가 권위이며 Toss의 비공개 asset, source, 상표 표현을 복제하지 않는다.
