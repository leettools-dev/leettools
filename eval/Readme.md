## How to run the evaluation program

First we need to install the required packages. To do this, run the following command:

```bash
% pip install -r dev-requirements.txt
```

We assumen the enviroment variables or .env file are set up correctly. If not, please 
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