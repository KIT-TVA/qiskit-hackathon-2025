import csv
import os

def get_transpiled_data(file_path):
    """
    Returns the transpiled data from the CSV file in transpiled_data/{circuit_class_dir}/{filename}.csv
    With rows: combination, [...quality variables], elapsed_time
    Returns list with the following structure:
    [
        [filename, combination, depth, size, cnot_count],
        [filename, combination, depth, size, cnot_count],
        ...
    ]
    """
    data = []
    with open(file_path, mode='r') as transpiled_file:
        transpiled_reader = csv.reader(transpiled_file)
        for row in transpiled_reader:
            # combinations, depth, (width), size, cnot_count, (t_count)
            data.append([filename, row[0], row[1], row[3], row[4]])
    
    return data                    


def get_best_combinations(data):
    """
    Sorts the data by depth, size, and cnot_count in descending order.
    """
    sorted_data = sorted(data, key=lambda x: (x[2], x[3], x[4]))
    return sorted_data

# Save the sorted data to a CSV file
# Training data csv layout: id, depth, width, size, cnot_count, t_count, combination
def save_sorted_data_to_csv(sorted_data, filename='training_data.csv', amount=10):
    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        for data in sorted_data[:amount]:
            # Assuming data is structured as [filename, depth, size, cnot_count, combination]
            writer.writerow([data[0], *data[2:], data[1]])

for circuit_class_dir in os.listdir('./transpiled_data'):
    if not os.path.isdir(f'./transpiled_data/{circuit_class_dir}'):
        continue

    for filename in os.listdir(f'./transpiled_data/{circuit_class_dir}'):
        if not filename.endswith('.csv'):
            continue

        file_path = f'./transpiled_data/{circuit_class_dir}/{filename}'
        
        data = get_transpiled_data(file_path)

        sorted_data = get_best_combinations(data)

        save_sorted_data_to_csv(sorted_data, amount=10)

        print(f'Found {len(sorted_data)} combinations for {filename}')

