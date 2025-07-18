"""
Unit tests for agent_builder module.

Tests cover all aspects of the AgentBuilder including:
- Basic builder functionality
- File generation (Python, YAML, Dockerfile, etc.)
- Output directory management
- Configuration handling
- Secret processing
- Integration with AgentfileConfig
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest
import yaml

from agentman.agent_builder import AgentBuilder, build_from_agentfile
from agentman.agentfile_parser import (
    Agent,
    AgentfileConfig,
    Chain,
    MCPServer,
    Orchestrator,
    Router,
    SecretContext,
    SecretValue,
)


class TestAgentBuilder:
    """Test suite for AgentBuilder class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = AgentfileConfig()
        self.config.base_image = "yeahdongcn/agentman-base:latest"
        self.config.default_model = "generic.qwen3:latest"
        self.config.cmd = ["python", "agent.py"]

    def test_init_default_output(self):
        """Test builder initialization with default output directory."""
        builder = AgentBuilder(self.config)
        assert builder.config == self.config
        assert builder.output_dir == Path("output")

    def test_init_custom_output(self):
        """Test builder initialization with custom output directory."""
        builder = AgentBuilder(self.config, "custom_output")
        assert builder.config == self.config
        assert builder.output_dir == Path("custom_output")

    def test_ensure_output_dir(self):
        """Test output directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_output"
            builder = AgentBuilder(self.config, str(output_path))

            # Directory should not exist initially
            assert not output_path.exists()

            builder._ensure_output_dir()

            # Directory should exist after calling _ensure_output_dir
            assert output_path.exists()
            assert output_path.is_dir()

    def test_build_python_content_basic(self):
        """Test basic Python content generation."""
        builder = AgentBuilder(self.config)
        content = builder.framework.build_agent_content()

        expected_lines = [
            "import asyncio",
            "from mcp_agent.core.fastagent import FastAgent",
            "",
            "# Create the application",
            'fast = FastAgent("Generated by Agentman")',
            "",
            "async def main() -> None:",
            "    async with fast.run() as agent:",
            "        await agent()",
            "",
            "",
            'if __name__ == "__main__":',
            "    asyncio.run(main())",
        ]

        for line in expected_lines:
            assert line in content

    def test_build_python_content_with_agents(self):
        """Test Python content generation with agents."""
        # Add an agent to the config
        agent = Agent("test_agent")
        agent.instruction = "You are a test assistant"
        agent.servers = ["test_server"]
        self.config.agents["test_agent"] = agent

        builder = AgentBuilder(self.config)
        content = builder.framework.build_agent_content()

        # Should contain agent decorator
        assert "@fast.agent" in content
        assert "test_agent" in content

    def test_build_python_content_with_chains(self):
        """Test Python content generation with chains."""
        # Add a chain to the config
        chain = Chain("test_chain")
        chain.sequence = ["agent1", "agent2"]
        self.config.chains["test_chain"] = chain

        builder = AgentBuilder(self.config)
        content = builder.framework.build_agent_content()

        # Should contain chain decorator
        assert "@fast.chain" in content
        assert "test_chain" in content

    def test_build_python_content_with_routers(self):
        """Test Python content generation with routers."""
        # Add a router to the config
        router = Router("test_router")
        router.agents = ["agent1", "agent2"]
        self.config.routers["test_router"] = router

        builder = AgentBuilder(self.config)
        content = builder.framework.build_agent_content()

        # Should contain router decorator
        assert "@fast.router" in content
        assert "test_router" in content

    def test_build_python_content_with_orchestrators(self):
        """Test Python content generation with orchestrators."""
        # Add an orchestrator to the config
        orchestrator = Orchestrator("test_orchestrator")
        orchestrator.agents = ["agent1", "agent2"]
        self.config.orchestrators["test_orchestrator"] = orchestrator

        builder = AgentBuilder(self.config)
        content = builder.framework.build_agent_content()

        # Should contain orchestrator decorator
        assert "@fast.orchestrator" in content
        assert "test_orchestrator" in content

    def test_generate_config_yaml_basic(self):
        """Test basic config YAML generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            builder = AgentBuilder(self.config, temp_dir)
            builder._generate_config_yaml()

            config_file = Path(temp_dir) / "fastagent.config.yaml"
            assert config_file.exists()

            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)

            assert config_data["default_model"] == "generic.qwen3:latest"
            assert "logger" in config_data
            assert config_data["logger"]["level"] == "info"

    def test_generate_config_yaml_with_servers(self):
        """Test config YAML generation with MCP servers."""
        # Add a server to the config
        server = MCPServer("test_server")
        server.command = "uvx"
        server.args = ["mcp-server-test"]
        server.transport = "stdio"
        self.config.servers["test_server"] = server

        with tempfile.TemporaryDirectory() as temp_dir:
            builder = AgentBuilder(self.config, temp_dir)
            builder._generate_config_yaml()

            config_file = Path(temp_dir) / "fastagent.config.yaml"
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)

            assert "mcp" in config_data
            assert "servers" in config_data["mcp"]
            assert "test_server" in config_data["mcp"]["servers"]

    def test_generate_secrets_yaml_simple(self):
        """Test secrets YAML generation with simple secrets."""
        self.config.secrets = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]

        with tempfile.TemporaryDirectory() as temp_dir:
            builder = AgentBuilder(self.config, temp_dir)
            builder.framework.generate_config_files()

            secrets_file = Path(temp_dir) / "fastagent.secrets.yaml"
            assert secrets_file.exists()

            with open(secrets_file, 'r') as f:
                content = f.read()
                # Skip comments to get to YAML content
                yaml_content = []
                for line in content.split('\n'):
                    if not line.startswith('#') and line.strip():
                        yaml_content.append(line)

                if yaml_content:
                    secrets_data = yaml.safe_load('\n'.join(yaml_content))
                    assert "openai" in secrets_data
                    assert "anthropic" in secrets_data

    def test_generate_secrets_yaml_with_values(self):
        """Test secrets YAML generation with secret values."""
        secret_value = SecretValue("TEST_KEY", "test_value")
        self.config.secrets = [secret_value]

        with tempfile.TemporaryDirectory() as temp_dir:
            builder = AgentBuilder(self.config, temp_dir)
            builder.framework.generate_config_files()

            secrets_file = Path(temp_dir) / "fastagent.secrets.yaml"
            assert secrets_file.exists()

    def test_generate_secrets_yaml_with_context(self):
        """Test secrets YAML generation with secret context."""
        secret_context = SecretContext("GENERIC")
        secret_context.values = {"API_KEY": "test_key", "BASE_URL": "http://localhost"}
        self.config.secrets = [secret_context]

        with tempfile.TemporaryDirectory() as temp_dir:
            builder = AgentBuilder(self.config, temp_dir)
            builder.framework.generate_config_files()

            secrets_file = Path(temp_dir) / "fastagent.secrets.yaml"
            assert secrets_file.exists()

            with open(secrets_file, 'r') as f:
                content = f.read()
                # Should contain the context name
                assert "generic" in content.lower()

    # Note: _process_* methods are now internal to framework handlers
    # and tested through integration tests

    def test_generate_dockerfile_custom_base(self):
        """Test Dockerfile generation with custom base image."""
        with tempfile.TemporaryDirectory() as temp_dir:
            builder = AgentBuilder(self.config, temp_dir)
            builder._generate_dockerfile()

            dockerfile = Path(temp_dir) / "Dockerfile"
            assert dockerfile.exists()

            with open(dockerfile, 'r') as f:
                content = f.read()

            assert "FROM yeahdongcn/agentman-base:latest" in content
            assert "WORKDIR /app" in content
            assert 'CMD ["python", "agent.py"]' in content

    def test_generate_dockerfile_with_expose(self):
        """Test Dockerfile generation with exposed ports."""
        self.config.expose_ports = [8000, 8080]

        with tempfile.TemporaryDirectory() as temp_dir:
            builder = AgentBuilder(self.config, temp_dir)
            builder._generate_dockerfile()

            dockerfile = Path(temp_dir) / "Dockerfile"
            with open(dockerfile, 'r') as f:
                content = f.read()

            assert "EXPOSE 8000" in content
            assert "EXPOSE 8080" in content

    def test_generate_dockerfile_fast_agent_base(self):
        """Test Dockerfile generation with yeahdongcn/agentman-base:latest base."""
        self.config.base_image = "yeahdongcn/agentman-base:latest"

        with tempfile.TemporaryDirectory() as temp_dir:
            builder = AgentBuilder(self.config, temp_dir)
            builder._generate_dockerfile()

            dockerfile = Path(temp_dir) / "Dockerfile"
            with open(dockerfile, 'r') as f:
                content = f.read()

            assert "FROM yeahdongcn/agentman-base:latest" in content
            assert "COPY agent.py" in content
            assert "RUN pip install" in content

    def test_generate_requirements_txt_basic(self):
        """Test basic requirements.txt generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            builder = AgentBuilder(self.config, temp_dir)
            builder._generate_requirements_txt()

            req_file = Path(temp_dir) / "requirements.txt"
            assert req_file.exists()

            with open(req_file, 'r') as f:
                content = f.read()

            assert "fast-agent-mcp" in content
            assert "deprecated" in content

    def test_generate_requirements_txt_with_servers(self):
        """Test requirements.txt generation with server dependencies."""
        # Add servers that require additional packages
        server1 = MCPServer("fetch")
        server2 = MCPServer("postgres")
        self.config.servers["fetch"] = server1
        self.config.servers["postgres"] = server2

        with tempfile.TemporaryDirectory() as temp_dir:
            builder = AgentBuilder(self.config, temp_dir)
            builder._generate_requirements_txt()

            req_file = Path(temp_dir) / "requirements.txt"
            with open(req_file, 'r') as f:
                content = f.read()

            # FIXME: Adjust these assertions based on actual server requirements
            assert "requests" not in content
            assert "psycopg2-binary" not in content

    def test_generate_dockerignore(self):
        """Test .dockerignore generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            builder = AgentBuilder(self.config, temp_dir)
            builder._generate_dockerignore()

            dockerignore = Path(temp_dir) / ".dockerignore"
            assert dockerignore.exists()

            with open(dockerignore, 'r') as f:
                content = f.read()

            assert "__pycache__/" in content
            assert "*.py[cod]" in content
            assert ".git/" in content
            assert ".DS_Store" in content

    def test_generate_python_agent_file_creation(self):
        """Test that Python agent file is created."""
        with tempfile.TemporaryDirectory() as temp_dir:
            builder = AgentBuilder(self.config, temp_dir)
            builder._generate_python_agent()

            agent_file = Path(temp_dir) / "agent.py"
            assert agent_file.exists()

            with open(agent_file, 'r') as f:
                content = f.read()

            assert "import asyncio" in content
            assert "FastAgent" in content

    def test_build_all(self):
        """Test building all files at once."""
        with tempfile.TemporaryDirectory() as temp_dir:
            builder = AgentBuilder(self.config, temp_dir)
            builder.build_all()

            # Check that all expected files are created
            expected_files = [
                "agent.py",
                "fastagent.config.yaml",
                "fastagent.secrets.yaml",
                "Dockerfile",
                "requirements.txt",
                ".dockerignore",
            ]

            for filename in expected_files:
                file_path = Path(temp_dir) / filename
                assert file_path.exists(), f"File {filename} was not created"

    @patch('agentman.agent_builder.parse_agentfile')
    def test_build_from_agentfile(self, mock_parse_agentfile):
        """Test building from Agentfile function."""
        # Mock the parser function and its behavior
        mock_parse_agentfile.return_value = self.config

        with tempfile.TemporaryDirectory() as temp_dir:
            # Call the function
            build_from_agentfile("test_agentfile", temp_dir)

            # Verify parser was called correctly
            mock_parse_agentfile.assert_called_once_with("test_agentfile")

            # Check that files were created
            expected_files = [
                "agent.py",
                "fastagent.config.yaml",
                "fastagent.secrets.yaml",
                "Dockerfile",
                "requirements.txt",
                ".dockerignore",
            ]

            for filename in expected_files:
                file_path = Path(temp_dir) / filename
                assert file_path.exists(), f"File {filename} was not created"

    def test_build_from_agentfile_default_output(self):
        """Test building from Agentfile with default output directory."""
        with patch('agentman.agent_builder.parse_agentfile') as mock_parse_agentfile:
            mock_parse_agentfile.return_value = self.config

            # Mock the AgentBuilder.build_all method to avoid actual file creation
            with patch.object(AgentBuilder, 'build_all') as mock_build_all:
                build_from_agentfile("test_agentfile")

                # Verify the builder was created with default output
                mock_build_all.assert_called_once()

    def test_complex_configuration(self):
        """Test builder with complex configuration including all components."""
        # Set up complex configuration
        self.config.default_model = "anthropic/claude-3-sonnet"
        self.config.expose_ports = [8000, 9000]

        # Add server
        server = MCPServer("test_server")
        server.command = "uvx"
        server.args = ["mcp-server-test"]
        server.transport = "stdio"
        self.config.servers["test_server"] = server

        # Add agent
        agent = Agent("test_agent")
        agent.instruction = "You are a test assistant"
        agent.servers = ["test_server"]
        self.config.agents["test_agent"] = agent

        # Add chain
        chain = Chain("test_chain")
        chain.sequence = ["test_agent", "other_agent"]
        self.config.chains["test_chain"] = chain

        # Add secrets
        self.config.secrets = ["OPENAI_API_KEY", SecretValue("CUSTOM_KEY", "value")]

        with tempfile.TemporaryDirectory() as temp_dir:
            builder = AgentBuilder(self.config, temp_dir)
            builder.build_all()

            # Verify all files are created and contain expected content
            agent_file = Path(temp_dir) / "agent.py"
            with open(agent_file, 'r') as f:
                agent_content = f.read()
            assert "test_agent" in agent_content
            assert "test_chain" in agent_content

            config_file = Path(temp_dir) / "fastagent.config.yaml"
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)
            assert config_data["default_model"] == "anthropic/claude-3-sonnet"
            assert "test_server" in config_data["mcp"]["servers"]

            dockerfile = Path(temp_dir) / "Dockerfile"
            with open(dockerfile, 'r') as f:
                dockerfile_content = f.read()
            assert "EXPOSE 8000" in dockerfile_content
            assert "EXPOSE 9000" in dockerfile_content


