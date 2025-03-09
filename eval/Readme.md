**Important!** A newer version of the evaluation program is under development.
Please refer to [evaluation-on-financebench](./evaluation-on-financebench.md) for more info

## How to run the evaluation program

First we need to install the required packages. To do this, run the following command:

```bash
% pip install -r dev-requirements.txt
```

We assume the enviroment variables or .env file are set up correctly. If not, please 
refer to the [main README](../README.md) file.

To get an example configuration file, run the following command:

```bash
# to save the file in the current directory
% python eval.py -p > eval.conf.json
```

Check the eval.conf.json to change input files and sample questions as needed.

To run the evaluation program, run the following command:

```bash
% python eval.py -f eval.conf.json
```

By default, the evaluation program will
- ingest the file specified in the input_files property, we can specify directories in 
    the list as well.
- run the queries specified in the sample_questions property against the ingested data
    as a single knowledge base
- evaluate the query out using the RAGAS framework and output the metrics, currently
    default to context_recall, faithfulness, factual_correctness

## How to run the standalone pipeline

To run the standalone pipeline, run the following command under the root leettools directory

1. create a new eval.conf.json file with the following content:
```bash
% python -m eval.eval-v2 -c eval.conf.json
```

2. run the standalone conversion pipeline
```bash
% python -m eval.eval-v2 -i convert
```

3. run the standalone chunker and embedder pipeline
```bash
% python -m eval.eval-v2 -i embed
```

4. run the evaluation after ingestion
```bash
# if you skip chunker and embedder, you can still run evaluation but get all zeros for metrics. Otherwise, you should get metrics with values all close to 1.
% python -m eval.eval-v2 -e
```



