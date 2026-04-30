# العمارة المعتمدة

## فصل المسؤوليات

```txt
subjects/       ما يراه الطالب
corrections/    ما لا يراه الطالب
pools/          منطق الاختيار
workspace/      بيئة الطالب
traces/         آثار التصحيح
evaluators/     محركات الاختبار
compat/         استيراد فلسفة الأدوات القديمة
```

## أنواع التمارين

- `c_program`
- `c_function`
- `shell`
- `project`

## قرار مهم

لا تجعل exercise hardcoded داخل Python.  
كل exercise يقرأ من `meta.yml`.

## Session flow

```txt
pool -> pick exercise -> copy public subject -> student writes in rendu -> evaluator -> trace
```
