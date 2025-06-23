"""
Factology Manager

Handles the business logic for creating, retrieving, and managing structured facts.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List

from google.cloud import firestore
from bot.prompt_builder import ReorganisationAction

logger = logging.getLogger(__name__)


class FactologyManager:
    """Manages fact-related operations"""

    def __init__(self, firestore_client):
        self.firestore_client = firestore_client

    def save_new_fact(
        self, user_id: str, fact_content: str, category: str, priority: str
    ) -> dict:
        """
        Creates a new fact object and saves it to Firestore.

        Args:
            user_id: The ID of the user.
            fact_content: The content of the fact.
            category: The category of the fact.
            priority: The priority of the fact.

        Returns:
            The created fact dictionary.
        """
        try:
            timestamp = datetime.now(timezone.utc).isoformat()

            self.firestore_client.add_fact(
                user_id=user_id,
                category=category,
                content=fact_content,
                priority=priority,
                timestamp=timestamp,
                hot=1.0,
            )

            logger.info(f"Saved new fact for user {user_id}.")

            # Return fact data like in MVP
            return {
                "timestamp": timestamp,
                "category": category,
                "priority": priority,
                "hot": 1.0,
                "fact_content": fact_content,
            }

        except Exception as e:
            logger.error(
                f"Failed to save fact for user {user_id}: {str(e)}", exc_info=True
            )
            raise

    def create_fact(
        self, user_id: str, category: str, content: str, priority: str
    ) -> str:
        """
        Creates a new fact and stores it in Firestore.

        Args:
            user_id: The ID of the user.
            category: The category of the fact.
            content: The content of the fact.
            priority: The priority of the fact.

        Returns:
            A confirmation message.
        """
        if not all([user_id, category, content, priority]):
            error_msg = "Missing required fields for fact creation."
            logger.error(error_msg)
            return f"Error: {error_msg}"

        try:
            timestamp = datetime.now(timezone.utc).isoformat()

            self.firestore_client.add_fact(
                user_id=user_id,
                category=category,
                content=content,
                priority=priority,
                timestamp=timestamp,
                created_by="therapist_ai",
            )

            logger.info(f"Fact created for user {user_id}")
            return "Fact recorded successfully."

        except Exception as e:
            error_msg = f"Failed to create fact for user {user_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"Error: {error_msg}"

    def update_hot_scores(self, user_id: str, fact_ids: List[int]):
        """
        Increments the hot score for each referenced fact.
        Accepts integer IDs and converts them to strings for Firestore.
        """
        if not fact_ids:
            return

        for fact_id_int in fact_ids:
            fact_id_str = str(fact_id_int)
            try:
                # Firestore's Increment is atomic and safe.
                self.firestore_client.update_fact_fields(
                    user_id, fact_id_str, {"hot": firestore.Increment(1)}
                )
                logger.info(f"Incremented hot score for fact {fact_id_str}")
            except Exception as e:
                logger.error(
                    f"Could not increment hot score for fact {fact_id_str}: {e}"
                )

    def decay_hot_scores(self, user_id: str, referenced_fact_ids: List[int]):
        """
        Decays the hot score for all facts that were NOT referenced.
        Accepts integer IDs and converts them for comparison.
        """
        try:
            all_facts = self.firestore_client.get_facts(user_id)
            if not all_facts:
                return

            referenced_set = {str(id_int) for id_int in referenced_fact_ids}
            for fact in all_facts:
                fact_id = fact.get("firestore_doc_id")
                if fact_id and fact_id not in referenced_set:
                    # Apply a small decay factor
                    new_hot_score = fact.get("hot", 0) * 0.995
                    self.firestore_client.update_fact_fields(
                        user_id, fact_id, {"hot": new_hot_score}
                    )
        except Exception as e:
            logger.error(f"Error during hot score decay for user {user_id}: {e}")

    def merge_facts(
        self, user_id: str, reorganisation_actions: List[ReorganisationAction]
    ):
        """
        Merges facts based on instructions from the o4-mini model.
        """
        if not reorganisation_actions:
            return

        for action in reorganisation_actions:
            if action.action != "merge" or not action.ids:
                continue

            # Convert integer IDs from Pydantic model to strings for Firestore
            ids_to_merge_str = [str(id_int) for id_int in action.ids]

            # Get all fact documents that need to be merged
            facts_to_merge = self.firestore_client.get_facts_by_ids(
                user_id, ids_to_merge_str
            )
            if len(facts_to_merge) < 2:
                logger.warning(
                    f"Could not find enough facts for merge action: {action.model_dump_json()}"
                )
                continue

            # Determine the heir fact (highest hot score)
            heir_fact = max(facts_to_merge, key=lambda f: f.get("hot", 0))
            heir_id = heir_fact["firestore_doc_id"]

            # Sum hot scores from all facts involved in the merge
            total_hot = sum(f.get("hot", 0) for f in facts_to_merge)

            # Update the heir fact with new content and new hot score.
            # DO NOT update the timestamp, as per instructions.
            updates = {
                "content": action.final_content,
                "hot": total_hot,
            }
            self.firestore_client.update_fact_fields(user_id, heir_id, updates)

            # Delete the other facts that were merged into the heir
            ids_to_delete = [
                f["firestore_doc_id"]
                for f in facts_to_merge
                if f["firestore_doc_id"] != heir_id
            ]
            if ids_to_delete:
                self.firestore_client.delete_facts_by_ids(user_id, ids_to_delete)

            logger.info(f"Merged facts {ids_to_delete} into fact {heir_id}.")

    def prune_facts(self, user_id: str):
        """
        Removes facts that are older than 60 days and have a low hot score.
        """
        try:
            all_facts = self.firestore_client.get_facts(user_id)
            if not all_facts:
                return

            facts_to_delete = []
            sixty_days_ago = datetime.now(timezone.utc) - timedelta(days=60)

            for fact in all_facts:
                is_cold = fact.get("hot", 0) < 0.03

                try:
                    # Firestore timestamp can be a datetime object or an ISO string
                    timestamp_str = fact.get("timestamp")
                    if isinstance(timestamp_str, datetime):
                        timestamp = timestamp_str.replace(tzinfo=timezone.utc)
                    else:
                        timestamp = datetime.fromisoformat(
                            timestamp_str.replace("Z", "+00:00")
                        )

                    is_old = timestamp < sixty_days_ago
                except (AttributeError, ValueError):
                    # If timestamp is missing or invalid, don't delete the fact
                    is_old = False

                if is_cold and is_old:
                    facts_to_delete.append(fact["firestore_doc_id"])

            if facts_to_delete:
                self.firestore_client.delete_facts_by_ids(user_id, facts_to_delete)
                logger.info(
                    f"Pruned {len(facts_to_delete)} old/cold facts for user {user_id}: {facts_to_delete}"
                )

        except Exception as e:
            logger.error(
                f"Error during fact pruning for user {user_id}: {e}", exc_info=True
            )
