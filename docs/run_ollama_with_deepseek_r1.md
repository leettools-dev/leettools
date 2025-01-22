With the new DeepSeek-R1 model, we can now run reasoning tasks with the open source LLM.
The R1 model is also available through the DeepSeek API, which means we can integrate
it into our workflow. Even better, Ollama added several versions of the R1 model to their
library, now we can run the R1 model with Ollama locally.

In this example, we will run the R1 model with Ollama locally using LeetTools with 
a full end-to-end document pipeline with RAG functionality. Since we use DuckDB as the
backend, the whole pipeline fits comfortably in a single laptop with 16GB of RAM and no
dedicated GPU.

# Install Ollama

1. Follow the instructions on https://github.com/ollama/ollama to install the ollama 
program. Make sure the ollama program is running:

```bash
# if the ollama program is not running, start it with the following command
ollama serve
```

2. Load the ollama models:
```bash
% ollama pull deepseek-r1:1.5b
% ollama pull nomic-embed-text
```

# Install LeetTools

```bash
% conda create -y -n leettools python=3.11
% conda activate leettools
% pip install leettools

# where we store all the data and logs
% export LEET_HOME=${HOME}/leettools
% mkdir -p ${LEET_HOME}

% cat > .env.ollama <<EOF
# need tot change LEET_HOME to the correct path
LEET_HOME=</Users/myhome/leettools>
EDS_DEFAULT_LLM_BASE_URL=http://localhost:11434/v1
EDS_LLM_API_KEY=dummy-key
EDS_DEFAULT_INFERENCE_MODEL=deepseek-r1:1.5b
EDS_DEFAULT_EMBEDDING_MODEL=nomic-embed-text
EDS_EMBEDDING_MODEL_DIMENSION=768
EOF
```

# Build your local knowledge base with one command

With one commandline, we can build the knowledge base with a PDF file from the URL. 
You can add more URLs if need to.

```bash
# this is a great LLM introduction book with 231 pages
leet kb add-url -e .env.ollama -k llmbook -l info \
    -r https://arxiv.org/pdf/2501.09223

# you can also add local directory / files using the "kb add-local" command
# or add a list of urls saved in a file using the "kb add-url-list" command
```

# Query your local knowledge base with R1

The following command will anwser the question with the R1 model using the content from
the LLM introduction book.

```bash
leet flow -t answer -e .env.ollama -k llmbook -p retriever_type=local -l info \
    -p output_language=cn -q "How does the FineTune process Work?" 
```

# Resource Usage

The best part of the process is that, the whole pipeline is only using around 2GB of 
memory and does not need special GPU to run:

1. the LeetTools document pipeline with RAG service backend is using around 350MB of memory
2. the R1 model is using around 1.6GB of memory and the embed model is using around 370MB of memory

```bash
% ollama ps 
NAME                       ID              SIZE      PROCESSOR    UNTIL              
deepseek-r1:1.5b           a42b25d8c10a    1.6 GB    100% CPU     4 minutes from now    
nomic-embed-text:latest    0a109f422b47    370 MB    100% CPU     4 minutes from now  
```
