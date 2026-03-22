#!/usr/bin/env python
# Legacy Python 2 / old Python 3 code — demo sample

import os, sys, time, datetime

DB_FILE = "records.dat"
LOG_FILE = "app.log"

def log_message(msg):
    f = open(LOG_FILE, 'a')
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    f.write("[%s] %s\n" % (ts, msg))
    f.close()

def read_records():
    records = []
    if not os.path.exists(DB_FILE):
        log_message("Database file not found: " + DB_FILE)
        return records
    f = open(DB_FILE, 'r')
    lines = f.readlines()
    f.close()
    for line in lines:
        line = line.strip()
        if line != "":
            parts = line.split(",")
            record = {}
            record['id'] = int(parts[0])
            record['name'] = parts[1]
            record['score'] = float(parts[2])
            records.append(record)
    return records

def get_top_scorers(records, n):
    sorted_records = []
    for i in range(len(records)):
        for j in range(i + 1, len(records)):
            if records[j]['score'] > records[i]['score']:
                tmp = records[i]
                records[i] = records[j]
                records[j] = tmp
    for i in range(n):
        if i < len(records):
            sorted_records.append(records[i])
    return sorted_records

def calculate_stats(records):
    if len(records) == 0:
        return None
    total = 0
    minimum = records[0]['score']
    maximum = records[0]['score']
    for r in records:
        total = total + r['score']
        if r['score'] < minimum:
            minimum = r['score']
        if r['score'] > maximum:
            maximum = r['score']
    avg = total / len(records)
    stats = {}
    stats['count'] = len(records)
    stats['total'] = total
    stats['average'] = avg
    stats['min'] = minimum
    stats['max'] = maximum
    return stats

def save_report(stats, top_list):
    report_path = "report_" + str(int(time.time())) + ".txt"
    f = open(report_path, 'w')
    f.write("=== SCORE REPORT ===\n")
    f.write("Count   : %d\n" % stats['count'])
    f.write("Average : %.2f\n" % stats['average'])
    f.write("Min     : %.2f\n" % stats['min'])
    f.write("Max     : %.2f\n" % stats['max'])
    f.write("\nTop Scorers:\n")
    for i in range(len(top_list)):
        r = top_list[i]
        f.write("  %d. %s => %.2f\n" % (i + 1, r['name'], r['score']))
    f.close()
    log_message("Report saved: " + report_path)
    return report_path

class ReportManager:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.reports = []

    def add_report(self, path):
        self.reports.append(path)
        print "Added report: " + path   # Python 2 print

    def list_reports(self):
        print "All reports:"
        for r in self.reports:
            print "  - " + r

    def get_count(self):
        return len(self.reports)

if __name__ == "__main__":
    log_message("Application started")
    records = read_records()
    if len(records) == 0:
        print "No records found."
        sys.exit(1)
    stats = calculate_stats(records)
    top = get_top_scorers(records, 5)
    path = save_report(stats, top)
    print "Report generated: " + path
    manager = ReportManager("./outputs")
    manager.add_report(path)
    manager.list_reports()
    log_message("Application finished")
