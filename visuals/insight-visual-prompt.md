# Engineer File Prompt — візуалізацыя інсайту «Слепы подпіс»
Дата: 2026-08-28 · Прызначэнне: image_generate → візуал для сабмішну (README/відэа-тумбнейл) і LinkedIn-поста

## Context
Інсайт (фінальны, прыняты): «Людзі аўтаматызуюць рашэнні, але подпіс пакідаюць чалавеку — бо давер
будуецца не на правільнасці адказу, а на магчымасці спыніць памылку — хоць усе ўпэўнены, што
"проста дададзім яшчэ адзін слой праверкі"».
Драма (эскалe): кожны новы слой суддзі/праверкі = новы экран паміж чалавекам і рашэннем;
veto слепне; памылка праходзіць пад звычайным «OK». Павер'е ў слаі замяніла давер да рашэння.

## Task
Стварыць АДНУ канцэптуальную візуалізацыю інсайту для сабмішну micro1 (спагляд: суддзі —
інжынеры; мова выяў — агульначалавечая, без літар). Затым падрыхтаваць варыянт
LinkedIn-фармату (квадрат).

## Ideal ending (ИКР)
Візуал тлумачыць інсайт БЕЗ тэксту-выканаўцы: глядач павінен за 3 секунды адчуць «кожны слой —
гэта экран, подпіс слепы» і ўбачыць, дзе ў гэтай архітэктуры чалавек. Дзеля гэтага ўся
стаграфія — на ўжо існуючым інструменце image_generate; нічога новага не будаваць.

## Acceptance criteria
- AC1: Слой-метафора чытаецца іерархіяй: шмат празрыстых экранаў/штоў паміж чалавекам і рашэннем.
- AC2: Чалавечая рука/подпіс — адзіны цёплы (жывы) элемент у халоднай схеме; размешчана так,
  што яна фізічна НЕ дасягае рашэння (экраны перакрываюць).
- AC3: Памылка «пад OK» — адзіны чырвоны знак, які праходзіць скрозь усе слоі скрозь, а OK-падпіс
  наперадзе яго на апошнім слаі.
- AC4: No text inside the image (толькі графіка; подпіс «OK» — дапушчальны як адзіны надпіс).
- AC5: Тэхнічна: 2 варыянты — landscape (README/відэа 16:9) + square (LinkedIn 1:1).
- AC6: Без логатыпаў, без фота-рэалісткі асоб, без кітчу; мова сцэны — clean editorial/conceptual.

## Prompt (landscape, для image_generate)
Conceptual editorial illustration, dark navy background. In the center-right: a glowing white
decision document floating in space. Between the viewer and the document: a series of 6-7
translucent glass panes arranged in a receding row, each pane slightly darker and more opaque,
like a corridor of screens — each pane subtly decorated with faint machine interfaces (rubric
checkmarks, score dials). From the left edge, a single human hand in warm golden light reaches
toward the document to sign it — but the panes block it: the hand stops at the first pane,
warm light fading where glass begins. Through all panes, a thin red error line passes freely
(all the way through), while on the nearest pane a small bright green OK stamp glows in front
of the red line. Mood: quiet tension, not dystopia. Style: minimal, precise, tech-editorial,
soft depth of field, cool blues vs single warm accent, no text except the OK stamp.

## Prompt (square, LinkedIn — той жа сцэнарый, кампазіцыя 1:1)

## Constraints & style
- Ствараць толькі праз image_generate (landscape + square); без фотастокаў, без прэтшэрыў.
- Пасля генерацыі: праверыць AC1-4 на вока (vision_analyze), пры правале — пераробіць промпт,
  не прымаць «прымерна».
- Размяшчэнне файлаў: /root/.hermes/micro1-hackathon/visuals/insight-landscape.png,
  insight-square.png ( дырэкторыю стварыць).

## Verification / self-check (унутраны, не паказваць)
Праверыць: адзіны цёплы элемент = рука (AC2)? чырвоная лінія праходзіць скрозь (AC3)?
стога празрыстасці нарастае ўглыб (AC1)? тэксту акрамя OK няма (AC4)? Кожны AC — так/не,
не — перагенерацыя (макс 2 спробы, затым змяніць кампазіцыю).
