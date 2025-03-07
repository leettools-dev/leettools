# Run LeetTools Docker containers

We can use Docker Compose to start the LeetTools service and web UI.

## Usage

First copy the [docker/env.template](docker/env.template) file to [docker/.env](docker/.env) 
and adjust the environment variables if needed.

```bash
cp docker/env.template docker/.env
```

The following environment variables are used by the docker-compose.yml file:

```bash
# env variables for docker-compose.yml

COMPOSE_PROFILES=full

# fix to a stable version if needed
LEETTOOLS_VERSION=latest
LEETTOOLS_WEB_VERSION=latest

LEETTOOLS_ENV_FILE=../.env
DEFAULT_LANGUAGE=en
# specify the DOCUMENETS_HOME variable if you want to use a different directory
DOCUMENETS_HOME=~/documents
```

To build the Docker images, you can run the following command:
```bash
docker/build.sh
```

If you do not want to build the Docker images, you can pull the latest images from the 
Docker Hub by running the following command:
```bash
cd docker
docker compose pull
cd ..
```

To start the LeetTools service and web UI, you can run the following command:
```bash
docker/start.sh
```

Now you can go [http://localhost:3000](http://localhost:3000) to access the LeetTools web UI.

By default this command will mount $LEET_HOME directory as read-write volume and 
$DOCUMENETS_HOME directory as read-only volume to the Docker containers. The $DOCUMENETS_HOME
is ~/Documents directory on Linux and macOS and C:\Users\<username>\Documents on Windows.

If you need to change these behaviors, you can change the settings in the 
[docker/.env](docker/.env) file.

To stop the LeetTools service, you can run the following command:
```bash
docker/stop.sh
```

Note that the leettols-web application is currently under development and not open sourced
yet. We plan to open source it in the near future.
