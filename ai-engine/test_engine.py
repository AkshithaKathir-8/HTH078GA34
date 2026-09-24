import json
from dotenv import load_dotenv

from engine import analyze_dataset


load_dotenv()


result = analyze_dataset(
    file_path="test_data/sales.csv",
    question="Which product has the highest total sales?"
)


print("\n" + "=" * 60)
print("DATA DETECTIVE AI - TEST RESULT")
print("=" * 60)

print("\nANSWER:")
print(result["answer"])

print("\nEXPLANATION:")
for item in result["explanation"]:
    print(f"- {item}")

print("\nOPERATION:")
print(json.dumps(result["operation"], indent=2))

print("\nRESULT:")
print(json.dumps(result["result"], indent=2))

print("\nCHART:")
print(json.dumps(result["chart"], indent=2))

print("\nSUCCESS:")
print(result["success"])

print("\n" + "=" * 60)