#!/usr/bin/env python3
"""
Bio-to-Workspace Generator

Transforms human_interview_bio.md into atomic .md workspace files.
Uses a single LLM call with structured extraction instructions.

Usage:
    python bio_to_workspace.py                    # Auto-detect latest bio
    python bio_to_workspace.py --bio path/to/bio.md
    python bio_to_workspace.py --output ./my-workspace --zip

Output Structure:
    workspace/
    ├── SOUL.md              # Existential layer (first-person)
    ├── IDENTITY.md          # AI role definition
    ├── USER.md              # User profile (descriptive)
    ├── AGENTS.md            # Deviation mapping & routing
    ├── MEMORY.md            # Session context
    ├── CONVENTIONS.md       # Terminology dictionary
    ├── OPEN_QUESTIONS.md    # Unresolved tensions
    ├── WORKFLOWS.md         # Recurring playbooks
    ├── HEARTBEAT.md         # Periodic checks
    └── CLAUDE.md            # Root instructions
"""

import sys
import json
import re
import argparse
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import asyncio

# Import config from current directory
sys.path.insert(0, str(Path(__file__).parent))
from config import config, get_most_recent_file
from llm import LLMHandle, create_client, generate_text_async
from prompt_loader import load_prompt


# ============================================================================
# FILE DEFINITIONS - Maps bio sections to target files
# ============================================================================

@dataclass
class WorkspaceFileSpec:
    """Specification for a workspace file"""
    filename: str
    scope: str
    priority: str
    voice: str
    description: str
    source_sections: List[str]


WORKSPACE_FILES: List[WorkspaceFileSpec] = [
    WorkspaceFileSpec(
        filename="SOUL.md",
        scope="soul",
        priority="critical",
        voice="first-person",
        description="Agent's long-term personality, tone, values, and 'self' narrative",
        source_sections=[
            "core_identity_architecture",
            "unspoken_directional_pulls",
            "pillar_1_adapted_views",
            "pillar_4_aspirational_trajectory"
        ]
    ),
    WorkspaceFileSpec(
        filename="IDENTITY.md",
        scope="identity",
        priority="critical",
        voice="first-person",
        description="Concrete role the AI should play for this user",
        source_sections=[
            "core_identity_architecture",
            "pillar_4_aspirational_trajectory"
        ]
    ),
    WorkspaceFileSpec(
        filename="USER.md",
        scope="user",
        priority="critical",
        voice="descriptive",
        description="Description of the human: patterns, preferences, constraints, wounds",
        source_sections=[
            "core_identity_architecture",
            "meaningful_absences",
            "cognitive_architecture",
            "pillar_1_adapted_views",
            "pillar_3_life_narrative"
        ]
    ),
    WorkspaceFileSpec(
        filename="AGENTS.md",
        scope="agents",
        priority="high",
        voice="instructional",
        description="Global rules, deviation mapping, success criteria, routing guidance",
        source_sections=[
            "deviation_mapping",
            "downstream_model_routing"
        ]
    ),
    WorkspaceFileSpec(
        filename="MEMORY.md",
        scope="memory",
        priority="high",
        voice="descriptive",
        description="Persistent high-level context to re-read every session",
        source_sections=[
            "unspoken_directional_pulls",
            "pillar_3_life_narrative",
            "open_questions"
        ]
    ),
    WorkspaceFileSpec(
        filename="CONVENTIONS.md",
        scope="conventions",
        priority="high",
        voice="reference",
        description="Shared terminology dictionary and response style rules",
        source_sections=[
            "pillar_2_semantic_symbols"
        ]
    ),
    WorkspaceFileSpec(
        filename="OPEN_QUESTIONS.md",
        scope="questions",
        priority="medium",
        voice="analytical",
        description="Live unresolved questions and tensions",
        source_sections=[
            "open_questions"
        ]
    ),
    WorkspaceFileSpec(
        filename="WORKFLOWS.md",
        scope="workflows",
        priority="medium",
        voice="instructional",
        description="Recurring playbooks and 80/20 analysis",
        source_sections=[
            "pillar_5_path_engineering"
        ]
    ),
    WorkspaceFileSpec(
        filename="HEARTBEAT.md",
        scope="heartbeat",
        priority="medium",
        voice="checklist",
        description="Periodic checks and reminders",
        source_sections=[
            "pillar_5_path_engineering",
            "open_questions"
        ]
    ),
    WorkspaceFileSpec(
        filename="CLAUDE.md",
        scope="root",
        priority="high",
        voice="instructional",
        description="Root project instructions for coding context",
        source_sections=[
            "downstream_model_routing",
            "deviation_mapping"
        ]
    ),
]


# ============================================================================
# MAIN GENERATOR CLASS
# ============================================================================

