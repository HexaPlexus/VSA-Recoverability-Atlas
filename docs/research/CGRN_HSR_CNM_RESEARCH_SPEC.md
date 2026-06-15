---
status: DEFERRED
maturity: HYPOTHESIS
implementation_authorized: false
activation_gate: explicit future decision after prior-art and necessity kill-test
---

# CGRN-HSR / CNM
## Context Navigation Memory — исследовательская спецификация и anti-NIH guardrail

**Версия:** 0.1  
**Дата:** 2026-06-15  
**Статус:** новая проверяемая гипотеза, не часть подтверждённого mainline до прохождения kill-test  
**Рекомендуемый verdict:** `COMPOSE + WRAP + PROTOTYPE`  
**Запрещённый преждевременный verdict:** `BUILD NEW MEMORY SUBSTRATE`

---

## 0. Краткий вывод

Level 1 CGRN-HSR подтвердил узкий, но устойчивый механизм:

> внешний семантический контекст повышает candidate recall и тем самым делает локальную задачу поиска разрешимее.

При этом контекст в экспериментах уже был задан или синтетически выведен harness. Остаётся более фундаментальный вопрос:

> кто и каким механизмом определяет, какие контекстные поля релевантны прямо сейчас?

**Context Navigation Memory (CNM)** — гипотеза об отдельной дешёвой ассоциативной памяти ориентации, которая по непосредственно доступному causal runtime state возвращает распределение над контекстными handles. Эти handles не являются фактами, эпизодами или вложенными композиционными структурами. Они служат устойчивыми атомарными адресами режимов релевантности и указывают внешнему controller, каким областям основной памяти, schemas и native mechanisms выдать приоритет и вычислительный бюджет.

Главная причина отделения CNM от основной памяти H₁:

> указатель, который должен спасать поиск от глубокой вложенности, factorization failure и композиционного шума, не должен сам зависеть от глубокого unbinding или ненадёжного поиска в той же геометрии.

Однако отдельная «вторая гиперсфера» пока не считается доказанно необходимой. Она должна победить или существенно дополнить готовые механизмы:

- обычный vector similarity index;
- direct H₁ context-prototype lookup;
- VSA/SPA cleanup и heteroassociative memory;
- Sparse Distributed Memory;
- Adaptive Resonance Theory для online-категоризации и novelty;
- HMM/HSMM или latent-cause inference для временно устойчивых скрытых режимов;
- symbolic/rule-based routing.

Если отдельный H₂ не даёт преимущества по надёжности, стоимости, open-world insertion или downstream false-exclusion risk, его следует удалить, оставив обычный индекс и внешний controller.

---

# 1. Связь с исходной CGRN-HSR

Исходная гипотеза CGRN-HSR использует внешний probabilistic context для:

- candidate priors;
- выбора context slice;
- выделения search budget;
- расширения области поиска;
- accept / fallback / abstain policy.

CNM не заменяет этот слой. Она заполняет недостающий upstream-контракт:

```text
Causal Runtime State
        ↓
Context inference / orientation          ← CNM hypothesis
        ↓
Context posterior / context facets
        ↓
CGRN candidate selection and budgeting
        ↓
Native proposal engine
        ↓
Evidence / expansion / abstention
```

Иными словами:

- **CGRN отвечает:** как использовать контекст для управления поиском;
- **CNM должна проверить:** как дешёво и безопасно получить сам context posterior.

CNM не имеет права менять уже подтверждённые и опровергнутые результаты Level 1.

---

# 2. Рабочее определение контекста

Контекст не определяется как:

- одна папка;
- один тег;
- один ближайший концепт;
- один composite hypervector;
- один кластер наблюдений;
- полная копия working memory;
- истинное описание мира.

Рабочее определение:

> **Контекст — временно актуальный режим релевантности, при котором определённое распределение поискового бюджета по памяти, schemas и mechanisms повышает ожидаемую полезность downstream-решения.**

Пусть основная память и доступные механизмы образуют множество:

```text
M = {m₁, m₂, ..., mₙ}
```

Контекст `c` задаёт мягкое поле приоритетов:

```text
w_c(mᵢ) ∈ [0, 1]
```

Это поле может быть:

- широким;
- разреженным;
- многомодальным;
- геометрически несвязным в H₁;
- пересекающимся с другими полями;
- зависящим от цели, запроса и текущего operator-state.

