To use the logging library:

```python
import os
from leettools.common.logging import logger

# the logger() function will return a thread-local logger object
# log to stdout
logger().info('test')

# log to a file
current_dir = os.getcwd()
logger().log_to_file(path=current_dir, filename='test.log', level='DEBUG')

# if you want to use a different logger, you can creat a new logger with a unique name
my_logger = EventLogger.get_instance('my_logger')
my_logger.info('test')
```

