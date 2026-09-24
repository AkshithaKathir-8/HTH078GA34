import pandas as pd

from insight_engine import generate_insights
file_path = "..\\testdata\\anomaly_test.csv"

df = pd.read_csv(file_path)

print("\nDATASET")
print("--------------------")
print(df)

result = generate_insights(df)


print("\n🔍 DATA DETECTIVE REPORT")
print("========================")


print("\n🔴 ANOMALIES")
print("------------------------")

if result["anomalies"]:
    for item in result["anomalies"]:
        print("•", item["message"])
else:
    print("No unusual values detected.")


print("\n💡 PATTERNS")
print("------------------------")

if result["patterns"]:
    for item in result["patterns"]:
        print("•", item["message"])
else:
    print("No strong relationships detected.")


print("\n📈 TRENDS")
print("------------------------")

if result["trends"]:
    for item in result["trends"]:
        print("•", item["message"])
else:
    print("No significant trends detected.")


print("\n❓ FOLLOW-UP QUESTIONS")
print("------------------------")

for question in result["follow_up_questions"]:
    print("•", question)