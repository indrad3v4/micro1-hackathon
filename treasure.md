# ПЕЧОРА СКАРБАЎ — манэтызацыя Creative Court (CRAFT этап 5)
# micro1 Frontier Engineering Challenge 2026, 28–30.08, HackerEarth
# Крыніцы фактаў: research.md, concept.md (у тым ліку брыф PDF з кікофу 28.08)
# Усё, чаго няма ў гэтых файлах — пазначана ASSUMPTION.

## Галоўнае (адказ на «што такое поспех»)
Галоўны прыз — НЕ $3,000 кэш, а **топ-50 paid opportunities** з micro1:
інжынеры з рэальным досведам агентаў + eval-дасведчанасць каштуюць
**$50–200 за гадзіну** (research.md §2, ва ўкраінскай крыніцы «год» = гадзіна).
Прыз і выкуп трас — дадатковыя рэкі. Усё ніжэй падпарадкавана гэтай лесвіцы:
paid opportunities → прыз → выкуп трас → кейс у портфоліо.

---

## ТРЭК 1 — Прыз $3,000 cash (з пула $5,000)
### Што глядзяць суддзі (факты з брыфа)
- Ацэнка /100: Problem & User Value 15 · Agent Solution & Engineering 30 ·
  End-to-End Quality 20 · Measured Improvement 15 · Reproducibility 15 ·
  Hot Take 5. Тай-брейк №1 — Agent Solution & Engineering.
- «Кожная валідная работа = baseline + advanced solution» — паляпшэнне
  capability/reliability/efficiency/coverage/quality, НЕ касметыка.
- ≥10 кейсаў (калі магчыма), метрыкі: primary outcome + human time + cost per task.
- Reproducibility: Reproduction guide (чыстае асяроддзе, каманды, версіі, runtime/cost).

### Што трэба ў сабмішне, каб зачапіць прыз (крокі)
1. Зачыніць гэпы з fit-check (concept.md): **baseline** (адзін промпт/просты скрыпт
   vs Creative Court на ТЫХ ЖЭ брыфах), **10+ брыфаў з метрыкамі**, **Improvement
   Changelog** (кожная ітэрацыя → evidence + адзін выдалены эксперымент),
   **Reproduction guide**, **відэа ≤5 хв** (праблема → baseline → прагон →
   параўнанне → changelog → «самае каштоўнае змяненне»).
2. Інжынерная падача, не «крэатыў рады крэатыву»: Creative Court як eval-слой —
   baseline (генератар + просты скорынг) → advanced (Judge: кантэкстныя рубрыкі,
   edge-кейсы, veto, trace). Мова сабмішну = іх мова: trust, edge cases,
   contextual evaluations.
3. Hot take (5 балаў, ужо ёсць кандыдат): «LLM-суддзя без human veto прымае
   edge-кейс за ісціну → veto абавязковы».
4. Reproducibility 15/100: чыстыя каманды + версіі + runtime/cost у гайдзе;
   TraceRecorder JSONL як доказ празрыстасці.

### Да чаго прывязаны
Загалоўкі README (user/bottleneck/value + галоўны failure mode), структура відэа,
Changelog — усё робіцца адзін раз і ідзе ў ТРЭК 2 (там тыя ж матэрыялы прадаюць
Індру, не толькі сабмішн).

### Метрыка поспеху
Валіднае сабмішн (сертыфікат усім) = мінімум; траплення ва ўсе рубрыкі з
поўным evidence-пакетам = рэальны замах на прыз. Практычная планка: 100% чэк-ліста
SUBMIT (concept.md §SUBMIT) да 30.08 23:59.
- ASSUMPTION: дакладны парог балаў для прыза не апублікаваны.

---

## ТРЭК 2 — 50 paid opportunities (ГАЛЎНЫ ПРЫЗ)
### Што micro1 глядзіць у агент-інжынераў (факты)
- Півот micro1 = **AI-training/data lab**: пастаўка правераных экспертаў для
  ацэнкі/навучання frontier-моделяў (research.md §2). Патрэбныя: інжынеры з
  рэальным агентным досведам + «людскі фактар» дадзеных.
- Падвоеная цэннасць: «людзі, якія ўмеюць БУДАВАЦЬ агентаў І АЦЭНІВАЦЬ мадэлі»
  (research.md §3). Creative Court паказвае абедзве паловы ў адным демо.
