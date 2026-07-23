# rs_dev UI Icon Pack

승인된 비규격 장비 UI/UX 시안에 맞춰 만든 오리지널 단색 SVG 아이콘입니다.

## 구성

- `icons/feature/`: 비규격 옵션, 비규격 개방옵션, 티어별 옵션
- `icons/ui/`: 메인, 테마, 검색, 가이드, 즐겨찾기, 펼치기 등
- `icons/equipment/`: 비규격 장비군 34종
- `icons/sprite.svg`: React에서 `<use>`로 불러오는 통합 스프라이트
- `react/Icon.tsx`: Vite/React용 컴포넌트
- `react/iconMap.ts`: 한국어 장비명 → sprite ID 매핑
- `react/icons.css`: 기본 스타일
- `preview.html`: 전체 아이콘 미리보기

## 권장 설치 위치

```text
web/public/icons/sprite.svg
web/src/components/Icon.tsx
web/src/components/iconMap.ts
web/src/icons.css
```

개별 SVG가 필요하면 `icons/feature`, `icons/ui`, `icons/equipment`를 그대로 복사합니다.

## React 사용 예

```tsx
import { Icon } from "./components/Icon";
import { equipmentIconId } from "./components/iconMap";

<Icon id="feature-instandard-option" size={28} />
<Icon id={equipmentIconId[item.item_group_name]} size={18} />
```

모든 SVG는 `currentColor`를 사용하므로 부모 요소의 `color`로 색을 변경할 수 있습니다.
