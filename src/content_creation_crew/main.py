#!/usr/bin/env python
# Windows signal compatibility patch (runs before any imports)
import sys
from pathlib import Path
from datetime import datetime
if sys.platform == 'win32':
    import signal
    for sig_name, sig_value in [('SIGHUP', 1), ('SIGTSTP', 20), ('SIGCONT', 18), 
                                  ('SIGQUIT', 3), ('SIGUSR1', 10), ('SIGUSR2', 12)]:
        if not hasattr(signal, sig_name):
            setattr(signal, sig_name, sig_value)

# Import the package __init__ first to ensure its patch runs
import content_creation_crew  # noqa: F401

from content_creation_crew.crew import ContentCreationCrew

def run():
    """
    Run the crew with a specific topic.
    """
    print("Welcome to the Content Creation Crew!")
    print("This crew will help you create comprehensive blog posts on any topic.")
    print()
    
    topic = input("Enter the topic you want to create content about: ")
    
    if not topic.strip():
        print("Please provide a valid topic.")
        return
    
    print(f"\nCreating content about: {topic}")
    print("This may take a few minutes as the agents collaborate...")
    print("-" * 50)
    
    inputs = {
        'topic': topic
    }
    
    try:
        result = ContentCreationCrew().crew().kickoff(inputs=inputs)
        
        # Save output to markdown file
        output_file = Path("content_output.md")
        output_content = f"# Content Creation: {topic}\n\n"
        output_content += f"**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        output_content += "---\n\n"
        output_content += str(result)
        
        output_file.write_text(output_content, encoding='utf-8')
        
        print("\n" + "="*50)
        print("FINAL RESULT:")
        print("="*50)
        print(result)
        print("\n" + "="*50)
        print(f"✓ Content saved to: {output_file.absolute()}")
        print("="*50)
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Make sure Ollama is running and the llama3.2:1b model is available.")
        print("Try running: ollama list")
        print("If llama3.2:1b is not listed, run: ollama pull llama3.2:1b")

def train():
    """
    Train the crew for a given number of iterations.
    """
    topic = input("Enter the topic for training: ")
    
    inputs = {
        'topic': topic
    }
    try:
        ContentCreationCrew().crew().train(n_iterations=int(sys.argv[1]), inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        ContentCreationCrew().crew().replay(task_id=sys.argv[1])
    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the results.
    """
    topic = input("Enter the topic for testing: ")
    
    inputs = {
        'topic': topic
    }
    try:
        ContentCreationCrew().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)
    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")

def run_with_trigger():
    """
    Run the crew with trigger payload.
    """
    import json
    
    if len(sys.argv) < 2:
        raise Exception("No trigger payload provided. Please provide JSON payload as argument.")
    
    try:
        trigger_payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        raise Exception("Invalid JSON payload provided as argument")
    
    inputs = {
        "crewai_trigger_payload": trigger_payload,
        "topic": trigger_payload.get("topic", ""),
    }
    
    try:
        result = ContentCreationCrew().crew().kickoff(inputs=inputs)
        return result
    except Exception as e:
        raise Exception(f"An error occurred while running the crew with trigger: {e}")

if __name__ == "__main__":
    run()