class BioToWorkspaceGenerator:
    """Generates atomic workspace files from human_interview_bio.md"""
    
    def __init__(self):
        self.handle: Optional[LLMHandle] = None
        self._init_llm()
    
    def _init_llm(self):
        """Initialize LLM client using config"""
        try:
            # Use grok-4 for extraction (needs strong synthesis ability)
            self.handle = create_client(config.api, model="grok-4", async_mode=True)
            print(f"Info: Initialized LLM {self.handle.provider} / {self.handle.model}")
        except Exception as e:
            print(f"Error: Failed to initialize LLM: {e}")
            raise
    
    async def generate_workspace(
        self,
        bio_path: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        output_format: str = "folder"
    ) -> Path:
        """
        Main entry point: bio.md → workspace files
        
        Args:
            bio_path: Path to human_interview_bio.md (auto-detect if None)
            output_dir: Where to create workspace (default: workspace/)
            output_format: "folder", "zip", or "both"
            
        Returns:
            Path to created workspace (folder or zip file)
        """
        print("\n" + "="*60)
        print("Bio-to-Workspace Generator")
        print("="*60 + "\n")
        
        # 1. Load bio content
        bio_content = self._load_bio(bio_path)
        
        # 2. Single LLM call extracts all files
        print("\nInfo: Extracting content into atomic files")
        files_content = await self._extract_files(bio_content)
        
        # 3. Validate extraction
        self._validate_extraction(files_content)
        
        # 4. Write files to disk
        workspace_path = self._write_workspace(files_content, output_dir)
        
        # 5. Create zip if requested
        if output_format in ["zip", "both"]:
            zip_path = self._create_zip(workspace_path)
            print(f"Info: Created zip archive {zip_path}")
            if output_format == "zip":
                return zip_path
        
        print("\nInfo: Workspace generation complete")
        print(f"Info: Location {workspace_path}")
        
        return workspace_path
    
    def _load_bio(self, bio_path: Optional[Path] = None) -> str:
        """Load bio content from file"""
        resolved_path: Path
        if bio_path is None:
            # Auto-detect most recent bio file in output directory
            output_dir = config.paths.OUTPUT_DIR
            bio_files = sorted(output_dir.glob("human_interview_bio*.md"))
            if not bio_files:
                raise FileNotFoundError(
                    "No human_interview_bio*.md files found in output/ directory. "
                    "Run prompt_creator.py first or specify --bio path."
                )
            resolved_path = bio_files[-1]  # Most recent
        else:
            resolved_path = Path(bio_path)
        
        if not resolved_path.exists():
            raise FileNotFoundError(f"Bio file not found: {resolved_path}")
        
        print(f"Info: Loading bio {resolved_path}")
        content = resolved_path.read_text(encoding="utf-8")
        print(f"Info: Bio size {len(content):,} characters")
        return content
    
    async def _extract_files(self, bio_content: str) -> Dict[str, str]:
        """Single LLM call to extract all files"""
        # Generate file specs text
        file_specs_text = self._format_file_specs()
        
        # Build prompt
        prompt = load_prompt("workspace_extraction_template").format(
            bio_content=bio_content,
            file_specs=file_specs_text,
            timestamp=datetime.now().isoformat()
        )
        
        # Call LLM
        response = await self._call_llm(prompt)
        
        # Extract and parse JSON
        files_content = self._parse_json_response(response)
        
        print(f"Info: Extracted {len(files_content)} files")
        return files_content
    
    def _format_file_specs(self) -> str:
        """Format file specifications for the prompt"""
        lines = []
        for spec in WORKSPACE_FILES:
            lines.append(f"\n{spec.filename}:")
            lines.append(f"  Scope: {spec.scope}")
            lines.append(f"  Priority: {spec.priority}")
            lines.append(f"  Voice: {spec.voice}")
            lines.append(f"  Description: {spec.description}")
            lines.append(f"  Source Sections: {', '.join(spec.source_sections)}")
        return "\n".join(lines)
    
    async def _call_llm(self, prompt: str) -> str:
        """Call LLM and return response"""
        try:
            if self.handle is None:
                raise ValueError("LLM handle is not initialized")

            print(f"Info: Calling {self.handle.provider.upper()} ({self.handle.model})")
            return await generate_text_async(
                self.handle,
                user_prompt=prompt,
                temperature=0.3,
                max_output_tokens=config.api.MAX_COMPLETION_TOKENS,
            )
        except Exception as e:
            print(f"Error: LLM call failed: {e}")
            raise

    def _parse_json_response(self, response: str) -> Dict[str, str]:
        """Extract and parse JSON from LLM response"""
        # Try to find JSON in the response
        # Handle cases where LLM wraps in markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find raw JSON object
            json_match = re.search(r'(\{[\s\S]*"SOUL\.md"[\s\S]*"CLAUDE\.md"[\s\S]*\})', response)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response.strip()
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"Warning: JSON parse error: {e}")
            print("Info: Attempting to fix common issues")
            # Try to fix common JSON issues
            fixed = self._fix_json(json_str)
            return json.loads(fixed)
    
    def _fix_json(self, json_str: str) -> str:
        """Attempt to fix common JSON formatting issues"""
        # Remove trailing commas
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        # Fix unescaped newlines in strings
        json_str = re.sub(r'(?<!\\)\n(?!\s*[}\]])', r'\\n', json_str)
        return json_str
    
    def _validate_extraction(self, files_content: Dict[str, str]):
        """Validate that all required files were extracted"""
        expected_files = {spec.filename for spec in WORKSPACE_FILES}
        actual_files = set(files_content.keys())
        
        missing = expected_files - actual_files
        extra = actual_files - expected_files
        
        if missing:
            print(f"Warning: Missing files: {', '.join(missing)}")
        if extra:
            print(f"Info: Extra files will be included: {', '.join(extra)}")
        
        # Check each file has minimum content
        for filename, content in files_content.items():
            if len(content) < 100:
                print(f"Warning: {filename} seems very short ({len(content)} chars)")
            if "---" not in content[:100]:
                print(f"Warning: {filename} is missing YAML frontmatter")

        print(f"Info: Validated {len(files_content)} files")
    
    def _write_workspace(
        self,
        files_content: Dict[str, str],
        output_dir: Optional[Path] = None
    ) -> Path:
        """Write all files to workspace directory"""
        # Determine output path
        if output_dir is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            workspace = Path("workspace") / f"cognitive-assistant-{timestamp}"
        else:
            workspace = Path(output_dir)
        
        workspace.mkdir(parents=True, exist_ok=True)
        print(f"\nInfo: Writing files to {workspace}")
        
        # Write each file
        for filename, content in files_content.items():
            filepath = workspace / filename
            filepath.write_text(content, encoding="utf-8")
            print(f"Info: Wrote {filename} ({len(content):,} chars)")
        
        # Create memory directory (empty, ready for use)
        memory_dir = workspace / "memory"
        memory_dir.mkdir(exist_ok=True)
        
        # Create .gitignore for memory directory
        gitignore = memory_dir / ".gitignore"
        gitignore.write_text("# Ephemeral memory files - don't commit\n*.md\n!README.md\n")
        
        # Create README in memory dir
        readme = memory_dir / "README.md"
        readme.write_text("# Memory Directory\n\nPlace daily/session notes here.\nFiles follow format: YYYY-MM-DD.md\n")
        
        print("Info: Created memory directory")
        
        return workspace
    
    def _create_zip(self, workspace_path: Path) -> Path:
        """Create zip archive of workspace"""
        zip_path = workspace_path.with_suffix(".zip")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for filepath in workspace_path.rglob("*"):
                if filepath.is_file():
                    arcname = filepath.relative_to(workspace_path.parent)
                    zf.write(filepath, arcname)
        
        return zip_path


