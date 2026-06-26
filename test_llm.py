from utils.llm import generate_text

prompt = """
Write two sentences summarizing a magnitude 6.2 earthquake
in California for an emergency management report.
"""

response = generate_text(prompt)

print(response)