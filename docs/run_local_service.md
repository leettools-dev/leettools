# Run the LeetTools API service locally

First make sure we have the correct settings in the .env file. The template is listed
in [../env.template](../env.template). Copy the template to a new file named .env and
change the values to match your environment.

The important ones are:

- LEET_HOME=/usr/local/leettools
- EDS_DEFAULT_LLM_BASE_URL=https://api.openai.com/v1
- EDS_LLM_API_KEY=<your_openai_api_key>

Then you can start the service with the following command:

```bash
scripts/run.sh
```

The default logging level is set to INFO. If you want to change it, you can set the
EDS_LOG_LEVEL environment variable to one of the following values: DEBUG, INFO, WARNING.
To see even more detailed logs, you can set the EDS_LOG_NOOP_LEVEL to diffeent integer
values from 1 to 5.

```bash
EDS_LOG_LEVEL=DEBUG scripts/run.sh
```

If you want to save the log to a file,

```bash
scripts/run.sh >test.log
```

If you want to save the log to a rotating log file, you can use

```bash
LOG_OUTPUT=FILE scripts/run.sh
```