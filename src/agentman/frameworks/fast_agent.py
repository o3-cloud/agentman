"""Fast-Agent framework implementation for AgentMan."""

from typing import List

import yaml

from .base import BaseFramework


class FastAgentFramework(BaseFramework):
    """Framework implementation for Fast-Agent."""

    def build_agent_content(self) -> str:
        """Build the Python agent file content for Fast-Agent framework."""
        lines = []

        # Imports
        lines.extend(
            [
                "import asyncio",
                "from mcp_agent.core.fastagent import FastAgent",
                "",
                "# Create the application",
                'fast = FastAgent("Generated by Agentman")',
                "",
            ]
        )

        # Agent definitions
        for agent in self.config.agents.values():
            lines.append(agent.to_decorator_string(self.config.default_model))

        # Router definitions
        for router in self.config.routers.values():
            lines.append(router.to_decorator_string(self.config.default_model))

        # Chain definitions
        for chain in self.config.chains.values():
            lines.append(chain.to_decorator_string())

        # Orchestrator definitions
        for orchestrator in self.config.orchestrators.values():
            lines.append(orchestrator.to_decorator_string(self.config.default_model))

        # Main function
        lines.extend(
            [
                "async def main() -> None:",
                "    async with fast.run() as agent:",
            ]
        )

        # Check if prompt.txt exists and add prompt loading
        if self.has_prompt_file:
            lines.extend(
                [
                    "        # Check if prompt.txt exists and load its content",
                    "        import os",
                    "        prompt_file = 'prompt.txt'",
                    "        if os.path.exists(prompt_file):",
                    "            with open(prompt_file, 'r', encoding='utf-8') as f:",
                    "                prompt_content = f.read().strip()",
                    "            if prompt_content:",
                    "                await agent(prompt_content)",
                    "            else:",
                    "                await agent()",
                    "        else:",
                    "            await agent()",
                ]
            )
        else:
            lines.extend(["        await agent()"])

        lines.extend(
            [
                "",
                "",
                'if __name__ == "__main__":',
                "    asyncio.run(main())",
            ]
        )

        return "\n".join(lines)

    def get_requirements(self) -> List[str]:
        """Get requirements for Fast-Agent framework."""
        requirements = [
            "fast-agent-mcp>=0.2.33",
            "deprecated>=1.2.18",
        ]

        # Add additional requirements based on servers used
        server_requirements = {
            "fetch": [],
            "filesystem": [],
            "brave": [],
            "postgres": [],
            "sqlite": [],
        }

        for server_name in self.config.servers.keys():
            if server_name in server_requirements:
                requirements.extend(server_requirements[server_name])

        return requirements

    def generate_config_files(self) -> None:
        """Generate Fast-Agent specific configuration files."""
        self._ensure_output_dir()
        self._generate_config_yaml()
        self._generate_secrets_yaml()

    def _generate_config_yaml(self):
        """Generate the fastagent.config.yaml file."""
        config_data = {
            "default_model": self.config.default_model or "haiku",
            "logger": {
                "level": "info",
                "progress_display": True,
                "show_chat": True,
                "show_tools": True,
                "truncate_tools": True,
            },
        }

        if self.config.servers:
            config_data["mcp"] = {
                "servers": {name: server.to_config_dict() for name, server in self.config.servers.items()}
            }

        config_file = self.output_dir / "fastagent.config.yaml"
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

    def _generate_secrets_yaml(self):
        """Generate the fastagent.secrets.yaml template file."""
        secrets_data = {}
        mcp_servers_env = {}

        # Process secrets based on their type
        for secret in self.config.secrets:
            if isinstance(secret, str):
                # Simple secret reference
                self._process_simple_secret(secret, secrets_data, mcp_servers_env)
            elif hasattr(secret, 'value'):
                # SecretValue with inline value
                self._process_secret_value(secret, secrets_data, mcp_servers_env)
            elif hasattr(secret, 'values'):
                # SecretContext with multiple key-value pairs
                self._process_secret_context(secret, secrets_data)

        # Add MCP servers environment if any
        if mcp_servers_env:
            secrets_data["mcp"] = {"servers": mcp_servers_env}

        secrets_file = self.output_dir / "fastagent.secrets.yaml"
        with open(secrets_file, 'w', encoding='utf-8') as f:
            f.write("# FastAgent Secrets Configuration\n")
            f.write("# WARNING: Keep this file secure and never commit to version control\n\n")
            f.write(
                "# Alternatively set OPENAI_API_KEY and ANTHROPIC_API_KEY "
                "environment variables. Config file takes precedence.\n\n"
            )
            yaml.dump(secrets_data, f, default_flow_style=False, sort_keys=False)

    def _process_simple_secret(self, secret: str, secrets_data: dict, mcp_servers_env: dict):
        """Process a simple secret reference."""
        if secret == "OPENAI_API_KEY":
            if "openai" not in secrets_data:
                secrets_data["openai"] = {}
            secrets_data["openai"]["api_key"] = "<your-api-key-here>"
        elif secret == "ANTHROPIC_API_KEY":
            if "anthropic" not in secrets_data:
                secrets_data["anthropic"] = {}
            secrets_data["anthropic"]["api_key"] = "<your-api-key-here>"
        elif secret == "AZURE_OPENAI_API_KEY":
            if "azure" not in secrets_data:
                secrets_data["azure"] = {}
            secrets_data["azure"]["api_key"] = "<your-azure-api-key-here>"
        elif secret == "ALIYUN_API_KEY":
            if "aliyun" not in secrets_data:
                secrets_data["aliyun"] = {}
            secrets_data["aliyun"]["api_key"] = "<your-aliyun-api-key-here>"
        else:
            # Handle server-specific environment variables
            server_found = False
            for server_name, server in self.config.servers.items():
                if hasattr(server, 'env') and server.env and secret in server.env:
                    if server_name not in mcp_servers_env:
                        mcp_servers_env[server_name] = {"env": {}}
                    mcp_servers_env[server_name]["env"][secret] = f"<your_{secret.lower()}_here>"
                    server_found = True
                    break

            if not server_found:
                # Generic environment variable
                if "environment" not in mcp_servers_env:
                    mcp_servers_env["environment"] = {"env": {}}
                mcp_servers_env["environment"]["env"][secret] = f"<your_{secret.lower()}_here>"

    def _process_secret_value(self, secret, secrets_data: dict, mcp_servers_env: dict):
        """Process a secret with an inline value."""
        secret_name = secret.name
        secret_value = secret.value

        if secret_name == "OPENAI_API_KEY":
            if "openai" not in secrets_data:
                secrets_data["openai"] = {}
            secrets_data["openai"]["api_key"] = secret_value
        elif secret_name == "ANTHROPIC_API_KEY":
            if "anthropic" not in secrets_data:
                secrets_data["anthropic"] = {}
            secrets_data["anthropic"]["api_key"] = secret_value
        elif secret_name == "AZURE_OPENAI_API_KEY":
            if "azure" not in secrets_data:
                secrets_data["azure"] = {}
            secrets_data["azure"]["api_key"] = secret_value
        elif secret_name == "ALIYUN_API_KEY":
            if "aliyun" not in secrets_data:
                secrets_data["aliyun"] = {}
            secrets_data["aliyun"]["api_key"] = secret_value
        else:
            # Handle server-specific environment variables
            server_found = False
            for server_name, server in self.config.servers.items():
                if hasattr(server, 'env') and server.env and secret_name in server.env:
                    if server_name not in mcp_servers_env:
                        mcp_servers_env[server_name] = {"env": {}}
                    mcp_servers_env[server_name]["env"][secret_name] = secret_value
                    server_found = True
                    break

            if not server_found:
                # Generic environment variable
                if "environment" not in mcp_servers_env:
                    mcp_servers_env["environment"] = {"env": {}}
                mcp_servers_env["environment"]["env"][secret_name] = secret_value

    def _process_secret_context(self, secret, secrets_data: dict):
        """Process a secret context with multiple key-value pairs."""
        context_name = secret.name.lower()

        if context_name not in secrets_data:
            secrets_data[context_name] = {}

        for key, value in secret.values.items():
            secrets_data[context_name][key.lower()] = value

    def get_dockerfile_config_lines(self) -> List[str]:
        """Get Fast-Agent specific Dockerfile configuration lines."""
        return [
            "COPY fastagent.config.yaml .",
            "COPY fastagent.secrets.yaml .",
        ]
