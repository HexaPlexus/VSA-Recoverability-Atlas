# CGRN-HSR: Context-Gated Resonator Network with Hierarchical Search Relaxation

## Статус

- **Тип:** исследовательская архитектурная гипотеза
- **Текущая зрелость:** жизнеспособная гипотеза, не подтверждённая экспериментально
- **Предлагаемый verdict:** `FORK + COMPOSE + PROTOTYPE`
- **Запрещённый claim:** устранение фундаментального информационного коллапса VSA
- **Допустимый claim:** снижение вычислительной стоимости и частоты ложных аттракторов за счёт внешнего контекстного ограничения поиска, независимой проверки и права отказа

---

## 1. Рабочее название

**Context-Gated Resonator Network with Hierarchical Search Relaxation — CGRN-HSR**

Альтернативное описательное название:

**Context-Conditioned Selective Factorization with Hierarchical Search Relaxation and Transactional Non-Commit**

Термин *rollback* сохраняется для runtime-семантики отмены неподтверждённого результата. Для самого алгоритма поиска точнее использовать *hierarchical search relaxation* или *context expansion*, поскольку система не обязательно возвращается к предыдущему вычислительному состоянию, а последовательно расширяет область допустимых гипотез.

---

## 2. Центральная гипотеза

Глубокая VSA-факторизация становится ненадёжной не только из-за шума представления, но и из-за слишком большого числа правдоподобных конкурирующих факторов в глобальном codebook.

Вместо встраивания иерархического контекста в геометрию гипервекторов предлагается держать контекст во внешнем, явном и вероятностном субстрате. Этот контекст не изменяет сами атомарные гипервекторы, а управляет:

1. prior-вероятностями кандидатов;
2. порядком исследования контекстных областей;
3. вычислительным бюджетом factorizer;
4. условиями расширения поиска;
5. правом принять, отложить или отклонить найденную факторизацию.

Резонаторная сеть используется не как источник истины, а как локальный генератор кандидатной факторизации внутри ограниченного operating envelope.

Главное предположение:

> Если истинные факторы с высокой вероятностью находятся в малом контекстно-релевантном подмножестве глобального codebook, то внешний контекстный prior уменьшит число конкурирующих ложных аттракторов, ускорит факторизацию и снизит silent false-consensus. Ошибочный или недостаточный prior должен обнаруживаться независимым verifier и приводить к расширению поиска либо abstention, а не к принудительному ответу.

---

## 3. Что гипотеза не утверждает

CGRN-HSR не утверждает, что:

- контекст восстанавливает информацию, уже уничтоженную bundling или квантованием;
- resonator network гарантированно находит глобально правильную факторизацию;
- высокая энергия или стабильность аттрактора равна вероятности истинности;
- глубокая VSA-композиция становится произвольно обратимой;
- один контекстный тег способен полностью описать ситуацию;
- неизвестная сущность обязана быть ближайшим известным атомом;
- hard mask безопасен для вероятностных предположений;
- rollback без сохранённых operands и provenance физически возможен.

---

## 4. Relation to Prior Art и граница новизны

Отдельные части гипотезы уже имеют близкие аналоги:

- context-gated associative retrieval;
- resonator networks и их attention/sparse варианты;
- coarse-to-fine и best-first search;
- hierarchical probabilistic priors;
- selective prediction и abstention;
- transactional propose/verify/commit;
- open-world concept formation;
- Bayesian model expansion и reduction.

Поэтому научный claim не должен звучать как изобретение context gating или resonator factorization.

Потенциальная новизна находится в проверяемой композиции:

> вероятностный многомерный контекстный граф → selective VSA factorization → независимая многофакторная валидация → best-first расширение контекста → transactional non-commit → open-world lifecycle неизвестных понятий.

Новизна считается доказанной только в случае, если эта композиция показывает результат, который нельзя объяснить одним уменьшением размера codebook, увеличением compute budget, случайным pruning или обычным multi-start decoding.

---

## 5. Архитектура

### 5.1. Context Belief Graph

Контекст не является одной папкой или одним указателем. Он представлен как faceted DAG или lattice с вероятностными убеждениями.

Пример:

```text
location: Garage              0.72
environment: Indoor           0.91
task: Repair                  0.63
time: Night                   0.88
entity_domain: Tool           0.58
entity_domain: Animal         0.21
hazard_state: Unknown         0.44
```

