from engine import analyze_dataset


DATASET = "test_data/sales.csv"


questions = [
    "Are there any duplicate records?",
    "Are there any unusual sales values?",
    "What patterns do you see in the data?",
    "What recommendations can you give to improve sales?",
]


for question in questions:

    print("\n" + "=" * 70)
    print("QUESTION:")
    print(question)
    print("=" * 70)

    result = analyze_dataset(
        file_path=DATASET,
        question=question,
        api_key=None,
    )

    print("\nANSWER:")
    print(result.get("answer"))

    print("\nEXPLANATION:")
    for item in result.get("explanation", []):
        print("-", item)

    print("\nOPERATION:")
    print(result.get("operation"))

    print("\nRESULT:")
    print(result.get("result"))

    print("\nSUCCESS:")
    print(result.get("success"))