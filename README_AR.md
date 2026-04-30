# PiscineForge

PiscineForge أداة Terminal للتدرب على 42 Piscine وامتحانات الجمعة. ليست
برنامجاً رسمياً من 42. هي Terminal UI وليست GUI. الشكل الافتراضي بسيط
ومدرسي: محاذاة واضحة، فواصل هادئة، وبدون emojis افتراضياً.

## التثبيت

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/pforge doctor
```

بدون تثبيت:

```bash
python3 -m piscine_forge.cli --help
```

## أوامر مهمة

```bash
pforge
pforge doctor
pforge version
pforge menu
pforge start piscine42
pforge start piscine27
pforge projects
pforge project list
pforge project requirements bsq
pforge project check bsq
pforge vog status
pforge vog init myrepo
pforge vog commit -m "initial submit" myrepo
pforge vog push myrepo
pforge vog submit myrepo
pforge exam handwritten_v5 --seed 42
pforge subject current
pforge current
pforge module list
pforge module current
pforge module progress
pforge correct
pforge moulinette
pforge moulinette summary
pforge grademe
pforge trace
pforge status
pforge history
```

اقرأ الـ subject في `workspace/subject/` وضع ملفات الحل في
`workspace/rendu/`. ملفات التصحيح، hidden mains، والاختبارات الخاصة لا تُنسخ
إلى workspace الطالب.

## Piscine: Moulinette

ابدأ مسار Piscine:

```bash
pforge start piscine42
```

حلّ الـ subject الحالي داخل `workspace/rendu/` ثم شغّل Moulinette:

```bash
pforge correct
pforge moulinette
pforge moulinette summary
```

نتيجة Moulinette إذا كانت OK تقدّمك إلى التمرين التالي عندما يكون موجوداً.
تفاصيل التصحيح تظهر في trace داخل `workspace/traces/`.
الأمر `pforge correct` يختار طبقة التصحيح حسب mode. داخل Piscine، يبقى
`pforge grademe` للتوافق فقط ويعرض تحذيراً واضحاً بأن الجلسة تستعمل
Moulinette.

التنقل داخل Piscine صار واعياً بالموديولات. أوامر `pforge current` و
`pforge status` والقائمة الطرفية تعرض Pool وModule وExercise وSubject وNext،
مثلاً `z` يظهر كـ `Shell00 / ex00 / z`. استعمل `pforge module list` و
`pforge module progress` لفحص الموديول الحالي بدون تشغيل التصحيح.

الأمر `pforge moulinette summary` يعرض ملخصاً اختيارياً بأسلوب Moulinette
للموديول الحالي اعتماداً على session وprogress وtraces. هو طبقة تلخيص فقط:
لا يعيد تصحيح الموديول كاملاً ولا يستبدل تصحيح التمرين الواحد.
تصحيح موديول كامل ما زال عملاً مستقبلياً وليس مطبقاً في هذا الأمر.

## Exam: Grademe

ابدأ امتحاناً:

```bash
pforge exam handwritten_v5 --seed 42
```

حلّ التمرين المختار داخل `workspace/rendu/` ثم شغّل Grademe:

```bash
pforge grademe
pforge correct
```

نتيجة Grademe إذا كانت OK تفتح المستوى التالي عندما يكون موجوداً. تفاصيل
التصحيح تظهر في trace داخل `workspace/traces/`.
داخل Exam، الأمر `pforge moulinette` يرفض التشغيل ويوجهك إلى
`pforge grademe` أو `pforge correct`.

## المشاريع و Vogsphere المحلي

الأمر `pforge projects` يعرض فقط المشاريع الموجودة أو المهيأة حالياً في
الريبو: Rush00 وRush01 وRush02 وSastantua وMatch-N-Match وEval Expr وBSQ.

استعمل أوامر الفحص الأولي للمشاريع لمعرفة عقد التسليم المحلي وفحص
`workspace/rendu/` قبل التصحيح الكامل:

```bash
pforge project list
pforge project requirements bsq
pforge project check bsq
```

مشاريع BSQ وRush لديها عقود تسليم أولية في المحاكي المحلي الحالي. أما
Sastantua وMatch-N-Match وEval Expr فتظهر بوضوح كـ metadata incomplete إلى أن
تضاف عقود تسليم مفصلة.

الأمر `pforge vog` هو محاكاة تعليمية محلية لـ Vogsphere. يأخذ snapshots من
`workspace/rendu/` فقط إلى `workspace/vogsphere/repos/<name>/` ويحفظ الحالة
المحلية في `workspace/vogsphere/state.json`.

```bash
pforge vog status myrepo
pforge vog init myrepo
pforge vog commit -m "initial submit" myrepo
pforge vog log myrepo
pforge vog push myrepo
pforge vog submit myrepo
pforge vog history myrepo
```

هذه الطبقة ليست مطلوبة حالياً لتشغيل Moulinette أو Grademe. لا تستعمل شبكة،
ولا SSH، ولا Kerberos، ولا خوادم 42 حقيقية، ولا تلمس `~/.ssh`.
فحص المشاريع ما زال يقرأ `workspace/rendu/` فقط ولا يستعمل snapshots
Vogsphere حالياً.

## reset آمن

```bash
pforge reset session
pforge reset progress
pforge reset traces
pforge reset all
```

الأوامر `reset progress` و `reset traces` و `reset all` تطلب تأكيداً إلا إذا
استعملت `--yes`. الأمر `reset all` لا يحذف `workspace/rendu/` افتراضياً.

## الثيمات والألوان

```bash
PFORGE_THEME=official pforge menu
PFORGE_THEME=tokyo-night pforge menu
PFORGE_THEME=gruvbox pforge menu
PFORGE_THEME=plain pforge menu
```

`PFORGE_THEME=graphbox` يعمل كاسم بديل لـ `gruvbox`. لإيقاف الألوان استعمل:

```bash
NO_COLOR=1 pforge status
PFORGE_THEME=plain pforge status
```

الألوان تظهر فقط عندما يكون stdout طرفية TTY.

PiscineForge لا يستطيع تغيير خط الطرفية من Python. غيّر الخط من إعدادات
terminal app. خطوط مقروءة مقترحة: JetBrains Mono و IBM Plex Mono و Hack و
Fira Code و MesloLGS. Nerd Fonts اختيارية وليست مطلوبة.

## ملاحظات السلامة والتوزيع

PiscineForge محاكي تعليمي محلي، وليس برنامجاً رسمياً من 42، وليس judge آمناً
عن بعد. قد يحتوي الريبو المحلي على fixtures للتصحيح داخل `resources/` وبيانات
تصحيح خاصة داخل `corrections/`؛ هذه الملفات لا تُنسخ إلى
`workspace/subject/` المرئي للطالب. هذا يحمي workspace الطالب، لكنه لا يمنع
شخصاً من قراءة الريبو نفسه. أي توزيع عام بنمط تحديات سيحتاج طريقة تغليف
مختلفة للـ fixtures الخاصة.

طبقة Vogsphere هنا محاكاة تعليمية محلية فقط. PiscineForge لا يستعمل Kerberos،
لا يرفع ملفات إلى أي مكان، لا يعدل إعدادات SSH، لا يتصل ببنية 42 الحقيقية،
ولا يوفر GUI.

الدليل الكامل موجود في `docs/STUDENT_USAGE.md`.