Поэтому контекст — не обязательно локальная сферическая область H₁. Он может одновременно повышать приоритет:

- инструментов;
- отдельных эпизодов;
- procedural schemas;
- источников риска;
- конкретного temporal window;
- специализированного resolver;
- глобального fallback budget.

---

# 3. Центральная гипотеза CNM

## 3.1. Основная формулировка

> Отдельная динамическая associative memory атомарных context handles может надёжнее и дешевле ориентировать поиск, чем извлечение контекста непосредственно из глубоко композиционной основной памяти, если context handles изолированы от H₁, доступны через множество частичных entry keys, возвращаются как распределение, поддерживают `UNKNOWN_CONTEXT` и управляют только мягкими priors и budget allocation.

## 3.2. Более строгая операциональная формулировка

При одинаковом входном cue encoder и одинаковом downstream retrieval task CNM-H₂ должна обеспечить хотя бы одно из следующего относительно сильнейшего baseline:

1. больший context recall@k при шумных и неполных cues;
2. меньшую вероятность исключить правильное поисковое поле;
3. меньшую стоимость downstream search при фиксированном false-exclusion risk;
4. лучшую калибровку context posterior;
5. более честное unknown-context detection;
6. дешёвое online-добавление новых контекстов без перестройки H₁;
7. устойчивость context handles к изменению или деградации содержательных H₁-представлений;
8. переносимость одной context policy между несколькими native mechanisms.

Если ни одно преимущество не подтверждается, отдельный H₂ не нужен.

---

# 4. Что CNM не утверждает

CNM не утверждает, что:

- контекст можно определять абсолютно безошибочно;
- top-1 context всегда существует;
- вся релевантная память образует одну геометрически связную область;
- отдельная гиперсфера автоматически решает context inference;
- случайный atomic handle сам содержит смысл контекста;
- similarity равна вероятности истинности;
- высокая уверенность навигатора разрешает hard gate;
- unknown situation обязана соответствовать ближайшему известному context;
- CNM заменяет working memory, event store, planner, entity resolver или belief state;
- context handle может самостоятельно коммитить факт или действие;
- CNM является биологической моделью гиппокампа;
- context gating, semantic pointers, cleanup memory, online clustering или latent-cause inference являются новыми изобретениями проекта.

Практическая цель не «безошибочный top-1», а:

> **минимальная вероятность необратимо потерять правильное поле поиска при существенном уменьшении среднего search cost.**

---

# 5. Anti-NIH audit

## 5.1. Близкий prior art

### Context-gated associative retrieval

Уже существует двухступенчатая постановка, в которой внешний context gate изменяет retrieval landscape основной ассоциативной памяти. Поэтому нельзя заявлять новизну самого принципа `context → localized associative retrieval`.

### Semantic Pointer Architecture и cleanup memory

SPA/Nengo поддерживает отдельные vocabularies, semantic pointers, autoassociative cleanup, heteroassociative mapping и извлечение нескольких похожих memories. Поэтому atomic context pointer и partial/noisy cue retrieval сами по себе не новы.

### Sparse Distributed Memory

SDM уже задаёт content-addressable retrieval в высокоразмерном пространстве через множество активируемых адресов. Many-to-one mapping от нескольких похожих cues к устойчивому output является естественным кандидатом для реализации entry-key слоя.

### Adaptive Resonance Theory

ART решает stability–plasticity problem, online-категоризацию, создание новых категорий и novelty через vigilance. Это наиболее опасный prior art для динамического создания, merge/split и provisional lifecycle контекстов. Самописная online-кластеризация до сравнения с ART запрещена.

### Latent-cause inference / HMM / HSMM

Определение текущего скрытого контекста из временного потока наблюдений — зрелая задача latent-state inference. LCNet, Bayesian latent-cause models, HMM и HSMM уже моделируют временно устойчивые скрытые режимы и переходы между ними.

### Vector similarity indexes

FAISS и другие ANN/NN индексы уже решают хранение, dynamic add и поиск ближайших векторов. Отдельный H₂ codebook без дополнительного механизма может оказаться обычным vector index.

### Hippocampal indexing theory

