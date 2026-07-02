# 통합 레퍼런스 — 가중치 & 필드 딕셔너리 (v2.0)

> 이 파일은 새로운 설계 내용이 아니라 **이미 여러 문서에 흩어져 있는 숫자와 필드를 한 곳에 모은 조회용 문서**다. 설계 근거·문항 원문·이유는 각 원본 문서에 있고, 여기서는 "그래서 정확히 어떤 값을, 어떤 필드에" 만 빠르게 찾을 수 있게 정리한다. 실제 구현(마이그레이션, API 스키마, 알고리즘 코드) 작업 시 이 파일 하나만 열어도 되는 걸 목표로 한다.
>
> 원본: [00-overview.md](/docs/overview) · [01-questionnaire-a-personality.md](/docs/questionnaire-a) · [02-questionnaire-b-profile.md](/docs/questionnaire-b) · [03-questionnaire-c-trip.md](/docs/questionnaire-c) · [restaurant-recommendation-design.md](/docs/restaurant-recommendation-design)

---

## 목차

1. [16개 유형 마스터 테이블 (가중치 전체)](#1-16개-유형-마스터-테이블-가중치-전체)
2. [가중치 계산 공식 & 계수](#2-가중치-계산-공식--계수)
3. [필드 딕셔너리 — user_travel_persona (Part A 산출물)](#3-필드-딕셔너리--user_travel_persona-part-a-산출물)
4. [필드 딕셔너리 — user_preference_profile (Part B, 46개)](#4-필드-딕셔너리--user_preference_profile-part-b-46개)
5. [필드 딕셔너리 — user_trip_contexts (Part C)](#5-필드-딕셔너리--user_trip_contexts-part-c)
6. [크로스 레퍼런스](#6-크로스-레퍼런스)
7. [Open Question — 원문항 응답 로그](#7-open-question--원문항-응답-로그)

---

## 1. 16개 유형 마스터 테이블 (가중치 전체)

각 유형 파일(`types/*.md`)의 "4축 프로필"과 "추천 알고리즘 가중치 프로파일" 표를 16행 하나로 합쳤다. 축 값은 대표 예시값(`0.75`/`0.25`)이고, 실제 서비스에서는 사용자별 연속값을 그대로 쓴다 (2절 공식 참고).

| 코드 | 유형명 | social | adventure | experience | flow | taste | mood | price | novelty | menu_match | popularity | buzz | 예약보너스 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `SAEF` | 페스티벌 수달 | 0.75 | 0.75 | 0.75 | 0.75 | 0.200 | 0.138 | 0.062 | 0.150 | 0.200 | 0.175 | 0.075 | 0.112 |
| `SAEJ` | 갈라 플라밍고 | 0.75 | 0.75 | 0.75 | 0.25 | 0.200 | 0.138 | 0.062 | 0.150 | 0.200 | 0.175 | 0.075 | 0.188 |
| `SAVF` | 백패커 원숭이 | 0.75 | 0.75 | 0.25 | 0.75 | 0.200 | 0.062 | 0.138 | 0.150 | 0.200 | 0.175 | 0.075 | 0.112 |
| `SAVJ` | 플래너 꿀벌 | 0.75 | 0.75 | 0.25 | 0.25 | 0.200 | 0.062 | 0.138 | 0.150 | 0.200 | 0.175 | 0.075 | 0.188 |
| `SCEF` | VIP 사자 | 0.75 | 0.25 | 0.75 | 0.75 | 0.200 | 0.138 | 0.062 | 0.050 | 0.200 | 0.175 | 0.075 | 0.112 |
| `SCEJ` | 볼룸 백조 | 0.75 | 0.25 | 0.75 | 0.25 | 0.200 | 0.138 | 0.062 | 0.050 | 0.200 | 0.175 | 0.075 | 0.188 |
| `SCVF` | 동네 참새 | 0.75 | 0.25 | 0.25 | 0.75 | 0.200 | 0.062 | 0.138 | 0.050 | 0.200 | 0.175 | 0.075 | 0.112 |
| `SCVJ` | 패밀리 펭귄 | 0.75 | 0.25 | 0.25 | 0.25 | 0.200 | 0.062 | 0.138 | 0.050 | 0.200 | 0.175 | 0.075 | 0.188 |
| `PAEF` | 노마드 여우 | 0.25 | 0.75 | 0.75 | 0.75 | 0.200 | 0.138 | 0.062 | 0.150 | 0.200 | 0.125 | 0.025 | 0.112 |
| `PAEJ` | 탐험가 매 | 0.25 | 0.75 | 0.75 | 0.25 | 0.200 | 0.138 | 0.062 | 0.150 | 0.200 | 0.125 | 0.025 | 0.188 |
| `PAVF` | 로드 낙타 | 0.25 | 0.75 | 0.25 | 0.75 | 0.200 | 0.062 | 0.138 | 0.150 | 0.200 | 0.125 | 0.025 | 0.112 |
| `PAVJ` | 딜헌터 다람쥐 | 0.25 | 0.75 | 0.25 | 0.25 | 0.200 | 0.062 | 0.138 | 0.150 | 0.200 | 0.125 | 0.025 | 0.188 |
| `PCEF` | 힐링 판다 | 0.25 | 0.25 | 0.75 | 0.75 | 0.200 | 0.138 | 0.062 | 0.050 | 0.200 | 0.125 | 0.025 | 0.112 |
| `PCEJ` | 료칸 거북이 | 0.25 | 0.25 | 0.75 | 0.25 | 0.200 | 0.138 | 0.062 | 0.050 | 0.200 | 0.125 | 0.025 | 0.188 |
| `PCVF` | 호캉스 코알라 | 0.25 | 0.25 | 0.25 | 0.75 | 0.200 | 0.062 | 0.138 | 0.050 | 0.200 | 0.125 | 0.025 | 0.112 |
| `PCVJ` | 체크리스트 비버 | 0.25 | 0.25 | 0.25 | 0.25 | 0.200 | 0.062 | 0.138 | 0.050 | 0.200 | 0.125 | 0.025 | 0.188 |

이 표는 파이썬으로 2절 공식에 축 값을 대입해 기계적으로 계산한 값이다 (수작업 전사 아님) — 실제 구현 시 이 표를 그대로 시드 데이터/단위테스트 fixture로 써도 된다.

---

## 2. 가중치 계산 공식 & 계수

```
weight(feature, persona) = base_weight(feature) + k(feature) × (axis_score(persona) - 0.5)
```

| 피처 | base | k | 연동 축 | 축 방향 |
|---|---|---|---|---|
| `taste_ratio` | 0.20 | 0 | 없음 (항상 동일) | – |
| `mood_ratio` | 0.10 | +0.15 | `experience_score` | 높을수록(Experience) ↑ |
| `price_ratio` | 0.10 | −0.15 | `experience_score` | 높을수록(Experience) ↓ (Value일수록 ↑) |
| `novelty_score` | 0.10 | +0.20 | `adventure_score` | 높을수록(Adventure) ↑ |
| `menu_match` | 0.20 | 0 | 없음 (사용자 취향 직접 반영) | – |
| `popularity_norm` | 0.15 | +0.10 | `social_score` | 높을수록(Social) ↑ |
| `buzz_ratio` | 0.05 | +0.10 | `social_score` | 높을수록(Social) ↑ |
| 예약 보너스(`context_bonus` 구성 요소) | 0.15 | −0.15 | `flow_score` | 높을수록(Flow) ↓ (Plan일수록 ↑) |

- 실제 계산에는 **연속 축 점수**를 쓴다. 1절 표의 0.75/0.25는 유형 대표값일 뿐이고, 오버라이드가 있으면(Part C 5절) `effective_*_score`로 대체된다.
- 이 표의 출처는 [restaurant-recommendation-design.md](/docs/restaurant-recommendation-design) 4.4절/6.4절이다. 값을 바꿀 일이 생기면 **그 문서를 1차로 수정**하고, 이 파일과 1절 마스터 테이블을 재생성한다 (수동 동기화 필요 — 7절 참고).

---

## 3. 필드 딕셔너리 — `user_travel_persona` (Part A 산출물)

Part A 40문항([01-questionnaire-a-personality.md](/docs/questionnaire-a))을 채점한 결과만 저장한다. 개별 문항 응답 자체는 저장하지 않는다(7절 Open Question 참고).

| 필드 | 타입 | 값/범위 | 필수 | 설명 |
|---|---|---|---|---|
| `user_id` | BIGINT (PK, FK) | – | ✅ | 1 사용자 1 레코드 |
| `social_score` | NUMERIC(4,3) | 0.000~1.000 | ✅ | 0=Private ~ 1=Social |
| `adventure_score` | NUMERIC(4,3) | 0.000~1.000 | ✅ | 0=Classic ~ 1=Adventure |
| `experience_score` | NUMERIC(4,3) | 0.000~1.000 | ✅ | 0=Value ~ 1=Experience |
| `flow_score` | NUMERIC(4,3) | 0.000~1.000 | ✅ | 0=Plan ~ 1=Flow |
| `persona_code` | CHAR(4) | 16가지 중 하나 (예: `SAEF`) | ✅ | 4개 축을 0.5 기준 이분화한 표시용 코드. 1절 표의 코드 순서와 동일 |
| `survey_version` | SMALLINT | 1, 2, … | ✅ | 현재 `2` (Part A v2.0) |
| `computed_at` | TIMESTAMPTZ | – | ✅ | 마지막 채점 시각 |

---

## 4. 필드 딕셔너리 — `user_preference_profile` (Part B, 46개)

Part B([02-questionnaire-b-profile.md](/docs/questionnaire-b)) 문항이 그대로 저장되는 필드다. `Q#`는 원본 문항 번호(예: B1-4)를 가리킨다. SMALLINT 척도 필드는 전부 **1(낮음)~5(높음)** 정수로 인코딩한다.

### B-1 음식 (14개)

| 필드 | 타입 | 값 | 필수 | Q# |
|---|---|---|---|---|
| `food_category_preferences` | TEXT[] | 한식·중식·일식·양식·동남아음식·인도음식·중동음식·멕시코남미음식·카페/디저트·술집/포차·채식/비건·해산물전문 (최대 5개) | ✅ | B1-1 |
| `food_category_top` | TEXT | (위 목록 중 1개) | | B1-2 |
| `food_category_avoid` | TEXT[] | (위 목록과 동일) | | B1-3 |
| `allergies` | TEXT[] | 난류·우유·메밀·땅콩·대두·밀·고등어·게·새우·돼지고기·복숭아·토마토·아황산류·호두·닭고기·쇠고기·오징어·조개류·잣·기타(직접입력) | ✅ | B1-4 |
| `dietary_restriction` | TEXT | 없음·할랄·코셔·힌두교(소고기제외)·락토오보채식·락토채식·비건·기타 | | B1-5 |
| `spice_tolerance` | SMALLINT(1~5) | 1=전혀 못 먹음 ~ 5=아주 잘 먹음 | ✅ | B1-6 |
| `alcohol_preference` | TEXT | 안 마심·가볍게·즐겨 마심 | | B1-7 |
| `interest_in_alcohol_experience` | TEXT | 관심 있음·상관없음·관심 없음 | | B1-8 |
| `raw_food_tolerance` | TEXT | 잘 먹음·괜찮음·피함 | ✅ | B1-9 |
| `food_texture_avoid` | TEXT[] | 내장류·물컹한 식감·뼈 있는 생선·과도한 기름기·기타 | | B1-10 |
| `meal_pattern` | TEXT | 아침 꼭 챙김·아침 거의 안 먹음·브런치 선호·야식파 | | B1-11 |
| `solo_dining_comfort` | TEXT | 전혀 상관없음·가능은 함·혼자는 불편함 | | B1-12 |
| `local_vs_chain_preference` | SMALLINT(1~5) | 1=로컬 개인식당 ~ 5=익숙한 프랜차이즈 | | B1-13 |
| `default_meal_budget_tier` | SMALLINT(1~5) | 1=1만원 이하, 2=1~2만원, 3=2~4만원, 4=4~7만원, 5=7만원 이상 | | B1-14 |

### B-2 숙소 (10개)

| 필드 | 타입 | 값 | 필수 | Q# |
|---|---|---|---|---|
| `lodging_type_preferences` | TEXT[] | 호텔·리조트/풀빌라·게스트하우스/호스텔·한옥 등 전통숙소·독채 펜션·캠핑/글램핑·공유숙박 (최대 3개, **배열 순서 = 우선순위**) | ✅ | B2-1 |
| `room_type_preference` | TEXT | 침대형·온돌형·상관없음 | | B2-2 |
| `lodging_amenity_requirements` | TEXT[] | 수영장·조식 포함·온천/스파·헬스장·주차·반려동물 동반 가능·무장애(휠체어) 접근·키친/조리시설 | ✅ | B2-3 |
| `smoking_preference` | TEXT | 비흡연자·금연룸 필수·흡연 가능한 곳 선호·상관없음 | ✅ | B2-4 |
| `noise_sensitivity` | SMALLINT(1~5) | 1=전혀 민감하지 않음 ~ 5=매우 민감함 | | B2-5 |
| `view_preference` | TEXT[] | 오션뷰·마운틴뷰·시티뷰·특별히 상관없음 | | B2-6 |
| `checkin_flexibility_need` | TEXT | 자주 필요·가끔 필요·거의 필요 없음 | | B2-7 |
| `loyalty_programs` | TEXT[] | 메리어트 본보이·힐튼 아너스·IHG 원·아코르·없음·기타 | | B2-8 |
| `default_lodging_budget_tier` | SMALLINT(1~5) | 1=5만원 이하, 2=5~10만원, 3=10~20만원, 4=20~40만원, 5=40만원 이상 | | B2-9 |
| `lodging_top_priority` | TEXT | 위치·가격·청결도·분위기/인테리어·부대시설 | ✅ | B2-10 |

### B-3 신체·접근성·건강 (6개)

| 필드 | 타입 | 값 | 필수 | Q# |
|---|---|---|---|---|
| `mobility_assistance` | TEXT | 사용 안 함·휠체어·기타 보조기구(직접입력) | ✅ | B3-1 |
| `pregnancy_or_infant` | TEXT | 해당 없음·임신 중·영유아 동반 | | B3-2 |
| `health_notes` | TEXT (암호화 권장) | 자유입력 | | B3-3 |
| `physical_activity_tolerance` | SMALLINT(1~5) | 1=낮음 ~ 5=높음 | | B3-4 |
| `motion_sickness` | BOOLEAN | 있음/없음 | | B3-5 |
| `pet_owner_status` | TEXT | 기르지 않음·기르지만 여행엔 안 데려감·기르고 자주 함께 여행함 | | B3-6 |

### B-4 동행 기본 성향 (4개)

| 필드 | 타입 | 값 | 필수 | Q# |
|---|---|---|---|---|
| `default_companion_type` | TEXT | 혼자·연인·친구·가족(아이 동반)·부모님(시니어 동반)·반려동물 | ✅ | B4-1 |
| `child_age_range` | TEXT[] | 영유아(0~3세)·유아동(4~7세)·초등(8~13세)·청소년(14~19세) | | B4-2 |
| `senior_travel_notes` | TEXT | 자유입력 | | B4-3 |
| `pet_travel_frequency` | TEXT | 자주 함·가끔 함·안 함 | | B4-4 |

### B-5 이동·로지스틱 기본 성향 (5개)

| 필드 | 타입 | 값 | 필수 | Q# |
|---|---|---|---|---|
| `transport_preference` | TEXT[] | 도보·대중교통·렌터카(직접운전)·택시/차량호출·투어버스 | | B5-1 |
| `flight_direct_preference` | BOOLEAN | 직항 필수(true)/경유 상관없음(false) | | B5-2 |
| `jetlag_sensitivity` | SMALLINT(1~5) | 1=전혀 아님 ~ 5=매우 민감 | | B5-3 |
| `language_confidence` | SMALLINT(1~5) | 1=자신 없음 ~ 5=매우 자신 있음 | | B5-4 |
| `preferred_region_group` | TEXT[] | 동아시아·동남아·유럽·북미·중남미·중동·아프리카·오세아니아·국내 | | B5-5 |

### B-6 예산·소비 기본 성향 (3개)

| 필드 | 타입 | 값 | 필수 | Q# |
|---|---|---|---|---|
| `top_spending_priority` | TEXT | 음식·숙소·쇼핑·액티비티/체험·교통 | ✅ | B6-1 |
| `most_frugal_category` | TEXT | (위 목록과 동일) | | B6-2 |
| `budgeting_style` | TEXT | 총액부터 정하고 항목별 배분·항목별로 필요한 만큼·그때그때 유동적 | | B6-3 |

### B-7 정보 습득 & 기록 습관 (4개)

| 필드 | 타입 | 값 | 필수 | Q# |
|---|---|---|---|---|
| `info_source_channels` | TEXT[] | 인스타그램·유튜브·블로그·지도앱 리뷰·친구/지인 추천·여행 커뮤니티·방송/잡지 | | B7-1 |
| `trust_signal_preference` | TEXT | 리뷰 개수·평점·지인 추천·인플루언서 추천·직접 검색한 사진 | | B7-2 |
| `photo_documentation_importance` | SMALLINT(1~5) | 1=전혀 중요하지 않음 ~ 5=매우 중요함 | | B7-3 |
| `shopping_interest` | SMALLINT(1~5) | 1=전혀 없음 ~ 5=매우 많음 | | B7-4 |

### 메타 필드

| 필드 | 타입 | 설명 |
|---|---|---|
| `profile_completeness` | SMALLINT(0~100) | 선택 문항 응답 비율. 프로그레시브 프로파일링 배너 트리거 |
| `updated_at` | TIMESTAMPTZ | 마지막 수정 시각 |

---

## 5. 필드 딕셔너리 — `user_trip_contexts` (Part C)

Part C([03-questionnaire-c-trip.md](/docs/questionnaire-c)) 18문항 + 파생 플래그 3개 + 축 오버라이드 4개. 여행마다 새 레코드가 INSERT된다(UPDATE 아님). `기본값 출처` 열은 Part B 필드에서 자동 상속되는 경우만 표시한다.

### C-1 이번 여행 기본 정보

| 필드 | 타입 | 값 | 필수 | Q# | 기본값 출처 |
|---|---|---|---|---|---|
| `companion_type` | TEXT[] | 혼자·연인·친구·가족(아이 동반)·부모님(시니어 동반)·반려동물 동반 | ✅ | C1-1 | `default_companion_type` |
| `companion_count` | SMALLINT | 1 이상 정수 | ✅ | C1-2 | – |
| `pet_this_trip` | BOOLEAN | 예/아니오 (조건부 노출) | | C1-3 | – |
| `region` / `region_center` | TEXT / GEOGRAPHY(POINT,4326) | 지역명 / 좌표 | ✅ | C1-4 | – |
| `nights` / `days` | SMALLINT / SMALLINT | 당일치기(0/1) · 1박2일 · 2박3일 · 3박4일 · 4박5일 이상 | ✅ | C1-5 | – |
| `trip_start_date` / `trip_end_date` | DATE / DATE | – | | C1-6 | – |

### 파생 플래그 (질문 없음, 저장 시 계산)

| 필드 | 타입 | 계산 규칙 |
|---|---|---|
| `has_children` | BOOLEAN | `companion_type`에 `'가족(아이 동반)'` 포함 여부 |
| `has_elderly` | BOOLEAN | `companion_type`에 `'부모님(시니어 동반)'` 포함 여부 |
| `has_pet` | BOOLEAN | `pet_this_trip = true` 이거나 `companion_type`에 `'반려동물 동반'` 포함 여부 |

### C-2 이번 여행 예산

| 필드 | 타입 | 값 | 필수 | Q# | 기본값 출처 |
|---|---|---|---|---|---|
| `total_budget_tier` | TEXT | 알뜰하게·적당히·넉넉하게·프리미엄으로 | | C2-1 | – |
| `meal_budget_tier` | SMALLINT(1~5) | B1-14와 동일한 5구간 인코딩 | | C2-2 | `default_meal_budget_tier` |
| `lodging_budget_tier` | SMALLINT(1~5) | B2-9와 동일한 5구간 인코딩 | | C2-3 | `default_lodging_budget_tier` |

### C-3 이번 여행 목적·무드

| 필드 | 타입 | 값 | 필수 | Q# |
|---|---|---|---|---|
| `trip_purpose` | TEXT | 순수 휴식·기념일/이벤트·액티비티/체험·맛집 탐방·업무 겸 여행·가족 행사 | ✅ | C3-1 |
| `mood_tags` | TEXT[] | 대도시/번화가·자연/한적한 소도시·바다/휴양지·산/액티비티·이국적인 낯선 문화권 (최대 2개) | | C3-2 |
| `trip_special_occasion` | TEXT | 없음·생일·기념일·승진/합격 등 축하·힐링이 꼭 필요한 시기·기타 | | C3-3 |

### C-4 이번 여행 컨디션

| 필드 | 타입 | 값 | 필수 | Q# |
|---|---|---|---|---|
| `trip_specific_notes` | TEXT | 자유입력 | | C4-1 |
| `trip_child_senior_range` | TEXT[] | 영유아(0~3세)·유아동(4~7세)·초등(8~13세)·청소년(14~19세)·시니어(65세+) (조건부 노출) | | C4-2 |

### C-5 축 오버라이드

| 필드 | 타입 | 값 | 필수 | Q# | NULL의 의미 |
|---|---|---|---|---|---|
| `social_score_override` | NUMERIC(4,3) | 0.000~1.000 | | C5-1 | 오버라이드 없음 → `persona.social_score` 사용 |
| `adventure_score_override` | NUMERIC(4,3) | 0.000~1.000 | | C5-2 | 〃 `adventure_score` |
| `experience_score_override` | NUMERIC(4,3) | 0.000~1.000 | | C5-3 | 〃 `experience_score` |
| `flow_score_override` | NUMERIC(4,3) | 0.000~1.000 | | C5-4 | 〃 `flow_score` |

적용 공식(3.4절/03-questionnaire-c-trip.md 동일):

```
effective_X_score = COALESCE(trip.X_score_override, persona.X_score)   -- X ∈ {social, adventure, experience, flow}
```

---

## 6. 크로스 레퍼런스

| 찾고 있는 것 | 위치 |
|---|---|
| 문항 원문·UI 문구·섹션 구성 | [01](/docs/questionnaire-a)/[02](/docs/questionnaire-b)/[03](/docs/questionnaire-c)-questionnaire-*.md |
| 왜 3파트로 나눴는지, 유형 체계·궁합 규칙 | [00-overview.md](/docs/overview) |
| 유형별 서술(여행/음식/숙소 스타일, 강점/주의점, 궁합) | [types/*.md](types) |
| DB DDL 원본(CREATE TABLE 전체) | [restaurant-recommendation-design.md](/docs/restaurant-recommendation-design) 3.4절 |
| 하드 필터·스코어링·베이지안 보정 알고리즘 | 같은 문서 6장 |
| 이 파일의 표 자체가 정확한지 재검증하는 법 | 1절 표는 2절 공식으로 재계산 가능(파이썬 3줄), 4·5절 표는 DDL과 diff |

---

## 7. Open Question — 원문항 응답 로그

현재 스키마는 Part A 40문항의 **채점 결과(축 점수)만** 저장하고, 개별 문항 응답(예: A3에 몇 점을 줬는지)은 저장하지 않는다. 이 경우 나중에 채점 공식이나 문항 구성을 바꾸면(`survey_version` 상향) **과거 응답자를 새 공식으로 재채점할 방법이 없다** — 재진단을 다시 받아야 한다.

원문항 로그가 필요해지면 아래 같은 테이블을 추가하는 걸 권장한다 (지금 당장 필수는 아니므로 스키마에는 아직 반영하지 않음):

```sql
CREATE TABLE user_survey_responses (
    id             BIGSERIAL PRIMARY KEY,
    user_id        BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    survey_version SMALLINT NOT NULL,
    part           CHAR(1) NOT NULL,   -- 'A' | 'B' | 'C'
    question_id    TEXT NOT NULL,      -- 'A1', 'B1-4' 등
    raw_value      JSONB NOT NULL,     -- 숫자/문자열/배열 어떤 응답이든 그대로
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

이 테이블이 있으면 `survey_version`이 바뀌어도 원본 응답으로 재채점이 가능해지고, 향후 문항별 통계(예: "이 문항은 다른 문항들과 상관관계가 낮으니 다음 개정 때 빼자")도 낼 수 있다.