Один концепт может принадлежать множеству контекстов одновременно.

Контекстный слой хранит:

- typed context dimensions;
- posterior probability;
- источник свидетельства;
- временную актуальность;
- причинные или логические ограничения;
- историю обновлений;
- distinction между `constraint` и `expectation`.

### 5.2. Tagged / Indexed Codebook

Атомарные гипервекторы остаются геометрически нейтральными. Контекстные связи не обязаны входить в сам атом через XOR или phase binding.

Для каждого атома хранятся внешние метаданные:

```text
CodebookEntry
├── atom_id
├── atomic_hypervector
├── role/type constraints
├── probabilistic context links
├── lifecycle state
├── provenance
└── codebook version
```

Теги используются для индексирования и вычисления priors, а не для объявления единственной «папки» существования атома.

### 5.3. Context-Conditioned Factorizer

Factorizer получает:

- composite observation;
- factor role definitions;
- candidate priors;
- context slice;
- iteration budget;
- restart budget;
- representation/codebook version.

В простейшем варианте context prior изменяет candidate activation или energy:

\[
E'(z \mid c)=E_{\text{factorizer}}(z)-\lambda\log p(z\mid c)
\]

Точная формула является реализационной деталью и должна сравниваться с другими способами prior weighting.

### 5.4. Independent Verifier

Verifier не принимает решение по одному `max similarity`.

Он формирует типизированное свидетельство:

```text
FactorizationEvidence
├── reconstruction_score
├── top1_top2_margin_per_factor
├── restart_consensus
├── context_prior_support
├── context_expansion_stability
├── independent_check_score
├── unresolved_residual
├── novelty_score
├── calibrated_error_risk
└── failure_reasons
```

Ни один внутренний показатель resonator не имеет права самостоятельно коммитить результат.

### 5.5. Search Relaxation Controller

Controller управляет не линейным откатом по единственному дереву, а best-first расширением гипотез.

Пример frontier:

```text
Garage / Tools       posterior 0.48
Garage / Animals     posterior 0.17
Indoor / Unknown     posterior 0.12
Global sentinel      posterior 0.03
```

Каждая ветвь получает ограниченный вычислительный бюджет. Ветвь расширяется, если:

- evidence недостаточно;
- найденная факторизация нестабильна;
- независимая проверка отвергает решение;
- более широкий контекст резко меняет ranking;
- residual остаётся необъяснённым;
- novelty detector показывает отсутствие известного атома.

### 5.6. Transactional Runtime

Результат factorizer проходит стадии:

```text
PROPOSED
→ VERIFIED | REJECTED | AMBIGUOUS | UNKNOWN
→ COMMITTED только при допустимом риске
```

Runtime обязан хранить минимум:

```text
FactorizationAttempt
├── input_ref
├── operand_refs
├── context_snapshot
├── codebook_version
├── random_seed
├── factorizer_config
├── candidate_set
├── evidence
└── decision
```

Без этих данных rollback и повторяемость считаются недостоверными.

---

## 6. Hard gating и soft gating

### Hard gating

Разрешён только для доказуемых typed или causal impossibilities:

- factor не принадлежит требуемому role type;
- операция запрещена authority boundary;
- сущность причинно недоступна;
- кандидат нарушает структурный контракт;
- состояние логически несовместимо с каноническими фактами.

Hard gate не должен строиться только на статистическом ожидании.

### Soft gating

Используется для контекстных предположений:

- в гараже чаще находятся инструменты;
- ночью некоторые события менее вероятны;
- текущая задача повышает вероятность определённых объектов;
- животное в помещении необычно, но возможно.

Soft prior должен оставлять escape mass для аномалий и не иметь права навсегда исключать кандидата.

Основной принцип:

> Контекст управляет порядком и бюджетом поиска, но не объявляет гипотезу невозможной без typed invariant.

---

## 7. Execution Protocol

### Шаг 1. Context proposal

Context engine строит posterior над несколькими контекстными измерениями.

### Шаг 2. Initial selective factorization

Выбирается небольшое множество наиболее вероятных контекстных областей. Factorizer запускается с ограниченным budget.

### Шаг 3. Evidence construction

Для каждого результата вычисляются:

