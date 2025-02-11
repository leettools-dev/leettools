
The documents in this directory are generated using the `digest` flow with the following
commands:

```bash
leet flow -t digest -k market -p search_max_results=30 -p days_limit=360 \
    -q "Help me research recent AI-powered marketing campaigns to benchmark for 2025 planning" \
    -l info -o outputs/aimarket.md

leet flow -t digest -k interview -p search_max_results=30 -p days_limit=360 \
    -q "What is interviewing like now with everyone using AI?" \
    -l info -o outputs/interview.md

leet flow -t digest -k aijob -p search_max_results=30 -p days_limit=360 \
    -q "How will agentic AI and generative AI affect our non-tech jobs?" \
    -l info -o outputs/aijob.md
```

