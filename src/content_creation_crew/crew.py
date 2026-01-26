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
import logging

logger = logging.getLogger(__name__)
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
        
        logger.info(f"[LLM_INIT] Initializing LLM for tier '{tier}' with model '{model}'")
        logger.debug(f"[LLM_INIT] Content types requested: {content_types}")
        logger.debug(f"[LLM_INIT] Tier config loaded: {bool(self.tier_config)}")
        
        # Initialize the LLM with tier-appropriate model
        # Phase 1: Optimize for speed - lower temperature = faster, more deterministic responses
        tier_config = self.tier_config.get(tier, {})
        # Phase 1: Use 0.2 temperature for all tiers for faster, consistent generation
        temperature = 0.2  # Unified temperature for all tiers
        
        # Get LLM provider configuration
        from .config import config
        use_openai = bool(config.OPENAI_API_KEY)
        ollama_base_url = config.OLLAMA_BASE_URL if not use_openai else None
        
        logger.info(f"[LLM_INIT] Using provider: {'OpenAI' if use_openai else 'Ollama'}")
        if not use_openai:
            logger.debug(f"[LLM_INIT] Ollama base URL: {ollama_base_url}")
        else:
            logger.debug(f"[LLM_INIT] OpenAI API key configured (length: {len(config.OPENAI_API_KEY) if config.OPENAI_API_KEY else 0})")
        
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
        
        logger.info(f"[LLM_INIT] LLM Configuration: model={model}, temperature={temperature}, max_tokens={max_tokens}, timeout=180s, provider={'OpenAI' if use_openai else 'Ollama'}")
        
        # Build LLM initialization kwargs
        # CrewAI's LLM class expects parameters directly, not wrapped in a 'config' dict
        llm_kwargs = {
            "model": model,
            "temperature": temperature,  # Lower temperature for faster execution
            "max_tokens": max_tokens,  # Reduced token limits for faster generation
            # Timeout parameters are handled via environment variables and litellm settings
            # Don't pass 'config' parameter as it's not supported by CrewAI's LLM class
        }
        
        # Only add base_url for Ollama models (OpenAI doesn't need it)
        if not use_openai and ollama_base_url:
            llm_kwargs["base_url"] = ollama_base_url
        
        # Validate configuration before LLM initialization
        if use_openai and not config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required for OpenAI models but is not set. Please set OPENAI_API_KEY in backend environment variables.")
        
        if not use_openai and not ollama_base_url:
            raise ValueError("OLLAMA_BASE_URL is required for Ollama models but is not set. Please set OLLAMA_BASE_URL or OPENAI_API_KEY in backend environment variables.")
        
        # Initialize LLM with error handling
        try:
            # Use print() for Railway visibility
            print(f"[RAILWAY_DEBUG] Initializing LLM with kwargs: model={model}, temperature={temperature}, max_tokens={max_tokens}", file=sys.stdout, flush=True)
            self.llm = LLM(**llm_kwargs)
            print(f"[RAILWAY_DEBUG] LLM instance created successfully", file=sys.stdout, flush=True)
            logger.info(f"[LLM_INIT] LLM instance created successfully for model '{model}' using {'OpenAI' if use_openai else 'Ollama'}")
        except Exception as llm_error:
            error_type = type(llm_error).__name__
            error_msg = str(llm_error)
            
            # Provide more specific error messages
            if use_openai:
                if 'api key' in error_msg.lower() or 'authentication' in error_msg.lower():
                    raise ValueError(f"OpenAI API authentication failed: {error_msg}. Please verify OPENAI_API_KEY is correct and has proper permissions.") from llm_error
                elif 'invalid' in error_msg.lower() or 'not found' in error_msg.lower():
                    raise ValueError(f"Invalid OpenAI model or configuration: {error_msg}. Model '{model}' may not be available or API key may be invalid.") from llm_error
                else:
                    raise ValueError(f"OpenAI LLM initialization failed: {error_msg}") from llm_error
            else:
                if 'connection' in error_msg.lower() or 'connect' in error_msg.lower():
                    raise ValueError(f"Ollama connection failed: {error_msg}. Please ensure Ollama is running at {ollama_base_url} and model '{model}' is available.") from llm_error
                elif 'not found' in error_msg.lower() or 'model' in error_msg.lower():
                    raise ValueError(f"Ollama model not found: {error_msg}. Please ensure model '{model}' is pulled: ollama pull {model}") from llm_error
                else:
                    raise ValueError(f"Ollama LLM initialization failed: {error_msg}") from llm_error
    
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
        Defaults to gpt-4o-mini for all tiers (can be overridden in tiers.yaml)
        """
        tier_config = self.tier_config.get(tier, {})
        
        # Default model map - using gpt-4o-mini for all tiers
        # Can be overridden in tiers.yaml for tier-specific models
        model_map = {
            'free': 'gpt-4o-mini',      # Fast, cost-effective model for free tier
            'basic': 'gpt-4o-mini',     # Fast, cost-effective model for basic tier
            'pro': 'gpt-4o-mini',       # Fast, cost-effective model for pro tier
            'enterprise': 'gpt-4o-mini' # Fast, cost-effective model for enterprise tier
            # Note: Can use 'gpt-4o' for enterprise tier if better quality is needed
        }
        
        # Check tier config first, then fall back to model_map, then default
        model = tier_config.get('model') or model_map.get(tier, 'gpt-4o-mini')
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
        agent = Agent(
            config=self.agents_config['researcher'],
            llm=self.llm,
            verbose=False  # Reduced verbosity for faster execution
        )
        logger.debug(f"[AGENT_CREATE] Researcher agent created with LLM model '{self.llm.model}'")
        return agent

    @agent
    def writer(self) -> Agent:
        agent = Agent(
            config=self.agents_config['writer'],
            llm=self.llm,
            verbose=False  # Reduced verbosity for faster execution
        )
        logger.debug(f"[AGENT_CREATE] Writer agent created with LLM model '{self.llm.model}'")
        return agent

    @agent
    def editor(self) -> Agent:
        agent = Agent(
            config=self.agents_config['editor'],
            llm=self.llm,
            verbose=False  # Reduced verbosity for faster execution
        )
        logger.debug(f"[AGENT_CREATE] Editor agent created with LLM model '{self.llm.model}'")
        return agent

    @agent
    def social_media_specialist(self) -> Agent:
        agent = Agent(
            config=self.agents_config['social_media_specialist'],
            llm=self.llm,
            verbose=False  # Reduced verbosity for faster execution
        )
        logger.debug(f"[AGENT_CREATE] Social media specialist agent created with LLM model '{self.llm.model}'")
        return agent

    @agent
    def audio_content_specialist(self) -> Agent:
        agent = Agent(
            config=self.agents_config['audio_content_specialist'],
            llm=self.llm,
            verbose=False  # Reduced verbosity for faster execution
        )
        logger.debug(f"[AGENT_CREATE] Audio content specialist agent created with LLM model '{self.llm.model}'")
        return agent

    @agent
    def video_content_specialist(self) -> Agent:
        agent = Agent(
            config=self.agents_config['video_content_specialist'],
            llm=self.llm,
            verbose=False  # Reduced verbosity for faster execution
        )
        logger.debug(f"[AGENT_CREATE] Video content specialist agent created with LLM model '{self.llm.model}'")
        return agent

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
        
        logger.info(f"[CREW_BUILD] Building crew with {len(agents)} agents and {len(tasks)} tasks")
        logger.debug(f"[CREW_BUILD] Agents: {[agent.role if hasattr(agent, 'role') else 'unknown' for agent in agents]}")
        logger.debug(f"[CREW_BUILD] Tasks: {[task.description[:50] if hasattr(task, 'description') else 'unknown' for task in tasks]}")
        logger.info(f"[CREW_BUILD] Process type: {process}")
        
        # Use print() for Railway visibility
        import sys
        print(f"[RAILWAY_DEBUG] Building Crew with process={process}, manager_llm={'SET' if self.llm else 'NOT SET'}", file=sys.stdout, flush=True)
        
        crew = Crew(
            agents=agents,  # Manually collected agents
            tasks=tasks,  # Only include requested tasks
            process=process,
            manager_llm=self.llm,  # Required for hierarchical process
            verbose=False,  # Reduced verbosity for faster execution
        )
        
        print(f"[RAILWAY_DEBUG] Crew built successfully", file=sys.stdout, flush=True)
        logger.info(f"[CREW_BUILD] Crew built successfully")
        return crew
    
    @crew
    def crew(self) -> Crew:
        """
        Creates the ContentCreationCrew crew (default implementation).
        For custom content types, use _build_crew() method directly.
        """
        return self._build_crew()