Идея компактного индекса, который реактивирует распределённую кортикальную конфигурацию, имеет давний концептуальный аналог. Это не доказывает конкретную реализацию CNM, но запрещает заявлять новизну самой идеи «отдельный pointer к распределённому полю».

## 5.2. Verdict matrix

| Компонент | Verdict | Причина |
|---|---|---|
| Векторный поиск по context prototypes | `ADOPT` | FAISS/brute-force cosine уже закрывают задачу |
| Cleanup noisy context cue | `WRAP` | SPA/SDM/обычная associative memory |
| Heteroassociation `entry key → handle` | `WRAP` | стандартный key-value/associative pattern |
| Online создание категорий | `ADOPT / BASELINE` | ART обязателен как сильный baseline |
| Novelty / unknown context | `ADOPT / BASELINE` | ART/open-set/latent-cause methods |
| Temporal transition prior | `ADOPT` | HMM/HSMM/latent-cause inference |
| Atomic context handle | `ADOPT PATTERN` | semantic pointer / index pattern уже известен |
| Отдельный context vocabulary | `ADOPT PATTERN` | SPA namespaces/vocabularies |
| Soft top-k routing | `ADOPT PATTERN` | probabilistic routing/MoE/retrieval systems |
| Hard context gating | `BLOCK` | опасно при probabilistic context |
| Nested context unbinding | `BLOCK` | воспроизводит failure mode H₁ |
| Custom vector database | `BLOCK` | готовые индексы существуют |
| Custom online clustering до ART audit | `BLOCK` | NIH |
| CNM как отдельный fundamental substrate | `PROTOTYPE ONLY` | нужность не подтверждена |
| Изолированные handles + dynamic entry keys + safe search-field expansion | `COMPOSE / TEST` | возможный исследовательский seam |
| Unified context authority над heterogeneous mechanisms | `PROTOTYPE` | возможный системный вклад, требует overlap audit |

## 5.3. Возможный surviving research seam

Потенциальный вклад находится не в отдельном алгоритме cleanup, clustering или nearest-neighbour search, а в композиции:

> динамически создаваемые атомарные context handles + many-to-one entry keys + faceted posterior + мягкое search field над независимым H₁ + residual/global budget floor + downstream evidence-triggered expansion + transactional non-commit + open-world context lifecycle.

Даже эта композиция считается новой только после прямого сравнения с ART, latent-cause inference, standard vector retrieval и direct H₁ prototypes.

---

# 6. Два пространства

## 6.1. H₁ — Content / Knowledge Space

H₁ содержит содержательные представления:

- concepts;
- entities;
- episodes;
- roles;
- states;
- relations;
- procedures;
- plans;
- perceptual summaries;
- schemas.

H₁ может использовать VSA, SDM, indexed stores, graphs и иные substrates. CNM не требует, чтобы вся H₁ была одной гиперсферой.

## 6.2. H₂ — Context Handle Space

H₂ содержит только навигационные сущности:

- context facets;
- consolidated context regimes;
- search modes;
- schema-routing handles;
- optional mechanism-selection handles.

H₂ не содержит:

- фактическое местоположение объекта;
- полную историю;
- compositional episode;
- nested bound structures;
- текущую world truth;
- результат factorization;
- decision authority.

H₂ может использовать тот же тип HV и ту же размерность, что H₁, но обязана иметь:

- отдельный seed namespace;
- отдельный codebook/vocabulary;
- отдельную capacity accounting;
- отдельный lifecycle;
- типизированные границы;
- запрет случайного смешивания H₁- и H₂-векторов.

Математически отдельная «гиперсфера» не обязательна. Достаточно отдельного address space и контракта. Необходимость иной геометрии является отдельной гипотезой.

---

# 7. Основные сущности

## 7.1. ContextHandle

```text
ContextHandle
├── context_id
├── atomic_hv
├── namespace
├── kind: FACET | REGIME | MODE
├── lifecycle_state
├── created_at
├── version
└── provenance
```

`atomic_hv` является неделимым адресом. Он не обязан декодировать содержимое контекста.

## 7.2. ContextEntryKey

```text
ContextEntryKey
├── key_id
├── context_id
├── cue_hv_or_feature_vector
├── cue_schema
├── source
├── confidence
├── valid_time_range
├── usage_count
└── provenance
```

Один context handle может иметь множество entry keys.

Назначение:

```text
K₁ ─┐
K₂ ─┼→ C
K₃ ─┘
```

Это повышает доступность контекста из разных частичных состояний и не требует объединять все cues в один шумный composite.

## 7.3. ContextRecord

```text
ContextRecord
├── handle
├── entry_key_refs
├── routing_payload
├── transition_priors
├── maturity
├── support_count
├── contradiction_count
├── utility_history
├── merge_candidates
├── split_evidence
└── provenance
```

## 7.4. RoutingPayload

```text
RoutingPayload
├── eligible_memory_stores
├── eligible_schemas
├── typed_domain_priors
├── candidate_source_priors
├── mechanism_priors
├── temporal_window_policy
├── local_budget
├── expansion_policy
├── global_budget_floor
└── forbidden_only_by_typed_invariant
```

Routing payload хранится внешне и типизированно. Он не извлекается unbinding-операциями из context handle.

## 7.5. ContextCue

```text
ContextCue
├── current_observation_summary
├── active_goal
├── query_type
├── active_operator
├── recent_committed_actions
├── working_state_summary
├── temporal_horizon
├── uncertainty_signals
├── conflict_signals
├── previous_context_posterior
└── provenance
```

Cue может использовать только runtime-доступные сведения. Hidden evaluator truth запрещена.

## 7.6. ContextHypothesis

```text
ContextHypothesis
├── context_id
├── posterior_or_score
├── supporting_entry_keys
├── source_components
├── novelty_distance
├── transition_support
├── ambiguity_flags
└── evidence
```

## 7.7. ContextPosterior

```text
ContextPosterior
├── ranked_hypotheses
├── unknown_mass
├── entropy
├── top1_top2_margin
├── calibration_metadata
├── generation_method
└── snapshot_id
```

Navigator обязан возвращать distribution/top-k, а не только top-1.

## 7.8. SearchField

```text
SearchField
├── context_snapshot_id
├── typed_domain_weights
├── mechanism_budget
├── candidate_budget
├── global_residual_budget
├── expansion_frontier
└── hard_constraints
```

Hard constraints могут происходить только из typed/causal invariants, но не из similarity CNM.

---

# 8. Context facets и consolidated regimes

Контекст почти всегда многомерный:

```text
SPATIAL::WORKSHOP
GOAL::REPAIR
RISK::HIGH_VOLTAGE
TEMPORAL::IMMEDIATE
SOCIAL::HUMAN_PRESENT
```

Создание отдельного монолитного handle для каждой комбинации приведёт к комбинаторному взрыву и context fragmentation.

Поэтому CNM различает:

## 8.1. Facet handles

Независимые типизированные аспекты:

- spatial;
- goal;
- task;
- risk;
- social;
- temporal;
- epistemic;
- operational mode.

## 8.2. Consolidated regime handles

Часто повторяющаяся комбинация facets может получить отдельный handle:

```text
REGIME::EMERGENCY_ELECTRICAL_REPAIR
```

Regime создаётся только если даёт измеримое преимущество над смесью facets.

## 8.3. Field composition

Итоговое поле может быть смесью:

```text
w(mᵢ | qₜ) = Σⱼ P(cⱼ | qₜ) · w_cⱼ(mᵢ)
```

С обязательным residual/global floor:

```text
w_final = (1 - ε) · w_context + ε · w_global
```

`ε > 0` для probabilistic context.

---

# 9. Runtime contract

```text
Causal Runtime State
        ↓
ContextCueEncoder
        ↓
Candidate context retrieval
- direct vector index
- cleanup/SDM
- ART category field
- latent-state prior
        ↓
ContextPosterior
        ↓
ContextPolicy
        ↓
SearchField
        ↓
Native mechanisms
        ↓
Independent downstream evidence
        ↓
ACCEPT | EXPAND | SWITCH | UNKNOWN | ABSTAIN
```

## 9.1. Authority boundaries

### Navigator may

- propose context hypotheses;
- attach scores/posteriors;
- identify novelty;
- retrieve entry keys;
- propose search-field weights.

### Navigator may not

- declare current context as certain;
- hard-delete candidates;
- commit a fact;
- commit identity;
- commit a plan;
- update H₁ truth directly;
- create a confirmed context from one observation;
- validate its own output using the same similarity score.

