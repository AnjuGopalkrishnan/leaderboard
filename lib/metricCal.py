import psycopg2
from psycopg2.extras import DictCursor
from time import time


def get_query_performance(query):
    conn = psycopg2.connect(
        host="localhost",
        database="leaderboard",
        user="postgres",
        password=""
    )
    cur = conn.cursor(cursor_factory=DictCursor)

    start_time = time()
    cur.execute(f"EXPLAIN ANALYZE {query}")
    rows = cur.fetchall()
    end_time = time()

    performance = {}

    for row in rows:
        if row['QUERY PLAN'].startswith('Execution Time:'):
            performance['execution_time'] = float(row['QUERY PLAN'].split(':')[-1].replace(' ms', ''))
        elif row['QUERY PLAN'].startswith('Planning Time:'):
            performance['planning_time'] = float(row['QUERY PLAN'].split(':')[-1].replace(' ms', ''))
        elif row['QUERY PLAN'].startswith('Plan Rows:'):
            performance['query_complexity'] = float(row['QUERY PLAN'].split(' ')[-1])

    performance['query_time'] = performance.get('execution_time', 0) + performance.get('planning_time',0)
    performance['total_time'] = end_time - start_time

    return performance


def get_query_complexity(query):
    keywords = ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'HAVING', 'ORDER BY', 'LIMIT', 'OFFSET']
    operators = ['=', '<>', '>', '<', '>=', '<=', 'AND', 'OR', 'NOT', 'IN', 'LIKE']

    words = query.split()

    keyword_count = sum(word.upper() in keywords for word in words)
    operator_count = sum(word.upper() in operators for word in words)

    identifier_count = len(words) - keyword_count - operator_count

    return {"keyword_count": keyword_count, "operator_count": operator_count, "identifier_count": identifier_count}


def get_query_score(query):
    max_time = 2000
    performanceMetrics = get_query_performance(query)
    norm_execution_time = int(1000*performanceMetrics['execution_time'])
    norm_planning_time = int(1000*performanceMetrics['planning_time'])

    score = 100 - (norm_execution_time + norm_planning_time) / max_time * 100
    return score

