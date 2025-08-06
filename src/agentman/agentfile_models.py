"""Data models and utilities for Agentfile configurations."""

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

import yaml


def expand_env_vars(value: str) -> str:
    """
    Expand environment variables in a string.

    Supports both ${VAR} and $VAR syntax.
    If environment variable is not found, returns the original placeholder.

    Args:
        value: String that may contain environment variable references

    Returns:
        String with environment variables expanded
    """
    if not isinstance(value, str):
        return value

    # Pattern to match ${VAR} or $VAR (where VAR is alphanumeric + underscore)
    pattern = r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)'

    def replace_var(match):
        # Get the variable name from either group
        var_name = match.group(1) or match.group(2)
        env_value = os.environ.get(var_name)
        if env_value is not None:
            return env_value
            # Return the original placeholder if env var not found
        return match.group(0)

    return re.sub(pattern, replace_var, value)


@dataclass
class MCPServer:
    """Represents an MCP server configuration."""

    name: str
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)
    transport: str = "stdio"
    url: Optional[str] = None
    env: Dict[str, str] = field(default_factory=dict)

    def to_config_dict(self) -> Dict[str, Any]:
        """Convert to fastagent.config.yaml format."""
        config = {"transport": self.transport}

        if self.command:
            config["command"] = self.command
        if self.args:
            config["args"] = self.args
        if self.url:
            config["url"] = self.url
        if self.env:
            config["env"] = self.env

        return config


@dataclass
class OutputFormat:
    """Represents output format configuration for an agent."""

    type: str  # "json_schema" or "schema_file"
    schema: Optional[Dict[str, Any]] = None  # For inline JSON Schema as YAML
    file: Optional[str] = None  # For external schema file reference


@dataclass
class Agent:
    """Represents an agent configuration."""

    name: str
    instruction: str = "You are a helpful agent."
    servers: List[str] = field(default_factory=list)
    model: Optional[str] = None
    use_history: bool = True
    human_input: bool = False
    default: bool = False
    output_format: Optional[OutputFormat] = None

    def to_decorator_string(self, default_model: Optional[str] = None, base_path: Optional[str] = None) -> str:
        """Generate the @fast.agent decorator string."""
        # Escape quotes in the instruction to prevent breaking the decorator
        escaped_instruction = self.instruction.replace('"""', '\\"\\"\\"')
        params = [f'name="{self.name}"', f'instruction="""{escaped_instruction}"""']

        if self.servers:
            servers_str = "[" + ", ".join(f'"{s}"' for s in self.servers) + "]"
            params.append(f"servers={servers_str}")

        if model_to_use := (self.model or default_model):
            params.append(f'model="{model_to_use}"')

        if not self.use_history:
            params.append("use_history=False")

        if self.human_input:
            params.append("human_input=True")

        if self.default:
            params.append("default=True")

        # Add response_format if output_format is specified
        if self.output_format:
            request_params = self._generate_request_params(base_path)
            if request_params:
                params.append(f"request_params={request_params}")

        return "@fast.agent(\n    " + ",\n    ".join(params) + "\n)"

    def _generate_request_params(self, base_path: Optional[str] = None) -> Optional[str]:
        """Generate RequestParams with response_format from output_format."""
        if not self.output_format:
            return None

        if self.output_format.type == "json_schema" and self.output_format.schema:
            # Convert JSON Schema to OpenAI response_format structure
            schema = self.output_format.schema
            model_name = self._get_model_name_from_schema(schema)

            response_format = {"type": "json_schema", "json_schema": {"name": model_name, "schema": schema}}

            return f"RequestParams(response_format={response_format})"

        if self.output_format.type == "schema_file" and self.output_format.file:
            # Load and convert external schema file
            return self._generate_request_params_from_file(base_path)

        return None

    def _generate_request_params_from_file(self, base_path: Optional[str] = None) -> str:
        """Generate RequestParams by loading schema from external file."""

        file_path = self.output_format.file

        # Resolve relative paths relative to the Agentfile location
        if not os.path.isabs(file_path) and base_path:
            file_path = os.path.join(base_path, file_path)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.endswith('.json'):
                    schema = json.load(f)
                elif file_path.endswith(('.yaml', '.yml')):
                    schema = yaml.safe_load(f)
                else:
                    return f"# Error: Unsupported schema file format: {file_path}"

            model_name = self._get_model_name_from_schema(schema)
            response_format = {"type": "json_schema", "json_schema": {"name": model_name, "schema": schema}}

            return f"RequestParams(response_format={response_format})"

        except (FileNotFoundError, json.JSONDecodeError, yaml.YAMLError) as e:
            return f"# Error loading schema file {file_path}: {e}"

    def _get_model_name_from_schema(self, schema: Dict[str, Any]) -> str:
        """Generate a model name from the agent name or schema title."""
        if isinstance(schema, dict) and "title" in schema:
            return schema["title"]

        # Convert agent name to PascalCase for model name
        words = self.name.replace("-", "_").replace(" ", "_").split("_")
        model_name = "".join(word.capitalize() for word in words if word)
        return f"{model_name}Model"


