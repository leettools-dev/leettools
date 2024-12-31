from typing import Any, ClassVar, Dict, List

import nltk
from nltk import pos_tag
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize

from leettools.common.logging import logger
from leettools.context_manager import Context
from leettools.core.repo.vector_store import (
    VectorSearchResult,
    VectorType,
    create_vector_store_dense,
    create_vector_store_sparse,
)
from leettools.core.schemas.chat_query_metadata import ChatQueryMetadata
from leettools.core.schemas.knowledgebase import KnowledgeBase
from leettools.core.schemas.organization import Org
from leettools.core.schemas.segment import SearchResultSegment
from leettools.core.schemas.user import User
from leettools.eds.rag.search.filter import Filter
from leettools.eds.rag.search.searcher import AbstractSearcher


class SearcherHybrid(AbstractSearcher):

    nltk_initialized: ClassVar[bool] = False

    @classmethod
    def initialize_nltk(cls) -> None:
        nltk_packages = [
            "tokenizers/punkt",
            "corpora/wordnet",
            "taggers/averaged_perceptron_tagger",
            "corpora/stopwords",
        ]
        if not cls.nltk_initialized:
            for package in nltk_packages:
                logger().info(f"Checking if {package} is available...")
                try:
                    nltk.data.find(f"{package}")
                    logger().info(f"{package} is already available.")
                except LookupError:
                    logger().info(f"{package} is not available, downloading...")
                    nltk.download(package.split("/")[1])
            cls.nltk_initialized = True

    @classmethod
    def extract_keywords(cls, sentence: str) -> str:

        cls.initialize_nltk()

        # Tokenize the sentence
        words = word_tokenize(sentence)

        # Part-of-Speech tagging
        tagged_words = pos_tag(words)

        # Initialize lemmatizer and stopwords list
        lemmatizer = WordNetLemmatizer()
        stop_words = set(stopwords.words("english"))

        # Extract keywords
        keywords = [
            lemmatizer.lemmatize(word[0])
            for word in tagged_words
            if word[0] not in stop_words and word[1].startswith(("N", "V", "J"))
        ]
        return "|".join(keywords)

    def __init__(self, context: Context) -> None:
        repo_manager = context.get_repo_manager()
        self.segmentstore = repo_manager.get_segment_store()
        self.dense_vectorstore = create_vector_store_dense(context)
        self.sparse_vectorstore = create_vector_store_sparse(context)

    def _common_hit_fusion(
        self,
        list1: List[VectorSearchResult],
        list2: List[VectorSearchResult],
    ) -> Dict[str, VectorSearchResult]:
        """
        Fuse two lists of VectorSearchResult using common hit fusion.
        The idea to return hits that are common in both lists.
        Then for the rest of the hits, do the relative score fusion.

        Args:
        list1 (list of VectorSearchResult): First list of search results.
        list2 (list of VectorSearchResult): Second list of search results.

        Returns:
        Dict of VectorSearchResult: the key is the segment_uuid
        """
        dict1 = {result.segment_uuid: result.search_score for result in list1}
        dict2 = {result.segment_uuid: result.search_score for result in list2}
        common_uuids = set(dict1.keys()) & set(dict2.keys())
        common_results = {
            segment_uuid: VectorSearchResult(
                segment_uuid=segment_uuid,
                search_score=(dict1[segment_uuid] + dict2[segment_uuid]) / 2,
                vector_type=VectorType.COMMON,
            )
            for segment_uuid in common_uuids
        }
        return common_results

    def _normalize_scores(
        self, search_scores_dict: Dict[str, float], reverse=False
    ) -> Dict[str, float]:
        if search_scores_dict == {} or len(search_scores_dict) == 0:
            return search_scores_dict

        """Normalize dictionary scores to the range 0 to 1."""
        search_scores = list(search_scores_dict.values())
        min_score = min(search_scores)
        max_score = max(search_scores)
        range_score = max_score - min_score
        if range_score == 0.0:
            return {segment_uuid: 0.0 for segment_uuid in search_scores_dict.keys()}
        if reverse:
            return {
                segment_uuid: (max_score - search_score) / range_score
                for segment_uuid, search_score in search_scores_dict.items()
            }
        else:
            return {
                segment_uuid: (search_score - min_score) / range_score
                for segment_uuid, search_score in search_scores_dict.items()
            }

    def _relative_score_fusion(
        self,
        dense_list: List[VectorSearchResult],
        sparse_list: List[VectorSearchResult],
        dense_weight=0.6,
        sparse_weight=0.4,
        default_score=0.0,
    ) -> List[VectorSearchResult]:
        """
        Fuse two lists of VectorSearchResult using normalized weighted sum.

        Args:
        - search_result_list1 (list of VectorSearchResult): First list of search results.
        - search_result_list2 (list of VectorSearchResult): Second list of search results.
        - weight1 (float): Weight for the first list.
        - weight2 (float): Weight for the second list.
        - default_score (float): Default score to use if one segment is only in on of lists.

        Returns:
        - list of tuples: Fused list of VectorSearchResult.
        """
        # Create dictionaries from the lists
        dense_dict = {result.segment_uuid: result.search_score for result in dense_list}
        sparse_dict = {
            result.segment_uuid: result.search_score for result in sparse_list
        }

        # Normalize scores for COSINE similarity
        normalized_dict_dense = self._normalize_scores(dense_dict)
        logger().debug("Normalized scores for dense vector")
        for key, value in normalized_dict_dense.items():
            logger().debug(f"{key}: {value}")

        # Normalize scores for IP similarity
        normalized_dict_sparse = self._normalize_scores(sparse_dict)
        logger().debug("Normalized scores for sparse vector")
        for key, value in normalized_dict_sparse.items():
            logger().debug(f"{key}: {value}")

        common_uuids = set(dense_dict.keys()) & set(sparse_dict.keys())
        all_list = dense_list + sparse_list
        fused_results: Dict[str, VectorSearchResult] = {}
        for result in all_list:
            if result.segment_uuid in fused_results.keys():
                continue

            if result.segment_uuid in common_uuids:
                fused_results[result.segment_uuid] = VectorSearchResult(
                    segment_uuid=result.segment_uuid,
                    vector_type=VectorType.COMMON,
                    search_score=(
                        dense_weight
                        * normalized_dict_dense.get(result.segment_uuid, default_score)
                        + sparse_weight
                        * normalized_dict_sparse.get(result.segment_uuid, default_score)
                    ),
                )
            else:
                fused_results[result.segment_uuid] = VectorSearchResult(
                    segment_uuid=result.segment_uuid,
                    vector_type=result.vector_type,
                    search_score=(
                        dense_weight
                        * normalized_dict_dense.get(result.segment_uuid, default_score)
                        + sparse_weight
                        * normalized_dict_sparse.get(result.segment_uuid, default_score)
                    ),
                )

        rtn_results: List[VectorSearchResult] = []
        for result in fused_results.values():
            rtn_results.append(result)
        return rtn_results

    def _simple_fusion(
        self,
        list1: List[VectorSearchResult],
        list2: List[VectorSearchResult],
        default_score=1.0,
    ) -> List[VectorSearchResult]:
        """
        Fuse two lists of VectorSearchResult using simple fusion.
        """
        # Create dictionaries from the lists
        dict1 = {result.segment_uuid: result.search_score for result in list1}
        dict2 = {result.segment_uuid: result.search_score for result in list2}
        all_uuids = set(dict1.keys()) | set(dict2.keys())
        fused_results = [
            VectorSearchResult(
                segment_uuid=segment_uuid,
                search_score=min(
                    dict1.get(segment_uuid, default_score),
                    dict2.get(segment_uuid, default_score),
                ),
            )
            for segment_uuid in all_uuids
        ]
        return fused_results

    def execute_kb_search(
        self,
        org: Org,
        kb: KnowledgeBase,
        user: User,
        query: str,
        rewritten_query: str,
        top_k: int,
        search_params: Dict[str, Any],
        query_meta: ChatQueryMetadata,
        filter: Filter = None,
    ) -> List[SearchResultSegment]:
        """
        Search for segments in the knowledge base.

        Args:
        - org: The organization.
        - kb: The knowledge base.
        - user: The User
        - query: The query.
        - rewritten_query: The rewritten query.
        - top_k: The number of results to return.
        - search_params: The search parameters for dense vector.
        - filter: The filter used to filter the search results.
        """
        logger().info(f"The filter is: {filter} for query {query}")

        try:
            results_from_dense_vector: List[VectorSearchResult] = (
                self.dense_vectorstore.search_in_kb(
                    org=org,
                    kb=kb,
                    user=user,
                    query=rewritten_query,  # use rewritten query for dense search
                    top_k=top_k,
                    search_params=search_params,
                    filter=filter,
                )
            )
            for result in results_from_dense_vector:
                logger().debug(f"{result.segment_uuid}: {result.search_score}")
        except Exception as e:
            logger().error(f"Error in dense vector search: {e}")
            results_from_dense_vector = []

        logger().info(
            f"Found {len(results_from_dense_vector)} from dense vector search."
        )

        # keyword_query = self._extract_keywords(query)
        logger().info(f"Extracting keywords from query...")
        if (
            query_meta is not None
            and query_meta.keywords is not None
            and query_meta.keywords is not []
        ):
            keyword_query = "|".join(query_meta.keywords)
            logger().info(f"keyword_query from metadata: {keyword_query}")
        else:
            # we use original query instead of the rewritten query for keywords
            keyword_query = SearcherHybrid.extract_keywords(query)
            logger().info(f"keyword_query from original query: {keyword_query}")

        logger().info(f"Searching Sparse Vector...")
        try:
            results_from_sparse_vector: List[VectorSearchResult] = (
                self.sparse_vectorstore.search_in_kb(
                    org=org,
                    kb=kb,
                    user=user,
                    query=keyword_query,
                    top_k=top_k,
                    filter=filter,
                )
            )
            for result in results_from_sparse_vector:
                logger().debug(f"{result.segment_uuid}: {result.search_score}")
        except Exception as e:
            logger().error(f"Error in sparse vector search: {e}")
            results_from_sparse_vector = []
        logger().info(
            f"Found {len(results_from_sparse_vector)} from sparse vector search."
        )

        results = self._relative_score_fusion(
            results_from_dense_vector,
            results_from_sparse_vector,
        )

        # the high score, the better the result
        results.sort(key=lambda x: x.search_score, reverse=True)

        logger().debug(f"Fused search results for query: {query}")
        for result in results:
            logger().debug(result)

        # return the top k results
        rtn_list = []
        for result in results[:top_k]:
            segment = self.segmentstore.get_segment_by_uuid(
                org, kb, result.segment_uuid
            )
            if segment is None:
                logger().warning(
                    f"Hybrid search returned segment {result.segment_uuid} not found in "
                    "segment store, maybe from a deleted document."
                )
                self.sparse_vectorstore.delete_segment_vector(
                    org, kb, result.segment_uuid
                )
                self.dense_vectorstore.delete_segment_vector(
                    org, kb, result.segment_uuid
                )
                continue
            rtn_list.append(
                SearchResultSegment.from_segment(
                    segment, result.search_score, result.vector_type
                )
            )
        return rtn_list