### ContextPolicy may

- combine facets;
- allocate budget;
- maintain global residual mass;
- create an expansion frontier;
- select native mechanisms.

### Downstream evidence layer may

- accept a result;
- request context expansion;
- reject a context hypothesis;
- increase unknown mass;
- create evidence for provisional context formation.

---

# 10. Dynamic context lifecycle

CNM не должна автоматически превращать каждый новый cue в новый context.

```text
UNKNOWN_OBSERVATION
→ PROVISIONAL_CONTEXT
→ CANDIDATE_CONTEXT
→ CONFIRMED_CONTEXT
→ CONSOLIDATED_CONTEXT
```

Дополнительные состояния:

```text
CONFLICTED
SPLIT_PENDING
MERGE_PENDING
DEPRECATED
REJECTED
```

## 10.1. UNKNOWN_OBSERVATION

Возникает, если:

- max context score низок;
- posterior слишком плоский;
- известные contexts дают повторный downstream failure;
- cue содержит новые несовместимые признаки;
- transition prior и observation evidence конфликтуют.

На этой стадии поиск остаётся широким.

## 10.2. PROVISIONAL_CONTEXT

Создаётся только после повторяющегося evidence, что существующие contexts не дают полезного search field.

Требования:

- минимум несколько независимых observations;
- различимые entry keys;
- повторяемая routing utility;
- отсутствие утечки evaluator truth;
- новая atomic H₂ identity;
- ограниченный budget и низкая authority.

## 10.3. CANDIDATE_CONTEXT

Контекст прошёл development observations, но ещё не доказал переносимость.

## 10.4. CONFIRMED_CONTEXT

Требует held-out evidence, что context field:

- снижает downstream cost;
- сохраняет relevant-field recall;
- не увеличивает false exclusion;
- стабилен при умеренном cue noise;
- имеет приемлемую calibration.

## 10.5. CONSOLIDATED_CONTEXT

Допускается после длительной устойчивости и может получить:

- дополнительные entry keys;
- более высокий prior;
- более специализированный payload;
- transition links.

## 10.6. Merge

Два contexts объединяются, если:

- их routing payload практически эквивалентен;
- downstream utility взаимозаменяема;
- различия не улучшают decisions;
- объединение не повышает false exclusion.

## 10.7. Split

Context разделяется, если один handle систематически соответствует несовместимым search policies или двум различным downstream outcome distributions.

Similarity наблюдений недостаточно для merge/split. Критерий должен учитывать полезность routing policy.

---

# 11. Формирование контекста: запрещённый и разрешённый подход

## 11.1. Запрещённый подход

```text
similar observations
→ same context
```

Похожее наблюдение может соответствовать разным целям и policies.

## 11.2. Рабочий подход

Два runtime-state относятся к одному context, если для них полезна сходная комбинация:

- memory stores;
- schemas;
- candidate domains;
- mechanisms;
- search breadth;
- temporal window;
- evidence policy;
- transition expectations.

Контекст формируется из совместного evidence:

```text
observation similarity
+ goal/operator similarity
+ temporal continuity
+ transition prior
+ downstream routing utility
+ failure pattern
```

## 11.3. Bootstrap problem

До существования confirmed contexts система использует:

- broad global search;
- typed invariants;
- symbolic/rule routing;
- ART/latent-state baseline;
- provisional handles с низкой authority.

Никакой hidden oracle context не допускается.

---

# 12. Near-reliable navigation contract

Термин «безошибочный» заменяется измеримым контрактом.

CNM считается near-reliable при выполнении заданного operating envelope:

```text
P(correct field excluded) ≤ δ
```

при одновременном:

```text
E[search_cost_CNM] < E[search_cost_global]
```

Где `correct field excluded` означает, что search budget после CNM не позволяет native mechanism рассмотреть релевантный domain даже после разрешённого расширения.

Основные средства безопасности:

1. top-k contexts;
2. soft weights;
3. global residual budget;
4. `UNKNOWN_CONTEXT`;
5. entropy/margin-based expansion;
6. transition prior только как soft evidence;
7. downstream verifier;
8. context-dilation stability check;
9. transactional non-commit;
10. журнал provenance и context snapshot.

---

# 13. Обязательные baselines

Нельзя сравнивать H₂ только со случайным выбором.

## B0. Global

