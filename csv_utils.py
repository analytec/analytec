import csv

def csv_to_list(filename):
    results = []
    with open(filename) as csvfile:
        filereader = csv.reader(csvfile)
        for row in filereader:
            results.append(row)
    return [element[0] for element in results]
