
The document in this directory contains sample outputs from the `digest` flow type. 
The `digest` flow type is used to generate a summary of the most relevant information 
on a topic. The sample outputs in this directory are generated from the following commands:

```bash
leet flow -t digest -k market -q "Help me research recent AI-powered marketing campaigns to benchmark for 2025 planning" \
    -p search_max_results=30 -p days_limit=180 -l info -o outputs/aimarket.md
leet flow -t digest -k interview -q "What is interviewing like now with everyone using AI?" \
    -p search_max_results=30 -p days_limit=360 -l info -o outputs/interview.md
leet flow -t digest -k aijob -q "How will agentic AI and generative AI affect our non-tech jobs?" \
    -p search_max_results=30 -p days_limit=360 -l info -o outputs/aijob.md
```