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

- Parsed blocks: `176`
- Parsed non-empty rows: `7749`
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
- `11,0` rows=801
- `11,1` rows=546
- `11,3` rows=858

Row group values:
- `1` rows=3433
- `2` rows=2848
- `3` rows=1171
- `4` rows=242
- `5` rows=55

Open slot candidate values:
- `1` rows=466
- `2` rows=466
- `3` rows=466
- `4` rows=466
- `5` rows=466
- `6` rows=466
- `7` rows=466
- `8` rows=465
- `9` rows=438
- `10` rows=400
- `11` rows=386
- `12` rows=371
- `13` rows=348
- `14` rows=331
- `15` rows=311
- `16` rows=281
- `17` rows=214
- `18` rows=195
- `19` rows=137
- `20` rows=121
- `21` rows=108
- `22` rows=85
- `23` rows=63
- `24` rows=55
- `25` rows=42
- `26` rows=39
- `27` rows=36
- `28` rows=25
- `29` rows=21
- `30` rows=14
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
