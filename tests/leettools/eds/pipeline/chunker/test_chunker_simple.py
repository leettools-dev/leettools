""" Test markdown processor """

from leettools.context_manager import Context, ContextManager
from leettools.eds.pipeline.chunk._impl.chunker_simple import ChunkerSimple


def test_chunker_simple():
    context = ContextManager().get_context()  # type: Context
    context.reset(is_test=True)

    settings = context.settings
    settings.DEFAULT_CHUNK_SIZE = 1000
    simple_chunker = ChunkerSimple(settings)
    md_content = """
        # section 1
        1. differ materially from those in the forward-looking statements, including, without limitation, the risks set forth in Part I, Item 1A, “Risk Factors” of the Annual Report on Form 10-K for the fiscal year ended December 31, 2022 and that are otherwise described or updated from time to time in our other filings with the Securities and 
        2. differ materially from those in the forward-looking statements, including, without limitation, the risks set forth in Part I, Item 1A, “Risk Factors” of the Annual Report on Form 10-K for the fiscal year ended December 31, 2022 and that are otherwise described or updated from time to time in our other filings with the Securities and 

        Consolidated Balance Sheets (in millions, except per share data) (unaudited)
        something here
        |  | September 30, 2023 | December 31, 2022
        | --- | --- | ---
        | Assets
        | Current assets Cash and cash equivalents | $ 15,932 | $ 16,253
        | Short-term investments | 10,145 | 5,932
        | Accounts receivable, net | 2,520 | 2,952
        | Inventory | 13,721 | 12,839
        | Prepaid expenses and other current assets | 2,708 | 2,941
        Based on our estimation, it is the best time to invest in the stock market.
    """

    chunks = simple_chunker.chunk(md_content)

    for chunk in chunks:
        print("Heading: ", chunk.heading)
        print("Position: ", chunk.position_in_doc)
        print("Content: ", chunk.content)
        print("Start Offset: ", chunk.start_offset)
        print("End Offset: ", chunk.end_offset)
        print("-" * 20 + "\n")
        # extract the chunk content from the original text by using offsets
        print(md_content[chunk.start_offset : chunk.end_offset])
        print("#" * 20 + "\n")

    assert chunks[0].heading == "section 1"
    assert chunks[0].position_in_doc == "1.1"
    assert chunks[0].start_offset == 0
    assert chunks[0].end_offset == 1288