Без context navigation.

## B1. Symbolic router

Прозрачные правила по goal/query/operator/types.

## B2. Direct H₁ context prototype lookup

Context summaries хранятся и ищутся прямо в H₁ или в обычном индексе без отдельного atomic handle layer.

## B3. Flat vector index

FAISS/brute-force cosine над context cue/prototype vectors.

## B4. Cleanup / heteroassociative memory

NengoSPA/SDM или эквивалентный готовый механизм.

## B5. Adaptive Resonance Theory

Минимум Fuzzy ART или Hypersphere ART; при необходимости Dual Vigilance ART.

## B6. Temporal latent-state model

HMM/HSMM или Bayesian latent-cause baseline для последовательностей.

## B7. Proposed CNM-H₂

Atomic handles + multiple entry keys + external routing payload.

## B8. Oracle

Верхний потолок, не runtime method.

---

# 14. Главный ablation

Самый важный тест:

```text
Direct H₁ context prototype retrieval
vs
H₂ atomic handle retrieval
```

Условия должны совпадать:

- один cue encoder;
- одинаковая размерность;
- одинаковый metric;
- одинаковый ANN/backend;
- одинаковый top-k;
- одинаковые downstream mechanisms;
- одинаковый budget;
- одинаковые seeds.

Разница должна быть только в том, что H₂ использует:

- изолированные atomic handles;
- multiple entry keys;
- внешний payload;
- независимый lifecycle.

Если H₂ не даёт преимущества, отдельная навигационная память отклоняется.

---

# 15. Экспериментальная программа

## CNM-0 — Prior-art feasibility audit

Без нового memory framework.

Проверить:

- FAISS dynamic add/search;
- artlib Fuzzy ART/Hypersphere ART/Dual Vigilance ART;
- NengoSPA associative memory или минимальный SDM upstream;
- HMM/HSMM baseline;
- direct H₁ prototype lookup;
- compatibility с текущим abstract task layer.

Выход:

```text
docs/CNM_PRIOR_ART_MATRIX.md
results/cnm0/capability_matrix.json
results/cnm0/smoke_results.json
results/cnm0/verdicts.json
```

## CNM-1 — Fixed-context orientation kill-test

Contexts заранее известны; динамическое создание отключено.

Scenario families:

1. clean known context;
2. partial cue;
3. noisy cue;
4. overlapping contexts;
5. two simultaneously active facets;
6. fast context switch;
7. unknown context;
8. misleading transition prior.

Primary question:

> снижает ли CNM downstream search cost при фиксированном false-exclusion risk?

## CNM-2 — Dynamic context formation

Только если CNM-1 подтверждает пользу отдельного handle layer.

Проверить:

- online insertion;
- provisional lifecycle;
- context proliferation;
- merge/split;
- non-stationarity;
- unknown detection;
- transition priors;
- catastrophic context capture.

ART и latent-cause methods обязательны как baselines.

## CNM-3 — Heterogeneous routing

Только если CNM-2 проходит gates.

Один context posterior управляет выбором между:

- exact index;
- MAP candidate selection;
- BCF typed decoder;
- standard entity resolver;
- episodic query mechanism.

Native mechanisms не переписываются.

---

# 16. Метрики

## 16.1. Orientation

```text
context_recall_at_1
context_recall_at_k
facet_recall
posterior_brier_score
expected_calibration_error
unknown_detection_auroc
unknown_false_accept_rate
posterior_entropy
```

## 16.2. Search-field quality

```text
relevant_item_recall_at_budget
all_required_domains_included
false_exclusion_rate
field_precision
field_size
context_overlap_coverage
```

## 16.3. Downstream behavior

```text
proposal_success
false_commit_rate
abstention_rate
expansion_success_rate
wrong_context_action_rate
behavioral_utility
```

## 16.4. Compute

```text
orientation_latency
index_memory
entry_key_count
candidate_count
native_mechanism_calls
search_expansions
total_candidate_evaluations
end_to_end_latency
```

## 16.5. Lifecycle health

```text
contexts_created
context_creation_precision
provisional_survival_rate
merge_rate
split_rate
context_fragmentation
context_collapse
orphan_context_rate
stale_entry_key_rate
```

---

# 17. Failure taxonomy