- reconstruction;
- margins;
- multi-start agreement;
- independent checks;
- residual;
- novelty;
- calibrated risk.

### Шаг 4. Decision

Возможны четыре исхода:

1. `ACCEPT`: риск ниже допустимого порога.
2. `EXPAND`: evidence недостаточно, но существуют перспективные соседние контексты.
3. `ABSTAIN`: ни одна известная факторизация не подтверждается.
4. `REJECT`: найдено противоречие или нарушение typed constraint.

### Шаг 5. Hierarchical / faceted expansion

Controller расширяет frontier:

- родительский контекст;
- соседнюю facet-комбинацию;
- unknown/open-set branch;
- более общий perceptual level.

### Шаг 6. Transactional commit

Только подтверждённая факторизация может изменить каноническое состояние или долговременную память.

---

## 8. Работа с аномалиями и неизвестными сущностями

Fallback к низкоуровневым примитивам должен опираться на отдельный perceptual substrate, а не на ту же неуспешную высокоуровневую факторизацию.

Пример допустимого результата:

```text
unknown moving bounded mass
approximate size: small
trajectory: irregular
location: indoor / garage
biological evidence: weak
known-concept match: rejected
```

Вместо принудительного присвоения ближайшего известного класса система создаёт:

```text
UnknownObservation
→ ProvisionalEntity
→ CandidateConcept
→ ConfirmedConcept
→ ConsolidatedConcept
```

### UnknownObservation

Содержит:

- ссылку на исходное наблюдение;
- low-level features;
- context posterior;
- unexplained residual;
- rejected candidates;
- provenance;
- uncertainty.

### ProvisionalEntity

Получает временный идентификатор и, при необходимости, новый атомарный HV, но ещё не входит в authoritative clean-up memory.

### CandidateConcept

Формируется после повторных согласованных наблюдений. Система проверяет устойчивые свойства и различимость от существующих концептов.

### Confirmed / Consolidated Concept

После накопления evidence концепт:

- добавляется в codebook;
- получает вероятностные связи с context graph;
- может быть позднее объединён, разделён или удалён;
- не обязан закрепляться в контексте первого наблюдения.

---

## 9. Ожидаемые эффекты

При правильном или частично правильном контексте ожидаются:

- снижение числа активных кандидатов;
- уменьшение количества spurious attractors;
- сокращение iterations и compute;
- повышение top-k factor recall;
- снижение silent false-consensus;
- более честное поведение на unknown inputs;
- graceful expansion вместо немедленного глобального поиска;
- сохранение геометрической нейтральности атомарных HV.

Не ожидаются:

- восстановление уничтоженной информации;
- бесконечная capacity;
- guaranteed exact factorization;
- immunity к ошибкам context controller;
- бесплатное решение open-world recognition.

---

## 10. Основные риски

### Context-induced false certainty

Ошибочный узкий prior может исключить истинный фактор и сделать ложный attractor более чистым.

### Context-controller correlation

Если context model и verifier используют один и тот же источник ошибок, их согласие не является независимым подтверждением.

### Symbolic codebook bottleneck

Слишком жёсткая иерархия тегов может превратить систему в хрупкую папочную классификацию.

### Expansion degeneracy

Если почти каждый запрос доходит до глобального codebook, система становится медленным вариантом обычного resonator.

### Unknown-to-known collapse

Без open-set branch неизвестные объекты будут систематически превращаться в ближайший известный класс.

### Calibration drift

Пороги confidence могут перестать соответствовать реальному риску при изменении codebook, контекстных priors или распределения данных.

---

## 11. Minimal Experimental Harness

### Baselines

1. Global resonator.
2. Random pruning до того же размера candidate pool.
3. Oracle-context hard gate.
4. Predicted-context hard gate.
5. Predicted-context soft prior.
6. Soft prior + multi-start.
7. Soft prior + verifier + best-first expansion.
8. Attention/sparse resonator baseline, если доступен.

### Test cases

- типичный объект в ожидаемом контексте;
- редкий объект в ожидаемом контексте;
- «крыса в гараже»;
- неверно предсказанный macro-context;
- объект с несколькими контекстными принадлежностями;
- полностью новый атом;
- известные факторы при высоком VSA-noise;
- информация, уже разрушенная bundling;
- конфликт top-down prior и bottom-up evidence;
- рост codebook;
- рост числа факторов;
- смена distribution.

