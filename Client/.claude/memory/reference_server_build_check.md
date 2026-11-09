---
name: reference-server-build-check
description: как честно проверить компиляцию сервера — mvn compile ненадёжен из-за автосборки IDE
metadata:
  type: reference
---

`mvn -o compile -pl game -am` в /workspace/server может ничего не компилировать: IDE (Java language
server) сама пишет `.class` в `game/target/classes` сразу после сохранения, даже для файлов с ошибками,
и maven видит "Nothing to compile - all classes are up to date" → BUILD SUCCESS при сломанном коде
(обнаружено 2026-09-29: закрывающая скобка класса ушла в комментарий, mvn это не поймал).

**Как проверять:** `javac` всех исходников `commons/src/main/java` + `game/src/main/java` в отдельную
папку в scratchpad. Classpath — из `mvn -o -X compile -pl game -am` (строки резолва зависимостей
`group:artifact:jar:version:compile` → `/root/.m2/repository/...jar`; плагин `dependency` офлайн
недоступен). Флаги: `-nowarn -encoding UTF-8 -proc:none`.