```text
CORRECT_CONTEXT_ORIENTATION
CORRECT_MULTI_CONTEXT_ORIENTATION
WRONG_CONTEXT_BUT_RECOVERED_BY_EXPANSION
WRONG_CONTEXT_FALSE_EXCLUSION
UNKNOWN_CONTEXT_CORRECTLY_DETECTED
UNKNOWN_CONTEXT_FORCED_TO_KNOWN
CONTEXT_COLLAPSE
CONTEXT_FRAGMENTATION
STALE_CONTEXT_CAPTURE
TRANSITION_PRIOR_CAPTURE
ENTRY_KEY_COLLISION
ROUTING_PAYLOAD_MISMATCH
DOWNSTREAM_FAILURE_DESPITE_CORRECT_CONTEXT
ABSTENTION
```

Важно разделять:

- context retrieval failure;
- search-field construction failure;
- native mechanism failure;
- verifier/policy failure.

---

# 18. Evidence and expansion

Navigator не является verifier.

После работы native mechanism controller проверяет:

- удалось ли получить достаточное evidence;
- устойчив ли результат при небольшом context dilation;
- меняется ли ranking при добавлении следующего context hypothesis;
- остался ли unexplained residual;
- согласуются ли независимые sources;
- не вырос ли novelty score.

Expansion выполняется cold на уровне candidate field / mechanism call. Перенос внутреннего resonator state между контекстами запрещён результатами Level 1E.1.

Пример:

```text
Top contexts: C1=.52, C2=.27, C3=.11, unknown=.10

Attempt 1: field(C1), budget 20%
Evidence insufficient

Attempt 2: field(C1 ∪ C2), cold mechanism call
Evidence sufficient

Commit result with context snapshot {C1,C2}
```

---

# 19. Кодовые границы

До прохождения CNM-0 запрещено писать новый большой runtime.

Предполагаемые тонкие интерфейсы:

```text
ContextCueEncoder
ContextRetriever
ContextPosteriorCalibrator
ContextLifecycleManager
SearchFieldCompiler
ContextExpansionPolicy
```

Каждый интерфейс должен иметь минимум две независимые реализации или baseline.

Запрещено:

- собственный ANN index;
- собственный ART;
- собственный HMM/HSMM;
- собственный vector database;
- новый VSA framework;
- вложенный context resonator;
- recursive unbinding context handles;
- один монолитный `context_memory.py` на тысячи строк;
- learned end-to-end router до простых baselines;
- изменение H₁ geometry ради победы H₂;
- скрытый доступ к evaluator truth;
- hard gate по similarity;
- автоматический confirmed context после одного случая.

---

# 20. Claim ladder

## Допустимый до экспериментов

> CNM является гипотезой об отдельной памяти ориентации, изолирующей context handles от композиционного шума основной памяти.

## Допустимый после CNM-1

Только при подтверждении:

> В измеренном operating envelope atomic context-handle layer снизил downstream search cost при сопоставимом или меньшем false-exclusion risk относительно direct H₁ and standard retrieval baselines.

## Допустимый после CNM-2

> Context handles могут динамически добавляться и поддерживаться с контролируемой fragmentation/collapse и честным unknown-context detection.

## Допустимый после CNM-3

> Один внешний context posterior переносимо управляет budget/candidate allocation нескольких heterogeneous native mechanisms.

## Запрещённые claims

- «CNM безошибочно определяет контекст»;
- «контекстная гиперсфера является новой идеей»;
- «CNM моделирует человеческий гиппокамп»;
- «atomic handles содержат смысл контекста»;
- «CNM устраняет VSA noise»;
- «CNM гарантирует retrieval»;
- «CNM является AGI context system»;
- «H₂ фундаментально лучше обычного vector index» без ablation;
- «динамические contexts новы» без сравнения с ART и latent-cause inference.

---

# 21. Gate decisions

## `GO CNM-2`

Если H₂:

- улучшает relevant-field recall или search cost;
- не повышает false exclusion;
- корректно выдаёт unknown;
- показывает преимущество над direct H₁ prototype и ART/vector baselines;
- не требует hidden oracle labels runtime.

## `NARROW TO INTERFACE`

Если готовый ART/SDM/HMM решает context orientation не хуже, но CGRN всё ещё нуждается в едином typed output:

> CNM становится интерфейсом/контрактом над adopted backends, а не новым substrate.

Это хороший и вероятный результат.

## `ENGINEERING ONLY`

Если ценность заключается только в интеграции готовых mechanisms без нового измеримого effect.

## `BLOCK H₂`

Если direct H₁ prototype lookup или обычный vector index не хуже по:

- recall;
- calibration;
- unknown detection;
- online insertion;
- downstream cost.

## `BLOCK DYNAMIC CONTEXT CLAIM`

Если ART или latent-cause baseline полностью покрывает lifecycle и routing utility без преимущества proposed composition.

---

# 22. Главные открытые вопросы

1. Как строить cue encoder без уже выбранного контекста?
2. Какие runtime-state fields являются causal bottom и не требуют retrieval?
3. Нужна ли H₂ отдельная геометрия или только отдельный namespace?
4. Как связывать H₂ handle с многомодальным routing payload?
5. Как предотвращать context fragmentation?
6. Как предотвращать context collapse?
7. Как отличать новый context от аномального observation внутри старого?
8. Как калибровать unknown mass?
9. Как обучать entry keys без circular confirmation bias?
10. Как проверять routing utility без target leakage?
11. Как представлять одновременно активные contexts?
12. Когда facets достаточно, а когда нужен consolidated regime?
13. Как переносить context policy между substrates с разными evidence surfaces?
14. Как учитывать long-term transition structure без захвата ошибочным prior?
15. Какой минимальный residual global budget обеспечивает safety?

---

# 23. Рекомендуемый следующий этап

Не реализовывать сразу динамическую вторую гиперсферу.

Следующий этап:

```text
CNM-0: Prior-Art Backend Audit and Fixed-Context Benchmark Design
```

Задачи:

1. заморозить эту спецификацию;
2. проверить готовые ART, vector-index, cleanup/SDM и latent-state backends;
3. определить единый `ContextPosterior` contract;
4. разработать paired CNM-1 protocol;
5. заранее зафиксировать false-exclusion risk target;
6. не писать custom context learner;
7. не интегрировать CNM в production architecture до kill-test.

---

# 24. Итоговая архитектурная позиция

```text
H₁ — содержательная память и native mechanisms
H₂ — гипотетическая изолированная память навигационных handles
ContextRecord — внешний typed routing payload
CGRN controller — budget, expansion and mechanism policy
Verifier — независимая оценка результата
Authority layer — accept / provisional / abstain / commit
```

Самая сильная surviving формулировка:

> **Context Navigation Memory — это не память фактов и не второй factorizer, а динамическая associative orientation layer. Она должна по непосредственному causal runtime state дешёво предложить несколько вероятных режимов релевантности, после чего внешний controller сформирует мягкое поисковое поле над H₁. Правильность обеспечивается не идеальным top-1 context, а сохранением escape mass, unknown detection, downstream evidence и безопасным расширением.**

Научный вопрос:

> Даёт ли изоляция atomic context handles в отдельном H₂ реальное преимущество поверх готовых online category, latent-state, cleanup и vector-retrieval mechanisms — или CNM должна остаться только единым typed interface над ними?

---

# 25. Основные источники prior art

1. Choraria, M. et al. **Context-Gated Associative Retrieval: From Theory to Transformers.** arXiv:2605.10970, 2026.
2. Kanerva, P. **Sparse Distributed Memory and Related Models.** In *Associative Neural Memories: Theory and Implementation*, 1993.
3. Melton, N. M., Tanksley, D., Wunsch, D. C. **Adaptive Resonance Lib: A Python package for Adaptive Resonance Theory models.** Journal of Open Source Software, 2025. DOI: 10.21105/joss.07764.
4. Lu, Q. et al. **Reconciling shared versus context-specific information in a neural network model of latent causes.** Scientific Reports 14, 16782, 2024.
5. Douze, M. et al. **The Faiss Library.** arXiv:2401.08281, 2024.
6. Nengo / Semantic Pointer Architecture documentation: associative and cleanup memory, separate vocabularies and semantic pointers.
7. Soar architecture documentation: working, semantic and episodic memory; cue-based retrieval.
8. ACT-R documentation: partial matching, spreading activation and retrieval thresholds.
9. Teyler–DiScenna / later reviews of the **Hippocampal Memory Indexing Theory**.
