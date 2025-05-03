import pandas as pd
from faker import Faker
import random

fake = Faker()

# Define number of rows
num_rows = 100

# Define data generation
data = {
    "Name": [fake.name() for _ in range(num_rows)],
    "Email": [fake.email() for _ in range(num_rows)],
    "Phone": [fake.phone_number() for _ in range(num_rows)],
    "Address": [fake.address().replace("\n", ", ") for _ in range(num_rows)],
    "DateOfBirth": [fake.date_of_birth(minimum_age=18, maximum_age=65).isoformat() for _ in range(num_rows)],
    "Salary": [round(random.uniform(30000, 120000), 2) for _ in range(num_rows)],
    "Department": [random.choice(['HR', 'Engineering', 'Marketing', 'Sales', 'Finance']) for _ in range(num_rows)]
}

# Create DataFrame
df = pd.DataFrame(data)

# Save to CSV
df.to_csv("random_dataset.csv", index=False)

print("CSV file 'random_dataset.csv' generated with 1000 rows.")
