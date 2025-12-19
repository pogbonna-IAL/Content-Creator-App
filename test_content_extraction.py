#!/usr/bin/env python
"""Test script to verify content extraction works correctly"""
import sys
from pathlib import Path

sys.path.insert(0, 'src')
from content_creation_crew.crew import ContentCreationCrew

# Test with a simple topic
topic = "Benefits of exercise"
print(f"Testing content generation for topic: {topic}")
print("=" * 60)

crew = ContentCreationCrew()
result = crew.crew().kickoff(inputs={'topic': topic})

print(f"\nResult type: {type(result)}")
print(f"Result attributes: {[attr for attr in dir(result) if not attr.startswith('_')]}")

# Check tasks_output
if hasattr(result, 'tasks_output'):
    print(f"\nTasks output count: {len(result.tasks_output) if result.tasks_output else 0}")
    if result.tasks_output:
        last_task = result.tasks_output[-1]
        print(f"Last task type: {type(last_task)}")
        print(f"Last task attributes: {[attr for attr in dir(last_task) if not attr.startswith('_')]}")
        if hasattr(last_task, 'raw'):
            print(f"Last task raw type: {type(last_task.raw)}")
            print(f"Last task raw preview: {str(last_task.raw)[:200]}")

# Check file
output_file = Path("content_output.md")
if output_file.exists():
    print(f"\n✓ content_output.md exists")
    content = output_file.read_text(encoding='utf-8')
    print(f"File length: {len(content)}")
    if "---" in content:
        parts = content.split("---", 1)
        extracted = parts[1].strip() if len(parts) > 1 else ""
        print(f"Extracted content length: {len(extracted)}")
        print(f"Extracted preview: {extracted[:200]}")
    else:
        print(f"File preview: {content[:200]}")

print("\n" + "=" * 60)
print("Test complete!")

