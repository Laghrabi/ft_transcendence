import csv
from django.http import HttpResponse


def summary_to_csv(summary):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="analytics-summary.csv"'
    writer = csv.writer(response)
    writer.writerow(["metric", "value"])
    
    return response