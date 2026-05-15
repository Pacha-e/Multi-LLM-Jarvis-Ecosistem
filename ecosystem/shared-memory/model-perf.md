# Model Performance Log
<!-- Escribe observaciones sobre cuándo un modelo sobresalió o falló. -->
<!-- Format: [YYYY-MM-DD CLI] Modelo: Tarea → Resultado (bueno/malo/ok) + nota -->

## Claude Sonnet 4.6 (claude-sonnet-4-6)
- Costo: $3/Mtok in, $15/Mtok out
- Mejor en: tool use, código complejo, razonamiento multi-step
- Evitar para: contexto >100k (usar Gemini), tareas triviales (usar Haiku)

## Claude Opus 4.7 (/fast mode)
- Costo: $15/Mtok in, $75/Mtok out
- Mejor en: audits profundos, refactoring complejo, análisis de seguridad
- Usar solo cuando la profundidad justifica el costo

## Gemini 2.5 Flash (via Qwen Code)
- Costo: $0.15/Mtok in, $0.60/Mtok out — 20x más barato que Sonnet
- Mejor en: contexto largo (1M tok), resúmenes, críticas, análisis de repos completos
- Usar como: crítico en eval-loop, contexto >50k tokens

## DeepSeek R1 (free via OpenRouter)
- Costo: GRATIS
- Mejor en: razonamiento matemático, chain-of-thought, algoritmos
- Limitación: latencia alta, context window moderado

## Qwen3-Coder 480B (free via OpenRouter)
- Costo: GRATIS
- Mejor en: código largo, generación de tests, scaffolding
- Limitación: rate limits estrictos

## GPT-5.4 (Codex CLI)
- Costo: ~$10/Mtok
- Mejor en: generación bulk, tasks de OpenAI, interop con ecosystem OpenAI
- Usar para: scaffold masivo, generación de documentación

## qwen2.5-coder:1.5b (Ollama local)
- Costo: GRATIS, sin internet
- Mejor en: completions simples, edits menores offline
- Limitación: 1.5B params, respuestas básicas
