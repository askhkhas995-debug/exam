# مطالبة التسليم الرئيسية إلى Codex

أنت عميل برمجة ذكاء اصطناعي. مهمتك هي إعادة بناء مشروع **PiscineForge** من هذه الحزمة ومن الأرشيفات القديمة التي ستجدها بجانبها.

## قاعدة مهمة جدًا

لا تعدّل الأرشيفات القديمة مباشرة.  
أنشئ مجلدًا جديدًا منظمًا باسم:

```txt
piscine-forge-rebuilt/
```

ثم انقل/أعد بناء المشروع داخله فقط.

## ما ستجده

```txt
pforge_handoff_package/
  docs/
  prompts/
  subjects/
  corrections/
  pools/
  schemas/
  piscine_forge/
  legacy_archives/
```

وفي `legacy_archives/` سيضع المستخدم أرشيفات قديمة مثل:

```txt
GradeMe
ExamShell
ExamPoolRevanced
DeepThought-like testers
```

## المطلوب منك

1. اقرأ الحزمة كاملة.
2. استخرج الأرشيفات القديمة في مجلد مؤقت.
3. حلل منطقها:
   - بنية `subjects/`
   - بنية `corrections/`
   - `pools/`
   - `tester.sh`
   - hidden `main.c`
   - traces / traceback
   - terminal menu
   - workspace / rendu
   - forbidden functions
   - Norminette
4. وثّق ما وجدته في:

```txt
piscine-forge-rebuilt/docs/LEGACY_TOOL_ANALYSIS.md
```

5. أعد بناء المشروع داخل `piscine-forge-rebuilt/` وفق الهيكل المحدد في `docs/ARCHITECTURE_AR.md`.
6. لا تجعل التمارين hardcoded في الكود. كل شيء يجب أن يأتي من `meta.yml` و`pools/*.yml`.
7. أبقِ correction files مخفية عن الطالب.
8. أضف التمارين الجديدة من `subjects/exams/handwritten_v5/`.
9. أضف مسار Piscine27 من `subjects/piscine27/`.
10. اجعل الواجهة terminal-first.
11. نفّذ CLI أوّلي:

```bash
pforge validate
pforge list subjects
pforge list pools
pforge start piscine42
pforge start piscine27
pforge exam handwritten_v5
pforge grademe
pforge trace
```

## مبدأ المنتج

هذا المشروع ليس repository حلول.  
هو **محاكي تعلم وتصحيح** يحترم فلسفة 42:

- strict filenames
- exact output
- Norminette
- allowed functions
- hidden tests
- traces
- peer-learning style
- Friday exams separate from normal Piscine
- no public solutions by default

## أولويات التنفيذ

نفّذ بالترتيب:

1. validation + loader + subject schema
2. pool loader + picker
3. C program evaluator
4. C function evaluator hidden-main
5. shell evaluator
6. Norminette wrapper
7. trace writer
8. terminal UI
9. legacy compatibility layer
10. BSQ and project evaluators

إذا وجدت أن الأرشيفات القديمة فيها منطق جيد، لا تنسخه عشوائيًا. استخرجه كفكرة، ثم أعد كتابته بشكل منظم وقابل للاختبار.