- Іх вакансіі: «design and author evaluation tasks» — да $85/гадз
  (concept.md, крыніца micro1 LinkedIn/forum).
- Zara (AI-інтэрв'юер), вета «топ-1%» → пасля хакатону верагодны крок — AI-інтэрв'ю.
- Рэд-флагі (research.md §4): абвінавачанні ў фейкавых вакансіях дзеля збору
  інтэрв'ю, ghost-інг пасля веты, нізкія стаўкі аннататараў. Правіла: легальны
  офер НІКОЛІ не просіць плаціць; кантракт чытаць уважліва пасля веты.

### Крокі (як падаць Creative Court як proof-of-skill)
1. **README сабмішну пішацца ДЛЯ micro1**: intended user = data lab / eval-каманда;
   bottleneck = execution gap, trust, edge-кейсы; value = «судзейскі слой, які можна
   пакласці на любую агентную задачу» (каркас рубрыкі → вердыкт → trace → veto —
   не прывязаны да крэатыву, concept.md «Масштабируемость»).
2. **Секцыя value для README** — ніжэй у гэтым файле, гатова да ўклейкі.
3. **Фоллоу-ап ліст Софіі (30.08–02.09)**: дэмка + «гатовы да paid opportunities»;
   кажам мовай іх блогу: «я праектую evaluation-задачы, не толькі ганяю агентаў».
4. **LinkedIn-пост** (пасля сабмішну): кейс Creative Court + тег micro1 —
   LinkedIn ~700 Kraków×AI дае дадатковую дарогу да рэкрутараў.
5. **Падрыхтоўка да Zara-інтэрв'ю**: 3–4 цэглы гатоўнасці — (а) архітэктура
   Creator/Judge/veto/trace на пальцах, (б) метрыкі 10 брыфаў напамяць,
   (в) прыклад edge-кейсу, які суддзя лоўкіць, (г) чаму veto абавязковы.

### Да чаго прывязаны
Fit-check у concept.md: Agent Solution & Engineering 30 балаў — «наша моцная зона»;
та самая зона — тое, што micro1 пакупае. Дэмка + trace = адзін артефакт працуе
двойчы (бал + кастынг).

### Метрыка поспеху
- Выніковая: ліст-запрашэнне ў paid opportunities / праход Zara-веты.
- Прамежкавая (кантралюемая): фоллоу-ап адпраўлены да 02.09; LinkedIn-пост
  апублікаваны; у README/відэа прамоўлены ўсе чатыры «цэглы» мовы micro1
  (contextual evaluations, edge cases, trust, human override).
- ASSUMPTION: крытэрыі адбору 50 з 1126+ зарэгістраваных micro1 не раскрывае.

---

## ТРЭК 3 — Выкуп agent-трас ($2–15/траса, кап $100–200/удзельнік)
### Факты з брыфа
- **НОВАЕ:** выкуп agent-use трас — $2–15/траса, кап $100–200/удзельнік, асобна
  ад прызаў, пасля валідацыі, па асобных умовах.
- Трасы — абавязковы дэліверабл сабмішну: інструкцыі → дзеянні → feedback →
  retries/human checkpoints.
- Сабмішн пераходзіць micro1 (Hackathon Participation Agreement) — можа
  выкарыстоўвацца для навучання мадэляў. Пагаджацца асознана.

### Колькі трас з планаваных прагонаў апынецца
- З concept.md (BUILD + тэст-мера-улучшэнне): дзень 1 — каркас + Creator,
  дзень 2 — Judge + UI + trace, дзень 3 — відэа + сабмішн; 28.08 — 3 свае брыфа
  на праверку демо, 29.08 — фікс слабых рубрык, 30.08 — фінальны прагон.
- **Кожны поўны прагон Creative Court = ≥1 траса** (Creator-веер + Judge-вердыкт
  + veto-падзея, калі была). Ацэнка:
  - праверачныя прагоны 28–29.08: ~6–9 (3 брыфа × 2 дні ітэрацыі) — ASSUMPTION;
  - фінальныя eval-прагоны на 10+ брыфаў: ≥10 трас (кожны брыф = асобная траса);
  - baseline-прагоны: яшчэ ~10, але іх цана ніжэй (просты агент) — ASSUMPTION,
    што валідатар цэніць advanced-трасы вышэй дыяпазону $2.
  - **Разам: ~20–30 трас** пры капе $100–200/удзельнік → **$100–200 нотаў**
    практычна гарантавана, калі здаваць усё. Гэта не галоўныя грошы — гэта
    аплаты за актыў, які ўсё адно неабходны для сабмішну.
- Важна: трасы навучаюць мадэлі micro1 нашаму стылю eval-думання → яшчэ адзін
  мост да paid opportunities.

### Крокі (як дакументаваць прыгожа)
1. **З першага дня:** TraceRecorder піша JSONL на КОЖНЫ прагон, без выключэнняў —
   падвойная цэннасць з concept.md ужо на гэта настроена.
2. **Фармат трасы пад брыф:** інструкцыя (брыф + рубрыкі) → дзеянні агентаў
   → feedback (скорынг/edge-кейс) → retries → human checkpoint (veto). Гэты ж
   фармат ідзе ў agent trajectories сабмішну.
3. **Чысціня:** адна траса = адзін брыф + адна поўная судовая сесія;
   veto-момант пазначаны ў кожнай трасе з вета (гэта самая каштоўная частка для
   data lab: «human judgment remains essential» — іх уласны лозунг).
4. **Экспарт:** агульны пакет трас у сабмішн-пакет + метададзеныя (мадэль, дата,
   runtime/cost на трасу — падцягвае Reproducibility).
5. **Згода:** Participation Agreement пацвердзіць асознана ў перад-субмітным
   чэк-лісце 30.08; асобныя ўмовы выкупу прачытаць асобна перад згодай
   (research: «па асобных умовах» — тэкст пакуль не бачылі).

### Да чаго прывязаны
Agent trajectories — абавязковы дэліверабл №4 сабмішну; выкуп — бакавы струмень
той жа работы. Пры правільным экспарце дадатковай працы роўна нуль.

### Метрыка поспеху
- Валідаваных трас ≥20, з іх ≥10 з veto/edge-падзеямі (найкаштоўнейшыя).
- Выплачаны $100–200 (поўны кап). Кантрольная точка: пацверджанне ўмоў выкупу
  (асобныя ўмовы ў брыфе) + payout rail PL працуе (крытэрый №7 з concept.md —
  праверыць да 30.08).
- ASSUMPTION: дакладны крытэр «валіднасці» трасы апісаны толькі ў асобных
  умовах, якіх у нас яшчэ няма.

---

## VALUE — секцыя для README сабмішну (гатова да ўклейкі)
(EN наўмысна — README чытаюць у micro1; сам гэты план — беларускі.)

> ## Value
>
> **Intended user:** data labs and creative teams that use agentic systems to
> generate ideas and must decide — at scale and with an audit trail — which
> outputs are actually good.
>
> **Their bottleneck:** generative agents produce a flood of plausible creative
> directions, but "is this good, for THIS brief, by THIS rubric?" still burns
> expensive human time — and an LLM judge without oversight quietly accepts
> edge cases as truth. Trust, not generation, is the missing layer.
>
> **Why this is valuable:** Creative Court closes the loop end-to-end — a
> Creator agent fans one brief into multiple framed directions; a Judge agent
> scores them against contextual rubrics (relevance, novelty, feasibility,
> risk) and catches edge cases; a human holds veto, and every decision is
> written to an evaluation trace. The judge layer is not tied to creativity:
> the same rubric → verdict → trace → veto skeleton drops onto any agentic
> task. That is contextual evaluation in miniature — the control layer that
> makes agent output auditable, reproducible, and safe to scale.
>
> **Main failure mode:** a rubric written too generically — the Judge then
> scores fluency instead of fit, and high-scoring outputs stop correlating
> with what a human would pick. Mitigation: per-brief contextual rubrics plus
> the human veto loop, which flags exactly these calibration drifts in the trace.

---

## Пасляслоўе: парадак дзеянняў (каротка)
- Да 30.08: зачыніць baseline + 10 кейсаў + changelog + reproduction + відэа
  (ТРЭК 1) — без гэтага мёртвыя і ТРЭК 2, і ТРЭК 3.
- Трасы пісаць з першага прагона сёння (ТРЭК 3) — нуль дадатковай працы пры
  правільным экспарце.
- 30.08–02.09: фоллоу-ап Софіі + LinkedIn (ТРЭК 2) — paid opportunities
  вырашаюцца пасля хакатону, але мост кладзецца ў сабмішн-тэкст.
