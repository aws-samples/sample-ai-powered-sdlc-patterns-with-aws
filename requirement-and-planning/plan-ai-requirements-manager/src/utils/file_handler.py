import json
import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class FileHandler:
    def __init__(self):
        self.inputs_dir = Path("inputs_data").resolve()
        self.outputs_dir = Path("outputs").resolve()
        self.inputs_dir.mkdir(exist_ok=True)
        self.outputs_dir.mkdir(exist_ok=True)

    def _validate_path(self, file_path: Path, base_dir: Path) -> bool:
        """
        Validate that file path is within the allowed base directory.

        Prevents path traversal attacks by resolving to absolute paths and
        checking containment. Rejects symlinks that could escape the directory.

        This is a customer-managed security control. AWS does not manage
        local file system access — customers are responsible for securing
        file paths and directory permissions.

        Security metrics:
            - Blocks directory traversal via ../ sequences
            - Rejects symlinks that resolve outside base_dir
            - Implementation priority: Critical

        AI/ML security note: Files validated here may be passed to Amazon Bedrock
        for AI processing. Validate content classification before processing.
        See docs/SECURITY.md section 11 for dataset compliance requirements.
        """
        try:
            # Resolve to absolute path and check if it's within base_dir
            resolved_path = file_path.resolve()
            resolved_base = base_dir.resolve()

            # Check if the resolved path is relative to the base directory
            resolved_path.relative_to(resolved_base)

            # Additional check: reject symlinks that escape the directory
            if resolved_path.is_symlink():
                return False

            return True
        except (ValueError, RuntimeError):
            # Path is outside base directory
            return False

    def _safe_read_file(self, file_path: Path, base_dir: Path, max_size: int = 10 * 1024 * 1024) -> str:
        """Safely read a file with path validation and size limits"""
        # Validate path
        if not self._validate_path(file_path, base_dir):
            raise ValueError(f"Invalid file path: {file_path}")

        # Check file size
        if file_path.stat().st_size > max_size:
            raise ValueError(f"File too large: {file_path} (max {max_size} bytes)")

        # Read file
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        logger.info(f"FILE_READ: path={file_path}, size={len(content)} bytes")
        return content

    def load_input_files(self) -> Dict[str, Any]:
        """Load all input files from inputs_data folder"""
        requirements = {"business_requirements": "", "market_analysis": {}}

        # Load text/markdown files as business requirements
        text_files = list(self.inputs_dir.glob("*.txt")) + list(
            self.inputs_dir.glob("*.md")
        )
        business_text = []

        for file in text_files:
            try:
                # Validate file is within inputs_dir
                if not self._validate_path(file, self.inputs_dir):
                    continue

                content = self._safe_read_file(file, self.inputs_dir)
                business_text.append(f"## {file.name}\n{content}")
            except (ValueError, OSError) as e:
                # Log error and skip file
                logger.warning(f"Skipping file {file}: {str(e)}")
                continue

        requirements["business_requirements"] = "\n\n".join(business_text)

        # Load JSON files as market analysis
        json_files = list(self.inputs_dir.glob("*.json"))
        market_data = {}

        for file in json_files:
            try:
                # Validate file is within inputs_dir
                if not self._validate_path(file, self.inputs_dir):
                    continue

                content = self._safe_read_file(file, self.inputs_dir)
                data = json.loads(content)
                market_data[file.stem] = data
            except (ValueError, OSError, json.JSONDecodeError) as e:
                # Log error and skip file
                logger.warning(f"Skipping file {file}: {str(e)}")
                continue

        requirements["market_analysis"] = market_data

        return requirements

    def save_features(self, features: List[Any]) -> None:
        """Save generated features to outputs folder"""
        try:
            features_data = {
                "features": [
                    feature.dict() if hasattr(feature, "dict") else feature
                    for feature in features
                ],
                "generated_at": self._get_timestamp(),
            }

            # Validate output path
            output_file = self.outputs_dir / "features.json"
            if not self._validate_path(output_file, self.outputs_dir):
                raise ValueError("Invalid output path")

            # Save as JSON
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(features_data, f, indent=2)
            logger.info(f"FILE_WRITE: path={output_file}, type=features_json")

            # Save as Markdown for human readability
            self._save_features_markdown(features)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to save features: {str(e)}")
            raise

    def _save_features_markdown(self, features: List[Any]) -> None:
        """Save features as markdown documentation"""
        md_content = "# Generated Features\n\n"

        for feature in features:
            feature_dict = feature.dict() if hasattr(feature, "dict") else feature
            md_content += f"## {feature_dict['title']}\n\n"
            md_content += f"**ID:** {feature_dict['id']}\n\n"
            md_content += f"**Description:** {feature_dict['description']}\n\n"
            md_content += f"**Business Value:** {feature_dict['business_value']}\n\n"
            md_content += f"**Priority:** {feature_dict['priority']}\n\n"
            md_content += f"**Complexity:** {feature_dict['complexity']}\n\n"

            md_content += "**Acceptance Criteria:**\n"
            for criteria in feature_dict["acceptance_criteria"]:
                md_content += f"- {criteria}\n"

            if feature_dict["dependencies"]:
                md_content += "\n**Dependencies:**\n"
                for dep in feature_dict["dependencies"]:
                    md_content += f"- {dep}\n"

            md_content += "\n---\n\n"

        md_content += "\n---\n\n"
        md_content += "*Generated by Product Requirement Assistant. "
        md_content += "AI-generated content — review before use. "
        md_content += "Licensed under MIT No Attribution. See LICENSE for details.*\n"

        # Validate output path
        output_file = self.outputs_dir / "features.md"
        if not self._validate_path(output_file, self.outputs_dir):
            raise ValueError("Invalid output path")

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(md_content)
        logger.info(f"FILE_WRITE: path={output_file}, type=features_md")

    def load_features(self) -> List[Dict[str, Any]]:
        """Load features from outputs folder"""
        features_file = self.outputs_dir / "features.json"

        # Validate path
        if not self._validate_path(features_file, self.outputs_dir):
            raise ValueError("Invalid file path")

        if not features_file.exists():
            return []

        try:
            content = self._safe_read_file(features_file, self.outputs_dir)
            data = json.loads(content)

            # Validate data structure
            if not isinstance(data, dict):
                raise ValueError("Invalid JSON structure: expected dictionary")

            features = data.get("features", [])
            if not isinstance(features, list):
                raise ValueError("Invalid JSON structure: 'features' must be a list")

            return features
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from {features_file}: {str(e)}")
            return []
        except (ValueError, OSError) as e:
            logger.error(f"Failed to load features from {features_file}: {str(e)}")
            return []

    def save_traceability(self, epics: List[Any]) -> None:
        """Save traceability mapping between features and epics"""
        try:
            features = self.load_features()

            traceability = {
                "features": features,
                "epics": [epic.dict() if hasattr(epic, "dict") else epic for epic in epics],
                "stories": [],
                "updated_at": self._get_timestamp(),
            }

            # Validate output path
            output_file = self.outputs_dir / "traceability.json"
            if not self._validate_path(output_file, self.outputs_dir):
                raise ValueError("Invalid output path")

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(traceability, f, indent=2)
            logger.info(f"FILE_WRITE: path={output_file}, type=traceability_json")
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to save traceability: {str(e)}")
            raise

    def update_traceability(self, stories: List[Any]) -> None:
        """Update traceability with user stories"""
        traceability_file = self.outputs_dir / "traceability.json"

        # Validate path
        if not self._validate_path(traceability_file, self.outputs_dir):
            raise ValueError("Invalid file path")

        try:
            if traceability_file.exists():
                content = self._safe_read_file(traceability_file, self.outputs_dir)
                traceability = json.loads(content)

                # Validate structure
                if not isinstance(traceability, dict):
                    raise ValueError("Invalid traceability structure")
            else:
                traceability = {"features": [], "epics": [], "stories": []}

            traceability["stories"] = [
                story.dict() if hasattr(story, "dict") else story for story in stories
            ]
            traceability["updated_at"] = self._get_timestamp()

            with open(traceability_file, "w", encoding="utf-8") as f:
                json.dump(traceability, f, indent=2)
            logger.info(f"FILE_WRITE: path={traceability_file}, type=traceability_update")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from {traceability_file}: {str(e)}")
            # Create new traceability file
            traceability = {"features": [], "epics": [], "stories": []}
            traceability["stories"] = [
                story.dict() if hasattr(story, "dict") else story for story in stories
            ]
            traceability["updated_at"] = self._get_timestamp()
            with open(traceability_file, "w", encoding="utf-8") as f:
                json.dump(traceability, f, indent=2)
            logger.info(f"FILE_WRITE: path={traceability_file}, type=traceability_recreated")

    def load_traceability(self) -> List[Dict[str, Any]]:
        """Load traceability data"""
        traceability_file = self.outputs_dir / "traceability.json"

        # Validate path
        if not self._validate_path(traceability_file, self.outputs_dir):
            raise ValueError("Invalid file path")

        if not traceability_file.exists():
            return []

        try:
            content = self._safe_read_file(traceability_file, self.outputs_dir)
            data = json.loads(content)

            # Validate structure
            if not isinstance(data, dict):
                raise ValueError("Invalid JSON structure: expected dictionary")

            epics = data.get("epics", [])
            if not isinstance(epics, list):
                raise ValueError("Invalid JSON structure: 'epics' must be a list")

            return epics
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from {traceability_file}: {str(e)}")
            return []
        except (ValueError, OSError) as e:
            logger.error(f"Failed to load traceability from {traceability_file}: {str(e)}")
            return []

    def save_progress(self, progress: Dict[str, Any]) -> None:
        """Save progress tracking data"""
        try:
            progress["saved_at"] = self._get_timestamp()

            # Validate output path
            output_file = self.outputs_dir / "progress.json"
            if not self._validate_path(output_file, self.outputs_dir):
                raise ValueError("Invalid output path")

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(progress, f, indent=2)
            logger.info(f"FILE_WRITE: path={output_file}, type=progress_json")

            # Also save as markdown report
            self._save_progress_markdown(progress)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to save progress: {str(e)}")
            raise

    def _save_progress_markdown(self, progress: Dict[str, Any]) -> None:
        """Save progress as markdown report"""
        md_content = "# Progress Report\n\n"
        md_content += f"**Generated:** {progress.get('saved_at', 'Unknown')}\n\n"

        md_content += "## Summary\n\n"
        md_content += f"- **Features:** {progress.get('total_features', 0)}\n"
        md_content += f"- **Epics:** {progress.get('completed_epics', 0)}/{progress.get('total_epics', 0)} completed ({progress.get('epic_completion_rate', 0):.1f}%)\n"
        md_content += f"- **Stories:** {progress.get('completed_stories', 0)}/{progress.get('total_stories', 0)} completed ({progress.get('story_completion_rate', 0):.1f}%)\n"
        md_content += (
            f"- **Overall Progress:** {progress.get('overall_percentage', 0):.1f}%\n\n"
        )

        if progress.get("feature_progress"):
            md_content += "## Feature Progress\n\n"
            for feature in progress["feature_progress"]:
                md_content += f"### {feature['feature_title']}\n"
                md_content += (
                    f"- Epics: {feature['completed_epics']}/{feature['total_epics']}\n"
                )
                md_content += f"- Stories: {feature['completed_stories']}/{feature['total_stories']}\n"
                md_content += f"- Progress: {feature['completion_percentage']:.1f}%\n\n"

        md_content += "\n---\n\n"
        md_content += "*Generated by Product Requirement Assistant. "
        md_content += "AI-generated content — review before use. "
        md_content += "Licensed under MIT No Attribution. See LICENSE for details.*\n"

        # Validate output path
        output_file = self.outputs_dir / "progress_report.md"
        if not self._validate_path(output_file, self.outputs_dir):
            raise ValueError("Invalid output path")

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(md_content)
        logger.info(f"FILE_WRITE: path={output_file}, type=progress_md")

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime

        return datetime.now().isoformat()