# ============================================================================
# CLI INTERFACE
# ============================================================================

def create_argument_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser"""
    parser = argparse.ArgumentParser(
        description="Transform human_interview_bio.md into atomic workspace files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-detect and generate folder
  python bio_to_workspace.py
  
  # Specify bio file
  python bio_to_workspace.py --bio output/human_interview_bio.md
  
  # Generate zip archive
  python bio_to_workspace.py --zip
  
  # Custom output location
  python bio_to_workspace.py --output ./my-workspace --format both
        """
    )
    
    parser.add_argument(
        "--bio",
        type=str,
        help="Path to human_interview_bio.md (auto-detect if not specified)"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output directory for workspace (default: workspace/YYYYmmdd_HHMMSS/)"
    )
    
    parser.add_argument(
        "--format", "-f",
        choices=["folder", "zip", "both"],
        default="folder",
        help="Output format (default: folder)"
    )
    
    parser.add_argument(
        "--zip", "-z",
        action="store_const",
        const="zip",
        dest="format",
        help="Shorthand for --format zip"
    )
    
    return parser


async def main():
    """Main entry point"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Initialize generator
    generator = BioToWorkspaceGenerator()
    
    # Generate workspace
    try:
        result_path = await generator.generate_workspace(
            bio_path=Path(args.bio) if args.bio else None,
            output_dir=Path(args.output) if args.output else None,
            output_format=args.format
        )
        
        print(f"\nInfo: Success. Output {result_path}")
        return 0

    except FileNotFoundError as e:
        print(f"\nError: {e}")
        return 1
    except Exception as e:
        print(f"\nError: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
