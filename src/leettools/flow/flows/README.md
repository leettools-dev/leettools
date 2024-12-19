# How to add a new flow

- Create a new directory in `src/leettools/flow/flows` with the name of the flow.
- Create a new file `flow.py` in the directory.
- Implement the AbstractExecutor class in the file.
  - The get_flow_options(cls) class method defines the options that the flow accepts.
  - The execute_for_query method is called when the flow is executed.
    It takes the following arguments:
        org: Org,
        kb: KnowledgeBase,
        user: User,
        chat_query_item: ChatQueryItem,
        display_logger: Optional[EventLogger] = None,
    And shoudl return a ChatQueryResultCreate object which will be added to the chat result.

