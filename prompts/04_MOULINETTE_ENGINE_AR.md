# Prompt 04 — محرك التصحيح

نفّذ evaluators:

- `c_program`
- `c_function`
- `shell`
- `project`

الخطوات القياسية:

1. تحقق من الملفات المطلوبة.
2. ارفض الملفات الزائدة إذا `strict`.
3. شغّل Norminette إذا مفعلة.
4. افحص forbidden functions.
5. compile بـ `-Wall -Wextra -Werror`.
6. شغّل fixed tests.
7. شغّل generated tests.
8. قارن stdout بدقة.
9. اكتب `trace.json` و`traceback.txt`.
