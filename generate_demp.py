import pandas as pd

data = [
    {"name": "John Doe", "email": "john.doe@example.com"},
    {"name": "Mary Smith", "email": "mary.smith@example.com"},
    {"name": "Ahmed Ali", "email": "ahmed.ali@example.com"},
]

df = pd.DataFrame(data)
df.to_excel("students.xlsx", index=False)
print("✅ students.xlsx created!")
