"""
This util function is used to sort the position_in_answer in the chat history.

It generates the position_in_answer in the chat history based on the two fields:
* position_layer: the layer of the block (currently called a section)
* position_index: the global sequence number of the block
* position_heading: whether the block has a heading

For example, we should sort the position_in_answer in the following order:

Position_in_answer
1        -> layer 1, index 1
1.1      -> layer 2, index 2
1.1.1    -> layer 3, index 3
1.1.2    -> layer 3, index 4
1.2      -> layer 2, index 5
2        -> layer 1, index 6
2.1      -> layer 2, index 7
2.2      -> layer 2, index 8
2.2.1    -> layer 3, index 9
3        -> layer 1, index 10

We may have pictures, tables, text blocks as sections in the chat history, therefore, 
the position_in_answer may not be the section_id shown. Only the sections that have
position_heading=True will be shown with a new heading in the chat history. Note that
we also have the title field in the answer_item, but it may be the title of the picture
or table, not the title of the section.

The main operations are:

- Sort: sort the position_in_answer in the chat history.
- Remove: remove a section in the chat history and all the positions after it will be moved up.
- Add: add a section in the chat history and all the positions after it will be moved down.
"""

from functools import cmp_to_key

from leettools.common import exceptions
from leettools.core.schemas.chat_query_result import ChatAnswerItem


def compare_pos(pos1: str, pos2: str) -> int:
    """
    Compare position_in_answer in the chat history.

    If pos1 is the same as pos2, return 0.
    If pos1 is before pos2, return -1.
    If pos1 is after pos2, return 1.
    """
    if pos1 == pos2:
        return 0

    if pos1 == "all":
        return -1
    if pos2 == "all":
        return 1

    # right now position_in_answer can only be integer
    if int(pos1) < int(pos2):
        return -1
    return 1


def is_answer_item_before(
    answer_items1: ChatAnswerItem, answer_items2: ChatAnswerItem
) -> int:
    return compare_pos(
        answer_items1.position_in_answer, answer_items2.position_in_answer
    )


def shift_down(pos: str, insertion_layer: int, insertion_index: int) -> str:
    """
    Get the new new position_in_answer after a new node is inserted in the specified
    layer and index.

    Right now pos can only be integer so this is pretty easy.
    """
    if pos == "all":
        raise exceptions.UnexpectedCaseException(
            f"pos 'all' is not expected to be shifted down"
        )
    cur_index = int(pos)
    if cur_index < insertion_index:
        return pos
    return str(cur_index + 1)