@dataclass
class Router:
    """Represents a router workflow."""

    name: str
    agents: List[str] = field(default_factory=list)
    model: Optional[str] = None
    instruction: Optional[str] = None
    default: bool = False

    def to_decorator_string(self, default_model: Optional[str] = None) -> str:
        """Generate the @fast.router decorator string."""
        params = [f'name="{self.name}"']

        if self.agents:
            agents_str = "[" + ", ".join(f'"{a}"' for a in self.agents) + "]"
            params.append(f"agents={agents_str}")

        if model_to_use := (self.model or default_model):
            params.append(f'model="{model_to_use}"')

        if self.instruction:
            # Escape quotes in the instruction to prevent breaking the decorator
            escaped_instruction = self.instruction.replace('"""', '\\"""')
            params.append(f'instruction="""{escaped_instruction}"""')

        if self.default:
            params.append("default=True")

        return "@fast.router(\n    " + ",\n    ".join(params) + "\n)"


@dataclass
class Chain:
    """Represents a chain workflow."""

    name: str
    sequence: List[str] = field(default_factory=list)
    instruction: Optional[str] = None
    cumulative: bool = False
    continue_with_final: bool = True
    default: bool = False

    def to_decorator_string(self) -> str:
        """Generate the @fast.chain decorator string."""
        params = [f'name="{self.name}"']

        if self.sequence:
            sequence_str = "[" + ", ".join(f'"{a}"' for a in self.sequence) + "]"
            params.append(f"sequence={sequence_str}")

        if self.instruction:
            # Escape quotes in the instruction to prevent breaking the decorator
            escaped_instruction = self.instruction.replace('"""', '\\"""')
            params.append(f'instruction="""{escaped_instruction}"""')

        if self.cumulative:
            params.append("cumulative=True")

        if not self.continue_with_final:
            params.append("continue_with_final=False")

        if self.default:
            params.append("default=True")

        return "@fast.chain(\n    " + ",\n    ".join(params) + "\n)"


@dataclass
class Parallel:
    """Represents a parallel workflow."""

    name: str
    fan_out: List[str] = field(default_factory=list)
    fan_in: Optional[str] = None
    instruction: Optional[str] = None
    include_request: bool = True
    default: bool = False

    def to_decorator_string(self) -> str:
        """Generate the @fast.parallel decorator string."""
        params = [f'name="{self.name}"']

        if self.fan_out:
            fan_out_str = "[" + ", ".join(f'"{a}"' for a in self.fan_out) + "]"
            params.append(f"fan_out={fan_out_str}")

        if self.fan_in:
            params.append(f'fan_in="{self.fan_in}"')

        if self.instruction:
            # Escape quotes in the instruction to prevent breaking the decorator
            escaped_instruction = self.instruction.replace('"""', '\\"""')
            params.append(f'instruction="""{escaped_instruction}"""')

        if not self.include_request:
            params.append("include_request=False")

        if self.default:
            params.append("default=True")

        return "@fast.parallel(\n    " + ",\n    ".join(params) + "\n)"