class TestAgentBuilderEdgeCases:
    """Test edge cases and error conditions for AgentBuilder."""

    def test_empty_config(self):
        """Test builder with minimal empty configuration."""
        config = AgentfileConfig()
        builder = AgentBuilder(config)

        with tempfile.TemporaryDirectory() as temp_dir:
            builder.output_dir = Path(temp_dir)
            builder.build_all()

            # Should still create all files even with empty config
            expected_files = [
                "agent.py",
                "fastagent.config.yaml",
                "fastagent.secrets.yaml",
                "Dockerfile",
                "requirements.txt",
                ".dockerignore",
            ]

            for filename in expected_files:
                file_path = Path(temp_dir) / filename
                assert file_path.exists()

    def test_no_default_model(self):
        """Test builder behavior when no default model is specified."""
        config = AgentfileConfig()
        config.default_model = None
        builder = AgentBuilder(config)

        with tempfile.TemporaryDirectory() as temp_dir:
            builder.output_dir = Path(temp_dir)
            builder._generate_config_yaml()

            config_file = Path(temp_dir) / "fastagent.config.yaml"
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)

            # Should default to "haiku"
            assert config_data["default_model"] == "haiku"

    def test_server_with_env_variables(self):
        """Test server configuration with environment variables."""
        config = AgentfileConfig()

        # Create server with env variables
        server = MCPServer("test_server")
        server.env = ["TEST_VAR1", "TEST_VAR2"]
        config.servers["test_server"] = server
        config.secrets = ["TEST_VAR1"]

        builder = AgentBuilder(config)

        with tempfile.TemporaryDirectory() as temp_dir:
            builder.output_dir = Path(temp_dir)
            builder.framework.generate_config_files()

            secrets_file = Path(temp_dir) / "fastagent.secrets.yaml"
            assert secrets_file.exists()


if __name__ == "__main__":
    pytest.main([__file__])
