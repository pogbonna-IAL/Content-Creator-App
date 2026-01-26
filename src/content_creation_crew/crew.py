# Windows signal compatibility patch (runs before crewai imports)
import sys
if sys.platform == 'win32':
    import signal
    for sig_name, sig_value in [('SIGHUP', 1), ('SIGTSTP', 20), ('SIGCONT', 18), 
                                  ('SIGQUIT', 3), ('SIGUSR1', 10), ('SIGUSR2', 12)]:
        if not hasattr(signal, sig_name):
            setattr(signal, sig_name, sig_value)

from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
from crewai import LLM
# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

@CrewBase
class ContentCreationCrew():
    """ContentCreationCrew crew"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def __init__(self, tier: str = 'free', content_types: List[str] = None) -> None:
        import os
        import yaml
        from pathlib import Path
        
        # Set LiteLLM timeout to 3 minutes (180 seconds) for Phase 1 speed optimization
        # Phase 1: Reduced from 1800s to 180s to match CREWAI_TIMEOUT and prevent hanging
        # These must be set before importing/using LiteLLM
        os.environ['LITELLM_REQUEST_TIMEOUT'] = '180'
        os.environ['LITELLM_TIMEOUT'] = '180'
        os.environ['LITELLM_CONNECTION_TIMEOUT'] = '60'  # Faster connection timeout
        
        # Also try setting via litellm if available
        try:
            import litellm
            # Set timeout in litellm settings
            litellm.request_timeout = 180
            litellm.timeout = 180
            litellm.drop_params = True  # Don't drop timeout params
            
            # Configure httpx timeout for Ollama connections
            # Phase 1: Reduced timeout for faster failure detection
            try:
                import httpx
                # Set environment variable for httpx default timeout
                os.environ['HTTPX_DEFAULT_TIMEOUT'] = '180'
            except (ImportError, AttributeError):
                pass
        except ImportError:
            pass
        
        # Load tier configuration and select model based on tier
        self.tier = tier
        self.content_types = content_types or []
        self.tier_config = self._load_tier_config()
        model = self._get_model_for_tier(tier)
        
        # Initialize the LLM with tier-appropriate model
        # Phase 1: Optimize for speed - lower temperature = faster, more deterministic responses
        tier_config = self.tier_config.get(tier, {})
        # Phase 1: Use 0.2 temperature for all tiers for faster, consistent generation
        temperature = 0.2  # Unified temperature for all tiers
        
        # Get Ollama base URL from config
        from .config import config
        ollama_base_url = config.OLLAMA_BASE_URL
        
        # Phase 1: Reduce max_tokens by 25% for faster generation while maintaining quality
        # Original limits: free=2000, basic=3000, pro=4000, enterprise=6000
        # New limits: free=1500, basic=2250, pro=3000, enterprise=4500
        max_tokens_map = {
            'free': 1500,      # Reduced from 2000 (25% reduction)
            'basic': 2250,     # Reduced from 3000 (25% reduction)
            'pro': 3000,       # Reduced from 4000 (25% reduction)
            'enterprise': 4500 # Reduced from 6000 (25% reduction)
        }
        max_tokens = max_tokens_map.get(tier, 1500)
        
        self.llm = LLM(
            model=model,
            base_url=ollama_base_url,
            temperature=temperature,  # Lower temperature for faster execution
            # Phase 1: Reduced timeouts to match CREWAI_TIMEOUT (180s)
            config={
                "timeout": 180.0,  # Total timeout in seconds (reduced from 1800)
                "request_timeout": 180.0,  # Request timeout (reduced from 1800)
                "connection_timeout": 30.0,  # Connection timeout (reduced from 60)
                "temperature": temperature,  # Also set in config for compatibility
                "max_tokens": max_tokens,  # Reduced token limits for faster generation
            }
        )
    
    def _load_tier_config(self) -> dict:
        """Load tier configuration from YAML file"""
        import yaml
        from pathlib import Path
        try:
            config_path = Path(__file__).parent / "config" / "tiers.yaml"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    return config.get('tiers', {})
        except Exception:
            pass
        return {}
    
    def _get_model_for_tier(self, tier: str) -> str:
        """
        Get appropriate LLM model for subscription tier
        Phase 1: Use smaller, faster models for free tier to improve speed
        """
        tier_config = self.tier_config.get(tier, {})
        
        # Phase 1: Use smaller models for free tier, keep larger models for paid tiers
        # This improves speed for free tier while maintaining quality for paid users
        model_map = {
            'free': 'ollama/llama3.2:1b',      # Smallest, fastest model for free tier
            'basic': 'ollama/llama3.2:3b',     # Medium model for basic tier
            'pro': 'ollama/llama3.2:3b',       # Medium model for pro tier
            'enterprise': 'ollama/llama3.1:8b' # Larger model for enterprise tier
        }
        
        # Check tier config first, then fall back to model_map, then default
        model = tier_config.get('model') or model_map.get(tier, 'ollama/llama3.2:1b')
        return model
    
    def _get_max_parallel_tasks(self) -> int:
        """Get maximum parallel tasks for current tier"""
        tier_config = self.tier_config.get(self.tier, {})
        return tier_config.get('max_parallel_tasks', 1)

    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    
    # If you would like to add tools to your agents, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools
    @agent
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config['researcher'],
            llm=self.llm,
            verbose=False  # Reduced verbosity for faster execution
        )

    @agent
    def writer(self) -> Agent:
        return Agent(
            config=self.agents_config['writer'],
            llm=self.llm,
            verbose=False  # Reduced verbosity for faster execution
        )

    @agent
    def editor(self) -> Agent:
        return Agent(
            config=self.agents_config['editor'],
            llm=self.llm,
            verbose=False  # Reduced verbosity for faster execution
        )

    @agent
    def social_media_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config['social_media_specialist'],
            llm=self.llm,
            verbose=False  # Reduced verbosity for faster execution
        )

    @agent
    def audio_content_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config['audio_content_specialist'],
            llm=self.llm,
            verbose=False  # Reduced verbosity for faster execution
        )

    @agent
    def video_content_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config['video_content_specialist'],
            llm=self.llm,
            verbose=False  # Reduced verbosity for faster execution
        )

    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
    @task
    def research_task(self) -> Task:
        return Task(
            config=self.tasks_config['research_task'],
            agent=self.researcher()
        )

    @task
    def writing_task(self) -> Task:
        return Task(
            config=self.tasks_config['writing_task'],
            agent=self.writer(),
            context=[self.research_task()]
        )

    @task
    def editing_task(self) -> Task:
        return Task(
            config=self.tasks_config['editing_task'],
            agent=self.editor(),
            context=[self.writing_task()],
            output_file='content_output.md'  # Save final output to markdown file
        )

    @task
    def social_media_task(self) -> Task:
        return Task(
            config=self.tasks_config['social_media_task'],
            agent=self.social_media_specialist(),
            context=[self.editing_task()],  # Branch from editing task
            output_file='social_media_output.md'  # Save social media content to separate file
        )

    @task
    def audio_content_task(self) -> Task:
        return Task(
            config=self.tasks_config['audio_content_task'],
            agent=self.audio_content_specialist(),
            context=[self.editing_task()],  # Branch from editing task
            output_file='audio_output.md'  # Save audio content to separate file
        )

    @task
    def video_content_task(self) -> Task:
        return Task(
            config=self.tasks_config['video_content_task'],
            agent=self.video_content_specialist(),
            context=[self.editing_task()],  # Branch from editing task
            output_file='video_output.md'  # Save video content to separate file
        )

    def _build_crew(self, content_types: List[str] = None) -> Crew:
        """
        Builds the ContentCreationCrew crew with conditional task execution
        based on tier and requested content types.
        
        Args:
            content_types: List of content types to generate ('blog', 'social', 'audio', 'video')
                         If None, uses tier defaults from configuration
        """
        # Determine which content types to generate
        if content_types is None:
            content_types = self.content_types
        
        # If no content types specified, use tier defaults
        if not content_types:
            tier_config = self.tier_config.get(self.tier, {})
            content_types = tier_config.get('content_types', ['blog'])
        
        # Collect agents manually (since we're not using @crew decorator)
        # CrewBase creates agents from @agent decorated methods
        agents = [
            self.researcher(),
            self.writer(),
            self.editor(),
        ]
        
        # Add optional agents based on content types
        if 'social' in content_types:
            agents.append(self.social_media_specialist())
        if 'audio' in content_types:
            agents.append(self.audio_content_specialist())
        if 'video' in content_types:
            agents.append(self.video_content_specialist())
        
        # Build task list based on content types
        tasks = []
        
        # Core tasks (always included)
        tasks.append(self.research_task())
        tasks.append(self.writing_task())
        tasks.append(self.editing_task())
        
        # Optional tasks based on content types
        # These can run in parallel after editing_task completes
        optional_tasks = []
        
        if 'social' in content_types:
            optional_tasks.append(self.social_media_task())
        if 'audio' in content_types:
            optional_tasks.append(self.audio_content_task())
        if 'video' in content_types:
            optional_tasks.append(self.video_content_task())
        
        tasks.extend(optional_tasks)
        
        # Phase 1: Always use hierarchical process for better parallel execution
        # This allows optional tasks to run in parallel after editing_task completes
        # Improves overall generation speed without quality impact
        process = Process.hierarchical
        
        return Crew(
            agents=agents,  # Manually collected agents
            tasks=tasks,  # Only include requested tasks
            process=process,
            verbose=False,  # Reduced verbosity for faster execution
        )
    
    @crew
    def crew(self) -> Crew:
        """
        Creates the ContentCreationCrew crew (default implementation).
        For custom content types, use _build_crew() method directly.
        """
        return self._build_crew()
