# Red Stone Converter Data Trace

## Source

- Local data folder: `/mnt/c/game/Red Stone/Data`
- Original files were read only.
- Web data was not used.

## Confirmed Links

| effect_id | capa evidence | decoded item.dat item names | status |
|---:|---|---|---|
| 920 | 개방옵션변환창생성 | 개방옵션 변환창 생성 | 개방 옵션 변환창 생성 | 개방 옵션 변환기; 개방 옵션 변환기[E] | confirmed_name_and_effect |
| 935 | 개방옵션변환창생성2 | 개선된 개방 옵션 변환창 생성 | 개선된 개방 옵션 변환창 생성 | 개선된 개방 옵션 변환기; 개선된 개방 옵션 변환기[E] | confirmed_name_and_effect |
| 954 | 개방옵션변환창생성3 | 약화된 개방옵션 변환창 생성 | 약화된 개방 옵션 변환창 생성 | 모조 개방 옵션 변환기; 모조 개방 옵션 변환기[E]; 모조 개방 옵션 변환기[거래불가] | confirmed_name_and_effect |
| 966 | 개방옵션변환창생성4 | 협회 전용 개방옵션 변환창 생성 | 협회 전용 개방 옵션 변환창 생성 | 개방 옵션 변환기[협회] | confirmed_name_and_effect |
| 1020 | 개방옵션변환창생성5 | 향상된 개방 옵션 변환창 생성 | 향상된 개방 옵션 변환창 생성 | not found | effect_only_no_decoded_item_name_found |

## Confirmed Equipment IDs

From `capa.dat` option `958`:

- `0` = 무기
- `1` = 보조무기
- `2` = 갑옷
- `3` = 장갑
- `4` = 헬멧
- `5` = 귀걸이/망토
- `6` = 목걸이
- `7` = 벨트
- `8` = 신발
- `9` = 반지

## item_option_open.dat

- Retained blocks: `146`
- Retained non-empty rows: `5544`
- `section_type=11` blocks are intentionally excluded from derived trace outputs.
- These rows are confirmed binary table rows, but their block header axes are not yet linked to Korean converter names.

Section pairs observed:
- `7,0` rows=702
- `7,1` rows=426
- `8,0` rows=816
- `8,1` rows=501
- `8,2` rows=735
- `9,0` rows=946
- `9,1` rows=603
- `9,3` rows=815

Row group values:
- `1` rows=2736
- `2` rows=2069
- `3` rows=739

Open slot candidate values:
- `1` rows=348
- `2` rows=348
- `3` rows=348
- `4` rows=348
- `5` rows=348
- `6` rows=348
- `7` rows=348
- `8` rows=347
- `9` rows=328
- `10` rows=290
- `11` rows=277
- `12` rows=267
- `13` rows=248
- `14` rows=237
- `15` rows=216
- `16` rows=192
- `17` rows=150
- `18` rows=141
- `19` rows=85
- `20` rows=77
- `21` rows=62
- `22` rows=50
- `23` rows=34
- `24` rows=30
- `25` rows=23
- `26` rows=19
- `27` rows=17
- `28` rows=10
- `29` rows=5
- `30` rows=2
- `31` rows=1

## UI Text Evidence

- `textData2.dat` index `903`: 해당 아이템은 개방 옵션 변경을 진행 할 수 없습니다.
- `textData2.dat` index `921`: <c:LTRED>- 불타는 / 모조 / 협회 개방 옵션 변환기의 옵션이 적용된 장비에는 잠금 사용 불가<n>
- `textData2.dat` index `2001`: 개방 옵션 변경

## Raw Folder Scan

- Files with raw term/id hits: `14`
- InstandardEquip MessagePack matches: `0`
- Raw numeric hits in unrelated binary files are not treated as evidence unless a nearby string or known structure supports them.

## Current Boundary

- Confirmed: converter item names in decoded `item.dat` map to effect ids `920`, `935`, `954`, `966` by nearby binary records.
- Confirmed: `capa.dat` defines those effect ids as open-option conversion window effects.
- Confirmed: `capa.dat` also defines `1020` as `향상된 개방 옵션 변환창 생성`, but no decoded item name is linked to it in this pass.
- Confirmed: `item_option_open.dat` contains the open-option conversion option table.
- Not confirmed yet: which `item_option_open.dat` section type/group corresponds to each converter item name.
- Not found in current pass: a direct local table row that stores both converter effect id/name and `item_option_open.dat` section type/group together.