### Метрики

- exact factor recovery;
- top-k recall;
- silent false-consensus;
- selective risk;
- coverage;
- calibration error;
- abstention rate;
- context-exclusion rate истинного фактора;
- iterations / compute;
- rollback / expansion depth;
- residual;
- novelty detection precision/recall;
- memory overhead;
- performance при ошибке context model.

---

## 12. Обязательные Ablations

1. Semantic context gate против random gate того же размера.
2. Soft prior против hard mask.
3. Verifier включён / выключен.
4. Multi-start включён / выключен.
5. Best-first expansion против линейного parent rollback.
6. Independent check против same-input reconstruction.
7. Context graph против единственного context pointer.
8. Open-set branch включён / выключен.
9. Equal compute budget для всех систем.
10. Equal dimension и RAM budget.

---

## 13. Критерии опровержения

Гипотеза считается опровергнутой или существенно ослабленной, если:

1. random pruning даёт тот же выигрыш, что и semantic context;
2. после выравнивания compute budget преимущество исчезает;
3. небольшая ошибка context model резко увеличивает silent false-consensus;
4. verifier не отличает context-induced false certainty;
5. почти все запросы доходят до глобального поиска;
6. unknown inputs регулярно принимаются как известные;
7. результат объясняется только увеличением dimension, restart count или codebook redundancy;
8. система не превосходит простой soft-prior attention factorizer;
9. calibration ломается при умеренном росте codebook;
10. write-back создаёт больше ложных концептов, чем устойчивых новых категорий.

---

## 14. Claim Gate

### Допустимый научный claim

> В пределах измеренного operating envelope вероятностный внешний контекст, используемый как soft prior и механизм управления бюджетом поиска, совместно с независимой валидацией и best-first расширением контекста снижает вычислительную стоимость и частоту ложных аттракторов VSA-factorization, сохраняя возможность abstention и open-world fallback.

### Недопустимые claims

- «CGRN-HSR устраняет шум глубокой VSA».
- «Контекст гарантирует правильную факторизацию».
- «Resonator является точным solver».
- «Высокая resonance energy доказывает истинность».
- «Fallback к примитивам автоматически понимает новую сущность».
- «Система является AGI-substrate без дополнительных доказательств».

---

## 15. Authority Boundary

```text
Context Model
    → предлагает priors и constraints

Search Controller
    → распределяет compute budget и расширяет frontier

Resonator / Factorizer
    → предлагает candidate factorization

Independent Verifier
    → оценивает evidence и риск

Transactional Runtime
    → принимает решение ACCEPT / EXPAND / ABSTAIN / REJECT

Canonical Memory
    → коммитит только подтверждённое состояние
```

Ни context model, ни resonator, ни одиночная confidence metric не обладают authority истины.

---

## 16. Минимальный путь реализации

Не строить полноценный RGM и не писать новую resonator network.

Первый прототип:

1. существующая VSA/resonator implementation;
2. внешний metadata-indexed codebook;
3. простой probabilistic context DAG;
4. soft candidate priors;
5. multi-start factorization;
6. evidence object;
7. best-first context expansion;
8. abstention;
9. bounded transaction log;
10. provisional concept store.

Hardware gating, сложная active inference модель и долговременное автоматическое concept consolidation допускаются только после подтверждения базового эффекта.

---

## 17. Краткая формула гипотезы

> Не кодировать контекст внутрь гипервектора.  
> Не доверять сходимости resonator.  
> Использовать контекст как мягкий prior и план поиска.  
> Расширять область гипотез при недостаточном evidence.  
> Проверять результат независимыми сигналами.  
> Не коммитить сомнительное.  
> Неизвестное сохранять как provisional, а не насильно называть известным.

---

## 18. Маяк

CGRN-HSR не пытается победить информационный предел VSA геометрической магией. Она меняет архитектурную постановку задачи:

> Гипервектор не обязан самостоятельно содержать контекст, доказывать собственную интерпретацию и выбирать область поиска. Он является распределённым носителем и локальным объектом факторизации. Контекст, проверка, право отказа, структура поиска и запись нового знания принадлежат отдельным типизированным системам с разными authority boundaries.

Именно эта декомпозиция является главным содержанием гипотезы.