@dataclass
class Orchestrator:
    """Represents an orchestrator workflow."""

    name: str
    agents: List[str] = field(default_factory=list)
    model: Optional[str] = None
    instruction: Optional[str] = None
    plan_type: str = "full"
    plan_iterations: int = 5
    human_input: bool = False
    default: bool = False

    def to_decorator_string(self, default_model: Optional[str] = None) -> str:
        """Generate the @fast.orchestrator decorator string."""
        params = []
        params.append(f'name="{self.name}"')

        if self.agents:
            agents_str = "[" + ", ".join(f'"{a}"' for a in self.agents) + "]"
            params.append(f"agents={agents_str}")

        model_to_use = self.model or default_model
        if model_to_use:
            params.append(f'model="{model_to_use}"')

        if self.instruction:
            # Escape quotes in the instruction to prevent breaking the decorator
            escaped_instruction = self.instruction.replace('"""', '\\"""')
            params.append(f'instruction="""{escaped_instruction}"""')

        if self.plan_type != "full":
            params.append(f'plan_type="{self.plan_type}"')

        if self.plan_iterations != 5:
            params.append(f"plan_iterations={self.plan_iterations}")

        if self.human_input:
            params.append("human_input=True")

        if self.default:
            params.append("default=True")

        return "@fast.orchestrator(\n    " + ",\n    ".join(params) + "\n)"


@dataclass
class EvaluatorOptimizer:
    """Represents an evaluator-optimizer workflow."""

    name: str
    generator: str
    evaluator: str
    min_rating: Union[str, float]
    max_refinements: int = 3
    include_request: bool = True
    instruction: Optional[str] = None
    default: bool = False

    def to_decorator_string(self) -> str:
        """Generate the @fast.evaluator_optimizer decorator string."""
        params = [f'name="{self.name}"']

        params.append(f'generator="{self.generator}"')
        params.append(f'evaluator="{self.evaluator}"')

        if isinstance(self.min_rating, str):
            params.append(f'min_rating="{self.min_rating}"')
        else:
            params.append(f'min_rating={self.min_rating}')

        if self.max_refinements != 3:
            params.append(f"max_refinements={self.max_refinements}")

        if not self.include_request:
            params.append("include_request=False")

        if self.instruction:
            # Escape quotes in the instruction to prevent breaking the decorator
            escaped_instruction = self.instruction.replace('"""', '\\"""')
            params.append(f'instruction="""{escaped_instruction}"""')

        if self.default:
            params.append("default=True")

        return "@fast.evaluator_optimizer(\n    " + ",\n    ".join(params) + "\n)"


@dataclass
class SecretValue:
    """Represents a secret with an inline value."""

    name: str
    value: str


@dataclass
class SecretContext:
    """Represents a secret context that contains multiple key-value pairs."""

    name: str
    values: Dict[str, str] = field(default_factory=dict)


# Type alias for secrets that can be strings, values, or contexts
SecretType = Union[str, SecretValue, SecretContext]


@dataclass
class DockerfileInstruction:
    """Represents a Dockerfile instruction."""

    instruction: str
    args: List[str]

    def to_dockerfile_line(self) -> str:
        """Convert to Dockerfile line format."""
        if self.instruction in ["CMD", "ENTRYPOINT"]:
            # Always use array format for CMD/ENTRYPOINT for consistency
            args_str = json.dumps(self.args)
            return f"{self.instruction} {args_str}"
        return f"{self.instruction} {' '.join(self.args)}"


@dataclass
class AgentfileConfig:
    """Represents the complete Agentfile configuration."""

    base_image: str = "ghcr.io/o3-cloud/agentman/base:main"
    default_model: Optional[str] = None
    framework: str = "fast-agent"  # "fast-agent" or "agno"
    servers: Dict[str, MCPServer] = field(default_factory=dict)
    agents: Dict[str, Agent] = field(default_factory=dict)
    routers: Dict[str, Router] = field(default_factory=dict)
    chains: Dict[str, Chain] = field(default_factory=dict)
    parallels: Dict[str, Parallel] = field(default_factory=dict)
    orchestrators: Dict[str, Orchestrator] = field(default_factory=dict)
    evaluator_optimizers: Dict[str, EvaluatorOptimizer] = field(default_factory=dict)
    secrets: List[SecretType] = field(default_factory=list)
    expose_ports: List[int] = field(default_factory=list)
    cmd: List[str] = field(default_factory=lambda: ["python", "agent.py"])
    entrypoint: List[str] = field(default_factory=list)
    dockerfile_instructions: List[DockerfileInstruction] = field(default_factory=list)
