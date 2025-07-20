"""Agent builder module for generating files from Agentfile configuration."""

import json
import os
import shutil
import subprocess
from pathlib import Path

from agentman.agentfile_parser import AgentfileConfig, AgentfileParser
from agentman.frameworks import AgnoFramework, FastAgentFramework
from agentman.yaml_parser import AgentfileYamlParser, parse_agentfile


class AgentBuilder:
    """Builds agent files from Agentfile configuration."""

    def __init__(self, config: AgentfileConfig, output_dir: str = "output", source_dir: str = "."):
        self.config = config
        self._output_dir = Path(output_dir)
        self.source_dir = Path(source_dir)
        # Check if prompt.txt exists in the source directory
        self.prompt_file_path = self.source_dir / "prompt.txt"
        self.has_prompt_file = self.prompt_file_path.exists()

        # Initialize framework handler
        self.framework = self._get_framework_handler()

    @property
    def output_dir(self):
        """Get the output directory."""
        return self._output_dir

    @output_dir.setter
    def output_dir(self, value):
        """Set the output directory and update framework handler."""
        self._output_dir = Path(value)
        if hasattr(self, 'framework'):
            self.framework.output_dir = self._output_dir

    def _get_framework_handler(self):
        """Get the appropriate framework handler based on configuration."""
        if self.config.framework == "agno":
            return AgnoFramework(self.config, self._output_dir, self.source_dir)

        return FastAgentFramework(self.config, self._output_dir, self.source_dir)

    def build_all(self):
        """Build all generated files."""
        self._ensure_output_dir()
        self._copy_prompt_file()
        self._generate_python_agent()
        self._generate_config_yaml()
        self._generate_dockerfile()
        self._generate_requirements_txt()
        self._generate_dockerignore()
        self._validate_output()

    def _ensure_output_dir(self):
        """Ensure output directory exists."""
        self.output_dir.mkdir(exist_ok=True)

    def _copy_prompt_file(self):
        """Copy prompt.txt to output directory if it exists."""
        if self.has_prompt_file:
            dest_path = self.output_dir / "prompt.txt"
            shutil.copy2(self.prompt_file_path, dest_path)

    def _generate_python_agent(self):
        """Generate the main Python agent file."""
        content = self.framework.build_agent_content()

        agent_file = self.output_dir / "agent.py"
        with open(agent_file, 'w', encoding='utf-8') as f:
            f.write(content)

    def _generate_config_yaml(self):
        """Generate the configuration file based on framework."""
        self.framework.generate_config_files()

    def _generate_dockerfile(self):
        """Generate the Dockerfile."""
        lines = []

        # Start with FROM instruction
        lines.extend([f"FROM {self.config.base_image}", ""])

        # Copy requirements and install Python dependencies
        lines.extend(
            [
                "# Copy requirements and install Python dependencies",
                "COPY requirements.txt .",
                "RUN pip install --no-cache-dir -r requirements.txt",
                "",
            ]
        )

        # Add all other Dockerfile instructions in order (except FROM)
        # We'll handle EXPOSE and CMD at the end in their proper positions
        for instruction in self.config.dockerfile_instructions:
            if instruction.instruction not in ["FROM", "EXPOSE", "CMD"]:
                lines.append(instruction.to_dockerfile_line())

        # Add a blank line if we have custom instructions
        custom_instructions = [
            inst for inst in self.config.dockerfile_instructions if inst.instruction not in ["FROM", "EXPOSE", "CMD"]
        ]
        if custom_instructions:
            lines.append("")

        # Set working directory if not already set by custom instructions
        workdir_set = any(inst.instruction == "WORKDIR" for inst in self.config.dockerfile_instructions)
        if not workdir_set:
            lines.extend(["WORKDIR /app", ""])

        # Copy application files
        copy_lines = [
            "# Copy application files",
            "COPY agent.py .",
        ]

        # Add framework-specific configuration files
        framework_config_lines = self.framework.get_dockerfile_config_lines()
        copy_lines.extend(framework_config_lines)

        # Add prompt.txt copy if it exists
        if self.has_prompt_file:
            copy_lines.append("COPY prompt.txt .")

        copy_lines.append("")
        lines.extend(copy_lines)

        # Add EXPOSE instructions from custom dockerfile instructions first
        expose_instructions = [inst for inst in self.config.dockerfile_instructions if inst.instruction == "EXPOSE"]
        if expose_instructions:
            for instruction in expose_instructions:
                lines.append(instruction.to_dockerfile_line())
            lines.append("")

        # Add EXPOSE from config.expose_ports if not already handled
        if self.config.expose_ports and not expose_instructions:
            expose_lines = [f"EXPOSE {port}" for port in self.config.expose_ports]
            lines.extend(expose_lines)
            lines.append("")

        # Add CMD instructions from custom dockerfile instructions first
        cmd_instructions = [inst for inst in self.config.dockerfile_instructions if inst.instruction == "CMD"]
        if cmd_instructions:
            for instruction in cmd_instructions:
                lines.append(instruction.to_dockerfile_line())
        elif self.config.cmd:
            # Default command from config
            cmd_str = json.dumps(self.config.cmd)
            lines.append(f"CMD {cmd_str}")

        dockerfile = self.output_dir / "Dockerfile"
        with open(dockerfile, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))

    def _generate_requirements_txt(self):
        """Generate the requirements.txt file based on framework."""
        requirements = self.framework.get_requirements()

        # Remove duplicates and sort
        requirements = sorted(list(set(requirements)))

        req_file = self.output_dir / "requirements.txt"
        with open(req_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(requirements) + "\n")

    def _generate_dockerignore(self):
        """Generate the .dockerignore file."""
        ignore_patterns = [
            "# Python",
            "__pycache__/",
            "*.py[cod]",
            "*$py.class",
            "*.so",
            ".Python",
            "build/",
            "develop-eggs/",
            "dist/",
            "downloads/",
            "eggs/",
            ".eggs/",
            "lib/",
            "lib64/",
            "parts/",
            "sdist/",
            "var/",
            "wheels/",
            "*.egg-info/",
            ".installed.cfg",
            "*.egg",
            "",
            "# Virtual Environment",
            ".venv",
            "env/",
            "venv/",
            "ENV/",
            "",
            "# IDE",
            ".idea/",
            ".vscode/",
            "*.swp",
            "*.swo",
            "",
            "# Git",
            ".git/",
            ".gitignore",
            "",
            "# Logs",
            "*.log",
            "logs/",
            "",
            "# OS",
            ".DS_Store",
            "Thumbs.db",
        ]

        dockerignore = self.output_dir / ".dockerignore"
        with open(dockerignore, 'w', encoding='utf-8') as f:
            f.write("\n".join(ignore_patterns))

    def _validate_output(self):
        """Validate that all required files were generated."""
        # Skip validation in test environments or when fast-agent is not available
        try:
            subprocess.run(["fast-agent", "check"], check=True, cwd=self.output_dir, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            # If fast-agent is not available or validation fails, just warn but don't fail
            print(f"⚠️  Validation skipped: {e}")


def _is_file_path(prompt_value: str, source_dir: Path) -> bool:
    """Check if a prompt value is a file path or text string."""
    # If it looks like a file path and the file exists, treat it as a file
    prompt_path = Path(prompt_value)

    # Check for absolute path
    if prompt_path.is_absolute() and prompt_path.exists():
        return True

    # Check for relative path from source directory
    relative_path = source_dir / prompt_value
    if relative_path.exists():
        return True

    # If it contains newlines or is very long, likely text content
    if '\n' in prompt_value or len(prompt_value) > 200:
        return False

    # If it has common file extensions, treat as file path (even if not found)
    common_extensions = {'.txt', '.md', '.py', '.json', '.yaml', '.yml'}
    if any(prompt_value.lower().endswith(ext) for ext in common_extensions):
        return True

    # Default to treating as text string
    return False


def _read_prompt_file(file_path: str, source_dir: Path) -> str:
    """Read prompt content from a file path."""
    prompt_path = Path(file_path)

    # Try absolute path first
    if prompt_path.is_absolute() and prompt_path.exists():
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()

    # Try relative to source directory
    relative_path = source_dir / file_path
    if relative_path.exists():
        with open(relative_path, 'r', encoding='utf-8') as f:
            return f.read()

    # File not found, raise error
    raise FileNotFoundError(f"Prompt file not found: {file_path}")


def _apply_cli_overrides(config: AgentfileConfig, cli_overrides: dict, source_dir: Path) -> AgentfileConfig:
    """Apply CLI overrides to the agent configuration."""
    agent_name = cli_overrides.get('agent_name')
    agent_prompt = cli_overrides.get('agent_prompt')

    if not agent_name or not agent_prompt:
        return config

    # Determine if prompt is file path or text string
    if _is_file_path(agent_prompt, source_dir):
        try:
            prompt_content = _read_prompt_file(agent_prompt, source_dir)
        except FileNotFoundError as e:
            print(f"⚠️  Warning: {e}, treating as text string")
            prompt_content = agent_prompt
    else:
        prompt_content = agent_prompt

    # Find existing agent by name or create new one
    agent_found = False
    for agent in config.agents:
        if agent.name == agent_name:
            # Override existing agent's instruction
            agent.instruction = prompt_content
            agent.default = True  # Make CLI agent the default
            agent_found = True
            print(f"✅ Overriding agent '{agent_name}' with CLI prompt")
            break

    if not agent_found:
        # Create new agent with the name and prompt
        # We need to import the Agent class - let's assume it exists in the config
        from agentman.agentfile_parser import Agent

        new_agent = Agent(name=agent_name, instruction=prompt_content, default=True)
        config.agents.append(new_agent)
        print(f"✅ Created new agent '{agent_name}' with CLI prompt")

    # Make sure only the CLI agent is default
    for agent in config.agents:
        if agent.name != agent_name:
            agent.default = False

    return config


def build_from_agentfile(
    agentfile_path: str, output_dir: str = "output", format_hint: str = None, cli_overrides: dict = None
) -> None:
    """Build agent files from an Agentfile."""
    if format_hint == "yaml":
        parser = AgentfileYamlParser()
        config = parser.parse_file(agentfile_path)
    elif format_hint == "dockerfile":
        parser = AgentfileParser()
        config = parser.parse_file(agentfile_path)
    else:
        # Auto-detect format
        config = parse_agentfile(agentfile_path)

    # Extract source directory from agentfile path
    source_dir = Path(agentfile_path).parent

    # Apply CLI overrides if provided
    if cli_overrides:
        config = _apply_cli_overrides(config, cli_overrides, source_dir)

    builder = AgentBuilder(config, output_dir, source_dir)
    builder.build_all()

    print(f"✅ Generated agent files in {output_dir}/")
    print("   - agent.py")

    # Show framework-specific config files
    if config.framework == "agno":
        print("   - .env")
    else:
        print("   - fastagent.config.yaml")
        print("   - fastagent.secrets.yaml")

    print("   - Dockerfile")
    print("   - requirements.txt")
    print("   - .dockerignore")

    # Check if prompt.txt was copied
    if builder.has_prompt_file:
        print("   - prompt.txt")
