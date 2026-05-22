import json
from typing import Dict, Any, List
from pathlib import Path


class ProgressTracker:
    def __init__(self):
        self.outputs_dir = Path("outputs")
        self.outputs_dir.mkdir(exist_ok=True)

    # nosec B108 - outputs folder not exposed, path traversal not applicable
    def get_progress(self) -> Dict[str, Any]:
        """Get current progress of all features, epics, and stories"""

        # Load traceability data
        traceability_file = self.outputs_dir / "traceability.json"
        if not traceability_file.exists():
            return self._empty_progress()

        try:
            with open(traceability_file, "r", encoding="utf-8") as f:
                traceability = json.load(f)
        except (json.JSONDecodeError, PermissionError, OSError) as e:
            import logging
            logging.error(f"Error loading traceability file: {e}")
            return self._empty_progress()

        # Calculate progress metrics
        progress = {
            "total_features": len(traceability.get("features", [])),
            "total_epics": len(traceability.get("epics", [])),
            "total_stories": len(traceability.get("stories", [])),
            "completed_epics": 0,
            "completed_stories": 0,
            "epic_progress": [],
            "feature_progress": [],
        }

        # Mock completion status (in real implementation, query JIRA)
        progress["completed_epics"] = self._get_completed_epics_count(
            traceability.get("epics", [])
        )
        progress["completed_stories"] = self._get_completed_stories_count(
            traceability.get("stories", [])
        )

        # Calculate percentages
        if progress["total_epics"] > 0:
            progress["epic_completion_rate"] = (
                progress["completed_epics"] / progress["total_epics"]
            ) * 100
        else:
            progress["epic_completion_rate"] = 0

        if progress["total_stories"] > 0:
            progress["story_completion_rate"] = (
                progress["completed_stories"] / progress["total_stories"]
            ) * 100
        else:
            progress["story_completion_rate"] = 0

        progress["overall_percentage"] = (
            progress["epic_completion_rate"] + progress["story_completion_rate"]
        ) / 2

        # Feature-level progress
        progress["feature_progress"] = self._calculate_feature_progress(traceability)

        return progress

    def _empty_progress(self) -> Dict[str, Any]:
        """Return empty progress structure"""
        return {
            "total_features": 0,
            "total_epics": 0,
            "total_stories": 0,
            "completed_epics": 0,
            "completed_stories": 0,
            "epic_completion_rate": 0,
            "story_completion_rate": 0,
            "overall_percentage": 0,
            "feature_progress": [],
            "epic_progress": [],
        }

    def _get_completed_epics_count(self, epics: List[Dict]) -> int:
        """Get completed epics count.

        Note: In the current implementation, real-time progress tracking
        is handled by app.py's track_overall_progress() which fetches
        status directly from JIRA via MCP. This method is a placeholder
        for offline progress estimation.
        """
        return 0

    def _get_completed_stories_count(self, stories: List[Dict]) -> int:
        """Get completed stories count.

        Note: In the current implementation, real-time progress tracking
        is handled by app.py's track_overall_progress() which fetches
        status directly from JIRA via MCP. This method is a placeholder
        for offline progress estimation.
        """
        return 0

    def _calculate_feature_progress(self, traceability: Dict) -> List[Dict]:
        """Calculate progress for each feature"""
        features = traceability.get("features", [])
        epics = traceability.get("epics", [])
        stories = traceability.get("stories", [])

        feature_progress = []

        for feature in features:
            feature_epics = [
                e for e in epics if e.get("feature_id") == feature.get("id")
            ]
            feature_stories = []

            for epic in feature_epics:
                epic_stories = [
                    s for s in stories if s.get("epic_id") == epic.get("jira_key")
                ]
                feature_stories.extend(epic_stories)

            # Mock completion calculation
            completed_epics = len(feature_epics) // 2  # Mock: half completed
            completed_stories = len(feature_stories) // 3  # Mock: third completed

            progress_item = {
                "feature_id": feature.get("id"),
                "feature_title": feature.get("title"),
                "total_epics": len(feature_epics),
                "completed_epics": completed_epics,
                "total_stories": len(feature_stories),
                "completed_stories": completed_stories,
                "completion_percentage": 0,
            }

            if len(feature_epics) > 0:
                progress_item["completion_percentage"] = (
                    completed_epics / len(feature_epics)
                ) * 100

            feature_progress.append(progress_item)

        return feature_progress
